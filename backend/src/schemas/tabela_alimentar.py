"""SAD Carcinicultura — Schemas Pydantic para Tabela Alimentar (RF-010, Critério 5)."""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class FaixaAlimentarItem(BaseModel):
    """Ponto de calibração de arraçoamento (% da biomassa por peso médio em gramas)."""

    peso_g: float = Field(..., gt=0, description="Peso médio do camarão em gramas")
    taxa_pct: float = Field(..., gt=0, description="Percentual da biomassa a ser arraçoado por dia")


class TabelaAlimentarCreate(BaseModel):
    """Payload para criação de nova tabela ou nova versão."""

    nome: str = Field(..., min_length=2, max_length=120)
    descricao: str | None = Field(None, max_length=255)
    is_padrao: bool = False
    faixas: list[FaixaAlimentarItem] = Field(..., min_length=2)


class TabelaAlimentarUpdate(BaseModel):
    """Payload para atualização ou inativação."""

    nome: str | None = Field(None, min_length=2, max_length=120)
    descricao: str | None = None
    is_padrao: bool | None = None
    ativo: bool | None = None
    faixas: list[FaixaAlimentarItem] | None = Field(None, min_length=2)


class TabelaAlimentarResponse(BaseModel):
    """Resposta com dados completos da tabela de arraçoamento."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    versao: int
    descricao: str | None = None
    is_padrao: bool
    ativo: bool
    faixas: list[FaixaAlimentarItem]
    created_at: datetime
    updated_at: datetime
