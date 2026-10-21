"""SAD Carcinicultura — Schemas Pydantic para Viveiro."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


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
    capacidade: float | None = None
    status_ativo: bool
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_virtual_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            ident = data.get("identificacao") or data.get("nome") or data.get("codigo")
            area = data.get("area_util_m2") or data.get("area_m2") or data.get("area") or 1000.0
            data["nome"] = ident
            data["codigo"] = ident
            data["area_m2"] = area
            data["descricao"] = data.get("descricao") or data.get("localizacao")
            data["capacidade"] = data.get("capacidade") or 5000.0
            return data

        ident = getattr(data, "identificacao", None)
        area = getattr(data, "area_util_m2", 1000.0)
        loc = getattr(data, "localizacao", None)
        return {
            "id": getattr(data, "id", None),
            "identificacao": ident,
            "nome": ident,
            "codigo": ident,
            "area_util_m2": area,
            "area_m2": area,
            "profundidade_media_m": getattr(data, "profundidade_media_m", None),
            "localizacao": loc,
            "descricao": loc,
            "capacidade": 5000.0,
            "status_ativo": getattr(data, "status_ativo", True),
            "created_at": getattr(data, "created_at", datetime.now()),
            "updated_at": getattr(data, "updated_at", datetime.now()),
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

