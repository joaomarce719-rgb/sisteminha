"""SAD Carcinicultura — Schemas Pydantic para Ciclo Produtivo."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from src.models.enums import StatusCiclo


class CicloCreate(BaseModel):
    viveiro_id: UUID
    data_povoamento: date
    quantidade_pos_larvas: int = Field(..., gt=0)
    custo_aquisicao_pl: float = Field(..., ge=0)
    laboratorio_origem: str | None = Field(None, max_length=120)
    tabela_alimentar_id: UUID | None = None

    @model_validator(mode="before")
    @classmethod
    def map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data.get("data_povoamento") and data.get("data_inicio"):
            data["data_povoamento"] = data["data_inicio"]
        return data


class CicloEncerrar(BaseModel):
    data_despesca_real: date
    biomassa_colhida_kg: float = Field(..., gt=0)
    receita_real_rs: float = Field(..., ge=0)


class CicloResponse(BaseModel):
    id: UUID
    viveiro_id: UUID
    data_povoamento: date
    data_inicio: date | None = None
    quantidade_pos_larvas: int
    custo_aquisicao_pl: float
    laboratorio_origem: str | None
    status: StatusCiclo
    tabela_alimentar_id: UUID | None = None
    data_despesca_real: date | None
    biomassa_colhida_kg: float | None
    receita_real_rs: float | None
    # Densidade de estocagem (PLs/m²), derivada da área útil do viveiro
    densidade_inicial: float | None = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_virtual_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data["data_inicio"] = data.get("data_inicio") or data.get("data_povoamento")
            return data
        viveiro = getattr(data, "viveiro", None)
        densidade = None
        if viveiro is not None and viveiro.area_util_m2:
            densidade = round(data.quantidade_pos_larvas / viveiro.area_util_m2, 2)
        return {
            "id": data.id,
            "viveiro_id": data.viveiro_id,
            "data_povoamento": data.data_povoamento,
            "data_inicio": data.data_povoamento,
            "quantidade_pos_larvas": data.quantidade_pos_larvas,
            "custo_aquisicao_pl": data.custo_aquisicao_pl,
            "laboratorio_origem": data.laboratorio_origem,
            "status": data.status,
            "tabela_alimentar_id": data.tabela_alimentar_id,
            "data_despesca_real": data.data_despesca_real,
            "biomassa_colhida_kg": data.biomassa_colhida_kg,
            "receita_real_rs": data.receita_real_rs,
            "densidade_inicial": densidade,
            "created_at": data.created_at,
        }

    model_config = {"from_attributes": True}


class MetricasAtuaisResponse(BaseModel):
    """Métricas consolidadas do ciclo ativo (RF-09, RN-01..06, RN-015)."""
    ciclo_id: UUID
    viveiro_identificacao: str
    dias_cultivo: int
    densidade_estocagem: float
    alerta_hiperdensidade: bool

    # População e biomassa
    populacao_inicial: int
    taxa_sobrevivencia_fuzzy_pct: float
    populacao_estimada: int
    peso_medio_atual_g: float | None = None
    biomassa_atual_kg: float | None = None

    # Alimentação
    racao_acumulada_kg: float
    fca_atual: float | None = None
    classificacao_fca: str | None = None
    taxa_alimentar_clifford_pct: float | None = None
    racao_diaria_sugerida_kg: float | None = None

    # Financeiro (None = indisponível ou sem permissão — RN-015)
    custo_operacional_total_rs: float | None = None
    receita_bruta_estimada_rs: float | None = None
    lucro_operacional_rs: float | None = None
    margem_operacional_pct: float | None = None
    preco_venda_atual_rs_kg: float | None = None

    # Indicadores ausentes ou não calculáveis (RN-015)
    entradas_faltantes: list[str] = Field(default_factory=list)
