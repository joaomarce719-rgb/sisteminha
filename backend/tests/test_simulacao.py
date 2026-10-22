"""Simulação ΔV de despesca com dados reais do ciclo."""


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
