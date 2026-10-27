"""Sobrevivência estimada: ração real × tabela alimentar e camarões mortos informados."""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from src.models.enums import NivelSobraBandeja as Sobra
from src.services.sobrevivencia import (
    agrupar_por_dia,
    confrontar_vivos,
    nova_sobrevivencia,
    sobrevivencia_implicita_pct,
    sobrevivencia_vigente,
)

DIA = date(2026, 9, 1)


def _registro(dias_apos, racao, sobra=Sobra.SEM_SOBRA, mortos=None):
    return SimpleNamespace(
        data_registro=DIA + timedelta(days=dias_apos), quantidade_racao_kg=racao, sobra_bandeja_nivel=sobra,
        camaroes_mortos=mortos, created_at=None, taxa_sobrevivencia_estimada_fuzzy=None,
    )


def _tres_dias(racao=60.0, sobra=Sobra.SEM_SOBRA):
    return [_registro(i, racao, sobra) for i in range(3)]


TAXA_3_PCT = lambda peso: 3.0  # noqa: E731  (taxa fixa de 3% ao dia, como no exemplo do documento)
PESO_20_G = lambda data: 20.0  # noqa: E731


# ── Estimativa pelo consumo (exemplo: 60 kg/dia a 3% = 2.000 kg) ──

def test_biomassa_implicita_do_exemplo_do_documento():
    # 60 kg ÷ 3% = 2.000 kg; 2.000 kg ÷ 20 g = 100.000 camarões; com 120.000 PLs, 83,33% vivos
    dias = agrupar_por_dia(_tres_dias())
    assert sobrevivencia_implicita_pct(dias, 120_000, PESO_20_G, TAXA_3_PCT, DIA + timedelta(days=2)) == pytest.approx(
        100_000 / 120_000 * 100
    )


def test_sobra_reduz_a_racao_efetiva():
    # Sobra moderada: 15% da ração não foi comida → 51 kg ÷ 3% = 1.700 kg → 85.000 camarões
    dias = agrupar_por_dia(_tres_dias(sobra=Sobra.SOBRA_MODERADA))
    assert sobrevivencia_implicita_pct(dias, 120_000, PESO_20_G, TAXA_3_PCT, DIA + timedelta(days=2)) == pytest.approx(
        85_000 / 120_000 * 100
    )


def test_implicita_limitada_a_100_e_exige_dias_de_registro():
    dias = agrupar_por_dia(_tres_dias(racao=500.0))
    assert sobrevivencia_implicita_pct(dias, 120_000, PESO_20_G, TAXA_3_PCT, DIA + timedelta(days=2)) == 100.0
    poucos = agrupar_por_dia(_tres_dias()[:2])
    assert sobrevivencia_implicita_pct(poucos, 120_000, PESO_20_G, TAXA_3_PCT, DIA + timedelta(days=1)) is None


def test_tratos_do_mesmo_dia_somam():
    dias = agrupar_por_dia([_registro(0, 30.0, mortos=100), _registro(0, 30.0, Sobra.SOBRA_LEVE, mortos=50)])
    assert len(dias) == 1
    assert dias[0].racao_kg == 60.0 and dias[0].mortos == 150
    assert dias[0].pior_sobra == Sobra.SOBRA_LEVE
    assert dias[0].racao_efetiva_kg == pytest.approx(30.0 + 30.0 * 0.95)


# ── Combinação dos sinais ─────────────────────────────

def test_mortos_contados_sao_o_piso_da_perda():
    assert nova_sobrevivencia(100.0, 1, mortos_pct=2.0, ajuste_fuzzy_semanal=0.0, implicita=None) == 98.0


def test_maior_perda_vale_sem_somar_os_sinais():
    # Mortos 1% e fuzzy −3 pontos na semana: vale o fuzzy (3), não a soma (4)
    assert nova_sobrevivencia(100.0, 7, 1.0, -3.0, None) == pytest.approx(97.0, abs=0.01)


def test_sobrevivencia_nunca_sobe():
    assert nova_sobrevivencia(95.0, 7, 0.0, +0.5, None) == 95.0
    assert nova_sobrevivencia(95.0, 1, 0.0, 0.0, implicita=100.0) == 95.0


def test_consumo_abaixo_da_tabela_derruba_a_sobrevivencia_com_teto_diario():
    # Diferença de 20 pontos: corrige metade (10) mas o teto é 12 pontos/semana = 1,71 por dia
    assert nova_sobrevivencia(100.0, 1, 0.0, 0.0, implicita=80.0) == pytest.approx(98.29, abs=0.01)
    assert nova_sobrevivencia(100.0, 7, 0.0, 0.0, implicita=80.0) == pytest.approx(90.0, abs=0.01)


def test_diferenca_pequena_e_ignorada():
    assert nova_sobrevivencia(100.0, 1, 0.0, 0.0, implicita=99.0) == 100.0


def test_sobrevivencia_vigente_e_a_do_ultimo_registro():
    assert sobrevivencia_vigente([]) == 100.0
    a, b = _registro(0, 10.0), _registro(1, 10.0)
    a.taxa_sobrevivencia_estimada_fuzzy, b.taxa_sobrevivencia_estimada_fuzzy = 97.0, 95.5
    assert sobrevivencia_vigente([b, a]) == 95.5


# ── Confronto vivos pela contagem × vivos pela alimentação ──

