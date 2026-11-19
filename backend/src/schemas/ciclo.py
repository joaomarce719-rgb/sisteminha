"""SAD Carcinicultura — Schemas Pydantic para Ciclo Produtivo."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from src.models.enums import StatusCiclo
from src.schemas.manejo_alimentar import ConfrontoVivosResponse


class CicloPlanejar(BaseModel):
    """Planejamento: a data é só a prevista (qualquer data). Campos desconhecidos dão 422,
    para que um cliente antigo que envia pós-larvas falhe em vez de criar um ciclo planejado."""

    model_config = {"extra": "forbid"}

    viveiro_id: UUID
    data_povoamento: date
    tabela_alimentar_id: UUID | None = None

    @model_validator(mode="before")
    @classmethod
    def map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict) and "data_inicio" in data:
            data = dict(data)
            data_inicio = data.pop("data_inicio")
            data.setdefault("data_povoamento", data_inicio)
        return data


class CicloReagendar(BaseModel):
    """Só os campos enviados mudam; data e viveiro não podem ser apagados."""

    model_config = {"extra": "forbid"}

    data_povoamento: date | None = None
    tabela_alimentar_id: UUID | None = None
    viveiro_id: UUID | None = None

    @model_validator(mode="after")
    def obrigatorios_nao_nulos(self) -> "CicloReagendar":
        for campo in ("data_povoamento", "viveiro_id"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"O campo {campo} não pode ser vazio.")
        return self


class CicloPovoar(BaseModel):
    data_povoamento: date
    # limites = colunas Integer (32 bits) e Numeric(12,2)
    quantidade_pos_larvas: int = Field(..., gt=0, le=2_147_483_647)
    custo_aquisicao_pl: float = Field(..., ge=0, le=9_999_999_999.99)
    peso_medio_pl_g: float | None = Field(None, ge=0, le=5)
    laboratorio_origem: str | None = Field(None, max_length=120)


class CicloEncerrar(BaseModel):
    """Biomassa e receita vêm juntas (viram a venda da despesca final) ou nenhuma (valem as vendas lançadas)."""

    data_despesca_real: date | None = None
    # limites = escala e dígitos das colunas da venda (abaixo/acima o valor gravado muda ou estoura)
    biomassa_colhida_kg: float | None = Field(None, ge=0.01, le=9_999_999_999)
    receita_real_rs: float | None = Field(None, ge=0, le=9_999_999_999.99)

    @model_validator(mode="after")
    def biomassa_e_receita_juntas(self) -> "CicloEncerrar":
        if (self.biomassa_colhida_kg is None) != (self.receita_real_rs is None):
            raise ValueError("Informe a biomassa colhida e a receita real juntas, ou nenhuma das duas.")
        return self


class CicloResponse(BaseModel):
    id: UUID
    viveiro_id: UUID
    data_povoamento: date
    data_inicio: date | None = None
    # vazios no ciclo PLANEJADO (antes do povoamento)
    quantidade_pos_larvas: int | None = None
    custo_aquisicao_pl: float | None = None
    peso_medio_pl_g: float | None = None
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
        if viveiro is not None and viveiro.area_util_m2 and data.quantidade_pos_larvas is not None:
            densidade = round(data.quantidade_pos_larvas / viveiro.area_util_m2, 2)
        return {
            "id": data.id,
            "viveiro_id": data.viveiro_id,
            "data_povoamento": data.data_povoamento,
            "data_inicio": data.data_povoamento,
            "quantidade_pos_larvas": data.quantidade_pos_larvas,
            "custo_aquisicao_pl": data.custo_aquisicao_pl,
            "peso_medio_pl_g": data.peso_medio_pl_g,
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
    densidade_atual: float | None = None  # população atual (descontadas as vendas) ÷ área
    alerta_hiperdensidade: bool

    # População e biomassa
    populacao_inicial: int
    taxa_sobrevivencia_fuzzy_pct: float
    # Vivos pela contagem de mortos x vivos pela alimentação
    confronto_vivos: ConfrontoVivosResponse | None = None
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
    lucro_operacional_rs: float | None = None  # lucro estimado se despescar hoje, já com as vendas
    margem_operacional_pct: float | None = None
    preco_venda_atual_rs_kg: float | None = None
    receita_realizada_rs: float | None = None  # soma das vendas já feitas
    lucro_realizado_rs: float | None = None    # receita realizada − custo operacional total

    # Indicadores ausentes ou não calculáveis (RN-015)
    entradas_faltantes: list[str] = Field(default_factory=list)
