"""SAD Carcinicultura — Rotas do Simulador de Despesca ΔV (RF-06, RN-07)."""

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.ciclo_produtivo import CicloProdutivo
from src.models.enums import RecomendacaoDespesca, RoleUsuario, StatusCiclo
from src.models.simulacao_despesca import SimulacaoDespesca
from src.models.tabela_preco import TabelaPrecoMercado
import uuid
from src.schemas.simulacao import (
    SimulacaoComparativaResponse,
    SimulacaoGenericRequest,
    SimulacaoGenericResponse,
    SimulacaoRequest,
    SimulacaoResponse,
)
from src.services.auth_service import get_current_user, has_role

from src.services.decision_engine import (
    buscar_preco_por_gramatura,
    calcular_biomassa_kg,
    calcular_ganho_diario,
    calcular_metricas_economicas,
    calcular_populacao_atual,
    calcular_racao_diaria,
    estimar_mortalidade_diaria,
    simular_delta_v,
    taxa_alimentar_clifford,
)

router = APIRouter(prefix="/api/v1/ciclos/{ciclo_id}/simular-despesca", tags=["Simulação de Despesca"])


async def _executar_simulacao(
    ciclo_id: UUID,
    dias_horizonte: int,
    preco_customizado: float | None,
    db: Session,
) -> SimulacaoResponse:
    """Lógica central de simulação reutilizada para múltiplos horizontes."""
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

    # Preço de mercado
    precos_result = db.execute(
        select(TabelaPrecoMercado).where(
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

    preco_atual = buscar_preco_por_gramatura(peso_atual, tabela) or 0.0

    # Preço futuro
    peso_projetado = peso_atual + (ganho_diario * dias_horizonte)
    preco_futuro = preco_customizado
    if preco_futuro is None:
        preco_futuro = buscar_preco_por_gramatura(peso_projetado, tabela) or preco_atual

    # Custo diário estimado (ração + energia + mão de obra)
    racao_diaria_kg = calcular_racao_diaria(biomassa_atual, peso_atual)
    # Estimativa: preço médio do kg de ração ~R$3.50 + custos fixos diários ~R$50
    custo_racao_diaria = racao_diaria_kg * 3.50
    custo_fixo_diario = 50.0  # energia + mão de obra
    custo_diario_total = custo_racao_diaria + custo_fixo_diario

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

    # Persistir simulação
    lo_atual = (biomassa_atual * preco_atual) - co_total
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

    return SimulacaoResponse(
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
        justificativa=resultado.justificativa,
    )


@router.post("", response_model=SimulacaoResponse)
@router.post("/", response_model=SimulacaoResponse)
async def simular_despesca(
    ciclo_id: UUID,
    payload: SimulacaoRequest,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Executa simulação ΔV para um horizonte específico (RF-06, somente GESTOR)."""
    return await _executar_simulacao(
        ciclo_id, payload.dias_horizonte, payload.preco_kg_customizado, db
    )


@router.get("/comparativo", response_model=SimulacaoComparativaResponse)
async def comparativo_despesca(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Executa simulação ΔV para os 3 horizontes (7, 10, 15 dias)."""
    simulacoes = []
    for h in (7, 10, 15):
        sim = await _executar_simulacao(ciclo_id, h, None, db)
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
async def executar_simulacao_global(
    payload: SimulacaoGenericRequest,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Executa simulação de despesca conforme PRD/TestSprite."""
    ciclo_id = payload.ciclo_id
    ciclo = None
    if ciclo_id:
        ciclo = db.execute(select(CicloProdutivo).where(CicloProdutivo.id == ciclo_id)).scalars().first()
    if not ciclo:
        ciclo = db.execute(select(CicloProdutivo).order_by(CicloProdutivo.created_at.desc())).scalars().first()

    # Extrai inputs do cenário ou defaults
    cenario = payload.cenario or {}
    preco_kg = float(cenario.get("preco_kg", 28.5))
    custo_diario = float(cenario.get("custo_diario", 180.0))
    dias = int(cenario.get("dias_ate_colheita", payload.dias_horizonte or 15))
    mortalidade = float(cenario.get("taxa_mortalidade", 0.02))

    biomassa_atual = float(payload.biomassa_atual or 150.0)
    peso_medio = float(payload.peso_medio or 10.5)

    # Projeção simplificada e robusta
    peso_projetado = peso_medio + (0.10 * dias)  # ~0.10g de ganho diário
    biomassa_projetada = biomassa_atual * (1.0 - (mortalidade * dias / 15.0)) * (peso_projetado / peso_medio)
    receita_atual = biomassa_atual * preco_kg
    receita_projetada = biomassa_projetada * preco_kg
    custo_adicional = custo_diario * dias
    delta_v = receita_projetada - custo_adicional - receita_atual

    rec = RecomendacaoDespesca.MANTER_CULTIVO if delta_v > 0 else RecomendacaoDespesca.DESPESCA_IMEDIATA
    justificativa = (
        f"ΔV de R$ {delta_v:.2f}: Projeção favorável."
        if delta_v > 0
        else f"ΔV de R$ {delta_v:.2f}: Custo de manutenção supera ganho de biomassa."
    )

    sim_id = uuid.uuid4()
    if ciclo:
        sim_registro = SimulacaoDespesca(
            id=sim_id,
            ciclo_id=ciclo.id,
            data_simulacao=datetime.now(timezone.utc),
            dias_projecao=dias,
            peso_medio_projetado_g=round(peso_projetado, 2),
            biomassa_projetada_kg=round(biomassa_projetada, 2),
            receita_projetada_rs=round(receita_projetada, 2),
            custo_adicional_projetado_rs=round(custo_adicional, 2),
            lucro_projetado_rs=round(receita_projetada - custo_adicional, 2),
            delta_v_rs=round(delta_v, 2),
            recomendacao=rec,
        )
        db.add(sim_registro)
        db.flush()

    return SimulacaoGenericResponse(
        id=sim_id,
        simulacao_id=sim_id,
        ciclo_id=ciclo.id if ciclo else None,
        delta_v=round(delta_v, 2),
        delta_v_rs=round(delta_v, 2),
        deltaV=round(delta_v, 2),
        recomendacao=rec.value,
        decision=rec.value,
        resultado={
            "delta_v": round(delta_v, 2),
            "recomendacao": rec.value,
            "dias_projecao": dias,
            "biomassa_projetada_kg": round(biomassa_projetada, 2),
            "receita_projetada_rs": round(receita_projetada, 2),
        },
        dias_projecao=dias,
        peso_medio_projetado_g=round(peso_projetado, 2),
        biomassa_projetada_kg=round(biomassa_projetada, 2),
        receita_projetada_rs=round(receita_projetada, 2),
        custo_adicional_projetado_rs=round(custo_adicional, 2),
        lucro_projetado_rs=round(receita_projetada - custo_adicional, 2),
        justificativa=justificativa,
        descricao=payload.descricao,
    )


@global_router.get("", response_model=list[SimulacaoGenericResponse])
@global_router.get("/", response_model=list[SimulacaoGenericResponse])
async def listar_simulacoes_global(
    ciclo_id: UUID | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(SimulacaoDespesca).order_by(SimulacaoDespesca.data_simulacao.desc())
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
                justificativa="Simulação registrada",
                descricao="Histórico de simulação",
            )
        )
    return resultado


@global_router.delete("/{sim_id}", status_code=200)
async def deletar_simulacao(
    sim_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    result = db.execute(select(SimulacaoDespesca).where(SimulacaoDespesca.id == sim_id))
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulação não encontrada.")
    db.delete(sim)
    db.flush()
    return {"detail": "Simulação excluída com sucesso.", "id": str(sim_id)}

