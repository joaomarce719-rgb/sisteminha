"""SAD Carcinicultura — Schemas Pydantic para Organização (RF-002, RF-003)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


RegraArredondamento = Literal["PARA_BAIXO", "PARA_CIMA", "PROPORCIONAL"]


class OrganizacaoCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=120)
    identificador: str | None = Field(None, max_length=30)
    moeda: str = Field("BRL", max_length=3)


class OrganizacaoUpdate(BaseModel):
    nome: str | None = Field(None, min_length=2, max_length=120)
    identificador: str | None = Field(None, max_length=30)
    moeda: str | None = Field(None, max_length=3)
    status_ativo: bool | None = None
    regra_arredondamento: RegraArredondamento | None = None


class OrganizacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    identificador: str | None = None
    moeda: str
    status_ativo: bool
    regra_arredondamento: RegraArredondamento
    created_at: datetime
