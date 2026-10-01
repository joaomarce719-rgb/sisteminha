"""SAD Carcinicultura — Schemas Pydantic para Custos Operacionais."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.enums import CategoriaCusto


class CustoCreate(BaseModel):
    data_lancamento: date
    categoria: CategoriaCusto
    descricao: str = Field(..., min_length=3, max_length=255)
    valor_rs: float = Field(..., gt=0)


class CustoResponse(BaseModel):
    id: UUID
    ciclo_id: UUID
    data_lancamento: date
    categoria: CategoriaCusto
    descricao: str
    valor_rs: float
    created_at: datetime

    model_config = {"from_attributes": True}


class CustoResumoResponse(BaseModel):
    """Resumo de custos por categoria no ciclo."""
    categoria: CategoriaCusto
    total_rs: float
    qtd_lancamentos: int
