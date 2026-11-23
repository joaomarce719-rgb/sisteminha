"""Fase do custo: preparo e despesca contam no lucro, mas não no custo diário de manter o viveiro."""

from tests.test_simulacao import _ciclo_com_biometrias, _lancar_racao


def _custo(client, gestor, url, **extra):
    corpo = {
        "data_lancamento": "2026-09-10",
        "categoria": "MANUTENCAO",
        "descricao": "Custo de teste",
        "valor_rs": 12_000.0,
        **extra,
    }
    return client.post(f"{url}/custos/", json=corpo, headers=gestor)


def _primeira_simulacao(client, gestor, url):
    r = client.get(f"{url}/simular-despesca/comparativo", headers=gestor)
    assert r.status_code == 200, r.text
    return r.json()["simulacoes"][0]


def test_custo_preparo_nao_entra_no_custo_diario_mas_reduz_o_lucro(client, gestor, novo_ciclo):
    _, url = _ciclo_com_biometrias(client, gestor, novo_ciclo)
    _lancar_racao(client, gestor, url)
    antes = _primeira_simulacao(client, gestor, url)

    r = _custo(client, gestor, url, fase="PREPARO", descricao="Calagem do viveiro")
    assert r.status_code == 201, r.text
    depois = _primeira_simulacao(client, gestor, url)

    assert depois["custo_diario_rs"] == antes["custo_diario_rs"]
    assert depois["lucro_operacional_atual_rs"] == round(antes["lucro_operacional_atual_rs"] - 12_000, 2)


def test_custo_despesca_tambem_fica_fora_do_custo_diario(client, gestor, novo_ciclo):
    _, url = _ciclo_com_biometrias(client, gestor, novo_ciclo)
    _lancar_racao(client, gestor, url)
    antes = _primeira_simulacao(client, gestor, url)

    assert _custo(client, gestor, url, fase="DESPESCA", descricao="Equipe de despesca").status_code == 201
    depois = _primeira_simulacao(client, gestor, url)

    assert depois["custo_diario_rs"] == antes["custo_diario_rs"]
    assert depois["lucro_operacional_atual_rs"] < antes["lucro_operacional_atual_rs"]


def test_custo_do_cultivo_continua_no_custo_diario(client, gestor, novo_ciclo):
    _, url = _ciclo_com_biometrias(client, gestor, novo_ciclo)
    _lancar_racao(client, gestor, url)
    antes = _primeira_simulacao(client, gestor, url)

    assert _custo(client, gestor, url, descricao="Manutenção dos aeradores").status_code == 201
    depois = _primeira_simulacao(client, gestor, url)

    assert depois["custo_diario_rs"] > antes["custo_diario_rs"]


def test_custo_manual_aceita_fase_e_devolve_na_resposta(client, gestor, novo_ciclo):
    _, url = _ciclo_com_biometrias(client, gestor, novo_ciclo)

    r = _custo(client, gestor, url, fase="PREPARO")
    assert r.status_code == 201, r.text
    assert r.json()["fase"] == "PREPARO"

    r = _custo(client, gestor, url)
    assert r.status_code == 201, r.text
    assert r.json()["fase"] == "CULTIVO"

    fases = {c["fase"] for c in client.get(f"{url}/custos/", headers=gestor).json()}
    assert fases == {"PREPARO", "CULTIVO"}


def test_fase_invalida_da_422(client, gestor, novo_ciclo):
    _, url = _ciclo_com_biometrias(client, gestor, novo_ciclo)
    assert _custo(client, gestor, url, fase="COLHEITA").status_code == 422
