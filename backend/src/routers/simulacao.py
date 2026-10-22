"""SAD Carcinicultura — Rotas do Simulador de Despesca ΔV (RF-06, RN-07)."""

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.escopo import (
    ciclo_da_organizacao,
    ids_ciclos_da_organizacao,
    verificar_ciclo_da_organizacao,
)
from src.services.audit import registrar_auditoria, snapshot
from src.models.ciclo_produtivo import CicloProdutivo
from src.models.enums import CategoriaCusto, RoleUsuario, StatusCiclo
from src.models.simulacao_despesca import SimulacaoDespesca
from src.models.tabela_preco import TabelaPrecoMercado
from src.schemas.simulacao import (
    SimulacaoComparativaResponse,
    SimulacaoGenericRequest,
    SimulacaoGenericResponse,
    SimulacaoRequest,
    SimulacaoResponse,
)
from src.services.auth_service import has_role

from src.services.decision_engine import (
    buscar_preco_por_gramatura,
    calcular_biomassa_kg,
    calcular_ganho_diario,
    calcular_populacao_atual,
    estimar_mortalidade_diaria,
    simular_delta_v,
)

router = APIRouter(
    prefix="/api/v1/ciclos/{ciclo_id}/simular-despesca",
    tags=["Simulação de Despesca"],
    dependencies=[Depends(verificar_ciclo_da_organizacao)],
)


AVISO_APOIO_DECISAO = (
    "Resultado de apoio à decisão: não substitui a avaliação técnica do gestor (RN-012)."
)


