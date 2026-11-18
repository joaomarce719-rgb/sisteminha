"""Preço médio ponderado móvel dos insumos: regras puras (`aplicar_preco_medio`) e leitura do banco."""

import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.insumo import CompraInsumo, ConsumoInsumo


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


def chave_do_nome(nome: str) -> str:
    """Nome sem acentos, em minúsculas e com espaços simples: a unicidade do insumo na organização."""
    sem_acento = "".join(c for c in unicodedata.normalize("NFKD", nome) if not unicodedata.combining(c))
    return " ".join(sem_acento.casefold().split())


def eventos_do_insumo(db: Session, insumo_id: UUID) -> list[EventoInsumo]:
    """Compras e usos do insumo, lidos por (data, criação, id) para o desempate ser estável."""
    compras = db.scalars(
        select(CompraInsumo)
        .where(CompraInsumo.insumo_id == insumo_id)
        .order_by(CompraInsumo.data_compra, CompraInsumo.created_at, CompraInsumo.id)
    )
    usos = db.scalars(
        select(ConsumoInsumo)
        .where(ConsumoInsumo.insumo_id == insumo_id)
        .order_by(ConsumoInsumo.data_uso, ConsumoInsumo.created_at, ConsumoInsumo.id)
    )
    return [
        EventoInsumo(c.id, "COMPRA", c.data_compra, c.created_at, float(c.quantidade), float(c.valor_total_rs))
        for c in compras
    ] + [
        EventoInsumo(
            u.id, "USO", u.data_uso, u.created_at, float(u.quantidade),
            preco_corrigido_rs=None if u.preco_corrigido_rs is None else float(u.preco_corrigido_rs),
        )
        for u in usos
    ]


def situacao_do_insumo(db: Session, insumo_id: UUID) -> tuple[float | None, float]:
    """(preço médio, saldo) atuais do insumo; o preço médio é None enquanto não há compra."""
    _, preco_medio, saldo = aplicar_preco_medio(eventos_do_insumo(db, insumo_id))
    return preco_medio, saldo


def reprocessar_insumo(db: Session, insumo_id: UUID) -> None:
    """Recalcula preço e custo dos usos do insumo depois de uma compra.

    Sem efeito por enquanto: os usos de insumo (e o recálculo) chegam com as rotas de uso.
    """
    pass
