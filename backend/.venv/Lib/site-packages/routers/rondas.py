"""SAD Carcinicultura — Rotas de Rondas Noturnas (RF-12, RF-13)."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.ciclo_produtivo import CicloProdutivo
from src.models.enums import RoleUsuario, StatusCiclo
from src.models.monitoramento_aerador import MonitoramentoAerador
from src.models.ronda_noturna import RondaNoturna
from src.models.usuario import Usuario
from src.schemas.ronda import PainelNoturnoResponse, RondaNoturnaCreate, RondaNoturnaResponse
from src.services.alert_engine import (
    calcular_taxa_aeracao,
    classificar_oxigenio,
    gerar_alerta_oxigenio,
    verificar_aeracao_noturna,
)
from src.services.auth_service import get_current_user, has_role

router = APIRouter(prefix="/api/v1/rondas-noturnas", tags=["Rondas Noturnas"])


def _build_ronda_response(ronda: RondaNoturna) -> RondaNoturnaResponse:
    """Monta a response de ronda com classificação de O₂ e dados de aeradores."""
    classificacao = classificar_oxigenio(float(ronda.oxigenio_dissolvido_mg_l))

    # Aeradores da ronda
    aerador = ronda.monitoramento_aeradores[0] if ronda.monitoramento_aeradores else None
    taxa_aeracao = None
    if aerador:
        taxa_aeracao = calcular_taxa_aeracao(aerador.aeradores_ligados, aerador.aeradores_instalados)

    return RondaNoturnaResponse(
        id=ronda.id,
        ciclo_id=ronda.ciclo_id,
        vigia_id=ronda.vigia_id,
        vigia_nome=ronda.vigia.nome_completo if ronda.vigia else "Desconhecido",
        data_hora_ronda=ronda.data_hora_ronda,
        oxigenio_dissolvido_mg_l=float(ronda.oxigenio_dissolvido_mg_l),
        temperatura_agua_c=float(ronda.temperatura_agua_c),
        comportamento=ronda.comportamento,
        observacoes=ronda.observacoes,
        classificacao_oxigenio=classificacao,
        created_at=ronda.created_at,
        aeradores_instalados=aerador.aeradores_instalados if aerador else None,
        aeradores_ligados=aerador.aeradores_ligados if aerador else None,
        taxa_aeracao_pct=round(taxa_aeracao, 1) if taxa_aeracao is not None else None,
        fonte_energia=aerador.fonte_energia if aerador else None,
        falha_mecanica_detectada=aerador.falha_mecanica_detectada if aerador else None,
    )


@router.post("/", response_model=RondaNoturnaResponse, status_code=201)
async def registrar_ronda(
    payload: RondaNoturnaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(has_role([RoleUsuario.VIGIA, RoleUsuario.GESTOR])),
):
    """Registra ronda noturna com parâmetros de água e aeradores (RF-12, RF-13)."""
    # Validar ciclo
    result = db.execute(select(CicloProdutivo).where(CicloProdutivo.id == payload.ciclo_id))
    ciclo = result.scalar_one_or_none()
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo não encontrado.")
    if ciclo.status != StatusCiclo.ATIVO:
        raise HTTPException(status_code=400, detail="Ciclo não está ativo.")

    # Validar aeradores
    if payload.aeradores_ligados > payload.aeradores_instalados:
        raise HTTPException(
            status_code=400,
            detail="Aeradores ligados não pode exceder os instalados.",
        )

    # Criar ronda
    ronda = RondaNoturna(
        ciclo_id=payload.ciclo_id,
        vigia_id=current_user.id,
        data_hora_ronda=payload.data_hora_ronda,
        oxigenio_dissolvido_mg_l=payload.oxigenio_dissolvido_mg_l,
        temperatura_agua_c=payload.temperatura_agua_c,
        comportamento=payload.comportamento,
        observacoes=payload.observacoes,
    )
    db.add(ronda)
    db.flush()

    # Criar monitoramento de aeradores
    aerador = MonitoramentoAerador(
        ronda_id=ronda.id,
        viveiro_id=ciclo.viveiro_id,
        aeradores_instalados=payload.aeradores_instalados,
        aeradores_ligados=payload.aeradores_ligados,
        fonte_energia=payload.fonte_energia,
        falha_mecanica_detectada=payload.falha_mecanica_detectada,
        detalhes_falha=payload.detalhes_falha,
    )
    db.add(aerador)
    db.flush()
    db.refresh(ronda)

    # Gerar alertas
    alerta = gerar_alerta_oxigenio(
        float(ronda.oxigenio_dissolvido_mg_l),
        ronda.comportamento,
        str(ciclo.viveiro_id),
    )

    return _build_ronda_response(ronda)


@router.get("/ciclo/{ciclo_id}", response_model=list[RondaNoturnaResponse])
async def listar_rondas_ciclo(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.VIGIA, RoleUsuario.GESTOR])),
):
    """Lista rondas noturnas de um ciclo."""
    result = db.execute(
        select(RondaNoturna)
        .where(RondaNoturna.ciclo_id == ciclo_id)
        .order_by(RondaNoturna.data_hora_ronda.desc())
    )
    rondas = result.scalars().all()
    return [_build_ronda_response(r) for r in rondas]


@router.get("/painel-noturno", response_model=list[PainelNoturnoResponse])
async def painel_noturno(
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Painel noturno consolidado das últimas 12 horas (RF-15, somente GESTOR)."""
    corte = datetime.now(timezone.utc) - timedelta(hours=12)

    result = db.execute(
        select(RondaNoturna)
        .where(RondaNoturna.data_hora_ronda >= corte)
        .order_by(RondaNoturna.data_hora_ronda)
    )
    rondas = result.scalars().all()

    # Agrupar por viveiro (via ciclo)
    por_viveiro: dict[UUID, list[RondaNoturna]] = {}
    for r in rondas:
        ciclo = r.ciclo
        vid = ciclo.viveiro_id
        if vid not in por_viveiro:
            por_viveiro[vid] = []
        por_viveiro[vid].append(r)

    paineis = []
    for vid, rondas_viv in por_viveiro.items():
        viveiro = rondas_viv[0].ciclo.viveiro
        o2_vals = [float(r.oxigenio_dissolvido_mg_l) for r in rondas_viv]
        alertas = sum(
            1 for o2 in o2_vals if classificar_oxigenio(o2).value == "EMERGENCIA"
        )
        paineis.append(
            PainelNoturnoResponse(
                viveiro_id=vid,
                viveiro_identificacao=viveiro.identificacao,
                rondas=[_build_ronda_response(r) for r in rondas_viv],
                o2_minimo=min(o2_vals) if o2_vals else None,
                o2_maximo=max(o2_vals) if o2_vals else None,
                alertas_criticos=alertas,
            )
        )
    return paineis
