"""Testes unitários para o motor de decisão bioeconômica (RNF-018).

Valida conformidade das fórmulas zootécnicas e financeiras:
- RN-003: Densidade de estocagem
- RN-006 / RN-007: População estimada e biomassa
- RN-008 / RN-020: Fator de Conversão Alimentar (FCA) com denominador zero ou negativo
- RN-010: Tabela de Clifford com interpolação
- RN-013 / RN-015: Métricas econômicas com dados presentes e faltantes
- RF-019 / RN-014: ROA e ROE
- RF-023 / RF-024: Simulação preditiva Delta V (ΔV)
"""

import pytest
from src.models.enums import ClassificacaoFCA, RecomendacaoDespesca
from src.services.decision_engine import (
    calcular_biomassa_kg,
    calcular_densidade,
    calcular_fca,
    calcular_metricas_economicas,
    calcular_populacao_atual,
    calcular_racao_diaria,
    calcular_roa,
    calcular_roe,
    classificar_fca,
    simular_delta_v,
    taxa_alimentar,
    taxa_alimentar_clifford,
    verificar_hiperdensidade,
)


def test_densidade_estocagem():
    """D = N / A (RN-003)."""
    densidade = calcular_densidade(100000, 5000.0)
    assert densidade == 20.0
    assert not verificar_hiperdensidade(densidade)

    # Hiperdensidade > 50 camarões/m²
    densidade_alta = calcular_densidade(300000, 5000.0)
    assert densidade_alta == 60.0
    assert verificar_hiperdensidade(densidade_alta)

    with pytest.raises(ValueError):
        calcular_densidade(10000, 0.0)


def test_populacao_e_biomassa():
    """Pop_Atual e B (kg) = (Pop * Peso_Médio) / 1000 (RN-006, RN-007)."""
    pop = calcular_populacao_atual(100000, 85.0)
    assert pop == 85000

    biomassa = calcular_biomassa_kg(pop, 12.0)
    assert biomassa == 1020.0  # (85000 * 12) / 1000 = 1020 kg


def test_fca_valido_e_classificacao():
    """FCA = Ração / Ganho de biomassa (RN-008)."""
    # Ganho de 500 kg (de 1000 kg para 1500 kg) com 600 kg de ração
    fca = calcular_fca(600.0, 1500.0, 1000.0)
    assert fca == 1.2
    assert classificar_fca(fca) == ClassificacaoFCA.ALTA_EFICIENCIA

    fca_padrao = calcular_fca(750.0, 1500.0, 1000.0)
    assert fca_padrao == 1.5
    assert classificar_fca(fca_padrao) == ClassificacaoFCA.FAIXA_PADRAO

    fca_alto = calcular_fca(900.0, 1500.0, 1000.0)
    assert fca_alto == 1.8
    assert classificar_fca(fca_alto) == ClassificacaoFCA.DESPERDICIO_INDICADO


def test_fca_invalido_sem_ganho():
    """FCA não calcula se ganho for zero ou negativo (RN-020, Critério de Aceite 3)."""
    assert calcular_fca(500.0, 1000.0, 1000.0) is None  # ganho 0
    assert calcular_fca(500.0, 900.0, 1000.0) is None   # ganho negativo
    assert classificar_fca(None) is None


def test_clifford_interpolacao():
    """Tabela de Clifford (1992) com interpolação linear (RN-010)."""
    assert taxa_alimentar_clifford(2.0) == 7.15
    assert taxa_alimentar_clifford(5.0) == 5.05
    assert taxa_alimentar_clifford(20.0) == 2.98
    # Interpolação entre 2g (7.15%) e 5g (5.05%): em 3.5g deve ficar no meio
    taxa_meio = taxa_alimentar_clifford(3.5)
    assert 5.05 < taxa_meio < 7.15

    # Ração diária para biomassa de 1000kg em peso de 10g (taxa 3.88%)
    racao = calcular_racao_diaria(1000.0, 10.0)
    assert round(racao, 2) == 38.80


def test_metricas_economicas_completas():
    """CO, RB, LO e MO (RN-013, RN-06)."""
    custos = [5000.0, 3000.0, 2000.0]  # total 10.000
    metricas = calcular_metricas_economicas(custos, 1000.0, 25.0)

    assert metricas.custo_operacional_total == 10000.0
    assert metricas.receita_bruta == 25000.0
    assert metricas.lucro_operacional == 15000.0
    assert metricas.margem_operacional_pct == 60.0  # (15000 / 25000) * 100


def test_metricas_economicas_dados_faltantes_rn015():
    """Se faltar biomassa ou preço, receita e lucro são None (RN-015)."""
    custos = [5000.0]
    # Sem biomassa (ex.: antes da primeira biometria)
    m1 = calcular_metricas_economicas(custos, None, 25.0)
    assert m1.custo_operacional_total == 5000.0
    assert m1.receita_bruta is None
    assert m1.lucro_operacional is None
    assert m1.margem_operacional_pct is None

    # Sem cotação de mercado
    m2 = calcular_metricas_economicas(custos, 1000.0, None)
    assert m2.receita_bruta is None
    assert m2.lucro_operacional is None


def test_roa_e_roe_critério_4():
    """ROA e ROE aparecem como None se faltar ativo/patrimônio (RF-019, RN-014, Critério 4)."""
    # Cálculo válido
    roa = calcular_roa(15000.0, 100000.0)
    assert roa == 15.0

    roe = calcular_roe(15000.0, 50000.0)
    assert roe == 30.0

    # Dados faltantes ou inválidos
    assert calcular_roa(None, 100000.0) is None
    assert calcular_roa(15000.0, None) is None
    assert calcular_roa(15000.0, 0.0) is None

    assert calcular_roe(None, 50000.0) is None
    assert calcular_roe(15000.0, None) is None
    assert calcular_roe(15000.0, 0.0) is None


def test_simulador_delta_v():
    """Algoritmo preditivo ΔV (RF-023, RF-024)."""
    resultado = simular_delta_v(
        dias_horizonte=10,
        peso_medio_atual_g=10.0,
        ganho_diario_g=0.2,
        populacao_atual=80000,
        mortalidade_diaria_pct=0.1,
        custo_operacional_total=15000.0,
        preco_atual_kg=22.0,
        preco_futuro_kg=25.0,  # pula de faixa de gramatura
        custo_diario_racao_energia=120.0,
        biomassa_atual_kg=800.0,
    )

    assert resultado.peso_medio_projetado_g == 12.0
    assert resultado.delta_v > 0
    assert resultado.recomendacao == RecomendacaoDespesca.MANTER_CULTIVO
    assert "retorno líquido" in resultado.justificativa


def test_tabela_alimentar_parametrizada_rf010():
    """Tabela de arraçoamento customizável com pontos parametrizados (RF-010, Critério 5)."""
    pontos_intensivo = [
        (1.0, 9.5),
        (3.0, 7.0),
        (8.0, 4.5),
        (15.0, 3.0),
    ]

    # Teste nos nós exatos
    assert taxa_alimentar(1.0, pontos_intensivo) == 9.5
    assert taxa_alimentar(8.0, pontos_intensivo) == 4.5

    # Teste em ponto intermediário (interpolação entre 1g [9.5%] e 3g [7.0%]: em 2g deve dar 8.25%)
    assert taxa_alimentar(2.0, pontos_intensivo) == 8.25

    # Cálculo da ração diária com a tabela customizada
    # Para 2000kg de biomassa em 2g (taxa 8.25%): 2000 * 0.0825 = 165 kg
    racao = calcular_racao_diaria(2000.0, 2.0, pontos_intensivo)
    assert racao == 165.0

