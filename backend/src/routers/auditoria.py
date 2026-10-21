from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.auth_service import is_superadmin
from src.services.escopo import org_do_usuario
from src.dependencies import require_gestor
from src.models.auditoria import LogAuditoria
from src.models.usuario import Usuario
from src.schemas.auditoria import LogAuditoriaResponse

router = APIRouter(prefix="/api/v1/auditoria", tags=["Auditoria"])


@router.get("/")
def listar_logs_auditoria(
    db: Annotated[Session, Depends(get_db)],
    _usuario: Annotated[Usuario, Depends(require_gestor)],
    entidade: str | None = Query(None, description="Filtrar por entidade"),
    entity: str | None = Query(None, description="Alias para entidade"),
    acao: str | None = Query(None, description="Filtrar por ação"),
    action: str | None = Query(None, description="Alias para ação"),
    date_from: str | None = Query(None, description="Data início ISO"),
    date_to: str | None = Query(None, description="Data fim ISO"),
    limite: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Lista eventos da trilha de auditoria ordenados por data decrescente (apenas GESTOR)."""
    filtro_entidade = entity or entidade
    filtro_acao = action or acao

    query = select(LogAuditoria).order_by(desc(LogAuditoria.created_at))
    if not is_superadmin(_usuario):
        # GESTOR vê a trilha da própria organização; superadmin vê toda a plataforma
        query = query.where(LogAuditoria.organizacao_id == org_do_usuario(_usuario))

    if filtro_entidade:
        query = query.where(LogAuditoria.entidade.ilike(f"%{filtro_entidade}%"))
    if filtro_acao:
        query = query.where(LogAuditoria.acao.ilike(f"%{filtro_acao}%"))

    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            query = query.where(LogAuditoria.created_at >= dt_from)
        except Exception:
            pass

    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
            query = query.where(LogAuditoria.created_at <= dt_to)
        except Exception:
            pass

    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    query = query.offset(offset).limit(limite)
    logs = list(db.scalars(query).all())
    
    # Formata respostas conforme schema
    items = [
        LogAuditoriaResponse.model_validate(log).model_dump(mode="json")
        for log in logs
    ]

    return {
        "items": items,
        "results": items,
        "data": items,
        "total": total,
        "count": len(items),
        "limite": limite,
        "offset": offset,
    }

