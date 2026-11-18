"""População, FCA, sobrevivência implícita e lucro com vendas (desbastes)."""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from src.services import decision_engine as de
from src.services.populacao import (
    animais_vendidos_ate,
    biomassa_vendida_kg,
    populacao_vigente,
    receita_realizada_rs,
)
from src.services.sobrevivencia import MIN_DIAS_COM_REGISTRO, DiaManejo, sobrevivencia_implicita_pct
from src.models.enums import NivelSobraBandeja

HOJE = date(2026, 11, 18)


def venda(data=HOJE, animais=10_000, biomassa=100.0, valor=3_000.0):
    return SimpleNamespace(data_venda=data, animais_estimados=animais, biomassa_kg=biomassa, valor_total_rs=valor)


def test_populacao_desconta_animais_vendidos():
    assert populacao_vigente(300_000, 80.0, [venda()]) == 230_000
    assert populacao_vigente(300_000, 80.0, []) == de.calcular_populacao_atual(300_000, 80.0)


def test_venda_posterior_a_data_de_referencia_nao_desconta():
    vendas = [venda(data=HOJE - timedelta(days=5)), venda(data=HOJE, animais=20_000)]
    assert populacao_vigente(300_000, 80.0, vendas, ate=HOJE - timedelta(days=1)) == 230_000
    assert populacao_vigente(300_000, 80.0, vendas, ate=HOJE) == 210_000
    assert animais_vendidos_ate(vendas, HOJE - timedelta(days=6)) == 0


def test_desbaste_maior_que_a_populacao_zera_sem_ficar_negativo():
    vendas = [venda(animais=500_000, biomassa=5_000.0, valor=150_000.0)]
    pop = populacao_vigente(300_000, 80.0, vendas)
    assert pop == 0
    biomassa = de.calcular_biomassa_kg(pop, 12.0)
    assert biomassa == 0.0
    assert de.calcular_fca(1_000.0, biomassa, 50.0) is None
    assert de.calcular_fca(1_000.0, 0.0, 50.0, biomassa_vendida_kg=0.0) is None
    m = de.calcular_metricas_economicas([10_000.0], biomassa, 30.0, receita_realizada_rs=0.0)
    assert m.receita_bruta == 0.0 and m.margem_operacional_pct is None
    m = de.calcular_metricas_economicas([10_000.0], biomassa, 30.0, receita_realizada_rs=receita_realizada_rs(vendas))
    assert m.lucro_operacional == pytest.approx(140_000.0)
    r = de.simular_delta_v(
        dias_horizonte=7, peso_medio_atual_g=12.0, ganho_diario_g=0.2, populacao_atual=pop,
        mortalidade_diaria_pct=0.1, custo_operacional_total=10_000.0, preco_atual_kg=30.0,
        preco_futuro_kg=None, custo_diario_racao_energia=100.0, biomassa_atual_kg=biomassa,
        receita_realizada_rs=150_000.0,
    )
    assert r.biomassa_projetada_kg == 0.0


def test_fca_soma_a_biomassa_vendida():
    assert de.calcular_fca(1_000.0, 400.0, 0.0, biomassa_vendida_kg=200.0) == pytest.approx(1_000 / 600)
    assert de.calcular_fca(1_000.0, 400.0, 0.0) == pytest.approx(1_000 / 400)
    assert biomassa_vendida_kg([venda(biomassa=120.0), venda(biomassa=80.0)]) == pytest.approx(200.0)


def test_implicita_com_vendidos():
    dias = [
        DiaManejo(data=HOJE - timedelta(days=i), racao_kg=20.0, racao_efetiva_kg=20.0,
                  pior_sobra=NivelSobraBandeja.SEM_SOBRA, mortos=0)
        for i in range(MIN_DIAS_COM_REGISTRO)
    ]
    args = (dias, 100_000, lambda d: 10.0, lambda p: 4.0, HOJE)
    assert sobrevivencia_implicita_pct(*args) == pytest.approx(50.0)
    assert sobrevivencia_implicita_pct(*args, vendidos_ate=lambda d: 10_000) == pytest.approx(60.0)


def test_delta_v_nao_muda_com_receita_realizada_mas_lucro_sim():
    base = dict(
        dias_horizonte=10, peso_medio_atual_g=12.0, ganho_diario_g=0.25, populacao_atual=200_000,
        mortalidade_diaria_pct=0.1, custo_operacional_total=50_000.0, preco_atual_kg=30.0,
        preco_futuro_kg=32.0, custo_diario_racao_energia=800.0, biomassa_atual_kg=2_400.0,
    )
    sem = de.simular_delta_v(**base)
    com = de.simular_delta_v(**base, receita_realizada_rs=20_000.0)
    assert com.delta_v == pytest.approx(sem.delta_v)
    assert com.lucro_projetado == pytest.approx(sem.lucro_projetado + 20_000.0)
    assert com.recomendacao == sem.recomendacao


def test_metricas_economicas_incluem_receita_realizada():
    sem = de.calcular_metricas_economicas([10_000.0, 5_000.0], 1_000.0, 30.0)
    com = de.calcular_metricas_economicas([10_000.0, 5_000.0], 1_000.0, 30.0, receita_realizada_rs=6_000.0)
    assert sem.receita_bruta == pytest.approx(30_000.0) and sem.lucro_operacional == pytest.approx(15_000.0)
    assert com.receita_bruta == pytest.approx(36_000.0)
    assert com.lucro_operacional == pytest.approx(21_000.0)
    assert com.margem_operacional_pct == pytest.approx(21_000 / 36_000 * 100)
