"""SAD Carcinicultura — Schemas Pydantic para Simulação de Despesca (Δ V)."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.enums import RecomendacaoDespesca


class SimulacaoRequest(BaseModel):
    dias_horizonte: int = Field(..., description="Horizonte de projeção: 7, 10 ou 15 dias")
    preco_kg_customizado: float | None = Field(
        None, gt=0,
        description="Se null, busca da tabela de preços vigente"
    )

    def model_post_init(self, __context) -> None:
        if self.dias_horizonte not in (7, 10, 15):
            raise ValueError("dias_horizonte deve ser 7, 10 ou 15")


class SimulacaoResponse(BaseModel):
    """Resultado completo da simulação de despesca (RF-06, RN-07)."""
    ciclo_id: UUID
    data_referencia: date

    # Estado atual
    peso_medio_atual_g: float
    biomassa_atual_kg: float
    lucro_operacional_atual_rs: float

    # Projeção
    dias_horizonte: int
    peso_medio_projetado_g: float
    biomassa_projetada_kg: float
    receita_projetada_rs: float
    custo_adicional_projetado_rs: float
    lucro_projetado_rs: float

    # Decisão
    delta_v_rs: float
    recomendacao: RecomendacaoDespesca
    justificativa: str


class SimulacaoComparativaResponse(BaseModel):
    """Comparativo para os 3 horizontes (7, 10, 15 dias)."""
    simulacoes: list[SimulacaoResponse]
    melhor_cenario: SimulacaoResponse | None
