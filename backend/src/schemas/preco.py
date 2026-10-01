"""SAD Carcinicultura — Schemas Pydantic para Tabela de Preços de Mercado."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PrecoCreate(BaseModel):
    faixa_gramatura_min: float = Field(..., ge=0)
    faixa_gramatura_max: float = Field(..., gt=0)
    preco_por_kg: float = Field(..., gt=0)
    vigencia_inicio: date
    vigencia_fim: date | None = None


class PrecoUpdate(BaseModel):
    preco_por_kg: float | None = Field(None, gt=0)
    vigencia_fim: date | None = None


class PrecoResponse(BaseModel):
    id: UUID
    faixa_gramatura_min: float
    faixa_gramatura_max: float
    preco_por_kg: float
    vigencia_inicio: date
    vigencia_fim: date | None
    created_at: datetime

    model_config = {"from_attributes": True}
