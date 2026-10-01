"""SAD Carcinicultura — Rotas de Ciclos Produtivos (RF-02, RF-09)."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.biometria import Biometria
from src.models.ciclo_produtivo import CicloProdutivo
from src.models.custo_operacional import CustoOperacional
from src.models.enums import RoleUsuario, StatusCiclo
from src.models.manejo_alimentar import ManejoAlimentar
from src.models.tabela_preco import TabelaPrecoMercado
from src.models.viveiro import Viveiro
from src.schemas.ciclo import CicloCreate, CicloEncerrar, CicloResponse, MetricasAtuaisResponse
from src.services.auth_service import get_current_user, has_role
from src.services import decision_engine as de

router = APIRouter(prefix="/api/v1/ciclos", tags=["Ciclos Produtivos"])


@router.post("/", response_model=CicloResponse, status_code=201)
async def criar_ciclo(
    payload: CicloCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Abre um novo ciclo produtivo em um viveiro (RF-02)."""
    # Verificar viveiro
    viv_result = await db.execute(select(Viveiro).where(Viveiro.id == payload.viveiro_id))
    viveiro = viv_result.scalar_one_or_none()
    if not viveiro:
        raise HTTPException(status_code=404, detail="Viveiro não encontrado.")
    if not viveiro.status_ativo:
        raise HTTPException(status_code=400, detail="Viveiro inativo.")

    # Verificar ciclo ativo existente
    ciclo_ativo = await db.execute(
        select(CicloProdutivo).where(
            CicloProdutivo.viveiro_id == payload.viveiro_id,
            CicloProdutivo.status == StatusCiclo.ATIVO,
        )
    )
    if ciclo_ativo.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este viveiro já possui um ciclo ATIVO.",
        )

    # Verificar densidade (RN-01)
    densidade = de.calcular_densidade(payload.quantidade_pos_larvas, viveiro.area_util_m2)

    ciclo = CicloProdutivo(
        **payload.model_dump(),
        status=StatusCiclo.ATIVO,
    )
    db.add(ciclo)

    # Auto-lançar custo de PLs
    from src.models.custo_operacional import CustoOperacional
    from src.models.enums import CategoriaCusto
    custo_pl = CustoOperacional(
        ciclo_id=ciclo.id,
        data_lancamento=payload.data_povoamento,
        categoria=CategoriaCusto.POS_LARVAS,
        descricao=f"Aquisição de {payload.quantidade_pos_larvas:,} PLs",
        valor_rs=payload.custo_aquisicao_pl,
    )
    db.add(custo_pl)

    await db.flush()
    await db.refresh(ciclo)
    return ciclo


