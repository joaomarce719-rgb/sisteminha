"""SAD Carcinicultura — Schemas Pydantic para Viveiro."""

from datetime import datetime
from uuid import UUID

from typing import Any

from pydantic import BaseModel, Field, model_validator


class ViveiroCreate(BaseModel):
    identificacao: str = Field(..., min_length=1, max_length=50)
    area_util_m2: float = Field(..., gt=0, description="Área útil em m², deve ser > 0")
    profundidade_media_m: float | None = Field(None, gt=0)
    localizacao: str | None = Field(None, max_length=255)

    @model_validator(mode="before")
    @classmethod
    def map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalizar identificação a partir de aliases se identificacao não estiver presente
            if "identificacao" not in data or data["identificacao"] is None:
                alias_ident = data.get("nome") or data.get("codigo") or data.get("name")
                if alias_ident:
                    data["identificacao"] = alias_ident
            # Normalizar área útil a partir de aliases se area_util_m2 não estiver presente
            if "area_util_m2" not in data or data["area_util_m2"] is None:
                for k in ("area_m2", "area"):
                    if k in data and data[k] is not None:
                        data["area_util_m2"] = data[k]
                        break
            # Normalizar localização / descrição
            if "localizacao" not in data or data["localizacao"] is None:
                data["localizacao"] = data.get("descricao") or data.get("description")
        return data


class ViveiroUpdate(BaseModel):
    identificacao: str | None = Field(None, min_length=1, max_length=50)
    area_util_m2: float | None = Field(None, gt=0)
    profundidade_media_m: float | None = None
    localizacao: str | None = Field(None, max_length=255)
    status_ativo: bool | None = None


class ViveiroResponse(BaseModel):
    id: UUID
    identificacao: str
    nome: str | None = None
    codigo: str | None = None
    area_util_m2: float
    area_m2: float | None = None
    profundidade_media_m: float | None = None
    localizacao: str | None = None
    descricao: str | None = None
    status_ativo: bool
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_virtual_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data["nome"] = data["codigo"] = data.get("identificacao")
            data["area_m2"] = data.get("area_util_m2")
            data["descricao"] = data.get("descricao") or data.get("localizacao")
            return data
        return {
            "id": data.id,
            "identificacao": data.identificacao,
            "nome": data.identificacao,
            "codigo": data.identificacao,
            "area_util_m2": data.area_util_m2,
            "area_m2": data.area_util_m2,
            "profundidade_media_m": data.profundidade_media_m,
            "localizacao": data.localizacao,
            "descricao": data.localizacao,
            "status_ativo": data.status_ativo,
            "created_at": data.created_at,
            "updated_at": data.updated_at,
        }

    model_config = {"from_attributes": True}


class ViveiroListResponse(BaseModel):
    items: list[ViveiroResponse]
    total: int
    kpis: dict[str, Any]


class ViveiroResumoResponse(ViveiroResponse):
    """Viveiro com informações resumidas do ciclo ativo, se houver."""
    ciclo_ativo_id: UUID | None = None
    dias_cultivo: int | None = None
    peso_medio_atual_g: float | None = None

