"""Preço médio ponderado móvel dos insumos (regras puras, sem acesso a banco)."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class EventoInsumo:
    id: UUID
    tipo: Literal["COMPRA", "USO"]
    data: date
    criado_em: datetime
    quantidade: float
    valor_total_rs: float | None = None  # só nas compras
    preco_corrigido_rs: float | None = None  # só nos usos corrigidos pelo gestor


@dataclass(frozen=True)
class ResultadoUso:
    uso_id: UUID
    preco_unitario_rs: float | None  # None = pendente de valor
    saldo_apos: float


def aplicar_preco_medio(
    eventos: list[EventoInsumo],
) -> tuple[list[ResultadoUso], float | None, float]:
    """Reaplica compras e usos em ordem e devolve (resultado de cada uso, preço médio final, saldo final).

    Na mesma data a compra vem antes do uso; depois vale a ordem de criação.
    """
    ordenados = sorted(eventos, key=lambda e: (e.data, e.tipo != "COMPRA", e.criado_em))
    saldo = 0.0
    preco_medio: float | None = None
    usos: list[ResultadoUso] = []
    for e in ordenados:
        if e.tipo == "COMPRA":
            base = max(saldo, 0.0)  # saldo negativo (uso sem estoque) não pesa no novo preço
            preco_medio = (base * (preco_medio or 0.0) + e.valor_total_rs) / (base + e.quantidade)
            saldo += e.quantidade
        else:
            saldo -= e.quantidade
            preco = e.preco_corrigido_rs if e.preco_corrigido_rs is not None else preco_medio
            usos.append(ResultadoUso(e.id, preco, saldo))
    return usos, preco_medio, saldo
