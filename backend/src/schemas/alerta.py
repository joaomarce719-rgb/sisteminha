"""SAD Carcinicultura — Schemas Pydantic para Alertas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import NivelAlerta, StatusAlerta


class AlertaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ciclo_id: UUID
    viveiro_id: UUID
    viveiro_identificacao: str | None = None
    ronda_id: UUID | None = None
    nivel: NivelAlerta
    codigo: str
    titulo: str
    mensagem: str
    status: StatusAlerta
    resolvido_em: datetime | None = None
    observacao_resolucao: str | None = None
    created_at: datetime


class AlertaResolver(BaseModel):
    observacao: str | None = Field(None, max_length=500)