def _confronto(mortos, dias=3):
    registros = [_registro(i, 60.0, mortos=mortos // dias) for i in range(dias)]
    return confrontar_vivos(registros, 120_000, PESO_20_G, TAXA_3_PCT, DIA + timedelta(days=dias - 1))


def test_confronto_de_acordo():
    # 20.000 mortos → 100.000 vivos pela contagem; a ração também indica 100.000
    c = _confronto(20_001)
    assert c.situacao == "DE_ACORDO"
    assert c.sobrevivencia_por_consumo_pct == pytest.approx(83.33, abs=0.01)


def test_confronto_perda_nao_contada():
    # 10.000 mortos → 110.000 vivos pela contagem, mas a ração indica 100.000
    c = _confronto(10_002)
    assert c.situacao == "PERDA_NAO_CONTADA"
    assert c.sobrevivencia_por_mortos_pct == pytest.approx(91.66, abs=0.01)


def test_confronto_mortos_acima_do_consumo():
    # 40.000 mortos → só 80.000 vivos pela contagem, mas a ração indica 100.000
    assert _confronto(40_002).situacao == "MORTOS_ACIMA_DO_CONSUMO"


def test_confronto_sem_dados_com_poucos_dias():
    assert _confronto(0, dias=2).situacao == "SEM_DADOS"


# ── API ───────────────────────────────────────────────

def _ciclo_com_biometria(client, gestor, novo_viveiro, pls=100_000, peso=20.0):
    viveiro = novo_viveiro(10_000.0)
    r = client.post("/api/v1/ciclos/", json={"viveiro_id": viveiro["id"], "data_povoamento": "2026-08-01",
                                             "quantidade_pos_larvas": pls, "custo_aquisicao_pl": 1_000}, headers=gestor)
    assert r.status_code == 201, r.text
    url = f"/api/v1/ciclos/{r.json()['id']}"
    r = client.post(f"{url}/biometrias/", json={"data_medicao": "2026-09-01", "quantidade_amostrada": 50,
                                                "peso_medio_g": peso}, headers=gestor)
    assert r.status_code == 201, r.text
    return url


def _manejo(client, gestor, url, dia, racao, sobra="SEM_SOBRA", mortos=None):
    corpo = {"data_registro": str(dia), "quantidade_racao_kg": racao, "sobra_bandeja_nivel": sobra}
    if mortos is not None:
        corpo["camaroes_mortos"] = mortos
    return client.post(f"{url}/manejos-alimentares/", json=corpo, headers=gestor)


def test_mortos_informados_reduzem_a_sobrevivencia(client, gestor, novo_viveiro):
    url = _ciclo_com_biometria(client, gestor, novo_viveiro)
    r = _manejo(client, gestor, url, "2026-09-02", 59.6, mortos=3_000)  # 3% das 100.000 PLs
    assert r.status_code == 201, r.text
    assert r.json()["camaroes_mortos"] == 3_000
    assert r.json()["taxa_sobrevivencia_estimada_fuzzy"] <= 97.0


def test_mortos_acima_da_populacao_ou_negativos_sao_recusados(client, gestor, novo_viveiro):
    url = _ciclo_com_biometria(client, gestor, novo_viveiro)
    assert _manejo(client, gestor, url, "2026-09-02", 59.6, mortos=100_001).status_code == 422
    assert _manejo(client, gestor, url, "2026-09-02", 59.6, mortos=-1).status_code == 422


def test_dois_tratos_no_dia_equivalem_a_um_trato_com_o_total(client, gestor, novo_viveiro):
    # 100.000 PLs de 20 g = 2.000 kg; a 2,98% a tabela pede 59,6 kg por dia
    dois = _ciclo_com_biometria(client, gestor, novo_viveiro)
    um = _ciclo_com_biometria(client, gestor, novo_viveiro)
    manha = _manejo(client, gestor, dois, "2026-09-02", 30.0).json()
    tarde = _manejo(client, gestor, dois, "2026-09-02", 30.0).json()
    unico = _manejo(client, gestor, um, "2026-09-02", 60.0).json()

    assert tarde["status_alimentar_ajustado"] == unico["status_alimentar_ajustado"] == "NORMAL"
    assert tarde["taxa_sobrevivencia_estimada_fuzzy"] == unico["taxa_sobrevivencia_estimada_fuzzy"]
    # O trato da manhã não fica marcado como "abaixo do padrão" por ser metade do dia
    lista = client.get(f"{dois}/manejos-alimentares/", headers=gestor).json()
    assert {m["id"]: m["status_alimentar_ajustado"] for m in lista}[manha["id"]] == "NORMAL"


def test_recomendacao_e_metricas_trazem_o_confronto(client, gestor, novo_viveiro):
    url = _ciclo_com_biometria(client, gestor, novo_viveiro)
    hoje = date.today()
    for dias_atras in (3, 2, 1):
        assert _manejo(client, gestor, url, hoje - timedelta(days=dias_atras), 59.6, mortos=500).status_code == 201
    assert _manejo(client, gestor, url, hoje, 30.0).status_code == 201
    assert _manejo(client, gestor, url, hoje, 30.0).status_code == 201

    rec = client.get(f"{url}/manejos-alimentares/recomendacao", headers=gestor).json()
    assert rec["racao_lancada_hoje_kg"] == 60.0
    assert rec["racao_tabela_dia_kg"] == pytest.approx(59.6, rel=0.02)
    assert rec["consumo_vs_tabela_pct"] == pytest.approx(60.0 / rec["racao_tabela_dia_kg"] * 100, abs=0.1)
    assert rec["status_alimentar"] == "NORMAL"
    assert rec["confronto_vivos"]["mortos_acumulados"] == 1_500

    m = client.get(f"{url}/metricas-atuais", headers=gestor).json()
    cv = m["confronto_vivos"]
    assert cv["mortos_acumulados"] == 1_500
    assert cv["sobrevivencia_por_mortos_pct"] == pytest.approx(98.5)
    assert cv["situacao"] in {"DE_ACORDO", "PERDA_NAO_CONTADA", "MORTOS_ACIMA_DO_CONSUMO", "SEM_DADOS"}
