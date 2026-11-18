"""Cadastro de insumos e compras (preço médio, permissões, isolamento e auditoria)."""

from datetime import date, timedelta

import pytest

from tests.conftest import unico

HOJE = date.today().isoformat()
ONTEM = (date.today() - timedelta(days=1)).isoformat()
AMANHA = (date.today() + timedelta(days=1)).isoformat()


def _criar_insumo(client, headers, nome=None, **extra):
    return client.post(
        "/api/v1/insumos/", json={"nome": nome or unico("Cal"), "unidade_uso": "kg", **extra}, headers=headers
    )


def _comprar(client, headers, insumo_id, quantidade, valor_total, **extra):
    return client.post(
        f"/api/v1/insumos/{insumo_id}/compras",
        json={"data_compra": HOJE, "quantidade": quantidade, "valor_total_rs": valor_total, **extra},
        headers=headers,
    )


def _do_insumo(client, headers, insumo_id):
    itens = client.get("/api/v1/insumos/", headers=headers).json()
    return next(i for i in itens if i["id"] == insumo_id)


def _auditoria(client, headers, entidade, registro_id):
    r = client.get("/api/v1/auditoria/", params={"limite": 200, "entidade": entidade}, headers=headers)
    assert r.status_code == 200
    return [log for log in r.json()["items"] if log["registro_id"] == registro_id]


@pytest.fixture
def insumo(client, gestor):
    r = _criar_insumo(client, gestor)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def gestor_outra_org(client, admin, login):
    org = client.post("/api/v1/organizacoes/", json={"nome": "Fazenda Insumos", "identificador": unico("INS")},
                      headers=admin)
    assert org.status_code == 201, org.text
    email = f"{unico('gestorins')}@x.com"
    r = client.post("/api/v1/admin/gestores", json={"nome_completo": "Gestor Insumos", "email": email,
                                                    "senha": "abc12345", "organizacao_id": org.json()["id"]},
                    headers=admin)
    assert r.status_code == 201, r.text
    return login(email, "abc12345")


def test_gestor_cria_insumo(client, gestor):
    nome = unico("Probiótico")
    r = _criar_insumo(client, gestor, nome=f"  {nome}  ", unidade_uso="L", categoria="PROBIOTICOS_QUIMICOS")
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["nome"] == nome
    assert corpo["unidade_uso"] == "L"
    assert corpo["categoria"] == "PROBIOTICOS_QUIMICOS"
    assert corpo["ativo"] is True
    assert corpo["saldo"] == 0
    assert corpo["preco_medio_rs"] is None
    assert corpo["saldo_negativo"] is False


def test_categoria_padrao_e_outros(client, insumo):
    assert insumo["categoria"] == "OUTROS"


def test_nome_duplicado_sem_diferenciar_maiusculas_da_409(client, gestor):
    nome = unico("Probiótico")
    assert _criar_insumo(client, gestor, nome=nome).status_code == 201
    for repetido in (nome.upper(), nome.replace("ó", "o"), f"  {nome}  "):
        r = _criar_insumo(client, gestor, nome=repetido)
        assert r.status_code == 409, (repetido, r.text)


def test_renomear_para_nome_existente_da_409(client, gestor, insumo):
    outro = _criar_insumo(client, gestor).json()
    assert client.put(f"/api/v1/insumos/{outro['id']}", json={"nome": insumo["nome"].upper()},
                      headers=gestor).status_code == 409
    # manter o próprio nome (só trocando a caixa) é permitido
    r = client.put(f"/api/v1/insumos/{outro['id']}", json={"nome": outro["nome"].upper()}, headers=gestor)
    assert r.status_code == 200, r.text
    assert r.json()["nome"] == outro["nome"].upper()


@pytest.mark.parametrize("categoria", ["RACAO", "POS_LARVAS"])
def test_categoria_racao_e_pos_larvas_da_422(client, gestor, insumo, categoria):
    assert _criar_insumo(client, gestor, categoria=categoria).status_code == 422
    assert client.put(f"/api/v1/insumos/{insumo['id']}", json={"categoria": categoria},
                      headers=gestor).status_code == 422


