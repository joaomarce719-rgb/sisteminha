"""SAD Carcinicultura — Schemas Pydantic para Viveiro."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ViveiroCreate(BaseModel):
    identificacao: str = Field(..., min_length=1, max_length=50)
    area_util_m2: float = Field(..., gt=0, description="Área útil em m², deve ser > 0")
    profundidade_media_m: float | None = Field(None, gt=0)
    localizacao: str | None = Field(None, max_length=255)


class ViveiroUpdate(BaseModel):
    identificacao: str | None = Field(None, min_length=1, max_length=50)
    area_util_m2: float | None = Field(None, gt=0)
    profundidade_media_m: float | None = None
    localizacao: str | None = Field(None, max_length=255)
    status_ativo: bool | None = None


class ViveiroResponse(BaseModel):
    id: UUID
    identificacao: str
    area_util_m2: float
    profundidade_media_m: float | None
    localizacao: str | None
    status_ativo: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ViveiroResumoResponse(ViveiroResponse):
    """Viveiro com informações resumidas do ciclo ativo, se houver."""
    ciclo_ativo_id: UUID | None = None
    dias_cultivo: int | None = None
    peso_medio_atual_g: float | None = None
