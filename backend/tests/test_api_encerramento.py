"""Encerramento do ciclo: despesca final pelo payload ou pelas vendas, totais somados e bloqueio por uso sem valor."""

from datetime import date

import pytest

from tests.conftest import unico

HOJE = date.today().isoformat()
DATA_FINAL = "2026-10-10"


@pytest.fixture
def ciclo(novo_ciclo):
    return novo_ciclo()


def _biometria(client, gestor, ciclo_id, peso=20.0, data="2026-09-01"):
    r = client.post(f"/api/v1/ciclos/{ciclo_id}/biometrias/",
                    json={"data_medicao": data, "quantidade_amostrada": 50, "peso_medio_g": peso}, headers=gestor)
    assert r.status_code == 201, r.text


def _vender(client, gestor, ciclo_id, tipo="DESPESCA_FINAL", data=DATA_FINAL, biomassa=1000, preco=25):
    r = client.post(f"/api/v1/ciclos/{ciclo_id}/vendas",
                    json={"data_venda": data, "tipo": tipo, "biomassa_kg": biomassa, "peso_medio_g": 20,
                          "preco_kg": preco, "retroativo": data != HOJE}, headers=gestor)
    assert r.status_code == 201, r.text
    return r.json()


def _vendas(client, gestor, ciclo_id):
    return client.get(f"/api/v1/ciclos/{ciclo_id}/vendas", headers=gestor).json()


def _encerrar(client, gestor, ciclo_id, **corpo):
    return client.post(f"/api/v1/ciclos/{ciclo_id}/encerrar", json=corpo, headers=gestor)


def _ciclo_da_api(client, gestor, ciclo_id):
    return client.get(f"/api/v1/ciclos/{ciclo_id}", headers=gestor).json()


def _uso_pendente(client, gestor, ciclo_id, insumo_id):
    r = client.post(f"/api/v1/ciclos/{ciclo_id}/usos-insumo",
                    json={"insumo_id": insumo_id, "data_uso": HOJE, "quantidade": 10, "fase": "CULTIVO"},
                    headers=gestor)
    assert r.status_code == 201, r.text
    assert r.json()["pendente_de_valor"] is True


@pytest.fixture
def insumo(client, gestor):
    r = client.post("/api/v1/insumos/", json={"nome": unico("Cal"), "unidade_uso": "kg"}, headers=gestor)
    assert r.status_code == 201, r.text
    return r.json()


def test_encerrar_com_payload_cria_venda_final(client, gestor, ciclo):
    _biometria(client, gestor, ciclo["id"], peso=20)
    r = _encerrar(client, gestor, ciclo["id"], data_despesca_real=DATA_FINAL, biomassa_colhida_kg=1000,
                  receita_real_rs=25000)
    assert r.status_code == 200, r.text
    assert (r.json()["status"], r.json()["data_despesca_real"]) == ("FINALIZADO", DATA_FINAL)
    assert (r.json()["biomassa_colhida_kg"], r.json()["receita_real_rs"]) == (1000.0, 25000.0)

    [venda] = _vendas(client, gestor, ciclo["id"])
    assert (venda["tipo"], venda["data_venda"], venda["retroativo"]) == ("DESPESCA_FINAL", DATA_FINAL, True)
    assert (venda["biomassa_kg"], venda["peso_medio_g"]) == (1000.0, 20.0)  # peso da última biometria
    assert venda["preco_kg"] == 25.0  # receita ÷ biomassa
    assert (venda["animais_estimados"], venda["valor_total_rs"]) == (50_000, 25_000.0)


def test_encerrar_mantem_a_receita_informada_com_preco_arredondado(client, gestor, ciclo):
    _biometria(client, gestor, ciclo["id"])
    r = _encerrar(client, gestor, ciclo["id"], data_despesca_real=DATA_FINAL, biomassa_colhida_kg=3,
                  receita_real_rs=100)
    assert r.status_code == 200, r.text
    assert _vendas(client, gestor, ciclo["id"])[0]["preco_kg"] == 33.33  # 100 ÷ 3
    assert r.json()["receita_real_rs"] == 100.0


def test_encerrar_sem_venda_final_da_422(client, gestor, ciclo):
    _biometria(client, gestor, ciclo["id"])
    _vender(client, gestor, ciclo["id"], tipo="DESBASTE", biomassa=200, preco=20)
    r = _encerrar(client, gestor, ciclo["id"], data_despesca_real=DATA_FINAL)
    assert r.status_code == 422
    assert "despesca final" in r.json()["detail"]
    assert _ciclo_da_api(client, gestor, ciclo["id"])["status"] == "ATIVO"


def test_encerrar_soma_varias_vendas(client, gestor, ciclo):
    _biometria(client, gestor, ciclo["id"])
    _vender(client, gestor, ciclo["id"], tipo="DESBASTE", data="2026-09-20", biomassa=200, preco=20)  # R$ 4.000
    r = _encerrar(client, gestor, ciclo["id"], data_despesca_real=DATA_FINAL, biomassa_colhida_kg=1000,
                  receita_real_rs=25000)
    assert r.status_code == 200, r.text
    assert (r.json()["biomassa_colhida_kg"], r.json()["receita_real_rs"]) == (1200.0, 29000.0)
    assert len(_vendas(client, gestor, ciclo["id"])) == 2


