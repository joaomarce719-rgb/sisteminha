"""SAD Carcinicultura — Schemas Pydantic do uso de insumo no ciclo."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import FaseCusto


class UsoInsumoCreate(BaseModel):
    """Também serve de corpo do PUT: a edição reenvia o uso inteiro."""

    model_config = ConfigDict(str_strip_whitespace=True)

    insumo_id: UUID
    data_uso: date
    # mínimo = escala da coluna Numeric(14,4); máximo = 10 dígitos inteiros
    quantidade: float = Field(..., ge=0.0001, le=9_999_999_999)
    fase: FaseCusto = FaseCusto.CULTIVO
    # etapa do preparo em que o insumo foi usado (do mesmo ciclo)
    etapa_id: UUID | None = None
    observacao: str | None = Field(None, max_length=500)
    retroativo: bool = False
    # correção do preço pelo gestor (nota fiscal); Numeric(12,4) = 8 dígitos inteiros
    preco_corrigido_rs: float | None = Field(None, ge=0.0001, le=99_999_999)


class UsoInsumoResponse(BaseModel):
    """`preco_unitario_rs`, `valor_rs`, `pendente_de_valor` e `preco_corrigido_rs` só para o GESTOR."""

    id: UUID
    insumo_id: UUID
    insumo_nome: str
    unidade_uso: str
    data_uso: date
    quantidade: float
    fase: FaseCusto
    etapa_id: UUID | None = None
    retroativo: bool
    observacao: str | None
    preco_unitario_rs: float | None = None
    valor_rs: float | None = None
    pendente_de_valor: bool | None = None
    # preço fixado pelo gestor (nota fiscal); o PUT precisa reenviá-lo para mantê-lo
    preco_corrigido_rs: float | None = None
    recalculado_em: datetime | None = None
