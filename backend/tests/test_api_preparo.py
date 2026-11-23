"""Ciclo em preparo: planejar, etapas, povoar, reagendar e cancelar (seção 5.7 do design)."""

from datetime import date, timedelta

import pytest

from tests.conftest import unico

BASE = "/api/v1/ciclos"
HOJE = date.today().isoformat()
PREVISTA = (date.today() + timedelta(days=30)).isoformat()
POVOAMENTO = (date.today() - timedelta(days=10)).isoformat()
ANTES_DO_POVOAMENTO = (date.today() - timedelta(days=20)).isoformat()
ETAPAS_SUGERIDAS = ["SECAGEM", "CALAGEM", "ADUBACAO", "ABASTECIMENTO", "TRATAMENTO_AGUA"]


def _planejar(client, headers, viveiro_id, **extra):
    return client.post(f"{BASE}/", json={"viveiro_id": viveiro_id, "data_povoamento": PREVISTA, **extra},
                       headers=headers)


def _etapas(client, headers, ciclo_id):
    r = client.get(f"{BASE}/{ciclo_id}/etapas-preparo", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _atualizar_etapa(client, headers, ciclo_id, etapa_id, **campos):
    return client.patch(f"{BASE}/{ciclo_id}/etapas-preparo/{etapa_id}", json=campos, headers=headers)


def _resolver_etapas(client, gestor, ciclo_id, status="NAO_REALIZADA"):
    for etapa in _etapas(client, gestor, ciclo_id):
        assert _atualizar_etapa(client, gestor, ciclo_id, etapa["id"], status=status).status_code == 200


def _povoar(client, headers, ciclo_id, **extra):
    corpo = {"data_povoamento": POVOAMENTO, "quantidade_pos_larvas": 300_000, "custo_aquisicao_pl": 3_000.0, **extra}
    return client.post(f"{BASE}/{ciclo_id}/povoar", json=corpo, headers=headers)


def _acoes(client, gestor, registro_id):
    r = client.get("/api/v1/auditoria/", params={"limite": 200, "entidade": "CicloProdutivo"}, headers=gestor)
    assert r.status_code == 200, r.text
    return [log["acao"] for log in r.json()["items"] if log["registro_id"] == registro_id]


def _criar_insumo(client, gestor):
    r = client.post("/api/v1/insumos/", json={"nome": unico("Cal"), "unidade_uso": "kg"}, headers=gestor)
    assert r.status_code == 201, r.text
    return r.json()


def _usar(client, headers, ciclo_id, insumo_id, **extra):
    corpo = {"insumo_id": insumo_id, "data_uso": HOJE, "quantidade": 1, "fase": "PREPARO", **extra}
    return client.post(f"{BASE}/{ciclo_id}/usos-insumo", json=corpo, headers=headers)


@pytest.fixture
def planejado(client, gestor, novo_viveiro):
    r = _planejar(client, gestor, novo_viveiro()["id"])
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def ativo(client, gestor, planejado):
    _resolver_etapas(client, gestor, planejado["id"])
    r = _povoar(client, gestor, planejado["id"])
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def gestor_outra_org(client, admin, login):
    org = client.post("/api/v1/organizacoes/", json={"nome": "Fazenda Preparo", "identificador": unico("PRE")},
                      headers=admin)
    assert org.status_code == 201, org.text
    email = f"{unico('gestorpre')}@x.com"
    r = client.post("/api/v1/admin/gestores", json={"nome_completo": "Gestor Preparo", "email": email,
                                                    "senha": "abc12345", "organizacao_id": org.json()["id"]},
                    headers=admin)
    assert r.status_code == 201, r.text
    return login(email, "abc12345")


def test_planejar_cria_ciclo_planejado_com_cinco_etapas(client, gestor, planejado):
    assert planejado["status"] == "PLANEJADO"
    assert planejado["data_povoamento"] == PREVISTA
    assert (planejado["quantidade_pos_larvas"], planejado["custo_aquisicao_pl"]) == (None, None)
    assert planejado["densidade_inicial"] is None

    etapas = _etapas(client, gestor, planejado["id"])
    assert [e["tipo"] for e in etapas] == ETAPAS_SUGERIDAS
    assert [e["ordem"] for e in etapas] == [1, 2, 3, 4, 5]
    assert {e["status"] for e in etapas} == {"PENDENTE"}
    assert "PLANEJAR_CICLO" in _acoes(client, gestor, planejado["id"])

    # leitores do ciclo toleram pós-larvas vazias
    assert planejado["id"] in [c["id"] for c in client.get(f"{BASE}/", headers=gestor).json()]
    assert client.get(f"{BASE}/{planejado['id']}", headers=gestor).status_code == 200
    assert client.get(f"{BASE}/{planejado['id']}/exportar-csv", headers=gestor).status_code == 200
    viveiro = planejado["viveiro_id"]
    assert client.get(f"/api/v1/viveiros/{viveiro}", headers=gestor).status_code == 200


def test_planejar_com_campos_de_pos_larvas_da_422(client, gestor, novo_viveiro):
    r = _planejar(client, gestor, novo_viveiro()["id"], quantidade_pos_larvas=300_000, custo_aquisicao_pl=3_000)
    assert r.status_code == 422


@pytest.mark.parametrize("status_aberto", ["PLANEJADO", "ATIVO", "PAUSADO"])
def test_planejar_em_viveiro_com_ciclo_aberto_da_409(client, gestor, planejado, status_aberto):
    if status_aberto != "PLANEJADO":
        _resolver_etapas(client, gestor, planejado["id"])
        assert _povoar(client, gestor, planejado["id"]).status_code == 200
    if status_aberto == "PAUSADO":
        assert client.post(f"{BASE}/{planejado['id']}/pausar", headers=gestor).status_code == 200
    assert _planejar(client, gestor, planejado["viveiro_id"]).status_code == 409


def test_planejar_em_viveiro_inativo_da_400(client, gestor, novo_viveiro):
    viveiro = novo_viveiro()
    r = client.put(f"/api/v1/viveiros/{viveiro['id']}", json={"status_ativo": False}, headers=gestor)
    assert r.status_code == 200, r.text
    assert _planejar(client, gestor, viveiro["id"]).status_code == 400


def test_povoar_bloqueado_com_etapa_pendente(client, gestor, planejado):
    etapas = _etapas(client, gestor, planejado["id"])
    for etapa in etapas[:3]:
        _atualizar_etapa(client, gestor, planejado["id"], etapa["id"], status="CONCLUIDA")
    _atualizar_etapa(client, gestor, planejado["id"], etapas[3]["id"], status="EM_ANDAMENTO")

    r = _povoar(client, gestor, planejado["id"])
    assert r.status_code == 409
    assert "2 etapas" in r.json()["detail"]
    assert client.get(f"{BASE}/{planejado['id']}", headers=gestor).json()["status"] == "PLANEJADO"


def test_povoar_com_etapas_resolvidas_ativa_e_lanca_custo_de_pos_larvas(client, gestor, planejado):
    _resolver_etapas(client, gestor, planejado["id"], status="CONCLUIDA")
    r = _povoar(client, gestor, planejado["id"], peso_medio_pl_g=0.002, laboratorio_origem="Lab X")
    assert r.status_code == 200, r.text
    ciclo = r.json()
    assert ciclo["status"] == "ATIVO"
    assert ciclo["data_povoamento"] == POVOAMENTO
    assert (ciclo["quantidade_pos_larvas"], ciclo["custo_aquisicao_pl"]) == (300_000, 3_000.0)
    assert (ciclo["peso_medio_pl_g"], ciclo["laboratorio_origem"]) == (0.002, "Lab X")
    assert ciclo["densidade_inicial"] == 30.0

    custos = client.get(f"{BASE}/{ciclo['id']}/custos/", headers=gestor).json()
    [custo_pl] = [c for c in custos if c["categoria"] == "POS_LARVAS"]
    assert (custo_pl["valor_rs"], custo_pl["data_lancamento"]) == (3_000.0, POVOAMENTO)
    assert "POVOAR_CICLO" in _acoes(client, gestor, ciclo["id"])
    assert client.get(f"{BASE}/{ciclo['id']}/metricas-atuais", headers=gestor).status_code == 200


@pytest.mark.parametrize("campo, valor", [
    ("quantidade_pos_larvas", 0), ("custo_aquisicao_pl", -1), ("peso_medio_pl_g", 5.1),
    ("laboratorio_origem", "x" * 121), ("quantidade_pos_larvas", 2_147_483_648),
])
def test_povoar_valida_limites(client, gestor, planejado, campo, valor):
    _resolver_etapas(client, gestor, planejado["id"])
    assert _povoar(client, gestor, planejado["id"], **{campo: valor}).status_code == 422


def test_povoar_exige_ciclo_planejado(client, gestor, ativo):
    assert _povoar(client, gestor, ativo["id"]).status_code == 400


def test_reagendar_muda_data_e_tabela_so_em_ciclo_planejado(client, gestor, planejado):
    insumo = _criar_insumo(client, gestor)
    assert _usar(client, gestor, planejado["id"], insumo["id"]).status_code == 201
    tabela = client.get("/api/v1/tabelas-alimentares/", headers=gestor).json()[0]
    nova_data = (date.today() + timedelta(days=60)).isoformat()

    r = client.patch(f"{BASE}/{planejado['id']}/planejamento",
                     json={"data_povoamento": nova_data, "tabela_alimentar_id": tabela["id"]}, headers=gestor)
    assert r.status_code == 200, r.text
    assert (r.json()["data_povoamento"], r.json()["tabela_alimentar_id"]) == (nova_data, tabela["id"])
    assert r.json()["viveiro_id"] == planejado["viveiro_id"]
    assert len(_etapas(client, gestor, planejado["id"])) == 5
    assert len(client.get(f"{BASE}/{planejado['id']}/usos-insumo", headers=gestor).json()) == 1
    assert "REAGENDAR_CICLO" in _acoes(client, gestor, planejado["id"])

    inexistente = {"tabela_alimentar_id": "00000000-0000-0000-0000-000000000000"}
    assert client.patch(f"{BASE}/{planejado['id']}/planejamento", json=inexistente,
                        headers=gestor).status_code == 404
    assert client.patch(f"{BASE}/{planejado['id']}/planejamento", json={"data_povoamento": None},
                        headers=gestor).status_code == 422

    _resolver_etapas(client, gestor, planejado["id"])
    assert _povoar(client, gestor, planejado["id"]).status_code == 200
    assert client.patch(f"{BASE}/{planejado['id']}/planejamento", json={"data_povoamento": nova_data},
                        headers=gestor).status_code == 400


def test_reagendar_muda_viveiro(client, gestor, planejado, novo_viveiro):
    livre = novo_viveiro()
    r = client.patch(f"{BASE}/{planejado['id']}/planejamento", json={"viveiro_id": livre["id"]}, headers=gestor)
    assert r.status_code == 200, r.text
    assert r.json()["viveiro_id"] == livre["id"]
    # o viveiro de origem fica livre
    assert _planejar(client, gestor, planejado["viveiro_id"]).status_code == 201


def test_reagendar_para_viveiro_ocupado_da_409(client, gestor, planejado, novo_viveiro):
    ocupado = novo_viveiro()
    assert _planejar(client, gestor, ocupado["id"]).status_code == 201
    r = client.patch(f"{BASE}/{planejado['id']}/planejamento", json={"viveiro_id": ocupado["id"]}, headers=gestor)
    assert r.status_code == 409


def test_reagendar_com_campo_desconhecido_da_422(client, gestor, planejado):
    r = client.patch(f"{BASE}/{planejado['id']}/planejamento", json={"quantidade_pos_larvas": 1}, headers=gestor)
    assert r.status_code == 422


def test_campo_nao_reagenda(client, campo, planejado):
    r = client.patch(f"{BASE}/{planejado['id']}/planejamento", json={"data_povoamento": PREVISTA}, headers=campo)
    assert r.status_code == 403


def test_cancelar_so_ciclo_planejado_e_libera_o_viveiro(client, gestor, planejado):
    r = client.post(f"{BASE}/{planejado['id']}/cancelar", headers=gestor)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "CANCELADO"
    assert "CANCELAR_CICLO" in _acoes(client, gestor, planejado["id"])
    assert client.post(f"{BASE}/{planejado['id']}/cancelar", headers=gestor).status_code == 400
    assert _povoar(client, gestor, planejado["id"]).status_code == 400

    # o viveiro fica livre para um novo planejamento; ciclo ativo não se cancela
    r = _planejar(client, gestor, planejado["viveiro_id"])
    assert r.status_code == 201, r.text
    novo = r.json()
    _resolver_etapas(client, gestor, novo["id"])
    assert _povoar(client, gestor, novo["id"]).status_code == 200
    assert client.post(f"{BASE}/{novo['id']}/cancelar", headers=gestor).status_code == 400


def test_gestor_cria_edita_e_exclui_etapa(client, gestor, planejado):
    url = f"{BASE}/{planejado['id']}/etapas-preparo"
    r = client.post(url, json={"tipo": "OUTRA", "observacao": "Limpeza das comportas"}, headers=gestor)
    assert r.status_code == 201, r.text
    etapa = r.json()
    assert (etapa["status"], etapa["ordem"]) == ("PENDENTE", 6)

    futura = (date.today() + timedelta(days=5)).isoformat()
    r = _atualizar_etapa(client, gestor, planejado["id"], etapa["id"], data_inicio=HOJE, data_fim=futura)
    assert r.status_code == 200, r.text
    assert (r.json()["data_inicio"], r.json()["data_fim"]) == (HOJE, futura)
    assert _atualizar_etapa(client, gestor, planejado["id"], etapa["id"], data_fim=HOJE,
                            data_inicio=futura).status_code == 422

    assert client.post(url, json={"tipo": "INVALIDA"}, headers=gestor).status_code == 422
    assert client.post(url, json={"tipo": "OUTRA", "observacao": "x" * 256}, headers=gestor).status_code == 422
    assert _atualizar_etapa(client, gestor, planejado["id"], etapa["id"], status="FEITA").status_code == 422

    assert client.delete(f"{url}/{etapa['id']}", headers=gestor).status_code == 204
    assert etapa["id"] not in [e["id"] for e in _etapas(client, gestor, planejado["id"])]
    assert client.delete(f"{url}/{etapa['id']}", headers=gestor).status_code == 404


def test_campo_atualiza_etapa_mas_nao_cria_nem_planeja(client, gestor, campo, vigia, planejado):
    url = f"{BASE}/{planejado['id']}/etapas-preparo"
    etapa = _etapas(client, campo, planejado["id"])[0]
    r = _atualizar_etapa(client, campo, planejado["id"], etapa["id"], status="EM_ANDAMENTO", data_inicio=HOJE,
                         observacao="Começou hoje")
    assert r.status_code == 200, r.text
    assert (r.json()["status"], r.json()["observacao"]) == ("EM_ANDAMENTO", "Começou hoje")

    assert client.post(url, json={"tipo": "OUTRA"}, headers=campo).status_code == 403
    assert client.delete(f"{url}/{etapa['id']}", headers=campo).status_code == 403
    assert _atualizar_etapa(client, campo, planejado["id"], etapa["id"], tipo="OUTRA").status_code == 422

    assert client.get(url, headers=vigia).status_code == 403
    assert _atualizar_etapa(client, vigia, planejado["id"], etapa["id"], status="CONCLUIDA").status_code == 403


def test_campo_nao_planeja_nem_povoa(client, campo, planejado, novo_viveiro):
    assert _planejar(client, campo, novo_viveiro()["id"]).status_code == 403
    assert _povoar(client, campo, planejado["id"]).status_code == 403
    assert client.post(f"{BASE}/{planejado['id']}/cancelar", headers=campo).status_code == 403


def test_uso_de_insumo_em_ciclo_planejado_so_na_fase_preparo(client, gestor, campo, planejado):
    insumo = _criar_insumo(client, gestor)
    assert _usar(client, gestor, planejado["id"], insumo["id"], fase="CULTIVO").status_code == 422
    assert _usar(client, campo, planejado["id"], insumo["id"]).status_code == 201


def test_uso_pode_ligar_a_etapa(client, gestor, planejado, novo_viveiro):
    insumo = _criar_insumo(client, gestor)
    calagem = _etapas(client, gestor, planejado["id"])[1]
    r = _usar(client, gestor, planejado["id"], insumo["id"], etapa_id=calagem["id"])
    assert r.status_code == 201, r.text
    uso = r.json()
    assert uso["etapa_id"] == calagem["id"]

    outro = _planejar(client, gestor, novo_viveiro()["id"]).json()
    etapa_alheia = _etapas(client, gestor, outro["id"])[0]
    assert _usar(client, gestor, planejado["id"], insumo["id"], etapa_id=etapa_alheia["id"]).status_code == 404

    # excluir a etapa mantém o uso, sem a ligação
    assert client.delete(f"{BASE}/{planejado['id']}/etapas-preparo/{calagem['id']}", headers=gestor).status_code == 204
    usos = client.get(f"{BASE}/{planejado['id']}/usos-insumo", headers=gestor).json()
    assert [(u["id"], u["etapa_id"]) for u in usos] == [(uso["id"], None)]


def test_venda_em_ciclo_planejado_da_400(client, gestor, planejado):
    corpo = {"data_venda": HOJE, "tipo": "DESBASTE", "biomassa_kg": 100, "peso_medio_g": 20, "preco_kg": 20}
    assert client.post(f"{BASE}/{planejado['id']}/vendas", json=corpo, headers=gestor).status_code == 400


def test_metricas_de_ciclo_planejado_da_409(client, gestor, campo, planejado):
    r = client.get(f"{BASE}/{planejado['id']}/metricas-atuais", headers=gestor)
    assert r.status_code == 409
    assert "Ciclo ainda em preparo" in r.json()["detail"]
    r = client.get(f"{BASE}/{planejado['id']}/manejos-alimentares/recomendacao", headers=campo)
    assert r.status_code == 409


def test_ciclo_ou_etapa_de_outra_organizacao_da_404(client, gestor, gestor_outra_org, planejado):
    base = f"{BASE}/{planejado['id']}"
    etapa = _etapas(client, gestor, planejado["id"])[0]
    go = gestor_outra_org
    assert client.get(f"{base}/etapas-preparo", headers=go).status_code == 404
    assert client.post(f"{base}/etapas-preparo", json={"tipo": "OUTRA"}, headers=go).status_code == 404
    assert _atualizar_etapa(client, go, planejado["id"], etapa["id"], status="CONCLUIDA").status_code == 404
    assert client.delete(f"{base}/etapas-preparo/{etapa['id']}", headers=go).status_code == 404
    assert _povoar(client, go, planejado["id"]).status_code == 404
    assert client.patch(f"{base}/planejamento", json={"data_povoamento": PREVISTA}, headers=go).status_code == 404
    assert client.post(f"{base}/cancelar", headers=go).status_code == 404
    assert _planejar(client, go, planejado["viveiro_id"]).status_code == 404

    # o viveiro de outra organização também não serve de destino do reagendamento
    viveiro_alheio = client.post("/api/v1/viveiros/", json={"identificacao": unico("VIV"), "area_util_m2": 100},
                                 headers=go).json()
    r = client.patch(f"{base}/planejamento", json={"viveiro_id": viveiro_alheio["id"]}, headers=gestor)
    assert r.status_code == 404


def test_etapa_de_outro_ciclo_da_404(client, gestor, planejado, novo_viveiro):
    outro = _planejar(client, gestor, novo_viveiro()["id"]).json()
    etapa_alheia = _etapas(client, gestor, outro["id"])[0]
    assert _atualizar_etapa(client, gestor, planejado["id"], etapa_alheia["id"], status="CONCLUIDA").status_code == 404
    assert client.delete(f"{BASE}/{planejado['id']}/etapas-preparo/{etapa_alheia['id']}",
                         headers=gestor).status_code == 404


def test_data_de_preparo_anterior_ao_povoamento_em_ciclo_existente_com_retroativo(client, gestor, ativo):
    insumo = _criar_insumo(client, gestor)
    assert _usar(client, gestor, ativo["id"], insumo["id"], data_uso=ANTES_DO_POVOAMENTO).status_code == 422
    assert _usar(client, gestor, ativo["id"], insumo["id"], data_uso=ANTES_DO_POVOAMENTO, fase="CULTIVO",
                 retroativo=True).status_code == 422
    r = _usar(client, gestor, ativo["id"], insumo["id"], data_uso=ANTES_DO_POVOAMENTO, retroativo=True)
    assert r.status_code == 201, r.text
    # o ciclo existente também recebe as etapas do preparo depois
    r = client.post(f"{BASE}/{ativo['id']}/etapas-preparo",
                    json={"tipo": "CALAGEM", "status": "CONCLUIDA", "data_inicio": ANTES_DO_POVOAMENTO}, headers=gestor)
    assert r.status_code == 201, r.text