@router.get("/", response_model=list[CicloResponse])
async def listar_ciclos(
    viveiro_id: UUID | None = None,
    status_filtro: StatusCiclo | None = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Lista ciclos com filtros opcionais."""
    query = select(CicloProdutivo).order_by(CicloProdutivo.data_povoamento.desc())
    if viveiro_id:
        query = query.where(CicloProdutivo.viveiro_id == viveiro_id)
    if status_filtro:
        query = query.where(CicloProdutivo.status == status_filtro)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{ciclo_id}", response_model=CicloResponse)
async def obter_ciclo(
    ciclo_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Retorna dados de um ciclo específico."""
    result = await db.execute(select(CicloProdutivo).where(CicloProdutivo.id == ciclo_id))
    ciclo = result.scalar_one_or_none()
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo não encontrado.")
    return ciclo


@router.post("/{ciclo_id}/encerrar", response_model=CicloResponse)
async def encerrar_ciclo(
    ciclo_id: UUID,
    payload: CicloEncerrar,
    db: AsyncSession = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Encerra o ciclo com dados da despesca real (RF-02)."""
    result = await db.execute(select(CicloProdutivo).where(CicloProdutivo.id == ciclo_id))
    ciclo = result.scalar_one_or_none()
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo não encontrado.")
    if ciclo.status != StatusCiclo.ATIVO:
        raise HTTPException(status_code=400, detail="Somente ciclos ATIVOS podem ser encerrados.")

    ciclo.status = StatusCiclo.FINALIZADO
    ciclo.data_despesca_real = payload.data_despesca_real
    ciclo.biomassa_colhida_kg = payload.biomassa_colhida_kg
    ciclo.receita_real_rs = payload.receita_real_rs
    db.add(ciclo)
    await db.flush()
    await db.refresh(ciclo)
    return ciclo


@router.get("/{ciclo_id}/metricas-atuais", response_model=MetricasAtuaisResponse)
async def metricas_atuais(
    ciclo_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Retorna métricas consolidadas do ciclo (RF-09, RN-01..06)."""
    # Buscar ciclo com viveiro
    result = await db.execute(select(CicloProdutivo).where(CicloProdutivo.id == ciclo_id))
    ciclo = result.scalar_one_or_none()
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo não encontrado.")

    viveiro = ciclo.viveiro
    hoje = date.today()
    dias_cultivo = (hoje - ciclo.data_povoamento).days

    # Densidade
    densidade = de.calcular_densidade(ciclo.quantidade_pos_larvas, viveiro.area_util_m2)
    alerta_hiper = de.verificar_hiperdensidade(densidade)

    # Última biometria
    biometrias = sorted(ciclo.biometrias, key=lambda b: b.data_medicao)
    peso_medio = biometrias[-1].peso_medio_g if biometrias else 1.0

    # Sobrevivência fuzzy mais recente
    manejos = sorted(ciclo.manejos_alimentares, key=lambda m: m.data_registro)
    taxa_sobrev = 100.0
    for m in manejos:
        if m.taxa_sobrevivencia_estimada_fuzzy is not None:
            taxa_sobrev = m.taxa_sobrevivencia_estimada_fuzzy

    # População e biomassa
    pop_atual = de.calcular_populacao_atual(ciclo.quantidade_pos_larvas, taxa_sobrev)
    biomassa_atual = de.calcular_biomassa_kg(pop_atual, peso_medio)
    biomassa_inicial = de.calcular_biomassa_kg(
        ciclo.quantidade_pos_larvas, biometrias[0].peso_medio_g if biometrias else 0.5
    )

    # Ração acumulada
    racao_total = sum(m.quantidade_racao_kg for m in manejos)

    # FCA
    fca = de.calcular_fca(racao_total, biomassa_atual, biomassa_inicial)
    class_fca = de.classificar_fca(fca)

    # Clifford
    taxa_clifford = de.taxa_alimentar_clifford(peso_medio)
    racao_diaria = de.calcular_racao_diaria(biomassa_atual, peso_medio)

    # Custos
    custos_vals = [float(c.valor_rs) for c in ciclo.custos_operacionais]

    # Preço de mercado vigente
    preco_result = await db.execute(
        select(TabelaPrecoMercado).where(
            TabelaPrecoMercado.faixa_gramatura_min <= peso_medio,
            TabelaPrecoMercado.faixa_gramatura_max >= peso_medio,
            TabelaPrecoMercado.vigencia_inicio <= hoje,
        ).order_by(TabelaPrecoMercado.vigencia_inicio.desc()).limit(1)
    )
    preco_row = preco_result.scalar_one_or_none()
    preco_kg = float(preco_row.preco_por_kg) if preco_row else 0.0

    metricas = de.calcular_metricas_economicas(custos_vals, biomassa_atual, preco_kg)

    # Restringir dados financeiros conforme perfil
    user = _user
    mostrar_financeiro = hasattr(user, 'papel') and user.papel == RoleUsuario.GESTOR

    return MetricasAtuaisResponse(
        ciclo_id=ciclo.id,
        viveiro_identificacao=viveiro.identificacao,
        dias_cultivo=dias_cultivo,
        densidade_estocagem=round(densidade, 2),
        alerta_hiperdensidade=alerta_hiper,
        populacao_inicial=ciclo.quantidade_pos_larvas,
        taxa_sobrevivencia_fuzzy_pct=taxa_sobrev,
        populacao_estimada=pop_atual,
        peso_medio_atual_g=peso_medio,
        biomassa_atual_kg=round(biomassa_atual, 2),
        racao_acumulada_kg=round(racao_total, 2),
        fca_atual=round(fca, 3) if fca else None,
        classificacao_fca=class_fca.value if class_fca else None,
        taxa_alimentar_clifford_pct=round(taxa_clifford, 2),
        racao_diaria_sugerida_kg=round(racao_diaria, 2),
        custo_operacional_total_rs=round(metricas.custo_operacional_total, 2) if mostrar_financeiro else 0.0,
        receita_bruta_estimada_rs=round(metricas.receita_bruta, 2) if mostrar_financeiro else 0.0,
        lucro_operacional_rs=round(metricas.lucro_operacional, 2) if mostrar_financeiro else 0.0,
        margem_operacional_pct=round(metricas.margem_operacional_pct, 2) if metricas.margem_operacional_pct and mostrar_financeiro else None,
        preco_venda_atual_rs_kg=preco_kg if mostrar_financeiro else None,
    )
