"""SAD Carcinicultura — Schemas Pydantic das vendas do ciclo (desbaste e despesca final)."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

TipoVenda = Literal["DESBASTE", "DESPESCA_FINAL"]


class VendaCreate(BaseModel):
    """Também serve de corpo do PUT: a edição reenvia a venda inteira.

    `preco_kg` omitido usa o preço sugerido pela tabela de preços da organização.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    data_venda: date
    tipo: TipoVenda
    # mínimos = escala da coluna (abaixo dele o valor gravado vira 0); máximos = dígitos inteiros das colunas
    biomassa_kg: float = Field(..., ge=0.01, le=9_999_999_999)
    peso_medio_g: float = Field(..., ge=0.01, le=999_999)
    preco_kg: float | None = Field(None, ge=0, le=99_999_999)
    comprador: str | None = Field(None, max_length=120)
    observacao: str | None = Field(None, max_length=500)
    retroativo: bool = False


class VendaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ciclo_id: UUID
    data_venda: date
    tipo: TipoVenda
    biomassa_kg: float
    peso_medio_g: float
    animais_estimados: int
    preco_kg: float
    valor_total_rs: float
    comprador: str | None
    observacao: str | None
    retroativo: bool
    created_at: datetime


class PrecoSugeridoResponse(BaseModel):
    preco_kg: float | None
