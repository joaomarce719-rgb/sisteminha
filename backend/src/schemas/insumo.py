"""SAD Carcinicultura — Schemas Pydantic de insumos e compras."""

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from src.models.enums import CategoriaCusto

# Ração e pós-larvas continuam sendo custos próprios (manejo alimentar e povoamento)
_CATEGORIAS_FORA_DE_INSUMO = (CategoriaCusto.RACAO, CategoriaCusto.POS_LARVAS)


def _categoria_de_insumo(categoria: CategoriaCusto) -> CategoriaCusto:
    if categoria in _CATEGORIAS_FORA_DE_INSUMO:
        raise ValueError("RACAO e POS_LARVAS não podem ser categoria de insumo.")
    return categoria


CategoriaInsumo = Annotated[CategoriaCusto, AfterValidator(_categoria_de_insumo)]


class InsumoCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nome: str = Field(..., min_length=1, max_length=120)
    unidade_uso: str = Field(..., min_length=1, max_length=20)
    categoria: CategoriaInsumo = CategoriaCusto.OUTROS


class InsumoUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nome: str | None = Field(None, min_length=1, max_length=120)
    unidade_uso: str | None = Field(None, min_length=1, max_length=20)
    categoria: CategoriaInsumo | None = None
    ativo: bool | None = None


class InsumoResponse(BaseModel):
    """`saldo` não vai para o VIGIA; `preco_medio_rs` e `saldo_negativo` só para o GESTOR."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    unidade_uso: str
    categoria: CategoriaCusto
    ativo: bool
    saldo: float | None = None
    preco_medio_rs: float | None = None
    saldo_negativo: bool | None = None


class CompraCreate(BaseModel):
    """Também serve de corpo do PUT: a edição reenvia a compra inteira."""

    model_config = ConfigDict(str_strip_whitespace=True)

    data_compra: date
    # mínimo = escala da coluna (Numeric(14,4) / Numeric(12,2)): abaixo dele o valor gravado vira 0;
    # máximo = 10 dígitos inteiros das colunas
    quantidade: float = Field(..., ge=0.0001, le=9_999_999_999)
    valor_total_rs: float = Field(..., ge=0.01, le=9_999_999_999)
    fornecedor: str | None = Field(None, max_length=120)
    observacao: str | None = Field(None, max_length=500)
    retroativo: bool = False


class CompraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    insumo_id: UUID
    data_compra: date
    quantidade: float
    valor_total_rs: float
    fornecedor: str | None
    observacao: str | None
    retroativo: bool
    created_at: datetime
