"""SAD Carcinicultura — Serviço de Registro de Auditoria (RF-027, RNF-017, Critério 10)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from src.models.auditoria import LogAuditoria
from src.models.usuario import Usuario


def _sanitize_for_json(obj: Any) -> Any:
    """Converte UUIDs, dates e datetimes para formato serializável."""
    if obj is None:
        return None
    if isinstance(obj, (uuid.UUID, date, datetime)):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_sanitize_for_json(i) for i in obj]
    return obj


# Colunas nunca gravadas na trilha (RNF-017)
_CAMPOS_SENSIVEIS = {"senha_hash"}


def snapshot(obj: Any) -> dict[str, Any]:
    """Estado das colunas de um objeto ORM, sem campos sensíveis, para antes/depois."""
    return {
        attr.key: getattr(obj, attr.key)
        for attr in inspect(obj).mapper.column_attrs
        if attr.key not in _CAMPOS_SENSIVEIS
    }


def registrar_auditoria(
    db: Session,
    acao: str,
    entidade: str,
    registro_id: str | uuid.UUID,
    usuario: Usuario | None = None,
    dados_anteriores: dict[str, Any] | None = None,
    dados_novos: dict[str, Any] | None = None,
    ip_origem: str | None = None,
) -> LogAuditoria:
    """Registra uma entrada na trilha de auditoria persistente."""
    log = LogAuditoria(
        usuario_id=usuario.id if usuario else None,
        organizacao_id=usuario.organizacao_id if usuario else None,
        usuario_nome=usuario.nome_completo if usuario else "Sistema / Anônimo",
        acao=acao,
        entidade=entidade,
        registro_id=str(registro_id),
        dados_anteriores=_sanitize_for_json(dados_anteriores),
        dados_novos=_sanitize_for_json(dados_novos),
        ip_origem=ip_origem,
    )
    db.add(log)
    db.flush()
    return log
