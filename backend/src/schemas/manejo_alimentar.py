"""SAD Carcinicultura — Schemas Pydantic para Manejo Alimentar."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.enums import NivelSobraBandeja, StatusAlimentar


from typing import Any
from pydantic import BaseModel, Field, model_validator


class ManejoAlimentarCreate(BaseModel):
    ciclo_id: UUID | None = None
    data_registro: date = Field(default_factory=date.today)
    quantidade_racao_kg: float = Field(..., ge=0)
    sobra_bandeja_nivel: NivelSobraBandeja = NivelSobraBandeja.SEM_SOBRA
    observacoes: str | None = None
    bandejas: list[Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("data_registro"):
                data["data_registro"] = data.get("data") or date.today()
            # Mapeia sobra de bandeja a partir de bandejas se fornecido
            if "sobra_bandeja_nivel" not in data and data.get("bandejas"):
                data["sobra_bandeja_nivel"] = NivelSobraBandeja.SEM_SOBRA
        return data


class ManejoAlimentarResponse(BaseModel):
    id: UUID
    ciclo_id: UUID
    data_registro: date
    data: date | None = None
    quantidade_racao_kg: float
    taxa_alimentar_calculada_pct: float | None = None
    sobra_bandeja_nivel: NivelSobraBandeja = NivelSobraBandeja.SEM_SOBRA
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
        dr = getattr(data, "data_registro", date.today())
        return {
            "id": getattr(data, "id", None),
            "ciclo_id": getattr(data, "ciclo_id", None),
            "data_registro": dr,
            "data": dr,
            "quantidade_racao_kg": getattr(data, "quantidade_racao_kg", 0.0),
            "taxa_alimentar_calculada_pct": getattr(data, "taxa_alimentar_calculada_pct", None),
            "sobra_bandeja_nivel": getattr(data, "sobra_bandeja_nivel", NivelSobraBandeja.SEM_SOBRA),
            "status_alimentar_ajustado": getattr(data, "status_alimentar_ajustado", None),
            "taxa_sobrevivencia_estimada_fuzzy": getattr(data, "taxa_sobrevivencia_estimada_fuzzy", None),
            "observacoes": getattr(data, "observacoes", None),
            "created_at": getattr(data, "created_at", datetime.now()),
        }

    model_config = {"from_attributes": True}



class RecomendacaoAlimentarResponse(BaseModel):
    """Retorno com a sugestão de ração para o próximo trato (RN-04)."""
    racao_diaria_sugerida_kg: float
    taxa_clifford_pct: float
    biomassa_estimada_kg: float
    ajuste_sugerido: str
