"""População do viveiro descontando os animais já vendidos (desbastes e despescas).

Cada venda expõe `data_venda`, `animais_estimados`, `biomassa_kg` e `valor_total_rs`. A taxa de
sobrevivência continua sendo a das pós-larvas originais; as vendas saem da população depois.
"""

from collections.abc import Iterable
from datetime import date

from src.services.decision_engine import calcular_populacao_atual


def animais_vendidos_ate(vendas: Iterable, ate: date | None = None) -> int:
    """Animais retirados nas vendas até a data (inclusive); sem data, todas as vendas."""
    return sum(v.animais_estimados or 0 for v in vendas if ate is None or v.data_venda <= ate)


def biomassa_vendida_kg(vendas: Iterable) -> float:
    return sum(float(v.biomassa_kg or 0) for v in vendas)


def receita_realizada_rs(vendas: Iterable) -> float:
    return sum(float(v.valor_total_rs or 0) for v in vendas)


def populacao_vigente(pos_larvas: int, taxa_sobrev_pct: float, vendas: Iterable, ate: date | None = None) -> int:
    """Pós-larvas × sobrevivência − animais vendidos até a data, nunca abaixo de zero."""
    return max(0, calcular_populacao_atual(pos_larvas, taxa_sobrev_pct) - animais_vendidos_ate(vendas, ate))
