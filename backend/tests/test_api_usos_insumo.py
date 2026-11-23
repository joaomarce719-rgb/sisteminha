"""Uso de insumo no ciclo: custo automático pelo preço médio e reprocessamento (seção 5.2 do design)."""

from datetime import date, timedelta
from uuid import UUID

import pytest

from tests.conftest import unico

HOJE = date.today().isoformat()
ONTEM = (date.today() - timedelta(days=1)).isoformat()
ANTEONTEM = (date.today() - timedelta(days=2)).isoformat()
AMANHA = (date.today() + timedelta(days=1)).isoformat()


def _criar_insumo(client, headers, **extra):
    r = client.post("/api/v1/insumos/", json={"nome": unico("Cal"), "unidade_uso": "kg", **extra}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _comprar(client, gestor, insumo_id, quantidade, valor_total, data=HOJE, **extra):
    r = client.post(
        f"/api/v1/insumos/{insumo_id}/compras",
        json={"data_compra": data, "quantidade": quantidade, "valor_total_rs": valor_total,
              "retroativo": data != HOJE, **extra},
        headers=gestor,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _usar(client, headers, ciclo_id, insumo_id, quantidade, data=HOJE, **extra):
    payload = {"insumo_id": insumo_id, "data_uso": data, "quantidade": quantidade, "fase": "CULTIVO", **extra}
    return client.post(f"/api/v1/ciclos/{ciclo_id}/usos-insumo", json=payload, headers=headers)


def _usos(client, headers, ciclo_id):
    r = client.get(f"/api/v1/ciclos/{ciclo_id}/usos-insumo", headers=headers)
    assert r.status_code == 200, r.text
    return {u["id"]: u for u in r.json()}


def _custos_do_insumo(client, gestor, ciclo_id, insumo):
    r = client.get(f"/api/v1/ciclos/{ciclo_id}/custos/", headers=gestor)
    assert r.status_code == 200, r.text
    return [c for c in r.json() if c["descricao"].startswith(insumo["nome"])]


def _mudar_status(ciclo_id, status):
    from src.database import SessionLocal
    from src.models.ciclo_produtivo import CicloProdutivo
    from src.models.enums import StatusCiclo

    with SessionLocal() as db:
        db.get(CicloProdutivo, UUID(ciclo_id)).status = StatusCiclo(status)
        db.commit()


@pytest.fixture
def insumo(client, gestor):
    return _criar_insumo(client, gestor, categoria="PROBIOTICOS_QUIMICOS")


@pytest.fixture
def ciclo(novo_ciclo):
    return novo_ciclo()


@pytest.fixture(scope="module")
def gestor_outra_org(client, admin, login):
    org = client.post("/api/v1/organizacoes/", json={"nome": "Fazenda Usos", "identificador": unico("USO")},
                      headers=admin)
    assert org.status_code == 201, org.text
    email = f"{unico('gestoruso')}@x.com"
    r = client.post("/api/v1/admin/gestores", json={"nome_completo": "Gestor Usos", "email": email,
                                                    "senha": "abc12345", "organizacao_id": org.json()["id"]},
                    headers=admin)
    assert r.status_code == 201, r.text
    return login(email, "abc12345")


def test_uso_gera_custo_automatico(client, gestor, insumo, ciclo):
    _comprar(client, gestor, insumo["id"], 100, 300)
    r = _usar(client, gestor, ciclo["id"], insumo["id"], 50, fase="DESPESCA")
    assert r.status_code == 201, r.text
    uso = r.json()
    assert (uso["preco_unitario_rs"], uso["valor_rs"], uso["pendente_de_valor"]) == (3.0, 150.0, False)
    assert (uso["insumo_nome"], uso["unidade_uso"], uso["fase"]) == (insumo["nome"], "kg", "DESPESCA")

    [custo] = _custos_do_insumo(client, gestor, ciclo["id"], insumo)
    assert custo["valor_rs"] == 150.0
    assert custo["categoria"] == "PROBIOTICOS_QUIMICOS"
    assert custo["fase"] == "DESPESCA"
    assert custo["descricao"] == f"{insumo['nome']} (50 kg)"
    assert custo["data_lancamento"] == HOJE


def test_editar_e_excluir_uso_atualiza_e_remove_o_custo(client, gestor, insumo, ciclo):
    _comprar(client, gestor, insumo["id"], 100, 300)
    uso = _usar(client, gestor, ciclo["id"], insumo["id"], 50).json()
    url = f"/api/v1/ciclos/{ciclo['id']}/usos-insumo/{uso['id']}"

    r = client.put(url, json={"insumo_id": insumo["id"], "data_uso": HOJE, "quantidade": 20, "fase": "CULTIVO"},
                   headers=gestor)
    assert r.status_code == 200, r.text
    assert r.json()["valor_rs"] == 60.0
    [custo] = _custos_do_insumo(client, gestor, ciclo["id"], insumo)
    assert (custo["valor_rs"], custo["descricao"]) == (60.0, f"{insumo['nome']} (20 kg)")

    assert client.delete(url, headers=gestor).status_code == 204
    assert _custos_do_insumo(client, gestor, ciclo["id"], insumo) == []
    assert uso["id"] not in _usos(client, gestor, ciclo["id"])


def test_campo_lanca_uso_e_nao_ve_valores(client, gestor, campo, insumo, ciclo):
    _comprar(client, gestor, insumo["id"], 100, 300)
    r = _usar(client, campo, ciclo["id"], insumo["id"], 10)
    assert r.status_code == 201, r.text
    for uso in (r.json(), _usos(client, campo, ciclo["id"])[r.json()["id"]]):
        assert uso["quantidade"] == 10
        assert (uso["preco_unitario_rs"], uso["valor_rs"], uso["pendente_de_valor"]) == (None, None, None)
    assert client.get(f"/api/v1/ciclos/{ciclo['id']}/custos/", headers=campo).status_code == 403
    # o custo foi gerado mesmo lançado pelo campo
    assert _usos(client, gestor, ciclo["id"])[r.json()["id"]]["valor_rs"] == 30.0


def test_campo_nao_pode_corrigir_preco(client, gestor, campo, insumo, ciclo):
    _comprar(client, gestor, insumo["id"], 100, 300)
    assert _usar(client, campo, ciclo["id"], insumo["id"], 10, preco_corrigido_rs=1).status_code == 403


def test_vigia_lanca_uso_sem_ver_valores_e_nao_lista_usos(client, gestor, vigia, insumo, ciclo):
    _comprar(client, gestor, insumo["id"], 100, 300)
    r = _usar(client, vigia, ciclo["id"], insumo["id"], 5)
    assert r.status_code == 201, r.text
    assert (r.json()["preco_unitario_rs"], r.json()["valor_rs"], r.json()["pendente_de_valor"]) == (None, None, None)
    assert client.get(f"/api/v1/ciclos/{ciclo['id']}/usos-insumo", headers=vigia).status_code == 403


def test_so_gestor_edita_e_exclui_uso(client, gestor, campo, vigia, insumo, ciclo):
    _comprar(client, gestor, insumo["id"], 100, 300)
    uso = _usar(client, campo, ciclo["id"], insumo["id"], 10).json()
    url = f"/api/v1/ciclos/{ciclo['id']}/usos-insumo/{uso['id']}"
    corpo = {"insumo_id": insumo["id"], "data_uso": HOJE, "quantidade": 1, "fase": "CULTIVO"}
    for headers in (campo, vigia):
        assert client.put(url, json=corpo, headers=headers).status_code == 403
        assert client.delete(url, headers=headers).status_code == 403


def test_uso_sem_compra_fica_pendente_e_sem_custo(client, gestor, insumo, ciclo):
    r = _usar(client, gestor, ciclo["id"], insumo["id"], 10)
    assert r.status_code == 201, r.text
    assert (r.json()["preco_unitario_rs"], r.json()["valor_rs"], r.json()["pendente_de_valor"]) == (None, None, True)
    assert _custos_do_insumo(client, gestor, ciclo["id"], insumo) == []


def test_compra_posterior_ao_uso_nao_gera_custo(client, gestor, insumo, ciclo):
    uso = _usar(client, gestor, ciclo["id"], insumo["id"], 10, data=ONTEM, retroativo=True).json()
    _comprar(client, gestor, insumo["id"], 100, 300)
    assert _usos(client, gestor, ciclo["id"])[uso["id"]]["pendente_de_valor"] is True
    assert _custos_do_insumo(client, gestor, ciclo["id"], insumo) == []


def test_compra_retroativa_gera_o_custo_pendente(client, gestor, insumo, ciclo):
    uso = _usar(client, gestor, ciclo["id"], insumo["id"], 10).json()
    _comprar(client, gestor, insumo["id"], 100, 300, data=ONTEM)
    atual = _usos(client, gestor, ciclo["id"])[uso["id"]]
    assert (atual["valor_rs"], atual["pendente_de_valor"]) == (30.0, False)
    assert [c["valor_rs"] for c in _custos_do_insumo(client, gestor, ciclo["id"], insumo)] == [30.0]


def test_uso_e_compra_no_mesmo_dia_usam_a_compra(client, gestor, insumo, ciclo):
    # o uso foi lançado antes, mas na mesma data a compra vem primeiro
    uso = _usar(client, gestor, ciclo["id"], insumo["id"], 10).json()
    assert uso["pendente_de_valor"] is True
    _comprar(client, gestor, insumo["id"], 100, 400)
    assert _usos(client, gestor, ciclo["id"])[uso["id"]]["valor_rs"] == 40.0


def test_uso_retroativo_entre_compras_usa_o_preco_da_epoca(client, gestor, insumo, ciclo):
    _comprar(client, gestor, insumo["id"], 100, 300, data=ANTEONTEM)
    _comprar(client, gestor, insumo["id"], 100, 500)
    uso = _usar(client, gestor, ciclo["id"], insumo["id"], 10, data=ONTEM, retroativo=True).json()
    assert uso["preco_unitario_rs"] == 3.0
    assert uso["retroativo"] is True


def test_saldo_insuficiente_aceita_e_marca_saldo_negativo(client, gestor, insumo, ciclo):
    _comprar(client, gestor, insumo["id"], 10, 30)
    r = _usar(client, gestor, ciclo["id"], insumo["id"], 50)
    assert r.status_code == 201, r.text
    assert r.json()["valor_rs"] == 150.0  # último preço médio conhecido
    item = next(i for i in client.get("/api/v1/insumos/", headers=gestor).json() if i["id"] == insumo["id"])
    assert (item["saldo"], item["saldo_negativo"]) == (-40, True)


def test_excluir_compra_deixa_usos_pendentes_e_remove_o_custo(client, gestor, insumo, ciclo):
    compra = _comprar(client, gestor, insumo["id"], 100, 300)
    uso = _usar(client, gestor, ciclo["id"], insumo["id"], 50).json()
    assert client.delete(f"/api/v1/insumos/{insumo['id']}/compras/{compra['id']}", headers=gestor).status_code == 204
    atual = _usos(client, gestor, ciclo["id"])[uso["id"]]
    assert (atual["preco_unitario_rs"], atual["valor_rs"], atual["pendente_de_valor"]) == (None, None, True)
    assert _custos_do_insumo(client, gestor, ciclo["id"], insumo) == []


def test_alterar_valor_da_compra_recalcula_o_custo_do_uso(client, gestor, insumo, ciclo):
    compra = _comprar(client, gestor, insumo["id"], 100, 300)
    uso = _usar(client, gestor, ciclo["id"], insumo["id"], 50).json()
    r = client.put(f"/api/v1/insumos/{insumo['id']}/compras/{compra['id']}",
                   json={"data_compra": HOJE, "quantidade": 100, "valor_total_rs": 400}, headers=gestor)
    assert r.status_code == 200, r.text
    atual = _usos(client, gestor, ciclo["id"])[uso["id"]]
    assert (atual["valor_rs"], atual["recalculado_em"]) == (200.0, None)  # ciclo ativo não marca recálculo
    assert [c["valor_rs"] for c in _custos_do_insumo(client, gestor, ciclo["id"], insumo)] == [200.0]


def test_preco_corrigido_pelo_gestor_e_preservado(client, gestor, insumo, ciclo):
    compra = _comprar(client, gestor, insumo["id"], 100, 300)
    uso = _usar(client, gestor, ciclo["id"], insumo["id"], 50, preco_corrigido_rs=2.5).json()
    assert (uso["preco_unitario_rs"], uso["valor_rs"]) == (2.5, 125.0)
    client.put(f"/api/v1/insumos/{insumo['id']}/compras/{compra['id']}",
               json={"data_compra": HOJE, "quantidade": 100, "valor_total_rs": 900}, headers=gestor)
    assert _usos(client, gestor, ciclo["id"])[uso["id"]]["valor_rs"] == 125.0
    # a correção vale até sem compra
    client.delete(f"/api/v1/insumos/{insumo['id']}/compras/{compra['id']}", headers=gestor)
    assert _usos(client, gestor, ciclo["id"])[uso["id"]]["pendente_de_valor"] is False


def _corpo_do_uso(insumo, quantidade, **extra):
    return {"insumo_id": insumo["id"], "data_uso": HOJE, "quantidade": quantidade, "fase": "CULTIVO", **extra}


def test_resposta_traz_o_preco_corrigido_so_para_o_gestor(client, gestor, campo, vigia, insumo, ciclo):
    _comprar(client, gestor, insumo["id"], 100, 300)
    criado = _usar(client, gestor, ciclo["id"], insumo["id"], 50, preco_corrigido_rs=2.5).json()
    sem_correcao = _usar(client, gestor, ciclo["id"], insumo["id"], 10).json()
    assert (criado["preco_corrigido_rs"], sem_correcao["preco_corrigido_rs"]) == (2.5, None)
    assert _usos(client, gestor, ciclo["id"])[criado["id"]]["preco_corrigido_rs"] == 2.5

    # CAMPO e VIGIA nunca recebem valores, nem o preço corrigido de um uso que o gestor corrigiu
    assert _usos(client, campo, ciclo["id"])[criado["id"]]["preco_corrigido_rs"] is None
    assert _usar(client, vigia, ciclo["id"], insumo["id"], 5).json()["preco_corrigido_rs"] is None


def test_editar_uso_reenviando_o_preco_corrigido_mantem_a_correcao(client, gestor, insumo, ciclo):
    _comprar(client, gestor, insumo["id"], 100, 300)
    uso = _usar(client, gestor, ciclo["id"], insumo["id"], 50, preco_corrigido_rs=2.5).json()
    url = f"/api/v1/ciclos/{ciclo['id']}/usos-insumo/{uso['id']}"

    # o formulário reenvia o preço corrigido que recebeu: a edição de quantidade não o perde
    r = client.put(url, json=_corpo_do_uso(insumo, 20, preco_corrigido_rs=uso["preco_corrigido_rs"]), headers=gestor)
    assert r.status_code == 200, r.text
    assert (r.json()["preco_corrigido_rs"], r.json()["preco_unitario_rs"], r.json()["valor_rs"]) == (2.5, 2.5, 50.0)
    assert [c["valor_rs"] for c in _custos_do_insumo(client, gestor, ciclo["id"], insumo)] == [50.0]


def test_editar_uso_sem_preco_corrigido_remove_a_correcao(client, gestor, insumo, ciclo):
    _comprar(client, gestor, insumo["id"], 100, 300)
    uso = _usar(client, gestor, ciclo["id"], insumo["id"], 50, preco_corrigido_rs=2.5).json()
    url = f"/api/v1/ciclos/{ciclo['id']}/usos-insumo/{uso['id']}"

    r = client.put(url, json=_corpo_do_uso(insumo, 20, preco_corrigido_rs=None), headers=gestor)
    assert r.status_code == 200, r.text
    assert (r.json()["preco_corrigido_rs"], r.json()["preco_unitario_rs"], r.json()["valor_rs"]) == (None, 3.0, 60.0)
    assert [c["valor_rs"] for c in _custos_do_insumo(client, gestor, ciclo["id"], insumo)] == [60.0]


def test_ciclo_finalizado_registra_recalculado_em(client, gestor, campo, insumo, ciclo):
    compra = _comprar(client, gestor, insumo["id"], 100, 300)
    uso = _usar(client, gestor, ciclo["id"], insumo["id"], 50).json()
    client.post(f"/api/v1/ciclos/{ciclo['id']}/biometrias/",
                json={"data_medicao": "2026-09-01", "quantidade_amostrada": 50, "peso_medio_g": 20}, headers=gestor)
    r = client.post(f"/api/v1/ciclos/{ciclo['id']}/encerrar",
                    json={"data_despesca_real": HOJE, "biomassa_colhida_kg": 1000, "receita_real_rs": 20000},
                    headers=gestor)
    assert r.status_code == 200, r.text

    client.put(f"/api/v1/insumos/{insumo['id']}/compras/{compra['id']}",
               json={"data_compra": HOJE, "quantidade": 100, "valor_total_rs": 500}, headers=gestor)
    atual = _usos(client, gestor, ciclo["id"])[uso["id"]]
    assert atual["valor_rs"] == 250.0
    assert atual["recalculado_em"] is not None
    logs = client.get("/api/v1/auditoria/", params={"limite": 200, "entidade": "ConsumoInsumo"}, headers=gestor)
    recalculos = [log for log in logs.json()["items"]
                  if log["registro_id"] == uso["id"] and log["acao"] == "RECALCULAR_USO_INSUMO"]
    assert len(recalculos) == 1
    assert (recalculos[0]["dados_anteriores"]["valor_rs"], recalculos[0]["dados_novos"]["valor_rs"]) == (150.0, 250.0)

    # no ciclo finalizado só o gestor lança
    assert _usar(client, campo, ciclo["id"], insumo["id"], 1).status_code == 403
    novo = _usar(client, gestor, ciclo["id"], insumo["id"], 1)
    assert novo.status_code == 201
    assert novo.json()["recalculado_em"] is None  # o uso que o gestor acabou de lançar não é recálculo
    logs = client.get("/api/v1/auditoria/", params={"limite": 200, "entidade": "ConsumoInsumo"}, headers=gestor)
    assert not [log for log in logs.json()["items"]
                if log["registro_id"] == novo.json()["id"] and log["acao"] == "RECALCULAR_USO_INSUMO"]


def test_status_do_ciclo_limita_o_uso(client, gestor, insumo, novo_ciclo):
    planejado = novo_ciclo()
    _mudar_status(planejado["id"], "PLANEJADO")
    assert _usar(client, gestor, planejado["id"], insumo["id"], 1).status_code == 422
    assert _usar(client, gestor, planejado["id"], insumo["id"], 1, fase="PREPARO").status_code == 201

    cancelado = novo_ciclo()
    _mudar_status(cancelado["id"], "CANCELADO")
    assert _usar(client, gestor, cancelado["id"], insumo["id"], 1).status_code == 400


def test_data_passada_exige_retroativo(client, gestor, insumo, ciclo):
    r = _usar(client, gestor, ciclo["id"], insumo["id"], 1, data=ONTEM)
    assert r.status_code == 422
    assert "retroativo" in r.json()["detail"]
    assert _usar(client, gestor, ciclo["id"], insumo["id"], 1, data=ONTEM, retroativo=True).status_code == 201


def test_data_futura_da_422(client, gestor, insumo, ciclo):
    assert _usar(client, gestor, ciclo["id"], insumo["id"], 1, data=AMANHA, retroativo=True).status_code == 422


def test_data_anterior_ao_povoamento_so_no_preparo(client, gestor, insumo, novo_ciclo):
    ciclo = novo_ciclo(data_povoamento=ONTEM)
    assert _usar(client, gestor, ciclo["id"], insumo["id"], 1, data=ANTEONTEM, retroativo=True).status_code == 422
    assert _usar(client, gestor, ciclo["id"], insumo["id"], 1, data=ANTEONTEM, retroativo=True,
                 fase="PREPARO").status_code == 201


def test_insumo_inativo_da_422(client, gestor, insumo, ciclo):
    client.put(f"/api/v1/insumos/{insumo['id']}", json={"ativo": False}, headers=gestor)
    assert _usar(client, gestor, ciclo["id"], insumo["id"], 1).status_code == 422


@pytest.mark.parametrize(
    "campo_invalido",
    [
        {"quantidade": 0}, {"quantidade": 0.00001}, {"quantidade": 1e10},
        {"preco_corrigido_rs": 0.00001}, {"preco_corrigido_rs": 1e8},
        {"fase": "COLHEITA"},
    ],
)
def test_uso_valida_quantidade_preco_e_fase(client, gestor, insumo, ciclo, campo_invalido):
    payload = {"insumo_id": insumo["id"], "data_uso": HOJE, "quantidade": 1, "fase": "CULTIVO", **campo_invalido}
    assert client.post(f"/api/v1/ciclos/{ciclo['id']}/usos-insumo", json=payload, headers=gestor).status_code == 422


def test_excluir_custo_gerado_por_uso_da_409(client, gestor, insumo, ciclo):
    _comprar(client, gestor, insumo["id"], 100, 300)
    _usar(client, gestor, ciclo["id"], insumo["id"], 50)
    [custo] = _custos_do_insumo(client, gestor, ciclo["id"], insumo)
    r = client.delete(f"/api/v1/custos/{custo['id']}", headers=gestor)
    assert r.status_code == 409
    assert "exclua o uso" in r.json()["detail"]


def test_usos_ficam_na_auditoria(client, gestor, insumo, ciclo):
    uso = _usar(client, gestor, ciclo["id"], insumo["id"], 10).json()
    url = f"/api/v1/ciclos/{ciclo['id']}/usos-insumo/{uso['id']}"
    client.put(url, json={"insumo_id": insumo["id"], "data_uso": HOJE, "quantidade": 8, "fase": "CULTIVO",
                          "preco_corrigido_rs": 4}, headers=gestor)
    client.delete(url, headers=gestor)
    logs = client.get("/api/v1/auditoria/", params={"limite": 200, "entidade": "ConsumoInsumo"}, headers=gestor)
    acoes = {log["acao"]: log for log in logs.json()["items"] if log["registro_id"] == uso["id"]}
    assert {"CRIAR_USO_INSUMO", "ATUALIZAR_USO_INSUMO", "EXCLUIR_USO_INSUMO"} <= set(acoes)
    assert acoes["ATUALIZAR_USO_INSUMO"]["dados_novos"]["preco_corrigido_rs"] == 4


def test_ciclo_ou_insumo_de_outra_organizacao_da_404(client, gestor, gestor_outra_org, insumo, ciclo):
    uso = _usar(client, gestor, ciclo["id"], insumo["id"], 1).json()
    base = f"/api/v1/ciclos/{ciclo['id']}/usos-insumo"
    corpo = {"insumo_id": insumo["id"], "data_uso": HOJE, "quantidade": 1, "fase": "CULTIVO"}

    assert client.post(base, json=corpo, headers=gestor_outra_org).status_code == 404
    assert client.get(base, headers=gestor_outra_org).status_code == 404
    assert client.put(f"{base}/{uso['id']}", json=corpo, headers=gestor_outra_org).status_code == 404
    assert client.delete(f"{base}/{uso['id']}", headers=gestor_outra_org).status_code == 404

    insumo_alheio = _criar_insumo(client, gestor_outra_org)
    assert _usar(client, gestor, ciclo["id"], insumo_alheio["id"], 1).status_code == 404


def test_uso_de_outro_ciclo_da_404(client, gestor, insumo, ciclo, novo_ciclo):
    outro = novo_ciclo()
    uso = _usar(client, gestor, outro["id"], insumo["id"], 1).json()
    url = f"/api/v1/ciclos/{ciclo['id']}/usos-insumo/{uso['id']}"
    assert client.delete(url, headers=gestor).status_code == 404


def test_excluir_ciclo_reprocessa_o_insumo_dos_outros_ciclos(client, gestor, insumo, novo_ciclo):
    dia = [(date.today() - timedelta(days=n)).isoformat() for n in (4, 3, 2, 1)]
    ciclo_x, ciclo_y = novo_ciclo(), novo_ciclo()
    _comprar(client, gestor, insumo["id"], 100, 300, data=dia[0])
    assert _usar(client, gestor, ciclo_x["id"], insumo["id"], 90, data=dia[1], retroativo=True).status_code == 201
    _comprar(client, gestor, insumo["id"], 100, 500, data=dia[2])
    uso_y = _usar(client, gestor, ciclo_y["id"], insumo["id"], 50, data=dia[3], retroativo=True).json()
    assert uso_y["valor_rs"] == 240.91  # pm = (10 x 3 + 500) / 110

    assert client.delete(f"/api/v1/ciclos/{ciclo_x['id']}", headers=gestor).status_code == 200
    assert _usos(client, gestor, ciclo_y["id"])[uso_y["id"]]["valor_rs"] == 200.0  # pm = (100 x 3 + 500) / 200
    assert [c["valor_rs"] for c in _custos_do_insumo(client, gestor, ciclo_y["id"], insumo)] == [200.0]
