"""SAD Carcinicultura — Rotas de Manejo Alimentar (RF-04)."""

from dataclasses import asdict
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
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
from src.models.enums import RoleUsuario, StatusAlimentar, StatusCiclo
from src.models.manejo_alimentar import ManejoAlimentar
from src.schemas.manejo_alimentar import (
    ManejoAlimentarCreate,
    ManejoAlimentarResponse,
    RecomendacaoAlimentarResponse,
)
from src.services.alimentacao import pontos_alimentares
from src.services.auth_service import has_role
from src.services.decision_engine import (
    calcular_biomassa_kg,
    calcular_populacao_atual,
    calcular_racao_diaria,
    taxa_alimentar,
    calcular_ganho_diario,
    calcular_ganho_semanal,
)
from src.services.regras_ciclo import validar_data_no_ciclo
from src.services.fuzzy_engine import inferir_ajuste_sobrevivencia
from src.services.sobrevivencia import (
    agrupar_por_dia,
    confrontar_vivos,
    nova_sobrevivencia,
    ordenar,
    peso_na_data,
    sobrevivencia_implicita_pct,
    sobrevivencia_vigente,
)

router = APIRouter(
    prefix="/api/v1/ciclos/{ciclo_id}/manejos-alimentares",
    tags=["Manejo Alimentar"],
    dependencies=[Depends(verificar_ciclo_da_organizacao)],
)


