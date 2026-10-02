"""SAD Carcinicultura — Schemas Pydantic para Ronda Noturna e Aeradores."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.enums import (
    ClassificacaoOxigenio,
    ComportamentoCamarao,
    StatusEnergia,
)


class RondaNoturnaCreate(BaseModel):
    ciclo_id: UUID
    data_hora_ronda: datetime
    oxigenio_dissolvido_mg_l: float = Field(..., ge=0.0, le=20.0)
    temperatura_agua_c: float = Field(..., ge=15.0, le=40.0)
    comportamento: ComportamentoCamarao = ComportamentoCamarao.NORMAL_FUNDO
    observacoes: str | None = None

    # Aeradores (integrados no mesmo form para UX rápida)
    aeradores_instalados: int = Field(..., ge=1, le=30)
    aeradores_ligados: int = Field(..., ge=0, le=30)
    fonte_energia: StatusEnergia = StatusEnergia.REDE_CONCESSIONARIA
    falha_mecanica_detectada: bool = False
    detalhes_falha: str | None = None


class RondaNoturnaResponse(BaseModel):
    id: UUID
    ciclo_id: UUID
    vigia_id: UUID
    vigia_nome: str
    data_hora_ronda: datetime
    oxigenio_dissolvido_mg_l: float
    temperatura_agua_c: float
    comportamento: ComportamentoCamarao
    observacoes: str | None
    classificacao_oxigenio: ClassificacaoOxigenio
    created_at: datetime

    # Aeradores
    aeradores_instalados: int | None = None
    aeradores_ligados: int | None = None
    taxa_aeracao_pct: float | None = None
    fonte_energia: StatusEnergia | None = None
    falha_mecanica_detectada: bool | None = None

    model_config = {"from_attributes": True}


class PainelNoturnoResponse(BaseModel):
    """Painel consolidado da última noite para todos os viveiros (RF-15)."""
    viveiro_id: UUID
    viveiro_identificacao: str
    rondas: list[RondaNoturnaResponse]
    o2_minimo: float | None
    o2_maximo: float | None
    alertas_criticos: int