def test_gestor_edita_insumo_e_inativo_some_da_lista_do_campo(client, gestor, campo, insumo):
    r = client.put(f"/api/v1/insumos/{insumo['id']}",
                   json={"unidade_uso": "saco", "categoria": "MANUTENCAO", "ativo": False}, headers=gestor)
    assert r.status_code == 200, r.text
    assert (r.json()["unidade_uso"], r.json()["categoria"], r.json()["ativo"]) == ("saco", "MANUTENCAO", False)
    assert insumo["id"] in [i["id"] for i in client.get("/api/v1/insumos/", headers=gestor).json()]
    assert insumo["id"] not in [i["id"] for i in client.get("/api/v1/insumos/", headers=campo).json()]


def test_campo_lista_insumos_com_saldo_e_sem_preco(client, gestor, campo, insumo):
    assert _comprar(client, gestor, insumo["id"], 100, 300).status_code == 201
    item = _do_insumo(client, campo, insumo["id"])
    assert item["saldo"] == 100
    assert item["preco_medio_rs"] is None
    assert item["saldo_negativo"] is None


def test_vigia_lista_insumos_so_com_nome_e_unidade(client, gestor, vigia, insumo):
    assert _comprar(client, gestor, insumo["id"], 100, 300).status_code == 201
    item = _do_insumo(client, vigia, insumo["id"])
    assert (item["nome"], item["unidade_uso"]) == (insumo["nome"], "kg")
    assert item["saldo"] is None
    assert item["preco_medio_rs"] is None
    assert item["saldo_negativo"] is None


def test_campo_nao_cria_insumo_nem_compra(client, gestor, campo, vigia, insumo):
    for headers in (campo, vigia):
        assert _criar_insumo(client, headers).status_code == 403
        assert client.put(f"/api/v1/insumos/{insumo['id']}", json={"ativo": False}, headers=headers).status_code == 403
        assert _comprar(client, headers, insumo["id"], 10, 30).status_code == 403
        assert client.get(f"/api/v1/insumos/{insumo['id']}/compras", headers=headers).status_code == 403


def test_compra_com_data_passada_exige_retroativo(client, gestor, insumo):
    base = {"quantidade": 10, "valor_total_rs": 30}
    url = f"/api/v1/insumos/{insumo['id']}/compras"
    sem_marca = client.post(url, json={**base, "data_compra": ONTEM}, headers=gestor)
    assert sem_marca.status_code == 422
    assert "retroativo" in sem_marca.json()["detail"]
    com_marca = client.post(url, json={**base, "data_compra": ONTEM, "retroativo": True}, headers=gestor)
    assert com_marca.status_code == 201, com_marca.text
    assert com_marca.json()["retroativo"] is True
    # data futura é recusada mesmo com a marca
    assert client.post(url, json={**base, "data_compra": AMANHA, "retroativo": True}, headers=gestor).status_code == 422


@pytest.mark.parametrize("campo_invalido", [{"quantidade": 0}, {"valor_total_rs": 0}, {"quantidade": -1}])
def test_compra_exige_quantidade_e_valor_positivos(client, gestor, insumo, campo_invalido):
    payload = {"data_compra": HOJE, "quantidade": 10, "valor_total_rs": 30, **campo_invalido}
    assert client.post(f"/api/v1/insumos/{insumo['id']}/compras", json=payload, headers=gestor).status_code == 422


def test_compra_atualiza_saldo_e_preco_medio_do_exemplo_da_cal(client, gestor, insumo):
    assert _comprar(client, gestor, insumo["id"], 100, 300).status_code == 201
    assert _comprar(client, gestor, insumo["id"], 100, 400).status_code == 201
    item = _do_insumo(client, gestor, insumo["id"])
    assert item["saldo"] == 200
    assert item["preco_medio_rs"] == 3.5
    assert item["saldo_negativo"] is False


