"""SAD Carcinicultura — Schemas Pydantic para Manejo Alimentar."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.enums import NivelSobraBandeja, StatusAlimentar


class ManejoAlimentarCreate(BaseModel):
    data_registro: date
    quantidade_racao_kg: float = Field(..., ge=0)
    sobra_bandeja_nivel: NivelSobraBandeja = NivelSobraBandeja.SEM_SOBRA


class ManejoAlimentarResponse(BaseModel):
    id: UUID
    ciclo_id: UUID
    data_registro: date
    quantidade_racao_kg: float
    taxa_alimentar_calculada_pct: float | None
    sobra_bandeja_nivel: NivelSobraBandeja
    status_alimentar_ajustado: StatusAlimentar | None
    taxa_sobrevivencia_estimada_fuzzy: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RecomendacaoAlimentarResponse(BaseModel):
    """Retorno com a sugestão de ração para o próximo trato (RN-04)."""
    racao_diaria_sugerida_kg: float
    taxa_clifford_pct: float
    biomassa_estimada_kg: float
    ajuste_sugerido: str
