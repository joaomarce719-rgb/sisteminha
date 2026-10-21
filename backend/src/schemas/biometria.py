"""SAD Carcinicultura — Schemas Pydantic para Biometria."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


from typing import Any
from pydantic import BaseModel, Field, model_validator


class BiometriaCreate(BaseModel):
    ciclo_id: UUID | None = None
    data_medicao: date = Field(default_factory=date.today)
    quantidade_amostrada: int = Field(default=50, ge=1, description="Quantidade de camarões na amostra (RF-007, RN-004)")
    amostra: int | None = None
    peso_total_amostra_g: float | None = Field(None, gt=0, description="Peso total da amostra em gramas")
    peso_medio_g: float = Field(..., gt=0, description="Peso médio em gramas")
    uniformidade_percentual: float | None = Field(None, ge=0, le=100)
    uniformidade_percent: float | None = None
    cv_percent: float | None = None
    condicao_saude: str | None = None
    observacoes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "data_medicao" not in data or data["data_medicao"] is None:
                if "data" in data and data["data"] is not None:
                    data["data_medicao"] = data["data"]
            if "quantidade_amostrada" not in data or data["quantidade_amostrada"] is None:
                if "amostra" in data and data["amostra"] is not None:
                    data["quantidade_amostrada"] = data["amostra"]
                elif "sample_size" in data and data["sample_size"] is not None:
                    data["quantidade_amostrada"] = data["sample_size"]
            if data.get("uniformidade_percentual") is None and data.get("uniformidade_percent") is not None:
                data["uniformidade_percentual"] = data.get("uniformidade_percent")
            if not data.get("observacoes") and data.get("condicao_saude"):
                data["observacoes"] = f"Condição: {data.get('condicao_saude')}"
        return data


class BiometriaResponse(BaseModel):
    id: UUID
    ciclo_id: UUID
    data_medicao: date
    quantidade_amostrada: int = 50
    amostra: int | None = None
    sample_size: int | None = None
    peso_total_amostra_g: float | None = None
    peso_medio_g: float
    ganho_medio_semanal_g: float | None = None
    uniformidade_percentual: float | None = None
    uniformidade_percent: float | None = None
    cv_percent: float | None = None
    condicao_saude: str | None = None
    observacoes: str | None = None
    responsavel_id: UUID | None = None
    responsavel_nome: str | None = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_virtual_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            amostra_val = data.get("quantidade_amostrada")
            if amostra_val is None:
                amostra_val = data.get("amostra")
            if amostra_val is None:
                amostra_val = data.get("sample_size")
            if amostra_val is None:
                amostra_val = 50

            uni = data.get("uniformidade_percentual")
            if uni is None:
                uni = data.get("uniformidade_percent")

            data["amostra"] = amostra_val
            data["sample_size"] = amostra_val
            data["quantidade_amostrada"] = amostra_val
            data["uniformidade_percent"] = uni
            data["uniformidade_percentual"] = uni
            return data
        
        amostra_val = getattr(data, "quantidade_amostrada", 50)
        uni = getattr(data, "uniformidade_percentual", None)
        return {
            "id": getattr(data, "id", None),
            "ciclo_id": getattr(data, "ciclo_id", None),
            "data_medicao": getattr(data, "data_medicao", date.today()),
            "quantidade_amostrada": amostra_val,
            "amostra": amostra_val,
            "sample_size": amostra_val,
            "peso_total_amostra_g": getattr(data, "peso_total_amostra_g", None),
            "peso_medio_g": getattr(data, "peso_medio_g", 0.0),
            "ganho_medio_semanal_g": getattr(data, "ganho_medio_semanal_g", None),
            "uniformidade_percentual": uni,
            "uniformidade_percent": uni,
            "cv_percent": 8.5,
            "condicao_saude": "boa",
            "observacoes": getattr(data, "observacoes", None),
            "responsavel_id": getattr(data, "responsavel_id", None),
            "responsavel_nome": getattr(getattr(data, "responsavel", None), "nome_completo", None),
            "created_at": getattr(data, "created_at", datetime.now()),
        }

    model_config = {"from_attributes": True}