def test_gestor_edita_e_exclui_compra(client, gestor, insumo):
    primeira = _comprar(client, gestor, insumo["id"], 100, 300).json()
    segunda = _comprar(client, gestor, insumo["id"], 100, 400).json()
    base = f"/api/v1/insumos/{insumo['id']}/compras"

    r = client.put(f"{base}/{segunda['id']}", json={"data_compra": HOJE, "quantidade": 100, "valor_total_rs": 600,
                                                    "fornecedor": "Calcário SA"}, headers=gestor)
    assert r.status_code == 200, r.text
    assert r.json()["fornecedor"] == "Calcário SA"
    assert _do_insumo(client, gestor, insumo["id"])["preco_medio_rs"] == 4.5

    assert client.delete(f"{base}/{segunda['id']}", headers=gestor).status_code == 204
    item = _do_insumo(client, gestor, insumo["id"])
    assert (item["saldo"], item["preco_medio_rs"]) == (100, 3.0)
    assert [c["id"] for c in client.get(base, headers=gestor).json()] == [primeira["id"]]

    # a data passada também vale na edição
    r = client.put(f"{base}/{primeira['id']}", json={"data_compra": ONTEM, "quantidade": 100, "valor_total_rs": 300},
                   headers=gestor)
    assert r.status_code == 422


def test_insumo_de_outra_organizacao_da_404(client, gestor, gestor_outra_org, insumo):
    compra = _comprar(client, gestor, insumo["id"], 100, 300).json()
    base = f"/api/v1/insumos/{insumo['id']}"
    corpo_compra = {"data_compra": HOJE, "quantidade": 1, "valor_total_rs": 1}

    assert insumo["id"] not in [i["id"] for i in client.get("/api/v1/insumos/", headers=gestor_outra_org).json()]
    assert client.put(base, json={"ativo": False}, headers=gestor_outra_org).status_code == 404
    assert client.get(f"{base}/compras", headers=gestor_outra_org).status_code == 404
    assert client.post(f"{base}/compras", json=corpo_compra, headers=gestor_outra_org).status_code == 404
    assert client.put(f"{base}/compras/{compra['id']}", json=corpo_compra, headers=gestor_outra_org).status_code == 404
    assert client.delete(f"{base}/compras/{compra['id']}", headers=gestor_outra_org).status_code == 404

    # o mesmo nome é livre em outra organização
    assert _criar_insumo(client, gestor_outra_org, nome=insumo["nome"]).status_code == 201


def test_compra_de_outro_insumo_da_404(client, gestor, insumo):
    outro = _criar_insumo(client, gestor).json()
    compra = _comprar(client, gestor, outro["id"], 10, 30).json()
    url = f"/api/v1/insumos/{insumo['id']}/compras/{compra['id']}"
    assert client.delete(url, headers=gestor).status_code == 404
    assert client.put(url, json={"data_compra": HOJE, "quantidade": 1, "valor_total_rs": 1},
                      headers=gestor).status_code == 404


def test_compras_ficam_na_auditoria(client, gestor, insumo):
    base = f"/api/v1/insumos/{insumo['id']}/compras"
    compra = _comprar(client, gestor, insumo["id"], 100, 300, fornecedor="Agro Sul").json()
    client.put(f"{base}/{compra['id']}", json={"data_compra": HOJE, "quantidade": 80, "valor_total_rs": 300},
               headers=gestor)
    client.delete(f"{base}/{compra['id']}", headers=gestor)

    logs = {log["acao"]: log for log in _auditoria(client, gestor, "CompraInsumo", compra["id"])}
    assert set(logs) == {"CRIAR_COMPRA_INSUMO", "ATUALIZAR_COMPRA_INSUMO", "EXCLUIR_COMPRA_INSUMO"}
    assert logs["CRIAR_COMPRA_INSUMO"]["dados_novos"]["quantidade"] == 100
    assert logs["ATUALIZAR_COMPRA_INSUMO"]["dados_anteriores"]["quantidade"] == 100
    assert logs["ATUALIZAR_COMPRA_INSUMO"]["dados_novos"]["quantidade"] == 80
    assert logs["EXCLUIR_COMPRA_INSUMO"]["dados_anteriores"]["quantidade"] == 80


def test_cadastro_de_insumo_fica_na_auditoria(client, gestor, insumo):
    client.put(f"/api/v1/insumos/{insumo['id']}", json={"unidade_uso": "saco"}, headers=gestor)
    logs = {log["acao"]: log for log in _auditoria(client, gestor, "Insumo", insumo["id"])}
    assert set(logs) == {"CRIAR_INSUMO", "ATUALIZAR_INSUMO"}
    assert logs["ATUALIZAR_INSUMO"]["dados_anteriores"]["unidade_uso"] == "kg"
    assert logs["ATUALIZAR_INSUMO"]["dados_novos"]["unidade_uso"] == "saco"
