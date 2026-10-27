"""Safra simulada de 100 dias: a sobrevivência estimada acompanha a real?

A "verdade" da fazenda (sobrevivência e crescimento) é conhecida aqui, pois é simulada. O raçoador
segue a ração sugerida, lança a sobra da bandeja (os camarões comem só o que a biomassa real pede) e
informa uma fração dos mortos que acha. O teste protege o comportamento contra regressão; as
premissas da simulação não são dados de campo.
"""

import random
from datetime import date, timedelta

import numpy as np
import pytest

from src.services.decision_engine import taxa_alimentar_clifford

DIAS = 100
PESO_PL_G = 0.01
INICIO_REGISTROS = 14
FRACAO_DE_MORTOS_ACHADOS = 0.35
PONTOS_DIA = [0, 14, 21, 28, 35, 42, 49, 56, 63, 70, 77, 84, 91, 100]
PONTOS_PESO = [0.01, 0.5, 1.1, 2.0, 3.1, 4.5, 6.0, 7.8, 9.6, 11.4, 13.0, 14.6, 16.0, 17.5]

# nome, área m², PLs, pontos (dia, sobrevivência real), fator de crescimento
CONTROLE = ("controle", 10_000, 300_000, [(0, 1.0), (100, 1.0)], 1.00)
GRADUAL = ("gradual", 10_000, 300_000, [(0, 1.0), (100, 0.78)], 1.00)
SURTO = ("surto", 10_000, 300_000, [(0, 1.0), (55, 0.90), (75, 0.60), (100, 0.55)], 0.85)
HIPERDENSIDADE = ("hiperdensidade", 6_000, 330_000, [(0, 1.0), (100, 0.65)], 0.88)


def _simular(client, gestor, novo_viveiro, cenario):
    nome, area, pls, pontos_sobrev, fator = cenario
    rnd = random.Random(nome)
    povoamento = date.today() - timedelta(days=DIAS)

    def peso_real(d):
        return PESO_PL_G + (float(np.interp(d, PONTOS_DIA, PONTOS_PESO)) - PESO_PL_G) * fator

    def sobrevivencia_real(d):
        return float(np.interp(d, [p[0] for p in pontos_sobrev], [p[1] for p in pontos_sobrev]))

    viveiro = novo_viveiro(area)
    r = client.post("/api/v1/ciclos/", json={
        "viveiro_id": viveiro["id"], "data_povoamento": str(povoamento), "quantidade_pos_larvas": pls,
        "custo_aquisicao_pl": pls / 1000 * 30, "peso_medio_pl_g": PESO_PL_G}, headers=gestor)
    assert r.status_code == 201, r.text
    url = f"/api/v1/ciclos/{r.json()['id']}"

    for d in range(INICIO_REGISTROS, DIAS + 1):
        data = str(povoamento + timedelta(days=d))
        w, s = peso_real(d), sobrevivencia_real(d)
        if d % 7 == 0 or d == INICIO_REGISTROS:
            r = client.post(f"{url}/biometrias/", json={"data_medicao": data, "quantidade_amostrada": 60,
                                                        "peso_medio_g": round(w * (1 + rnd.gauss(0, 0.02)), 2)}, headers=gestor)
            assert r.status_code == 201, r.text
        sugerida = client.get(f"{url}/manejos-alimentares/recomendacao", headers=gestor).json()["racao_diaria_sugerida_kg"]
        kg = round(sugerida * (1 + rnd.gauss(0, 0.03)), 1)
        apetite = pls * s * w / 1000 * taxa_alimentar_clifford(w) / 100
        sobra_pct = max(0.0, kg - apetite) / kg * 100 if kg > 0 else 0.0
        nivel = ("SEM_SOBRA" if sobra_pct < 3 else "SOBRA_LEVE" if sobra_pct < 10
                 else "SOBRA_MODERADA" if sobra_pct < 25 else "SOBRA_EXCESSIVA")
        mortes = max(0.0, pls * (sobrevivencia_real(d - 1) - s))
        achados = max(0, round(mortes * FRACAO_DE_MORTOS_ACHADOS * (1 + rnd.gauss(0, 0.25))))
        r = client.post(f"{url}/manejos-alimentares/", json={"data_registro": data, "quantidade_racao_kg": kg,
                                                             "sobra_bandeja_nivel": nivel, "camaroes_mortos": achados},
                        headers=gestor)
        assert r.status_code == 201, r.text

    m = client.get(f"{url}/metricas-atuais", headers=gestor).json()
    s_real = sobrevivencia_real(DIAS)
    return m, s_real * 100, pls * s_real * peso_real(DIAS) / 1000


@pytest.mark.parametrize("cenario,tolerancia_pp", [(GRADUAL, 6.0), (SURTO, 8.0), (HIPERDENSIDADE, 6.0)])
def test_sobrevivencia_estimada_acompanha_a_real(client, gestor, novo_viveiro, cenario, tolerancia_pp):
    m, s_real, bio_real = _simular(client, gestor, novo_viveiro, cenario)
    assert abs(m["taxa_sobrevivencia_fuzzy_pct"] - s_real) <= tolerancia_pp
    # Sem a estimativa por mortos e consumo o sistema ficava em 95–99%: a biomassa saía até 75% inflada
    assert abs(m["biomassa_atual_kg"] - bio_real) / bio_real <= 0.12
    # Os mortos achados são só uma parte dos que morrem: a alimentação mostra a perda que a contagem não viu
    assert m["confronto_vivos"]["situacao"] == "PERDA_NAO_CONTADA"
    assert m["confronto_vivos"]["sobrevivencia_por_mortos_pct"] > m["taxa_sobrevivencia_fuzzy_pct"]


def test_surto_derruba_a_sobrevivencia_estimada(client, gestor, novo_viveiro):
    m, s_real, _ = _simular(client, gestor, novo_viveiro, SURTO)
    assert s_real == pytest.approx(55.0)
    assert m["taxa_sobrevivencia_fuzzy_pct"] < 70.0


def test_hiperdensidade_dispara_o_alerta(client, gestor, novo_viveiro):
    m, _, _ = _simular(client, gestor, novo_viveiro, HIPERDENSIDADE)
    assert m["densidade_estocagem"] == 55.0 and m["alerta_hiperdensidade"] is True


def test_sem_mortalidade_o_sistema_nao_inventa_perdas(client, gestor, novo_viveiro):
    m, s_real, _ = _simular(client, gestor, novo_viveiro, CONTROLE)
    assert s_real == 100.0
    assert m["taxa_sobrevivencia_fuzzy_pct"] >= 94.0
    assert m["confronto_vivos"]["mortos_acumulados"] == 0
    assert m["confronto_vivos"]["situacao"] == "DE_ACORDO"
