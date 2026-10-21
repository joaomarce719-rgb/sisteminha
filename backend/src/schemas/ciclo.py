"""SAD Carcinicultura — Schemas Pydantic para Ciclo Produtivo."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.enums import StatusCiclo


from typing import Any
from pydantic import BaseModel, Field, model_validator


class CicloCreate(BaseModel):
    viveiro_id: UUID
    data_povoamento: date
    quantidade_pos_larvas: int = Field(..., gt=0)
    custo_aquisicao_pl: float = Field(..., ge=0)
    laboratorio_origem: str | None = Field(None, max_length=120)
    tabela_alimentar_id: UUID | None = None
    descricao: str | None = None
    densidade_inicial: float | None = None
    biomassa_inicial: float | None = None

    @model_validator(mode="before")
    @classmethod
    def map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Mapeia data_inicio para data_povoamento
            if not data.get("data_povoamento"):
                data["data_povoamento"] = data.get("data_inicio") or date.today()
            # Mapeia quantidade de pós-larvas
            if not data.get("quantidade_pos_larvas"):
                dens = data.get("densidade_inicial")
                if dens and float(dens) > 0:
                    data["quantidade_pos_larvas"] = int(float(dens) * 1000)
                else:
                    data["quantidade_pos_larvas"] = 50000
            # Mapeia custo de aquisição
            if data.get("custo_aquisicao_pl") is None:
                data["custo_aquisicao_pl"] = 0.0
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
    densidade_inicial: float | None = None
    biomassa_inicial: float | None = None
    descricao: str | None = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_virtual_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data["data_inicio"] = data.get("data_inicio") or data.get("data_povoamento")
            return data
        dp = getattr(data, "data_povoamento", None)
        return {
            "id": getattr(data, "id", None),
            "viveiro_id": getattr(data, "viveiro_id", None),
            "data_povoamento": dp,
            "data_inicio": dp,
            "quantidade_pos_larvas": getattr(data, "quantidade_pos_larvas", 50000),
            "custo_aquisicao_pl": getattr(data, "custo_aquisicao_pl", 0.0),
            "laboratorio_origem": getattr(data, "laboratorio_origem", None),
            "status": getattr(data, "status", StatusCiclo.ATIVO),
            "tabela_alimentar_id": getattr(data, "tabela_alimentar_id", None),
            "data_despesca_real": getattr(data, "data_despesca_real", None),
            "biomassa_colhida_kg": getattr(data, "biomassa_colhida_kg", None),
            "receita_real_rs": getattr(data, "receita_real_rs", None),
            "densidade_inicial": 10.0,
            "biomassa_inicial": 100.0,
            "descricao": "Ciclo de Produção",
            "created_at": getattr(data, "created_at", datetime.now()),
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

    # Financeiro
    custo_operacional_total_rs: float
    receita_bruta_estimada_rs: float | None = None
    lucro_operacional_rs: float | None = None
    margem_operacional_pct: float | None = None
    preco_venda_atual_rs_kg: float | None = None

    # Indicadores ausentes ou não calculáveis (RN-015)
    entradas_faltantes: list[str] = Field(default_factory=list)

