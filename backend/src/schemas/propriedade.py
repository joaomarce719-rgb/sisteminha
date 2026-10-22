"""SAD Carcinicultura — Schemas Pydantic para Propriedade / Fazenda (RF-002, RF-003)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PropriedadeCreate(BaseModel):
    organizacao_id: UUID
    nome: str = Field(..., min_length=2, max_length=120)
    localizacao: str | None = Field(None, max_length=255)
    area_total_ha: float | None = Field(None, gt=0)


class PropriedadeUpdate(BaseModel):
    nome: str | None = Field(None, min_length=2, max_length=120)
    localizacao: str | None = None
    area_total_ha: float | None = Field(None, gt=0)
    status_ativo: bool | None = None


class PropriedadeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organizacao_id: UUID
    nome: str
    localizacao: str | None = None
    area_total_ha: float | None = None
    status_ativo: bool
    created_at: datetime
