"""Simulação ΔV de despesca com dados reais do ciclo."""

from datetime import date

import pytest


def _ciclo_com_biometrias(client, gestor, novo_ciclo, pesos=(9.0, 11.0)):
    ciclo = novo_ciclo(data_povoamento="2026-08-01")
    url = f"/api/v1/ciclos/{ciclo['id']}"
    for dia, peso in zip(("2026-09-01", "2026-09-15"), pesos):
        r = client.post(
            f"{url}/biometrias/",
            json={"data_medicao": dia, "quantidade_amostrada": 50, "peso_medio_g": peso},
            headers=gestor,
        )
        assert r.status_code == 201, r.text
    return ciclo, url


def _lancar_racao(client, gestor, url, valor=6_000.0):
    r = client.post(
        f"{url}/custos/",
        json={"data_lancamento": "2026-09-10", "categoria": "RACAO", "descricao": "Ração", "valor_rs": valor},
        headers=gestor,
    )
    assert r.status_code == 201, r.text


def test_sem_preco_para_gramatura_recusa(client, gestor, novo_ciclo):
    _, url = _ciclo_com_biometrias(client, gestor, novo_ciclo, pesos=(4.0, 5.0))
    _lancar_racao(client, gestor, url)
    r = client.post(f"{url}/simular-despesca/", json={"dias_horizonte": 7}, headers=gestor)
    assert r.status_code == 400
    assert "preço" in r.json()["detail"]


def test_sem_custos_recorrentes_recusa(client, gestor, novo_ciclo):
    _, url = _ciclo_com_biometrias(client, gestor, novo_ciclo)
    r = client.post(f"{url}/simular-despesca/", json={"dias_horizonte": 7}, headers=gestor)
    assert r.status_code == 400
    assert "custo" in r.json()["detail"].lower()


def test_custo_diario_informado(client, gestor, novo_ciclo):
    _, url = _ciclo_com_biometrias(client, gestor, novo_ciclo)
    r = client.post(
        f"{url}/simular-despesca/", json={"dias_horizonte": 7, "custo_diario_rs": 100}, headers=gestor
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["custo_diario_rs"] == 100
    assert body["custo_adicional_projetado_rs"] == 700
    assert "RN-012" in body["justificativa"]


def test_custo_diario_derivado_dos_lancamentos(client, gestor, novo_ciclo):
    _, url = _ciclo_com_biometrias(client, gestor, novo_ciclo)
    _lancar_racao(client, gestor, url)
    body = client.post(f"{url}/simular-despesca/", json={"dias_horizonte": 7}, headers=gestor).json()
    assert body["custo_diario_rs"] > 0
    assert any("média dos custos lançados" in p for p in body["premissas"])
    assert body["simulacao_id"] is not None


def test_comparativo_nao_grava_historico(client, gestor, novo_ciclo):
    ciclo, url = _ciclo_com_biometrias(client, gestor, novo_ciclo)
    _lancar_racao(client, gestor, url)
    antes = client.get(f"/api/v1/simulacao/?ciclo_id={ciclo['id']}", headers=gestor).json()
    r = client.get(f"{url}/simular-despesca/comparativo", headers=gestor)
    assert r.status_code == 200, r.text
    assert [s["dias_horizonte"] for s in r.json()["simulacoes"]] == [7, 10, 15]
    depois = client.get(f"/api/v1/simulacao/?ciclo_id={ciclo['id']}", headers=gestor).json()
    assert len(depois) == len(antes)


def test_peso_projetado_fora_da_tabela_usa_preco_atual(client, gestor, novo_ciclo):
    _, url = _ciclo_com_biometrias(client, gestor, novo_ciclo, pesos=(17.0, 19.5))
    _lancar_racao(client, gestor, url)
    body = client.post(f"{url}/simular-despesca/", json={"dias_horizonte": 15}, headers=gestor).json()
    assert body["preco_futuro_rs_kg"] == body["preco_atual_rs_kg"]
    assert any("Sem faixa de preço" in p for p in body["premissas"])


# ── Custo diário padrão: ração de hoje × preço da ração + custos fixos ──

def test_custo_diario_marginal_calculado_a_mao():
    from src.services.decision_engine import estimar_custo_diario
    # Ração: R$ 29.000 em 5.000 kg = R$ 5,80/kg; fixos R$ 15.000 em 100 dias = R$ 150/dia
    c = estimar_custo_diario(29_000, 5_000, 15_000, 100, racao_diaria_hoje_kg=150)
    assert c.marginal and c.preco_racao_rs_kg == pytest.approx(5.8) and c.fixos_rs_dia == pytest.approx(150)
    assert c.total_rs == pytest.approx(150 * 5.8 + 150)  # R$ 1.020 por dia


def test_custo_diario_sem_kg_de_racao_cai_na_media_do_ciclo():
    from src.services.decision_engine import estimar_custo_diario
    c = estimar_custo_diario(29_000, 0, 15_000, 100, racao_diaria_hoje_kg=150)
    assert not c.marginal and c.total_rs == pytest.approx(440)  # (29.000 + 15.000) ÷ 100
    assert estimar_custo_diario(0, 0, 0, 100, None) is None


def test_simulacao_usa_a_racao_de_hoje_no_custo_diario(client, gestor, novo_ciclo):
    ciclo, url = _ciclo_com_biometrias(client, gestor, novo_ciclo)  # último peso: 11,0 g (taxa 3,74%)
    r = client.post(f"{url}/manejos-alimentares/", json={"data_registro": "2026-09-20", "quantidade_racao_kg": 500,
                                                         "sobra_bandeja_nivel": "SEM_SOBRA"}, headers=gestor)
    assert r.status_code == 201, r.text
    _lancar_racao(client, gestor, url, valor=2_900.0)  # R$ 5,80 por kg dos 500 kg lançados
    r = client.post(f"{url}/custos/", json={"data_lancamento": "2026-09-10", "categoria": "ENERGIA_ELETRICA",
                                            "descricao": "Energia", "valor_rs": 4_350}, headers=gestor)
    assert r.status_code == 201, r.text

    s = client.post(f"{url}/simular-despesca/", json={"dias_horizonte": 7}, headers=gestor).json()
    dias = (date.today() - date(2026, 8, 1)).days
    racao_hoje = s["biomassa_atual_kg"] * 0.0374
    assert s["custo_diario_rs"] == pytest.approx(racao_hoje * 5.8 + 4_350 / dias, abs=0.1)
    assert any("ração de hoje" in p for p in s["premissas"])
