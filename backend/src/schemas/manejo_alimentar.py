"""SAD Carcinicultura — Schemas Pydantic para Manejo Alimentar."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from src.models.enums import NivelSobraBandeja, StatusAlimentar


class ManejoAlimentarCreate(BaseModel):
    ciclo_id: UUID | None = None
    data_registro: date
    quantidade_racao_kg: float = Field(..., ge=0)
    sobra_bandeja_nivel: NivelSobraBandeja
    observacoes: str | None = Field(None, max_length=500)

    @model_validator(mode="before")
    @classmethod
    def map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data.get("data_registro") and data.get("data"):
            data["data_registro"] = data["data"]
        return data


class ManejoAlimentarResponse(BaseModel):
    id: UUID
    ciclo_id: UUID
    data_registro: date
    data: date | None = None
    quantidade_racao_kg: float
    taxa_alimentar_calculada_pct: float | None = None
    sobra_bandeja_nivel: NivelSobraBandeja
    status_alimentar_ajustado: StatusAlimentar | None = None
    taxa_sobrevivencia_estimada_fuzzy: float | None = None
    observacoes: str | None = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_virtual_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data["data"] = data.get("data") or data.get("data_registro")
            return data
        return {
            "id": data.id,
            "ciclo_id": data.ciclo_id,
            "data_registro": data.data_registro,
            "data": data.data_registro,
            "quantidade_racao_kg": data.quantidade_racao_kg,
            "taxa_alimentar_calculada_pct": data.taxa_alimentar_calculada_pct,
            "sobra_bandeja_nivel": data.sobra_bandeja_nivel,
            "status_alimentar_ajustado": data.status_alimentar_ajustado,
            "taxa_sobrevivencia_estimada_fuzzy": data.taxa_sobrevivencia_estimada_fuzzy,
            "observacoes": data.observacoes,
            "created_at": data.created_at,
        }

    model_config = {"from_attributes": True}


class RecomendacaoAlimentarResponse(BaseModel):
    """Retorno com a sugestão de ração para o próximo trato (RN-04)."""
    racao_diaria_sugerida_kg: float
    taxa_clifford_pct: float
    biomassa_estimada_kg: float
    ajuste_sugerido: str