@router.post("", response_model=ManejoAlimentarResponse, status_code=201)
@router.post("/", response_model=ManejoAlimentarResponse, status_code=201)
def registrar_manejo(
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

    # O confronto com a tabela é diário: os tratos da data se somam e partem da sobrevivência do dia anterior
    registros_dia = [m for m in ciclo.manejos_alimentares if m.data_registro == payload.data_registro]
    anteriores = ordenar(m for m in ciclo.manejos_alimentares if m.data_registro < payload.data_registro)
    taxa_sobrev_anterior = sobrevivencia_vigente(anteriores)
    pos_larvas = ciclo.quantidade_pos_larvas

    # Calcular biomassa estimada
    pop_atual = calcular_populacao_atual(pos_larvas, taxa_sobrev_anterior)
    biomassa = calcular_biomassa_kg(pop_atual, peso_medio)

    mortos_dia = sum(m.camaroes_mortos or 0 for m in registros_dia) + (payload.camaroes_mortos or 0)
    if mortos_dia > pop_atual:
        raise HTTPException(
            status_code=422,
            detail=f"Os camarões mortos do dia ({mortos_dia:,}) superam a população estimada ({pop_atual:,}).".replace(",", "."),
        )

    # Ração diária esperada pela tabela alimentar (do ciclo, padrão da organização ou Clifford)
    pontos_calibracao = pontos_alimentares(ciclo, db)
    racao_esperada = calcular_racao_diaria(biomassa, peso_medio, pontos_calibracao)
    taxa_alimentar_pct = (payload.quantidade_racao_kg / biomassa * 100) if biomassa > 0 else 0

    import uuid
    manejo = ManejoAlimentar(
        id=uuid.uuid4(),
        ciclo_id=ciclo_id,
        data_registro=payload.data_registro,
        quantidade_racao_kg=payload.quantidade_racao_kg,
        taxa_alimentar_calculada_pct=round(taxa_alimentar_pct, 2),
        sobra_bandeja_nivel=payload.sobra_bandeja_nivel,
        camaroes_mortos=payload.camaroes_mortos,
        observacoes=payload.observacoes,
    )
    dias = agrupar_por_dia([*ciclo.manejos_alimentares, manejo])
    dia = next(d for d in dias if d.data == payload.data_registro)

    # Delta consumo para fuzzy: ração do dia (todos os tratos) ÷ ração da tabela
    delta_consumo = dia.racao_kg / racao_esperada if racao_esperada > 0 else 1.0

    # Ganho semanal recente (None = ainda sem duas biometrias)
    ganho_semanal = None
    if len(biometrias) >= 2:
        dias_bio = (biometrias[-1].data_medicao - biometrias[-2].data_medicao).days
        if dias_bio > 0:
            gd = calcular_ganho_diario(biometrias[-2].peso_medio_g, biometrias[-1].peso_medio_g, dias_bio)
            ganho_semanal = calcular_ganho_semanal(gd)

    # ── Inferência Fuzzy (RN-05) ──────────────────
    ajuste = inferir_ajuste_sobrevivencia(
        delta_consumo=delta_consumo,
        nivel_sobra=dia.pior_sobra,
        ganho_semanal_g=ganho_semanal,
    )

    # ── Sobrevivência: mortos contados, consumo × tabela e fuzzy ──
    data_anterior = anteriores[-1].data_registro if anteriores else ciclo.data_povoamento
    dias_periodo = (payload.data_registro - data_anterior).days
    if not anteriores:
        dias_periodo = max(dias_periodo, 1)

    implicita = sobrevivencia_implicita_pct(
        dias,
        pos_larvas,
        lambda data: peso_na_data(biometrias, data),
        lambda peso: taxa_alimentar(peso, pontos_calibracao),
        payload.data_registro,
    )
    nova_taxa_sobrev = nova_sobrevivencia(
        taxa_sobrev_anterior, dias_periodo, mortos_dia / pos_larvas * 100, ajuste, implicita
    )

    # Status alimentar do dia
    if delta_consumo < 0.7:
        status_alimentar = StatusAlimentar.SUB_ARRAC_SUSPEITO
    elif delta_consumo > 1.3:
        status_alimentar = StatusAlimentar.SUPER_ARRAC_SUSPEITO
    else:
        status_alimentar = StatusAlimentar.NORMAL

    manejo.status_alimentar_ajustado = status_alimentar
    manejo.taxa_sobrevivencia_estimada_fuzzy = nova_taxa_sobrev
    for anterior_do_dia in registros_dia:  # o diagnóstico é do dia, não do trato
        anterior_do_dia.status_alimentar_ajustado = status_alimentar
        anterior_do_dia.taxa_sobrevivencia_estimada_fuzzy = nova_taxa_sobrev
    db.add(manejo)
    db.flush()
    db.refresh(manejo)
    registrar_auditoria(db, "CRIAR", "ManejoAlimentar", manejo.id, _user, dados_novos=snapshot(manejo))
    return manejo


@router.get("", response_model=list[ManejoAlimentarResponse])
@router.get("/", response_model=list[ManejoAlimentarResponse])
def listar_manejos(
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
def recomendacao_alimentar(
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

    manejos = ordenar(ciclo.manejos_alimentares)
    taxa_sobrev = sobrevivencia_vigente(manejos)

    pop_atual = calcular_populacao_atual(ciclo.quantidade_pos_larvas, taxa_sobrev)
    biomassa = calcular_biomassa_kg(pop_atual, peso_medio)
    pontos_calibracao = pontos_alimentares(ciclo, db)
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

    # Confronto de hoje: ração lançada (todos os tratos) contra a ração da tabela
    hoje = date.today()
    registros_hoje = [m for m in manejos if m.data_registro == hoje]
    taxa_inicio_dia = sobrevivencia_vigente(m for m in manejos if m.data_registro < hoje)
    biomassa_inicio_dia = calcular_biomassa_kg(
        calcular_populacao_atual(ciclo.quantidade_pos_larvas, taxa_inicio_dia), peso_medio
    )
    racao_tabela_dia = calcular_racao_diaria(biomassa_inicio_dia, peso_medio, pontos_calibracao)
    racao_hoje = sum(m.quantidade_racao_kg for m in registros_hoje)

    return RecomendacaoAlimentarResponse(
        racao_diaria_sugerida_kg=round(racao_sugerida, 2),
        taxa_clifford_pct=round(taxa_clifford_pct, 2),
        biomassa_estimada_kg=round(biomassa, 2),
        ajuste_sugerido=ajuste_texto,
        racao_tabela_dia_kg=round(racao_tabela_dia, 2),
        racao_lancada_hoje_kg=round(racao_hoje, 2),
        consumo_vs_tabela_pct=round(racao_hoje / racao_tabela_dia * 100, 1) if registros_hoje and racao_tabela_dia > 0 else None,
        status_alimentar=registros_hoje[-1].status_alimentar_ajustado if registros_hoje else None,
        confronto_vivos=asdict(
            confrontar_vivos(
                manejos,
                ciclo.quantidade_pos_larvas,
                lambda data: peso_na_data(biometrias, data),
                lambda peso: taxa_alimentar(peso, pontos_calibracao),
                hoje,
            )
        ),
    )


global_router = APIRouter(prefix="/api/v1/manejos", tags=["Manejo Alimentar"])


@global_router.post("", response_model=ManejoAlimentarResponse, status_code=201)
@global_router.post("/", response_model=ManejoAlimentarResponse, status_code=201)
def registrar_manejo_global(
    payload: ManejoAlimentarCreate,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.CAMPO, RoleUsuario.GESTOR])),
):
    if not payload.ciclo_id:
        raise HTTPException(status_code=422, detail="ciclo_id é obrigatório.")
    ciclo_da_organizacao(db, payload.ciclo_id, _user)
    return registrar_manejo(payload.ciclo_id, payload, db, _user)


@global_router.get("", response_model=list[ManejoAlimentarResponse])
@global_router.get("/", response_model=list[ManejoAlimentarResponse])
def listar_manejos_global(
    ciclo_id: UUID | None = None,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.CAMPO, RoleUsuario.VIGIA, RoleUsuario.GESTOR])),
):
    query = select(ManejoAlimentar).order_by(ManejoAlimentar.data_registro.desc())
    query = query.where(ManejoAlimentar.ciclo_id.in_(ids_ciclos_da_organizacao(_user)))
    if ciclo_id:
        query = query.where(ManejoAlimentar.ciclo_id == ciclo_id)
    result = db.execute(query)
    return result.scalars().all()


@global_router.delete("/{manejo_id}", status_code=200)
def deletar_manejo(
    manejo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    result = db.execute(select(ManejoAlimentar).where(ManejoAlimentar.id == manejo_id))
    man = result.scalar_one_or_none()
    if not man:
        raise HTTPException(status_code=404, detail="Manejo não encontrado.")
    ciclo_da_organizacao(db, man.ciclo_id, _user)
    registrar_auditoria(db, "EXCLUIR", "ManejoAlimentar", man.id, _user, dados_anteriores=snapshot(man))
    db.delete(man)
    db.flush()
    return {"detail": "Manejo excluído com sucesso.", "id": str(manejo_id)}

