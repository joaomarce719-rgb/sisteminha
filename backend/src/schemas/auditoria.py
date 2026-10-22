"""SAD Carcinicultura — Schemas Pydantic para Auditoria (RF-027, RNF-017, Critério 10)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class LogAuditoriaResponse(BaseModel):
    """Registro individual de evento na trilha de auditoria."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    usuario_id: uuid.UUID | None = None
    usuario_nome: str | None = None
    acao: str
    entidade: str
    registro_id: str
    dados_anteriores: dict[str, Any] | None = None
    dados_novos: dict[str, Any] | None = None
    ip_origem: str | None = None
    created_at: datetime
