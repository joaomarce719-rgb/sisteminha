"""SAD Carcinicultura — Schemas Pydantic para Custos Operacionais."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from src.models.enums import CategoriaCusto

# Sinônimos aceitos para a categoria (comparação por trecho, em maiúsculas)
_SINONIMOS_CATEGORIA = (
    ("ENERG", CategoriaCusto.ENERGIA_ELETRICA),
    ("RACAO", CategoriaCusto.RACAO),
    ("FEED", CategoriaCusto.RACAO),
    ("OBRA", CategoriaCusto.MAO_DE_OBRA),
    ("LABOR", CategoriaCusto.MAO_DE_OBRA),
    ("LARVA", CategoriaCusto.POS_LARVAS),
    ("MANUT", CategoriaCusto.MANUTENCAO),
)


class CustoCreate(BaseModel):
    ciclo_id: UUID | None = None
    data_lancamento: date
    categoria: CategoriaCusto
    descricao: str = Field(..., min_length=3, max_length=255)
    valor_rs: float = Field(..., gt=0)

    @model_validator(mode="before")
    @classmethod
    def map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if data.get("data_lancamento") is None and data.get("data") is not None:
                data["data_lancamento"] = data["data"]
            if data.get("valor_rs") is None:
                for k in ("valor", "amount", "value"):
                    if data.get(k) is not None:
                        data["valor_rs"] = data[k]
                        break
            cat = str(data.get("categoria") or "").upper()
            if cat and cat not in CategoriaCusto.__members__:
                # Categoria desconhecida não é convertida em OUTROS: falha na validação
                for trecho, categoria in _SINONIMOS_CATEGORIA:
                    if trecho in cat:
                        data["categoria"] = categoria
                        break
        return data


class CustoResponse(BaseModel):
    id: UUID
    ciclo_id: UUID
    data_lancamento: date
    data: date | None = None
    categoria: CategoriaCusto
    descricao: str
    valor_rs: float
    valor: float | None = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_virtual_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data["valor"] = data.get("valor_rs")
            data["data"] = data.get("data_lancamento")
            return data
        return {
            "id": data.id,
            "ciclo_id": data.ciclo_id,
            "data_lancamento": data.data_lancamento,
            "data": data.data_lancamento,
            "categoria": data.categoria,
            "descricao": data.descricao,
            "valor_rs": data.valor_rs,
            "valor": data.valor_rs,
            "created_at": data.created_at,
        }

    model_config = {"from_attributes": True}


class CustoListResponse(BaseModel):
    items: list[CustoResponse]
    total: int
    summary: dict[str, Any]


class CustoResumoResponse(BaseModel):
    """Resumo de custos por categoria no ciclo."""
    categoria: CategoriaCusto
    total_rs: float
    qtd_lancamentos: int
