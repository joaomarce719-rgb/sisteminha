"""Preço médio ponderado móvel dos insumos (função pura, sem banco)."""

from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest
from src.services.insumos import EventoInsumo, aplicar_preco_medio

BASE = datetime(2026, 1, 1, 8, 0)


def compra(dia: int, quantidade: float, valor: float, criado: int = 0) -> EventoInsumo:
    return EventoInsumo(
        id=uuid4(),
        tipo="COMPRA",
        data=date(2026, 1, dia),
        criado_em=BASE + timedelta(minutes=criado),
        quantidade=quantidade,
        valor_total_rs=valor,
    )


def uso(
    dia: int, quantidade: float, criado: int = 0, preco_corrigido: float | None = None
) -> EventoInsumo:
    return EventoInsumo(
        id=uuid4(),
        tipo="USO",
        data=date(2026, 1, dia),
        criado_em=BASE + timedelta(minutes=criado),
        quantidade=quantidade,
        preco_corrigido_rs=preco_corrigido,
    )


def test_exemplo_da_cal():
    c1, c2, u, c3 = compra(1, 100, 300), compra(2, 100, 400), uso(3, 50), compra(4, 150, 750)

    usos, preco_final, saldo_final = aplicar_preco_medio([c1, c2, u, c3])

    assert len(usos) == 1
    assert usos[0].uso_id == u.id
    assert usos[0].preco_unitario_rs == pytest.approx(3.50)
    assert usos[0].saldo_apos == pytest.approx(150)
    assert preco_final == pytest.approx(4.25)
    assert saldo_final == pytest.approx(300)


def test_compra_processa_antes_do_uso_na_mesma_data():
    # o uso foi criado antes da compra, mas a compra do mesmo dia vale primeiro
    u = uso(1, 10, criado=0)
    c = compra(1, 100, 300, criado=5)

    usos, _, _ = aplicar_preco_medio([u, c])

    assert usos[0].preco_unitario_rs == pytest.approx(3.00)
    assert usos[0].saldo_apos == pytest.approx(90)


def test_uso_sem_compra_anterior_fica_pendente():
    u = uso(1, 10)

    usos, preco_final, saldo_final = aplicar_preco_medio([u])

    assert usos[0].preco_unitario_rs is None
    assert usos[0].saldo_apos == -10
    assert preco_final is None
    assert saldo_final == -10


def test_saldo_insuficiente_usa_ultimo_preco_medio_e_fica_negativo():
    c1, u, c2 = compra(1, 100, 300), uso(2, 120), compra(3, 100, 500)

    usos, preco_final, saldo_final = aplicar_preco_medio([c1, u, c2])

    assert usos[0].preco_unitario_rs == pytest.approx(3.00)
    assert usos[0].saldo_apos == pytest.approx(-20)
    # saldo negativo é ignorado no novo preço médio: 500 / 100
    assert preco_final == pytest.approx(5.00)
    assert saldo_final == pytest.approx(80)


def test_preco_corrigido_vence_o_preco_medio():
    c, u1, u2 = compra(1, 100, 300), uso(2, 10, preco_corrigido=7.5), uso(3, 10)

    usos, preco_final, saldo_final = aplicar_preco_medio([c, u1, u2])

    por_id = {r.uso_id: r for r in usos}
    assert por_id[u1.id].preco_unitario_rs == pytest.approx(7.5)
    assert por_id[u2.id].preco_unitario_rs == pytest.approx(3.00)  # o corrigido não mexe no médio
    assert preco_final == pytest.approx(3.00)
    assert saldo_final == pytest.approx(80)


def test_ordem_por_data_depois_tipo_depois_criacao():
    eventos = [
        compra(1, 100, 300, criado=0),
        compra(1, 100, 500, criado=1),  # mesma data: ordem de criação
        uso(2, 50, criado=0),
        compra(2, 100, 700, criado=1),  # mesma data do uso: compra vem antes
        uso(3, 30, criado=0),
    ]
    esperado = aplicar_preco_medio(eventos)

    for embaralhado in (eventos[::-1], [eventos[3], eventos[0], eventos[4], eventos[2], eventos[1]]):
        assert aplicar_preco_medio(embaralhado) == esperado
