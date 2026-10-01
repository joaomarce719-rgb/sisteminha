"""SAD Carcinicultura — Schemas Pydantic para Ciclo Produtivo."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.enums import StatusCiclo


class CicloCreate(BaseModel):
    viveiro_id: UUID
    data_povoamento: date
    quantidade_pos_larvas: int = Field(..., gt=0)
    custo_aquisicao_pl: float = Field(..., ge=0)
    laboratorio_origem: str | None = Field(None, max_length=120)


class CicloEncerrar(BaseModel):
    data_despesca_real: date
    biomassa_colhida_kg: float = Field(..., gt=0)
    receita_real_rs: float = Field(..., ge=0)


class CicloResponse(BaseModel):
    id: UUID
    viveiro_id: UUID
    data_povoamento: date
    quantidade_pos_larvas: int
    custo_aquisicao_pl: float
    laboratorio_origem: str | None
    status: StatusCiclo
    data_despesca_real: date | None
    biomassa_colhida_kg: float | None
    receita_real_rs: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MetricasAtuaisResponse(BaseModel):
    """Métricas consolidadas do ciclo ativo (RF-09, RN-01..06)."""
    ciclo_id: UUID
    viveiro_identificacao: str
    dias_cultivo: int
    densidade_estocagem: float
    alerta_hiperdensidade: bool

    # População e biomassa
    populacao_inicial: int
    taxa_sobrevivencia_fuzzy_pct: float
    populacao_estimada: int
    peso_medio_atual_g: float
    biomassa_atual_kg: float

    # Alimentação
    racao_acumulada_kg: float
    fca_atual: float | None
    classificacao_fca: str | None
    taxa_alimentar_clifford_pct: float
    racao_diaria_sugerida_kg: float

    # Financeiro
    custo_operacional_total_rs: float
    receita_bruta_estimada_rs: float
    lucro_operacional_rs: float
    margem_operacional_pct: float | None
    preco_venda_atual_rs_kg: float | None
