"""Respostas e cadastros sem valores inventados (RN-015)."""

from uuid import uuid4


def test_ciclo_exige_dados_de_estocagem(client, gestor, novo_viveiro):
    viveiro = novo_viveiro()
    r = client.post("/api/v1/ciclos/", json={"viveiro_id": viveiro["id"]}, headers=gestor)
    assert r.status_code == 422


def test_ciclo_densidade_derivada_do_viveiro(client, gestor, novo_ciclo):
    ciclo = novo_ciclo(pls=300_000)  # viveiro de 10.000 m²
    r = client.get(f"/api/v1/ciclos/{ciclo['id']}", headers=gestor).json()
    assert r["densidade_inicial"] == 30.0
    assert "biomassa_inicial" not in r and "descricao" not in r


def test_biometria_sem_campos_ficticios(client, gestor, novo_ciclo):
    ciclo = novo_ciclo()
    r = client.post(
        f"/api/v1/ciclos/{ciclo['id']}/biometrias/",
        json={"data_medicao": "2026-09-01", "quantidade_amostrada": 40, "peso_total_amostra_g": 200},
        headers=gestor,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["peso_medio_g"] == 5.0
    assert "cv_percent" not in body and "condicao_saude" not in body


def test_biometria_exige_amostra_e_peso(client, gestor, novo_ciclo):
    ciclo = novo_ciclo()
    url = f"/api/v1/ciclos/{ciclo['id']}/biometrias/"
    assert client.post(url, json={"data_medicao": "2026-09-01", "peso_medio_g": 5}, headers=gestor).status_code == 422
    assert client.post(url, json={"data_medicao": "2026-09-01", "quantidade_amostrada": 10}, headers=gestor).status_code == 422


def test_viveiro_sem_capacidade_inventada(client, novo_viveiro):
    assert "capacidade" not in novo_viveiro()


def test_custo_global_exige_ciclo(client, gestor):
    payload = {"data_lancamento": "2026-09-01", "categoria": "RACAO", "descricao": "Ração", "valor_rs": 10}
    assert client.post("/api/v1/custos/", json=payload, headers=gestor).status_code == 422


def test_custo_categoria_desconhecida_rejeitada(client, gestor, novo_ciclo):
    ciclo = novo_ciclo()
    payload = {"data_lancamento": "2026-09-01", "categoria": "XYZ", "descricao": "Teste", "valor_rs": 10}
    r = client.post(f"/api/v1/ciclos/{ciclo['id']}/custos/", json=payload, headers=gestor)
    assert r.status_code == 422


def test_metricas_financeiras_ocultas_sao_nulas_para_campo(client, campo, novo_ciclo):
    ciclo = novo_ciclo()
    m = client.get(f"/api/v1/ciclos/{ciclo['id']}/metricas-atuais", headers=campo).json()
    assert m["custo_operacional_total_rs"] is None


def test_simulacao_global_usa_dados_do_ciclo(client, gestor, campo, novo_ciclo):
    ciclo = novo_ciclo()
    url = "/api/v1/simulacao/"
    assert client.post(url, json={"ciclo_id": ciclo["id"]}, headers=campo).status_code == 403
    assert client.post(url, json={}, headers=gestor).status_code == 422
    assert client.post(url, json={"ciclo_id": str(uuid4())}, headers=gestor).status_code == 404
    # Sem biometria não há como simular: nenhum número padrão é inventado
    r = client.post(url, json={"ciclo_id": ciclo["id"]}, headers=gestor)
    assert r.status_code == 400


def test_fca_usa_biomassa_do_povoamento(client, gestor, novo_viveiro):
    # Ganho de biomassa = biomassa atual − biomassa no povoamento (PLs × peso da PL)
    viveiro = novo_viveiro()
    r = client.post(
        "/api/v1/ciclos/",
        json={"viveiro_id": viveiro["id"], "data_povoamento": "2026-08-01",
              "quantidade_pos_larvas": 300_000, "custo_aquisicao_pl": 3_000, "peso_medio_pl_g": 0.002},
        headers=gestor,
    )
    assert r.status_code == 201, r.text
    ciclo = r.json()
    assert ciclo["peso_medio_pl_g"] == 0.002
    url = f"/api/v1/ciclos/{ciclo['id']}"
    assert client.post(f"{url}/biometrias/", json={"data_medicao": "2026-09-01", "quantidade_amostrada": 50,
                                                   "peso_medio_g": 5.0}, headers=gestor).status_code == 201
    assert client.post(f"{url}/manejos-alimentares/", json={"data_registro": "2026-09-02", "quantidade_racao_kg": 40,
                                                            "sobra_bandeja_nivel": "SEM_SOBRA"},
                       headers=gestor).status_code == 201

    m = client.get(f"{url}/metricas-atuais", headers=gestor).json()
    # Com uma única biometria o FCA já é calculável
    esperado = m["racao_acumulada_kg"] / (m["biomassa_atual_kg"] - 300_000 * 0.002 / 1000)
    assert abs(m["fca_atual"] - esperado) < 0.001


def test_peso_da_pl_fora_da_faixa_rejeitado(client, gestor, novo_viveiro):
    viveiro = novo_viveiro()
    r = client.post(
        "/api/v1/ciclos/",
        json={"viveiro_id": viveiro["id"], "data_povoamento": "2026-08-01",
              "quantidade_pos_larvas": 1000, "custo_aquisicao_pl": 10, "peso_medio_pl_g": 50},
        headers=gestor,
    )
    assert r.status_code == 422
