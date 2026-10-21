"""SAD Carcinicultura — Rotas de Manejo Alimentar (RF-04)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.ciclo_produtivo import CicloProdutivo
from src.models.enums import RoleUsuario, StatusAlimentar, StatusCiclo
from src.models.manejo_alimentar import ManejoAlimentar
from src.models.tabela_alimentar import TabelaAlimentar
from src.schemas.manejo_alimentar import (
    ManejoAlimentarCreate,
    ManejoAlimentarResponse,
    RecomendacaoAlimentarResponse,
)
from src.services.auth_service import has_role
from src.services.decision_engine import (
    calcular_biomassa_kg,
    calcular_populacao_atual,
    calcular_racao_diaria,
    taxa_alimentar,
    taxa_alimentar_clifford,
    calcular_ganho_diario,
    calcular_ganho_semanal,
)
from src.services.regras_ciclo import validar_data_no_ciclo
from src.services.fuzzy_engine import (
    atualizar_taxa_sobrevivencia,
    inferir_ajuste_sobrevivencia,
)

router = APIRouter(prefix="/api/v1/ciclos/{ciclo_id}/manejos-alimentares", tags=["Manejo Alimentar"])


def _obter_pontos_alimentares(ciclo: CicloProdutivo, db: Session) -> list[tuple[float, float]] | None:
    """Extrai pontos (peso_g, taxa_pct) da tabela do ciclo ou da tabela padrão."""
    if ciclo.tabela_alimentar and ciclo.tabela_alimentar.faixas:
        return [(float(f["peso_g"]), float(f["taxa_pct"])) for f in ciclo.tabela_alimentar.faixas]
    padrao = db.scalar(select(TabelaAlimentar).where(TabelaAlimentar.is_padrao.is_(True)).limit(1))
    if padrao and padrao.faixas:
        return [(float(f["peso_g"]), float(f["taxa_pct"])) for f in padrao.faixas]
    return None


@router.post("", response_model=ManejoAlimentarResponse, status_code=201)
@router.post("/", response_model=ManejoAlimentarResponse, status_code=201)
async def registrar_manejo(
    ciclo_id: UUID,
    payload: ManejoAlimentarCreate,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.CAMPO, RoleUsuario.GESTOR])),
):
    """Lança ração fornecida e nível de sobras (RF-04). Executa fuzzy (RN-05)."""
    # Carregar ciclo
    result = db.execute(select(CicloProdutivo).where(CicloProdutivo.id == ciclo_id))
    ciclo = result.scalar_one_or_none()
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo não encontrado.")
    if ciclo.status != StatusCiclo.ATIVO:
        raise HTTPException(status_code=400, detail="Ciclo não está ativo.")
    validar_data_no_ciclo(ciclo, payload.data_registro, "A data do manejo")

    # Dados de biometria mais recente
    biometrias = sorted(ciclo.biometrias, key=lambda b: b.data_medicao)
    peso_medio = biometrias[-1].peso_medio_g if biometrias else 1.0

    # Taxa de sobrevivência mais recente
    manejos_anteriores = sorted(ciclo.manejos_alimentares, key=lambda m: m.data_registro)
    taxa_sobrev_anterior = 100.0
    for m in manejos_anteriores:
        if m.taxa_sobrevivencia_estimada_fuzzy is not None:
            taxa_sobrev_anterior = m.taxa_sobrevivencia_estimada_fuzzy

    # Calcular biomassa estimada
    pop_atual = calcular_populacao_atual(ciclo.quantidade_pos_larvas, taxa_sobrev_anterior)
    biomassa = calcular_biomassa_kg(pop_atual, peso_medio)

    # Taxa alimentar e consumo esperado (Clifford ou tabela calibrada)
    pontos_calibracao = _obter_pontos_alimentares(ciclo, db)
    taxa_clifford = taxa_alimentar(peso_medio, pontos_calibracao)
    racao_esperada = calcular_racao_diaria(biomassa, peso_medio, pontos_calibracao)
    taxa_alimentar_pct = (payload.quantidade_racao_kg / biomassa * 100) if biomassa > 0 else 0

    # Delta consumo para fuzzy
    delta_consumo = payload.quantidade_racao_kg / racao_esperada if racao_esperada > 0 else 1.0

    # Ganho semanal recente
    ganho_semanal = 0.0
    if len(biometrias) >= 2:
        dias = (biometrias[-1].data_medicao - biometrias[-2].data_medicao).days
        if dias > 0:
            gd = calcular_ganho_diario(biometrias[-2].peso_medio_g, biometrias[-1].peso_medio_g, dias)
            ganho_semanal = calcular_ganho_semanal(gd)

    # ── Inferência Fuzzy (RN-05) ──────────────────
    ajuste = inferir_ajuste_sobrevivencia(
        delta_consumo=delta_consumo,
        nivel_sobra=payload.sobra_bandeja_nivel,
        ganho_semanal_g=ganho_semanal,
    )
    nova_taxa_sobrev = atualizar_taxa_sobrevivencia(taxa_sobrev_anterior, ajuste)

    # Status alimentar
    if delta_consumo < 0.7:
        status_alimentar = StatusAlimentar.SUB_ARRAC_SUSPEITO
    elif delta_consumo > 1.3:
        status_alimentar = StatusAlimentar.SUPER_ARRAC_SUSPEITO
    else:
        status_alimentar = StatusAlimentar.NORMAL

    import uuid
    manejo = ManejoAlimentar(
        id=uuid.uuid4(),
        ciclo_id=ciclo_id,
        data_registro=payload.data_registro,
        quantidade_racao_kg=payload.quantidade_racao_kg,
        taxa_alimentar_calculada_pct=round(taxa_alimentar_pct, 2),
        sobra_bandeja_nivel=payload.sobra_bandeja_nivel,
        status_alimentar_ajustado=status_alimentar,
        taxa_sobrevivencia_estimada_fuzzy=nova_taxa_sobrev,
        observacoes=payload.observacoes,
    )
    db.add(manejo)
    db.flush()
    db.refresh(manejo)
    return manejo


@router.get("", response_model=list[ManejoAlimentarResponse])
@router.get("/", response_model=list[ManejoAlimentarResponse])
async def listar_manejos(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.CAMPO, RoleUsuario.GESTOR])),
):
    """Lista registros de manejo alimentar do ciclo."""
    result = db.execute(
        select(ManejoAlimentar)
        .where(ManejoAlimentar.ciclo_id == ciclo_id)
        .order_by(ManejoAlimentar.data_registro)
    )
    return result.scalars().all()


@router.get("/recomendacao", response_model=RecomendacaoAlimentarResponse)
async def recomendacao_alimentar(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.CAMPO, RoleUsuario.GESTOR])),
):
    """Retorna a recomendação de ração para o próximo trato (RN-04)."""
    result = db.execute(select(CicloProdutivo).where(CicloProdutivo.id == ciclo_id))
    ciclo = result.scalar_one_or_none()
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo não encontrado.")

    biometrias = sorted(ciclo.biometrias, key=lambda b: b.data_medicao)
    peso_medio = biometrias[-1].peso_medio_g if biometrias else 1.0

    manejos = sorted(ciclo.manejos_alimentares, key=lambda m: m.data_registro)
    taxa_sobrev = 100.0
    for m in manejos:
        if m.taxa_sobrevivencia_estimada_fuzzy is not None:
            taxa_sobrev = m.taxa_sobrevivencia_estimada_fuzzy

    pop_atual = calcular_populacao_atual(ciclo.quantidade_pos_larvas, taxa_sobrev)
    biomassa = calcular_biomassa_kg(pop_atual, peso_medio)
    pontos_calibracao = _obter_pontos_alimentares(ciclo, db)
    taxa_clifford_pct = taxa_alimentar(peso_medio, pontos_calibracao)
    racao_sugerida = calcular_racao_diaria(biomassa, peso_medio, pontos_calibracao)

    # Ajuste baseado em sobras recentes
    ajuste_texto = "Manter ração sugerida."
    if manejos:
        ultimas_sobras = [m.sobra_bandeja_nivel.value for m in manejos[-3:]]
        if all(s == "SOBRA_EXCESSIVA" for s in ultimas_sobras):
            racao_sugerida *= 0.7
            ajuste_texto = "⚠️ Reduzir 30% — sobras excessivas consecutivas."
        elif ultimas_sobras[-1] == "SOBRA_MODERADA":
            racao_sugerida *= 0.85
            ajuste_texto = "Reduzir 15% — sobra moderada no último trato."
        elif ultimas_sobras[-1] == "SEM_SOBRA":
            ajuste_texto = "✅ Consumo limpo — manter ou avaliar incremento leve."

    return RecomendacaoAlimentarResponse(
        racao_diaria_sugerida_kg=round(racao_sugerida, 2),
        taxa_clifford_pct=round(taxa_clifford_pct, 2),
        biomassa_estimada_kg=round(biomassa, 2),
        ajuste_sugerido=ajuste_texto,
    )


global_router = APIRouter(prefix="/api/v1/manejos", tags=["Manejo Alimentar"])


@global_router.post("/", response_model=ManejoAlimentarResponse, status_code=201)
async def registrar_manejo_global(
    payload: ManejoAlimentarCreate,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.CAMPO, RoleUsuario.GESTOR])),
):
    if not payload.ciclo_id:
        raise HTTPException(status_code=422, detail="ciclo_id é obrigatório.")
    return await registrar_manejo(payload.ciclo_id, payload, db, _user)


@global_router.get("/", response_model=list[ManejoAlimentarResponse])
async def listar_manejos_global(
    ciclo_id: UUID | None = None,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.CAMPO, RoleUsuario.VIGIA, RoleUsuario.GESTOR])),
):
    query = select(ManejoAlimentar).order_by(ManejoAlimentar.data_registro.desc())
    if ciclo_id:
        query = query.where(ManejoAlimentar.ciclo_id == ciclo_id)
    result = db.execute(query)
    return result.scalars().all()


@global_router.delete("/{manejo_id}", status_code=200)
async def deletar_manejo(
    manejo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    result = db.execute(select(ManejoAlimentar).where(ManejoAlimentar.id == manejo_id))
    man = result.scalar_one_or_none()
    if not man:
        raise HTTPException(status_code=404, detail="Manejo não encontrado.")
    db.delete(man)
    db.flush()
    return {"detail": "Manejo excluído com sucesso.", "id": str(manejo_id)}

