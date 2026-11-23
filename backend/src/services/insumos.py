"""Preço médio ponderado móvel dos insumos: regras puras (`aplicar_preco_medio`) e leitura do banco."""

import unicodedata
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.ciclo_produtivo import CicloProdutivo
from src.models.custo_operacional import CustoOperacional
from src.models.enums import CategoriaCusto, StatusCiclo
from src.models.insumo import CompraInsumo, ConsumoInsumo, Insumo
from src.models.usuario import Usuario
from src.services.audit import registrar_auditoria


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


def _em_utc(momento: datetime) -> datetime:
    """Criação em UTC sem fuso: objetos recém-criados vêm com fuso e o SQLite devolve sem."""
    return momento.astimezone(timezone.utc).replace(tzinfo=None) if momento.tzinfo else momento


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
        EventoInsumo(c.id, "COMPRA", c.data_compra, _em_utc(c.created_at), float(c.quantidade), float(c.valor_total_rs))
        for c in compras
    ] + [
        EventoInsumo(
            u.id, "USO", u.data_uso, _em_utc(u.created_at), float(u.quantidade),
            preco_corrigido_rs=None if u.preco_corrigido_rs is None else float(u.preco_corrigido_rs),
        )
        for u in usos
    ]


def situacao_do_insumo(db: Session, insumo_id: UUID) -> tuple[float | None, float]:
    """(preço médio, saldo) atuais do insumo; o preço médio é None enquanto não há compra."""
    _, preco_medio, saldo = aplicar_preco_medio(eventos_do_insumo(db, insumo_id))
    return preco_medio, saldo


def _texto_da_quantidade(quantidade: float) -> str:
    return f"{quantidade:.4f}".rstrip("0").rstrip(".")


def reprocessar_insumo(
    db: Session, insumo_id: UUID, usuario: Usuario | None = None, uso_alterado: UUID | None = None
) -> None:
    """Reaplica compras e usos do insumo e acerta preço aplicado e custo gerado de cada uso.

    Uso pendente (sem compra até a data e sem preço corrigido) fica sem custo. Quando o custo de
    um uso de ciclo FINALIZADO muda, o uso recebe `recalculado_em` e a mudança vai para a auditoria;
    o uso que o próprio gestor acabou de lançar ou editar (`uso_alterado`) não conta como recálculo.
    """
    insumo = db.get(Insumo, insumo_id)
    resultados = {r.uso_id: r for r in aplicar_preco_medio(eventos_do_insumo(db, insumo_id))[0]}
    usos = db.scalars(select(ConsumoInsumo).where(ConsumoInsumo.insumo_id == insumo_id)).all()
    finalizados = set(db.scalars(
        select(CicloProdutivo.id).where(
            CicloProdutivo.id.in_({u.ciclo_id for u in usos}), CicloProdutivo.status == StatusCiclo.FINALIZADO
        )
    ))
    for uso in usos:
        preco = resultados[uso.id].preco_unitario_rs
        quantidade = float(uso.quantidade)
        valor = None if preco is None else round(quantidade * preco, 2)
        custo = db.get(CustoOperacional, uso.custo_id) if uso.custo_id else None
        valor_anterior = None if custo is None else float(custo.valor_rs)

        uso.preco_unitario_rs = None if preco is None else round(preco, 4)
        if valor is None:
            if custo is not None:
                uso.custo_id = None
                db.delete(custo)
        else:
            if custo is None:
                custo = CustoOperacional(id=uuid.uuid4(), ciclo_id=uso.ciclo_id)  # id já, para um flush só no fim
                db.add(custo)
            custo.data_lancamento = uso.data_uso
            custo.categoria = CategoriaCusto(insumo.categoria)
            custo.descricao = f"{insumo.nome} ({_texto_da_quantidade(quantidade)} {insumo.unidade_uso})"
            custo.valor_rs = valor
            custo.fase = uso.fase
            uso.custo_id = custo.id

        if valor != valor_anterior and uso.id != uso_alterado and uso.ciclo_id in finalizados:
            uso.recalculado_em = datetime.now(timezone.utc)
            registrar_auditoria(
                db, "RECALCULAR_USO_INSUMO", "ConsumoInsumo", uso.id, usuario,
                dados_anteriores={"valor_rs": valor_anterior}, dados_novos={"valor_rs": valor},
            )
    db.flush()
