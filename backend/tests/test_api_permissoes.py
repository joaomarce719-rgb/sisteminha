"""Controle de acesso por papel (CAMPO, VIGIA, GESTOR)."""


def test_somente_gestor_cria_viveiro(client, campo, vigia):
    payload = {"identificacao": "VIV-PERM", "area_util_m2": 1000}
    assert client.post("/api/v1/viveiros/", json=payload, headers=campo).status_code == 403
    assert client.post("/api/v1/viveiros/", json=payload, headers=vigia).status_code == 403


def test_campo_e_vigia_nao_acessam_custos(client, campo, vigia, novo_ciclo):
    ciclo = novo_ciclo()
    for headers in (campo, vigia):
        r = client.get(f"/api/v1/ciclos/{ciclo['id']}/custos/", headers=headers)
        assert r.status_code == 403


def test_vigia_nao_registra_biometria(client, vigia, novo_ciclo):
    ciclo = novo_ciclo()
    r = client.post(
        f"/api/v1/ciclos/{ciclo['id']}/biometrias/",
        json={"data_medicao": "2026-09-01", "peso_medio_g": 5.0},
        headers=vigia,
    )
    assert r.status_code == 403


def test_campo_nao_ve_dados_financeiros(client, campo, gestor, novo_ciclo):
    ciclo = novo_ciclo()
    m_campo = client.get(f"/api/v1/ciclos/{ciclo['id']}/metricas-atuais", headers=campo).json()
    m_gestor = client.get(f"/api/v1/ciclos/{ciclo['id']}/metricas-atuais", headers=gestor).json()
    assert m_gestor["custo_operacional_total_rs"] > 0
    assert m_campo["receita_bruta_estimada_rs"] is None
    assert m_campo["preco_venda_atual_rs_kg"] is None


def test_somente_gestor_simula_despesca(client, campo, novo_ciclo):
    ciclo = novo_ciclo()
    r = client.post(
        f"/api/v1/ciclos/{ciclo['id']}/simular-despesca/",
        json={"dias_horizonte": 7},
        headers=campo,
    )
    assert r.status_code == 403
