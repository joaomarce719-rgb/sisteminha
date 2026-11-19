"""SAD Carcinicultura — Schemas do financeiro do ciclo e do histórico do viveiro.

Campos em reais vêm `None` para CAMPO e VIGIA (só o histórico; o financeiro é só do GESTOR).
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from src.models.enums import StatusCiclo
from src.schemas.venda import VendaResponse


class CustoFaseCategoria(BaseModel):
    fase: str
    categoria: str
    total_rs: float


class FinanceiroCicloResponse(BaseModel):
    custos_por_fase: dict[str, float]
    custos_por_categoria: dict[str, float]
    custos_fase_categoria: list[CustoFaseCategoria]
    vendas: list[VendaResponse]
    receita_realizada_rs: float
    custo_total_rs: float
    # receita das vendas − custos lançados; definitivo com o ciclo finalizado
    lucro_realizado_rs: float
    margem_realizada_pct: float | None
    # lucro realizado + biomassa na água × preço de hoje; None no ciclo finalizado ou sem biometria/preço
    lucro_estimado_se_despescar_hoje_rs: float | None
    custo_por_kg_rs: float | None
    definitivo: bool
    usos_pendentes: int
    valores_recalculados_em: datetime | None


class EtapaHistorico(BaseModel):
    tipo: str
    status: str
    data_inicio: date | None
    data_fim: date | None


class InsumoHistorico(BaseModel):
    insumo_id: UUID
    nome: str
    unidade_uso: str
    quantidade_total: float
    custo_total_rs: float | None


class SemanaRacao(BaseModel):
    inicio: date
    fim: date
    kg: float
    custo_rs: float | None
    fca_parcial: float | None


class VendasHistorico(BaseModel):
    quantidade: int
    biomassa_total_kg: float
    receita_rs: float | None


class HistoricoCicloResponse(BaseModel):
    ciclo_id: UUID
    status: StatusCiclo
    data_povoamento: date
    data_despesca_real: date | None
    quantidade_pos_larvas: int | None
    etapas: list[EtapaHistorico]
    insumos: list[InsumoHistorico]
    racao_total_kg: float
    racao_custo_rs: float | None
    racao_por_semana: list[SemanaRacao]
    vendas: VendasHistorico
    peso_final_g: float | None
    sobrevivencia_final_pct: float | None
    fca: float | None
    custo_total_rs: float | None
    lucro_realizado_rs: float | None
    margem_pct: float | None
    custo_por_kg_rs: float | None
