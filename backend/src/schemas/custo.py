"""SAD Carcinicultura — Schemas Pydantic para Custos Operacionais."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.enums import CategoriaCusto


from typing import Any
from pydantic import BaseModel, Field, model_validator


class CustoCreate(BaseModel):
    ciclo_id: UUID | None = None
    data_lancamento: date = Field(default_factory=date.today)
    categoria: CategoriaCusto = CategoriaCusto.OUTROS
    descricao: str = Field(..., min_length=3, max_length=255)
    valor_rs: float = Field(..., gt=0)
    valor: float | None = None
    data: date | None = None

    @model_validator(mode="before")
    @classmethod
    def map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Mapeia data se data_lancamento não fornecida
            if "data_lancamento" not in data or data["data_lancamento"] is None:
                if "data" in data and data["data"] is not None:
                    data["data_lancamento"] = data["data"]
            # Mapeia valor se valor_rs não fornecido
            if "valor_rs" not in data or data["valor_rs"] is None:
                for k in ("valor", "amount", "value"):
                    if k in data and data[k] is not None:
                        data["valor_rs"] = data[k]
                        break
            # Mapeia categoria
            if "categoria" in data and data["categoria"] is not None:
                cat = str(data.get("categoria", "")).upper()
                if "ENERG" in cat:
                    data["categoria"] = CategoriaCusto.ENERGIA_ELETRICA
                elif "RACAO" in cat or "FEED" in cat:
                    data["categoria"] = CategoriaCusto.RACAO
                elif "OBRA" in cat or "LABOR" in cat:
                    data["categoria"] = CategoriaCusto.MAO_DE_OBRA
                elif "LARVA" in cat or "PL" in cat:
                    data["categoria"] = CategoriaCusto.POS_LARVAS
                elif "MANUT" in cat:
                    data["categoria"] = CategoriaCusto.MANUTENCAO
                elif cat in [c.value for c in CategoriaCusto]:
                    data["categoria"] = cat
                else:
                    data["categoria"] = CategoriaCusto.OUTROS
        return data


class CustoResponse(BaseModel):
    id: UUID
    ciclo_id: UUID | None = None
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
            val = data.get("valor_rs") or data.get("valor") or 0.0
            dl = data.get("data_lancamento") or data.get("data") or date.today()
            data["valor"] = val
            data["valor_rs"] = val
            data["data"] = dl
            return data
        val = getattr(data, "valor_rs", 0.0)
        dl = getattr(data, "data_lancamento", date.today())
        return {
            "id": getattr(data, "id", None),
            "ciclo_id": getattr(data, "ciclo_id", None),
            "data_lancamento": dl,
            "data": dl,
            "categoria": getattr(data, "categoria", CategoriaCusto.OUTROS),
            "descricao": getattr(data, "descricao", ""),
            "valor_rs": val,
            "valor": val,
            "created_at": getattr(data, "created_at", datetime.now()),
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

