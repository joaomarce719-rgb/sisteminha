"""SAD Carcinicultura — Rotas de Alertas de Manejo (RF-021)."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.escopo import ciclo_da_organizacao, ids_ciclos_da_organizacao
from src.models.alerta import Alerta
from src.models.enums import RoleUsuario, StatusAlerta
from src.schemas.alerta import AlertaResolver, AlertaResponse
from src.services.audit import registrar_auditoria
from src.services.auth_service import has_role

router = APIRouter(prefix="/api/v1/alertas", tags=["Alertas"])


def alerta_response(alerta: Alerta) -> AlertaResponse:
    resposta = AlertaResponse.model_validate(alerta)
    resposta.viveiro_identificacao = alerta.viveiro.identificacao if alerta.viveiro else None
    return resposta


@router.get("", response_model=list[AlertaResponse])
@router.get("/", response_model=list[AlertaResponse])
async def listar_alertas(
    status_alerta: StatusAlerta | None = None,
    ciclo_id: UUID | None = None,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.VIGIA, RoleUsuario.GESTOR])),
):
    """Lista alertas, mais recentes primeiro (filtros por status e ciclo)."""
    query = (
        select(Alerta)
        .where(Alerta.ciclo_id.in_(ids_ciclos_da_organizacao(_user)))
        .order_by(Alerta.created_at.desc())
    )
    if status_alerta:
        query = query.where(Alerta.status == status_alerta)
    if ciclo_id:
        query = query.where(Alerta.ciclo_id == ciclo_id)
    return [alerta_response(a) for a in db.scalars(query.limit(200)).all()]


@router.put("/{alerta_id}/resolver", response_model=AlertaResponse)
async def resolver_alerta(
    alerta_id: UUID,
    payload: AlertaResolver,
    db: Session = Depends(get_db),
    user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Marca o alerta como resolvido, registrando quem tratou e a observação."""
    alerta = db.get(Alerta, alerta_id)
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta não encontrado.")
    ciclo_da_organizacao(db, alerta.ciclo_id, user)
    if alerta.status == StatusAlerta.RESOLVIDO:
        raise HTTPException(status_code=400, detail="Alerta já resolvido.")

    alerta.status = StatusAlerta.RESOLVIDO
    alerta.resolvido_por_id = user.id
    alerta.resolvido_em = datetime.now(timezone.utc)
    alerta.observacao_resolucao = payload.observacao
    db.flush()

    registrar_auditoria(
        db=db,
        acao="RESOLVER_ALERTA",
        entidade="Alerta",
        registro_id=alerta.id,
        usuario=user,
        dados_anteriores={"status": StatusAlerta.ABERTO.value},
        dados_novos={"status": alerta.status.value, "observacao": payload.observacao},
    )
    return alerta_response(alerta)