def test_encerrar_sem_payload_usa_as_vendas_e_a_data_da_ultima_final(client, gestor, ciclo):
    _biometria(client, gestor, ciclo["id"])
    _vender(client, gestor, ciclo["id"], data="2026-10-05", biomassa=400, preco=20)  # R$ 8.000
    _vender(client, gestor, ciclo["id"], data=DATA_FINAL, biomassa=600, preco=25)  # R$ 15.000
    r = _encerrar(client, gestor, ciclo["id"])
    assert r.status_code == 200, r.text
    assert r.json()["data_despesca_real"] == DATA_FINAL  # a da última despesca final
    assert (r.json()["biomassa_colhida_kg"], r.json()["receita_real_rs"]) == (1000.0, 23000.0)
    assert len(_vendas(client, gestor, ciclo["id"])) == 2  # nenhuma venda extra


def test_data_despesca_real_padrao(client, gestor, ciclo):
    _biometria(client, gestor, ciclo["id"])
    r = _encerrar(client, gestor, ciclo["id"], biomassa_colhida_kg=1000, receita_real_rs=25000)
    assert r.status_code == 200, r.text
    assert r.json()["data_despesca_real"] == HOJE
    [venda] = _vendas(client, gestor, ciclo["id"])
    assert (venda["data_venda"], venda["retroativo"]) == (HOJE, False)


def test_encerrar_bloqueado_por_uso_pendente_de_valor(client, gestor, ciclo, insumo):
    _biometria(client, gestor, ciclo["id"])
    _vender(client, gestor, ciclo["id"])
    _uso_pendente(client, gestor, ciclo["id"], insumo["id"])
    _uso_pendente(client, gestor, ciclo["id"], insumo["id"])

    r = _encerrar(client, gestor, ciclo["id"])
    assert r.status_code == 409
    assert "2 usos de insumo pendentes de valor" in r.json()["detail"]
    assert _ciclo_da_api(client, gestor, ciclo["id"])["status"] == "ATIVO"

    # a compra faltante resolve as pendências e libera o encerramento
    compra = client.post(f"/api/v1/insumos/{insumo['id']}/compras", json={
        "data_compra": HOJE, "quantidade": 100, "valor_total_rs": 300}, headers=gestor)
    assert compra.status_code == 201, compra.text
    assert _encerrar(client, gestor, ciclo["id"]).status_code == 200


def test_encerrar_sem_biometria_com_payload_da_422(client, gestor, ciclo):
    r = _encerrar(client, gestor, ciclo["id"], biomassa_colhida_kg=1000, receita_real_rs=25000)
    assert r.status_code == 422
    assert "biometria" in r.json()["detail"]
    assert _vendas(client, gestor, ciclo["id"]) == []
    assert _ciclo_da_api(client, gestor, ciclo["id"])["status"] == "ATIVO"


def test_encerrar_sem_biometria_com_venda_final_da_422(client, gestor, ciclo):
    _vender(client, gestor, ciclo["id"])
    r = _encerrar(client, gestor, ciclo["id"])
    assert r.status_code == 422
    assert "biometria" in r.json()["detail"]


@pytest.mark.parametrize("corpo", [
    {"biomassa_colhida_kg": 1000},
    {"receita_real_rs": 25000},
    {"biomassa_colhida_kg": 0, "receita_real_rs": 25000},
    {"biomassa_colhida_kg": 1000, "receita_real_rs": -1},
    {"biomassa_colhida_kg": 1000, "receita_real_rs": 10_000_000_000},
    {"biomassa_colhida_kg": 0.01, "receita_real_rs": 9_999_999_999},  # preço por kg estoura a coluna
])
def test_encerrar_payload_invalido_da_422(client, gestor, ciclo, corpo):
    _biometria(client, gestor, ciclo["id"])
    assert _encerrar(client, gestor, ciclo["id"], **corpo).status_code == 422
    assert _ciclo_da_api(client, gestor, ciclo["id"])["status"] == "ATIVO"


def test_encerrar_antes_do_povoamento_da_422(client, gestor, ciclo):
    _biometria(client, gestor, ciclo["id"])
    r = _encerrar(client, gestor, ciclo["id"], data_despesca_real="2026-07-01", biomassa_colhida_kg=1000,
                  receita_real_rs=25000)
    assert r.status_code == 422
    assert _vendas(client, gestor, ciclo["id"]) == []


def test_encerrar_ciclo_ja_finalizado_da_400(client, gestor, ciclo):
    _biometria(client, gestor, ciclo["id"])
    assert _encerrar(client, gestor, ciclo["id"], biomassa_colhida_kg=1000, receita_real_rs=25000).status_code == 200
    assert _encerrar(client, gestor, ciclo["id"], biomassa_colhida_kg=1000, receita_real_rs=25000).status_code == 400


def test_encerrar_audita_o_que_mudou(client, gestor, ciclo):
    _biometria(client, gestor, ciclo["id"])
    _vender(client, gestor, ciclo["id"], tipo="DESBASTE", data="2026-09-20", biomassa=200, preco=20)
    assert _encerrar(client, gestor, ciclo["id"], data_despesca_real=DATA_FINAL, biomassa_colhida_kg=1000,
                     receita_real_rs=25000).status_code == 200

    r = client.get("/api/v1/auditoria/", params={"limite": 200, "entidade": "CicloProdutivo"}, headers=gestor)
    [log] = [x for x in r.json()["items"] if x["acao"] == "ENCERRAR_CICLO" and x["registro_id"] == ciclo["id"]]
    assert (log["dados_anteriores"]["status"], log["dados_novos"]["status"]) == ("ATIVO", "FINALIZADO")
    assert (log["dados_novos"]["biomassa_colhida_kg"], log["dados_novos"]["receita_real_rs"]) == (1200.0, 29000.0)
    [final] = [v for v in _vendas(client, gestor, ciclo["id"]) if v["tipo"] == "DESPESCA_FINAL"]
    assert log["dados_novos"]["venda_despesca_final_id"] == final["id"]
