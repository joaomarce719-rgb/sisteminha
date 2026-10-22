"""Motor fuzzy de sobrevivência (RN-05)."""

import itertools

import numpy as np
import pytest

from src.models.enums import NivelSobraBandeja as N
from src.services.fuzzy_engine import (
    SOBRA_MAPA,
    _inferir,
    ajuste_no_periodo,
    inferir_ajuste_sobrevivencia,
)


def test_base_de_regras_cobre_todo_o_universo():
    """Nenhuma combinação de entradas pode cair no fallback."""
    for consumo, sobra, cresc in itertools.product(
        np.arange(0.0, 2.01, 0.25), SOBRA_MAPA.values(), np.arange(-1.0, 3.01, 0.5)
    ):
        ajuste = _inferir(consumo, sobra, cresc)
        assert -3.0 <= ajuste <= 0.5


def test_manejo_ideal_e_estavel():
    ajuste = inferir_ajuste_sobrevivencia(1.0, N.SEM_SOBRA, 1.25)
    assert ajuste == pytest.approx(0.0, abs=0.1)


def test_sem_biometria_suficiente_nao_penaliza():
    assert inferir_ajuste_sobrevivencia(1.0, N.SEM_SOBRA, None) == pytest.approx(0.0, abs=0.1)


def test_mortalidade_silenciosa_e_queda_forte():
    assert inferir_ajuste_sobrevivencia(0.2, N.SOBRA_EXCESSIVA, -0.8) < -1.0


def test_crescimento_acelerado_e_positivo():
    assert inferir_ajuste_sobrevivencia(1.0, N.SEM_SOBRA, 2.5) > 0.0


def test_sobra_isolada_nao_conclui_mortalidade_severa():
    # RN-011: sobra excessiva com consumo e crescimento normais não é queda severa
    assert inferir_ajuste_sobrevivencia(1.0, N.SOBRA_EXCESSIVA, 1.25) > -1.5


def test_ajuste_proporcional_ao_intervalo():
    assert ajuste_no_periodo(-0.7, 1) == pytest.approx(-0.1)
    assert ajuste_no_periodo(-0.7, 0) == 0.0
    assert ajuste_no_periodo(-0.7, 30) == pytest.approx(-0.7)


def test_vinte_dias_de_manejo_ideal_preserva_sobrevivencia(client, gestor, novo_ciclo):
    ciclo = novo_ciclo(data_povoamento="2026-08-01", pls=300_000)
    url = f"/api/v1/ciclos/{ciclo['id']}"
    client.post(f"{url}/biometrias/", json={"data_medicao": "2026-09-01", "quantidade_amostrada": 50, "peso_medio_g": 5.0}, headers=gestor)
    racao = client.get(f"{url}/manejos-alimentares/recomendacao", headers=gestor).json()["racao_diaria_sugerida_kg"]
    for dia in range(1, 21):
        r = client.post(
            f"{url}/manejos-alimentares/",
            json={"data_registro": f"2026-09-{dia:02d}", "quantidade_racao_kg": racao, "sobra_bandeja_nivel": "SEM_SOBRA"},
            headers=gestor,
        )
        assert r.status_code == 201, r.text
    m = client.get(f"{url}/metricas-atuais", headers=gestor).json()
    assert m["taxa_sobrevivencia_fuzzy_pct"] >= 99.0
