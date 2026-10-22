"""Integridade de dados: exclusões, ciclos abertos, datas e versionamento."""

from datetime import date, timedelta
from uuid import uuid4

from tests.conftest import unico

RONDA = {
    "data_hora_ronda": "2026-10-20T02:00:00",
    "oxigenio_dissolvido_mg_l": 5.0,
    "temperatura_agua_c": 28,
    "aeradores_instalados": 4,
    "aeradores_ligados": 4,
}


def test_excluir_ciclo_com_ronda(client, gestor, vigia, novo_ciclo):
    ciclo = novo_ciclo()
    r = client.post("/api/v1/rondas-noturnas/", json={**RONDA, "ciclo_id": ciclo["id"]}, headers=vigia)
    assert r.status_code == 201, r.text
    assert client.delete(f"/api/v1/ciclos/{ciclo['id']}", headers=gestor).status_code == 200
    assert client.get(f"/api/v1/rondas-noturnas/ciclo/{ciclo['id']}", headers=gestor).status_code == 404


def test_custo_em_ciclo_inexistente(client, gestor):
    payload = {"data_lancamento": "2026-09-01", "categoria": "RACAO", "descricao": "Ração", "valor_rs": 10}
    r = client.post(f"/api/v1/ciclos/{uuid4()}/custos/", json=payload, headers=gestor)
    assert r.status_code == 404


def test_um_ciclo_aberto_por_viveiro(client, gestor, novo_ciclo):
    ciclo = novo_ciclo()
    assert client.post(f"/api/v1/ciclos/{ciclo['id']}/pausar", headers=gestor).status_code == 200
    r = client.post(
        "/api/v1/ciclos/",
        json={
            "viveiro_id": ciclo["viveiro_id"],
            "data_povoamento": "2026-09-01",
            "quantidade_pos_larvas": 1000,
            "custo_aquisicao_pl": 10,
        },
        headers=gestor,
    )
    assert r.status_code == 409


def test_encerrar_ciclo_pausado(client, gestor, novo_ciclo):
    ciclo = novo_ciclo()
    client.post(f"/api/v1/ciclos/{ciclo['id']}/pausar", headers=gestor)
    r = client.post(
        f"/api/v1/ciclos/{ciclo['id']}/encerrar",
        json={"data_despesca_real": "2026-10-01", "biomassa_colhida_kg": 1000, "receita_real_rs": 20000},
        headers=gestor,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "FINALIZADO"


def test_datas_fora_do_ciclo_rejeitadas(client, gestor, novo_ciclo):
    ciclo = novo_ciclo(data_povoamento="2026-08-01")
    url = f"/api/v1/ciclos/{ciclo['id']}"
    antes = {"data_medicao": "2026-07-01", "quantidade_amostrada": 30, "peso_medio_g": 5}
    assert client.post(f"{url}/biometrias/", json=antes, headers=gestor).status_code == 422
    futuro = (date.today() + timedelta(days=2)).isoformat()
    manejo = {"data_registro": futuro, "quantidade_racao_kg": 10, "sobra_bandeja_nivel": "SEM_SOBRA"}
    assert client.post(f"{url}/manejos-alimentares/", json=manejo, headers=gestor).status_code == 422


def test_viveiro_com_ciclo_nao_e_excluido(client, gestor, novo_ciclo):
    ciclo = novo_ciclo()
    r = client.delete(f"/api/v1/viveiros/{ciclo['viveiro_id']}", headers=gestor)
    assert r.status_code == 409


def test_usuario_com_registros_nao_e_excluido(client, gestor, login, novo_ciclo):
    email = f"{unico('vigia')}@x.com"
    r = client.post(
        "/api/v1/admin/operadores",
        json={"nome_completo": "Vigia Temp", "email": email, "senha": "abc12345", "papel": "VIGIA"},
        headers=gestor,
    )
    user_id = r.json()["id"]
    ciclo = novo_ciclo()
    client.post("/api/v1/rondas-noturnas/", json={**RONDA, "ciclo_id": ciclo["id"]}, headers=login(email, "abc12345"))
    assert client.delete(f"/api/v1/admin/usuarios/{user_id}", headers=gestor).status_code == 409


def test_alterar_faixas_cria_nova_versao(client, gestor):
    nome = unico("Tabela")
    faixas = [{"peso_g": 2, "taxa_pct": 7}, {"peso_g": 20, "taxa_pct": 3}]
    v1 = client.post(
        "/api/v1/tabelas-alimentares/", json={"nome": nome, "faixas": faixas}, headers=gestor
    ).json()

    novas = [{"peso_g": 2, "taxa_pct": 6.5}, {"peso_g": 20, "taxa_pct": 2.8}]
    v2 = client.put(f"/api/v1/tabelas-alimentares/{v1['id']}", json={"faixas": novas}, headers=gestor).json()

    assert v2["id"] != v1["id"]
    assert v2["versao"] == v1["versao"] + 1
    original = client.get(f"/api/v1/tabelas-alimentares/{v1['id']}", headers=gestor).json()
    assert original["faixas"][0]["taxa_pct"] == 7
    assert original["ativo"] is False
