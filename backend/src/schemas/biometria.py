"""SAD Carcinicultura — Schemas Pydantic para Biometria."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class BiometriaCreate(BaseModel):
    ciclo_id: UUID | None = None
    data_medicao: date
    quantidade_amostrada: int = Field(..., ge=1, description="Quantidade de camarões na amostra (RF-007, RN-004)")
    peso_total_amostra_g: float | None = Field(None, gt=0, description="Peso total da amostra em gramas")
    peso_medio_g: float | None = Field(None, gt=0, description="Peso médio em gramas (calculado se peso total informado)")
    uniformidade_percentual: float | None = Field(None, ge=0, le=100)
    observacoes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if data.get("data_medicao") is None and data.get("data") is not None:
                data["data_medicao"] = data["data"]
            if data.get("quantidade_amostrada") is None:
                for k in ("amostra", "sample_size"):
                    if data.get(k) is not None:
                        data["quantidade_amostrada"] = data[k]
                        break
            if data.get("uniformidade_percentual") is None and data.get("uniformidade_percent") is not None:
                data["uniformidade_percentual"] = data["uniformidade_percent"]
            if not data.get("observacoes") and data.get("condicao_saude"):
                data["observacoes"] = f"Condição: {data['condicao_saude']}"
        return data

    @model_validator(mode="after")
    def exigir_peso(self) -> "BiometriaCreate":
        if self.peso_medio_g is None and self.peso_total_amostra_g is None:
            raise ValueError("Informe peso_medio_g ou peso_total_amostra_g.")
        return self


class BiometriaResponse(BaseModel):
    id: UUID
    ciclo_id: UUID
    data_medicao: date
    quantidade_amostrada: int
    amostra: int | None = None
    sample_size: int | None = None
    peso_total_amostra_g: float | None = None
    peso_medio_g: float
    ganho_medio_semanal_g: float | None = None
    uniformidade_percentual: float | None = None
    uniformidade_percent: float | None = None
    observacoes: str | None = None
    responsavel_id: UUID | None = None
    responsavel_nome: str | None = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_virtual_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data["amostra"] = data["sample_size"] = data.get("quantidade_amostrada")
            data["uniformidade_percent"] = data.get("uniformidade_percentual")
            return data
        responsavel = getattr(data, "responsavel", None)
        return {
            "id": data.id,
            "ciclo_id": data.ciclo_id,
            "data_medicao": data.data_medicao,
            "quantidade_amostrada": data.quantidade_amostrada,
            "amostra": data.quantidade_amostrada,
            "sample_size": data.quantidade_amostrada,
            "peso_total_amostra_g": data.peso_total_amostra_g,
            "peso_medio_g": data.peso_medio_g,
            "ganho_medio_semanal_g": data.ganho_medio_semanal_g,
            "uniformidade_percentual": data.uniformidade_percentual,
            "uniformidade_percent": data.uniformidade_percentual,
            "observacoes": data.observacoes,
            "responsavel_id": data.responsavel_id,
            "responsavel_nome": responsavel.nome_completo if responsavel else None,
            "created_at": data.created_at,
        }

    model_config = {"from_attributes": True}