def _executar_simulacao(
    ciclo_id: UUID,
    dias_horizonte: int,
    preco_customizado: float | None,
    db: Session,
    custo_diario_customizado: float | None = None,
    persistir: bool = True,
) -> SimulacaoResponse:
    """Lógica central de simulação reutilizada para múltiplos horizontes.

    Sem dados suficientes (preço vigente para a gramatura atual ou base para o
    custo diário) a simulação é recusada com a entrada faltante (RN-015).
    """
    result = db.execute(select(CicloProdutivo).where(CicloProdutivo.id == ciclo_id))
    ciclo = result.scalar_one_or_none()
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo não encontrado.")
    if ciclo.status != StatusCiclo.ATIVO:
        raise HTTPException(status_code=400, detail="Ciclo não está ativo.")

    hoje = date.today()
    dias_cultivo = (hoje - ciclo.data_povoamento).days

    # Biometrias
    biometrias = sorted(ciclo.biometrias, key=lambda b: b.data_medicao)
    if not biometrias:
        raise HTTPException(status_code=400, detail="Nenhuma biometria registrada. Impossível simular.")

    peso_atual = biometrias[-1].peso_medio_g

    # Ganho diário
    ganho_diario = 0.0
    if len(biometrias) >= 2:
        b1, b2 = biometrias[-2], biometrias[-1]
        dias_entre = (b2.data_medicao - b1.data_medicao).days
        if dias_entre > 0:
            ganho_diario = calcular_ganho_diario(b1.peso_medio_g, b2.peso_medio_g, dias_entre)

    # Sobrevivência fuzzy
    manejos = sorted(ciclo.manejos_alimentares, key=lambda m: m.data_registro)
    taxa_sobrev = 100.0
    for m in manejos:
        if m.taxa_sobrevivencia_estimada_fuzzy is not None:
            taxa_sobrev = m.taxa_sobrevivencia_estimada_fuzzy

    pop_atual = calcular_populacao_atual(ciclo.quantidade_pos_larvas, taxa_sobrev)
    biomassa_atual = calcular_biomassa_kg(pop_atual, peso_atual)
    mortalidade_diaria = estimar_mortalidade_diaria(taxa_sobrev, dias_cultivo)

    # Custos
    custos_vals = [float(c.valor_rs) for c in ciclo.custos_operacionais]
    co_total = sum(custos_vals)
    premissas: list[str] = []

    # Preço de mercado
    precos_result = db.execute(
        select(TabelaPrecoMercado).where(
            TabelaPrecoMercado.organizacao_id == ciclo.viveiro.organizacao_id,
            TabelaPrecoMercado.vigencia_inicio <= hoje,
            (TabelaPrecoMercado.vigencia_fim.is_(None))
            | (TabelaPrecoMercado.vigencia_fim >= hoje),
        )
    )
    tabela = [
        {
            "faixa_gramatura_min": p.faixa_gramatura_min,
            "faixa_gramatura_max": p.faixa_gramatura_max,
            "preco_por_kg": float(p.preco_por_kg),
        }
        for p in precos_result.scalars().all()
    ]

    preco_atual = buscar_preco_por_gramatura(peso_atual, tabela)
    if preco_atual is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Sem preço de mercado vigente para a gramatura atual ({peso_atual:.1f} g). "
                "Cadastre a faixa na tabela de preços para simular."
            ),
        )

    # Preço futuro
    peso_projetado = peso_atual + (ganho_diario * dias_horizonte)
    preco_futuro = preco_customizado
    if preco_futuro is not None:
        premissas.append(f"Preço futuro informado pelo usuário: R$ {preco_futuro:,.2f}/kg.")
    else:
        preco_futuro = buscar_preco_por_gramatura(peso_projetado, tabela)
        if preco_futuro is None:
            preco_futuro = preco_atual
            premissas.append(
                f"Sem faixa de preço para {peso_projetado:.1f} g; usado o preço atual "
                f"(R$ {preco_atual:,.2f}/kg)."
            )

    # Custo diário: informado pelo usuário ou média dos custos lançados (exceto PLs)
    if custo_diario_customizado is not None:
        custo_diario_total = custo_diario_customizado
        premissas.append(f"Custo diário informado pelo usuário: R$ {custo_diario_total:,.2f}.")
    else:
        custos_recorrentes = sum(
            float(c.valor_rs)
            for c in ciclo.custos_operacionais
            if c.categoria != CategoriaCusto.POS_LARVAS
        )
        if custos_recorrentes <= 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Sem custos operacionais lançados (além das pós-larvas) para estimar o custo "
                    "diário. Lance os custos do ciclo ou informe custo_diario_rs."
                ),
            )
        custo_diario_total = custos_recorrentes / max(dias_cultivo, 1)
        premissas.append(
            f"Custo diário estimado pela média dos custos lançados: R$ {custo_diario_total:,.2f} "
            f"em {max(dias_cultivo, 1)} dias de cultivo."
        )
    if len(biometrias) < 2:
        premissas.append("Apenas uma biometria: ganho de peso projetado é zero.")

    # Executar simulação
    resultado = simular_delta_v(
        dias_horizonte=dias_horizonte,
        peso_medio_atual_g=peso_atual,
        ganho_diario_g=ganho_diario,
        populacao_atual=pop_atual,
        mortalidade_diaria_pct=mortalidade_diaria,
        custo_operacional_total=co_total,
        preco_atual_kg=preco_atual,
        preco_futuro_kg=preco_futuro,
        custo_diario_racao_energia=custo_diario_total,
        biomassa_atual_kg=biomassa_atual,
    )

    lo_atual = (biomassa_atual * preco_atual) - co_total
    simulacao_id = None
    if persistir:
        simulacao_id = _persistir(db, ciclo_id, dias_horizonte, resultado)

    return SimulacaoResponse(
        simulacao_id=simulacao_id,
        ciclo_id=ciclo_id,
        data_referencia=hoje,
        peso_medio_atual_g=peso_atual,
        biomassa_atual_kg=round(biomassa_atual, 2),
        lucro_operacional_atual_rs=round(lo_atual, 2),
        dias_horizonte=dias_horizonte,
        peso_medio_projetado_g=resultado.peso_medio_projetado_g,
        biomassa_projetada_kg=resultado.biomassa_projetada_kg,
        receita_projetada_rs=resultado.receita_projetada,
        custo_adicional_projetado_rs=resultado.custo_adicional,
        lucro_projetado_rs=resultado.lucro_projetado,
        delta_v_rs=resultado.delta_v,
        recomendacao=resultado.recomendacao,
        justificativa=f"{resultado.justificativa} {AVISO_APOIO_DECISAO}",
        preco_atual_rs_kg=preco_atual,
        preco_futuro_rs_kg=preco_futuro,
        custo_diario_rs=round(custo_diario_total, 2),
        premissas=premissas,
    )


def _persistir(db: Session, ciclo_id: UUID, dias_horizonte: int, resultado) -> UUID:
    sim = SimulacaoDespesca(
        ciclo_id=ciclo_id,
        data_simulacao=datetime.now(timezone.utc),
        dias_projecao=dias_horizonte,
        peso_medio_projetado_g=resultado.peso_medio_projetado_g,
        biomassa_projetada_kg=resultado.biomassa_projetada_kg,
        receita_projetada_rs=resultado.receita_projetada,
        custo_adicional_projetado_rs=resultado.custo_adicional,
        lucro_projetado_rs=resultado.lucro_projetado,
        delta_v_rs=resultado.delta_v,
        recomendacao=resultado.recomendacao,
    )
    db.add(sim)
    db.flush()
    return sim.id


