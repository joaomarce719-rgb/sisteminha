"""SAD Carcinicultura — Schemas Pydantic para Biometria."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BiometriaCreate(BaseModel):
    data_medicao: date
    peso_medio_g: float = Field(..., gt=0, description="Peso médio em gramas")
    uniformidade_percentual: float | None = Field(None, ge=0, le=100)
    observacoes: str | None = None


class BiometriaResponse(BaseModel):
    id: UUID
    ciclo_id: UUID
    data_medicao: date
    peso_medio_g: float
    ganho_medio_semanal_g: float | None
    uniformidade_percentual: float | None
    observacoes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