@router.post("", response_model=SimulacaoResponse)
@router.post("/", response_model=SimulacaoResponse)
def simular_despesca(
    ciclo_id: UUID,
    payload: SimulacaoRequest,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Executa simulação ΔV para um horizonte específico (RF-06, somente GESTOR)."""
    return _executar_simulacao(
        ciclo_id,
        payload.dias_horizonte,
        payload.preco_kg_customizado,
        db,
        custo_diario_customizado=payload.custo_diario_rs,
    )


@router.get("/comparativo", response_model=SimulacaoComparativaResponse)
def comparativo_despesca(
    ciclo_id: UUID,
    custo_diario_rs: float | None = Query(None, gt=0),
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Compara os horizontes de 7, 10 e 15 dias (consulta: não grava no histórico)."""
    simulacoes = []
    for h in (7, 10, 15):
        sim = _executar_simulacao(
            ciclo_id, h, None, db, custo_diario_customizado=custo_diario_rs, persistir=False
        )
        simulacoes.append(sim)

    # Melhor cenário = maior ΔV positivo
    positivos = [s for s in simulacoes if s.delta_v_rs > 0]
    melhor = max(positivos, key=lambda s: s.delta_v_rs) if positivos else None

    return SimulacaoComparativaResponse(
        simulacoes=simulacoes,
        melhor_cenario=melhor,
    )


global_router = APIRouter(prefix="/api/v1/simulacao", tags=["Simulação de Despesca"])


@global_router.post("", response_model=SimulacaoGenericResponse, status_code=200)
@global_router.post("/", response_model=SimulacaoGenericResponse, status_code=200)
def executar_simulacao_global(
    payload: SimulacaoGenericRequest,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Executa a simulação ΔV de um ciclo (mesmo cálculo da rota aninhada, somente GESTOR)."""
    ciclo_da_organizacao(db, payload.ciclo_id, _user)
    sim = _executar_simulacao(
        payload.ciclo_id,
        payload.dias_horizonte,
        payload.preco_kg_customizado,
        db,
        custo_diario_customizado=payload.custo_diario_rs,
    )
    resultado = {
        "delta_v": sim.delta_v_rs,
        "recomendacao": sim.recomendacao.value,
        "dias_projecao": sim.dias_horizonte,
        "biomassa_projetada_kg": sim.biomassa_projetada_kg,
        "receita_projetada_rs": sim.receita_projetada_rs,
    }
    return SimulacaoGenericResponse(
        id=sim.simulacao_id,
        simulacao_id=sim.simulacao_id,
        ciclo_id=sim.ciclo_id,
        delta_v=sim.delta_v_rs,
        delta_v_rs=sim.delta_v_rs,
        deltaV=sim.delta_v_rs,
        recomendacao=sim.recomendacao.value,
        decision=sim.recomendacao.value,
        resultado=resultado,
        dias_projecao=sim.dias_horizonte,
        peso_medio_projetado_g=sim.peso_medio_projetado_g,
        biomassa_projetada_kg=sim.biomassa_projetada_kg,
        receita_projetada_rs=sim.receita_projetada_rs,
        custo_adicional_projetado_rs=sim.custo_adicional_projetado_rs,
        lucro_projetado_rs=sim.lucro_projetado_rs,
        justificativa=sim.justificativa,
        descricao=payload.descricao,
    )


@global_router.get("", response_model=list[SimulacaoGenericResponse])
@global_router.get("/", response_model=list[SimulacaoGenericResponse])
def listar_simulacoes_global(
    ciclo_id: UUID | None = None,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    query = select(SimulacaoDespesca).order_by(SimulacaoDespesca.data_simulacao.desc())
    query = query.where(SimulacaoDespesca.ciclo_id.in_(ids_ciclos_da_organizacao(_user)))
    if ciclo_id:
        query = query.where(SimulacaoDespesca.ciclo_id == ciclo_id)
    sims = db.scalars(query).all()
    resultado = []
    for s in sims:
        resultado.append(
            SimulacaoGenericResponse(
                id=s.id,
                simulacao_id=s.id,
                ciclo_id=s.ciclo_id,
                delta_v=float(s.delta_v_rs),
                delta_v_rs=float(s.delta_v_rs),
                deltaV=float(s.delta_v_rs),
                recomendacao=s.recomendacao.value,
                decision=s.recomendacao.value,
                resultado={"delta_v": float(s.delta_v_rs), "recomendacao": s.recomendacao.value},
                dias_projecao=s.dias_projecao,
                peso_medio_projetado_g=float(s.peso_medio_projetado_g),
                biomassa_projetada_kg=float(s.biomassa_projetada_kg),
                receita_projetada_rs=float(s.receita_projetada_rs),
                custo_adicional_projetado_rs=float(s.custo_adicional_projetado_rs),
                lucro_projetado_rs=float(s.lucro_projetado_rs),
                justificativa="Simulação registrada no histórico.",
            )
        )
    return resultado


@global_router.delete("/{sim_id}", status_code=200)
def deletar_simulacao(
    sim_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    result = db.execute(select(SimulacaoDespesca).where(SimulacaoDespesca.id == sim_id))
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulação não encontrada.")
    ciclo_da_organizacao(db, sim.ciclo_id, _user)
    registrar_auditoria(db, "EXCLUIR", "SimulacaoDespesca", sim.id, _user, dados_anteriores=snapshot(sim))
    db.delete(sim)
    db.flush()
    return {"detail": "Simulação excluída com sucesso.", "id": str(sim_id)}

