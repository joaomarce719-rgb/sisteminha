"""Financeiro do ciclo e histórico do viveiro (seção 5.6 do design): valores conferidos à mão."""

from datetime import date

import pytest

from tests.conftest import unico

HOJE = date.today().isoformat()


def _ok(r, codigo=201):
    assert r.status_code == codigo, r.text
    return r.json()


def _biometria(client, gestor, ciclo_id, peso, data="2026-09-01"):
    _ok(client.post(f"/api/v1/ciclos/{ciclo_id}/biometrias/",
                    json={"data_medicao": data, "quantidade_amostrada": 50, "peso_medio_g": peso}, headers=gestor))


def _manejo(client, gestor, ciclo_id, data, kg):
    _ok(client.post(f"/api/v1/ciclos/{ciclo_id}/manejos-alimentares/",
                    json={"data_registro": data, "quantidade_racao_kg": kg, "sobra_bandeja_nivel": "SEM_SOBRA"},
                    headers=gestor))


def _custo(client, gestor, ciclo_id, valor, categoria="RACAO", fase="CULTIVO"):
    _ok(client.post(f"/api/v1/ciclos/{ciclo_id}/custos/",
                    json={"data_lancamento": "2026-09-10", "categoria": categoria, "descricao": "Lançamento",
                          "valor_rs": valor, "fase": fase}, headers=gestor))


def _vender(client, gestor, ciclo_id, data, tipo, biomassa, peso, preco):
    return _ok(client.post(f"/api/v1/ciclos/{ciclo_id}/vendas",
                           json={"data_venda": data, "tipo": tipo, "biomassa_kg": biomassa, "peso_medio_g": peso,
                                 "preco_kg": preco, "retroativo": data != HOJE}, headers=gestor))


def _insumo(client, gestor):
    return _ok(client.post("/api/v1/insumos/", json={"nome": unico("Probiotico"), "unidade_uso": "kg",
                                                     "categoria": "PROBIOTICOS_QUIMICOS"}, headers=gestor))


def _usar(client, headers, ciclo_id, insumo_id, quantidade):
    return _ok(client.post(f"/api/v1/ciclos/{ciclo_id}/usos-insumo",
                           json={"insumo_id": insumo_id, "data_uso": HOJE, "quantidade": quantidade,
                                 "fase": "CULTIVO"}, headers=headers))


def _financeiro(client, headers, ciclo_id):
    return _ok(client.get(f"/api/v1/ciclos/{ciclo_id}/financeiro", headers=headers), 200)


def _historico(client, headers, viveiro_id):
    return _ok(client.get(f"/api/v1/viveiros/{viveiro_id}/historico", headers=headers), 200)


@pytest.fixture
def ciclo_finalizado(client, gestor, novo_ciclo):
    """300.000 PLs (R$ 3.000), ração 1.000 kg (R$ 4.970), 10 kg de probiótico a R$ 3/kg (R$ 30).

    Vendas: desbastes de 200 kg (20 g, R$ 20) e 300 kg (20 g, R$ 22) e despesca final de 1.500 kg (25 g, R$ 30).
    """
    ciclo = novo_ciclo()
    _biometria(client, gestor, ciclo["id"], 20)
    _manejo(client, gestor, ciclo["id"], "2026-09-02", 1_000)
    _custo(client, gestor, ciclo["id"], 4_970)
    insumo = _insumo(client, gestor)
    _ok(client.post(f"/api/v1/insumos/{insumo['id']}/compras",
                    json={"data_compra": HOJE, "quantidade": 100, "valor_total_rs": 300}, headers=gestor))
    _usar(client, gestor, ciclo["id"], insumo["id"], 10)
    _vender(client, gestor, ciclo["id"], "2026-09-10", "DESBASTE", 200, 20, 20)
    _vender(client, gestor, ciclo["id"], "2026-09-20", "DESBASTE", 300, 20, 22)
    _vender(client, gestor, ciclo["id"], "2026-10-10", "DESPESCA_FINAL", 1_500, 25, 30)
    _ok(client.post(f"/api/v1/ciclos/{ciclo['id']}/encerrar", json={}, headers=gestor), 200)
    return {**ciclo, "insumo": insumo}


def test_financeiro_do_ciclo_finalizado(client, gestor, ciclo_finalizado):
    f = _financeiro(client, gestor, ciclo_finalizado["id"])
    assert f["receita_realizada_rs"] == 55_600.0  # 4.000 + 6.600 + 45.000
    assert f["custo_total_rs"] == 8_000.0  # 3.000 + 4.970 + 30
    assert f["lucro_realizado_rs"] == 47_600.0
    assert f["margem_realizada_pct"] == pytest.approx(47_600 / 55_600 * 100, abs=0.01)
    assert f["custo_por_kg_rs"] == 4.0  # 8.000 ÷ 2.000 kg vendidos
    assert f["definitivo"] is True
    assert f["lucro_estimado_se_despescar_hoje_rs"] is None
    assert f["usos_pendentes"] == 0 and f["valores_recalculados_em"] is None
    assert len(f["vendas"]) == 3
    assert f["custos_por_fase"] == {"CULTIVO": 8_000.0}
    assert f["custos_por_categoria"] == {"POS_LARVAS": 3_000.0, "RACAO": 4_970.0, "PROBIOTICOS_QUIMICOS": 30.0}
    assert {(c["fase"], c["categoria"], c["total_rs"]) for c in f["custos_fase_categoria"]} == {
        ("CULTIVO", "POS_LARVAS", 3_000.0), ("CULTIVO", "RACAO", 4_970.0), ("CULTIVO", "PROBIOTICOS_QUIMICOS", 30.0)
    }


def test_financeiro_separa_custos_por_fase(client, gestor, novo_ciclo):
    ciclo = novo_ciclo()
    _custo(client, gestor, ciclo["id"], 500, categoria="MAO_DE_OBRA", fase="PREPARO")
    f = _financeiro(client, gestor, ciclo["id"])
    assert f["custos_por_fase"] == {"CULTIVO": 3_000.0, "PREPARO": 500.0}
    assert f["receita_realizada_rs"] == 0.0 and f["lucro_realizado_rs"] == -3_500.0
    assert f["margem_realizada_pct"] is None and f["custo_por_kg_rs"] is None  # sem vendas


def test_ciclo_ativo_lucro_estimado_soma_a_agua_ao_realizado(client, gestor, novo_ciclo):
    ciclo = novo_ciclo()
    _biometria(client, gestor, ciclo["id"], 15)  # sem manejos: sobrevivência 100%
    _vender(client, gestor, ciclo["id"], "2026-09-10", "DESBASTE", 200, 15, 20)  # 13.333 animais, R$ 4.000
    preco = next(float(p["preco_por_kg"]) for p in client.get("/api/v1/precos-mercado/", headers=gestor).json()
                 if p["faixa_gramatura_min"] <= 15 <= p["faixa_gramatura_max"])
    f = _financeiro(client, gestor, ciclo["id"])
    assert f["definitivo"] is False
    assert f["lucro_realizado_rs"] == 1_000.0  # 4.000 − 3.000 das PLs
    biomassa = (300_000 - 13_333) * 15 / 1000
    assert f["lucro_estimado_se_despescar_hoje_rs"] == pytest.approx(1_000 + biomassa * preco, abs=0.01)
    metricas = client.get(f"/api/v1/ciclos/{ciclo['id']}/metricas-atuais", headers=gestor).json()
    assert f["lucro_estimado_se_despescar_hoje_rs"] == metricas["lucro_operacional_rs"]


def test_ciclo_ativo_sem_biometria_nao_estima_lucro(client, gestor, novo_ciclo):
    f = _financeiro(client, gestor, novo_ciclo()["id"])
    assert f["lucro_estimado_se_despescar_hoje_rs"] is None


def test_usos_pendentes_contados(client, gestor, novo_ciclo):
    ciclo = novo_ciclo()
    insumo = _insumo(client, gestor)  # sem compra: o uso fica pendente de valor
    _usar(client, gestor, ciclo["id"], insumo["id"], 5)
    _usar(client, gestor, ciclo["id"], insumo["id"], 2)
    f = _financeiro(client, gestor, ciclo["id"])
    assert f["usos_pendentes"] == 2
    assert f["custo_total_rs"] == 3_000.0


def test_historico_traz_sobrevivencia_e_peso_final(client, gestor, ciclo_finalizado):
    [item] = _historico(client, gestor, ciclo_finalizado["viveiro_id"])
    assert item["status"] == "FINALIZADO" and item["data_despesca_real"] == "2026-10-10"
    assert item["quantidade_pos_larvas"] == 300_000
    # 10.000 + 15.000 + 60.000 animais vendidos ÷ 300.000 PLs
    assert item["sobrevivencia_final_pct"] == pytest.approx(85_000 / 300_000 * 100, abs=0.01)
    assert item["peso_final_g"] == 25.0
    assert item["fca"] == 0.5  # 1.000 kg ÷ (2.000 kg vendidos − 0 inicial)
    assert item["vendas"] == {"quantidade": 3, "biomassa_total_kg": 2_000.0, "receita_rs": 55_600.0}
    assert item["racao_total_kg"] == 1_000.0 and item["racao_custo_rs"] == 4_970.0
    assert item["custo_total_rs"] == 8_000.0 and item["lucro_realizado_rs"] == 47_600.0
    assert item["custo_por_kg_rs"] == 4.0
    assert item["margem_pct"] == pytest.approx(47_600 / 55_600 * 100, abs=0.01)
    [insumo] = item["insumos"]
    assert insumo["insumo_id"] == ciclo_finalizado["insumo"]["id"]
    assert (insumo["unidade_uso"], insumo["quantidade_total"], insumo["custo_total_rs"]) == ("kg", 10.0, 30.0)
    assert len(item["etapas"]) > 0 and {e["status"] for e in item["etapas"]} == {"NAO_REALIZADA"}


def test_peso_final_ponderado_pela_biomassa_das_despescas(client, gestor, novo_ciclo):
    ciclo = novo_ciclo()
    _biometria(client, gestor, ciclo["id"], 25)
    _vender(client, gestor, ciclo["id"], "2026-09-10", "DESBASTE", 100, 10, 20)  # desbaste não pesa no peso final
    _vender(client, gestor, ciclo["id"], "2026-10-01", "DESPESCA_FINAL", 1_000, 25, 30)
    _vender(client, gestor, ciclo["id"], "2026-10-02", "DESPESCA_FINAL", 500, 28, 30)
    _ok(client.post(f"/api/v1/ciclos/{ciclo['id']}/encerrar", json={}, headers=gestor), 200)
    [item] = _historico(client, gestor, ciclo["viveiro_id"])
    assert item["peso_final_g"] == 26.0  # (1.000 × 25 + 500 × 28) ÷ 1.500


def test_campo_ve_historico_sem_valores_em_reais(client, gestor, campo, vigia, ciclo_finalizado):
    assert client.get(f"/api/v1/ciclos/{ciclo_finalizado['id']}/financeiro", headers=campo).status_code == 403
    assert client.get(f"/api/v1/ciclos/{ciclo_finalizado['id']}/financeiro", headers=vigia).status_code == 403
    for headers in (campo, vigia):
        [item] = _historico(client, headers, ciclo_finalizado["viveiro_id"])
        for campo_rs in ("racao_custo_rs", "custo_total_rs", "lucro_realizado_rs", "margem_pct", "custo_por_kg_rs"):
            assert item[campo_rs] is None, campo_rs
        assert item["vendas"]["receita_rs"] is None
        assert all(i["custo_total_rs"] is None for i in item["insumos"])
        assert all(s["custo_rs"] is None for s in item["racao_por_semana"])
        # o que não é dinheiro continua visível
        assert item["racao_total_kg"] == 1_000.0 and item["vendas"]["biomassa_total_kg"] == 2_000.0
        assert item["insumos"][0]["quantidade_total"] == 10.0
        assert item["peso_final_g"] == 25.0 and item["fca"] == 0.5 and item["sobrevivencia_final_pct"] is not None


@pytest.fixture(scope="module")
def gestor_outra_org(client, admin, login):
    org = client.post("/api/v1/organizacoes/", json={"nome": "Fazenda Histórico", "identificador": unico("HIS")},
                      headers=admin)
    assert org.status_code == 201, org.text
    email = f"{unico('gestorhis')}@x.com"
    r = client.post("/api/v1/admin/gestores", json={"nome_completo": "Gestor Histórico", "email": email,
                                                    "senha": "abc12345", "organizacao_id": org.json()["id"]},
                    headers=admin)
    assert r.status_code == 201, r.text
    return login(email, "abc12345")


def test_viveiro_de_outra_organizacao_da_404(client, gestor_outra_org, novo_ciclo):
    ciclo = novo_ciclo()
    assert client.get(f"/api/v1/viveiros/{ciclo['viveiro_id']}/historico", headers=gestor_outra_org).status_code == 404
    assert client.get(f"/api/v1/ciclos/{ciclo['id']}/financeiro", headers=gestor_outra_org).status_code == 404


def test_ciclo_planejado_aparece_no_historico(client, gestor, novo_viveiro):
    viveiro = novo_viveiro()
    cancelado = _ok(client.post("/api/v1/ciclos/", json={"viveiro_id": viveiro["id"], "data_povoamento": "2026-08-01"},
                                headers=gestor))
    _ok(client.post(f"/api/v1/ciclos/{cancelado['id']}/cancelar", headers=gestor), 200)
    planejado = _ok(client.post("/api/v1/ciclos/", json={"viveiro_id": viveiro["id"], "data_povoamento": "2026-12-01"},
                                headers=gestor))
    itens = _historico(client, gestor, viveiro["id"])
    assert [(i["ciclo_id"], i["status"]) for i in itens] == [
        (planejado["id"], "PLANEJADO"), (cancelado["id"], "CANCELADO")
    ]  # mais recente primeiro
    item = itens[0]
    assert item["quantidade_pos_larvas"] is None and item["racao_por_semana"] == []
    assert item["fca"] is None and item["sobrevivencia_final_pct"] is None and item["custo_por_kg_rs"] is None
    assert {e["status"] for e in item["etapas"]} == {"PENDENTE"}
    assert client.get(f"/api/v1/ciclos/{planejado['id']}/financeiro", headers=gestor).status_code == 200


def test_racao_por_semana_soma_os_manejos(client, gestor, novo_ciclo):
    ciclo = novo_ciclo(data_povoamento="2026-08-01")
    _manejo(client, gestor, ciclo["id"], "2026-08-02", 100)  # semana 1: 01/08 a 07/08
    _manejo(client, gestor, ciclo["id"], "2026-08-07", 50)
    _manejo(client, gestor, ciclo["id"], "2026-08-20", 150)  # semana 3: 15/08 a 21/08
    _custo(client, gestor, ciclo["id"], 600)  # R$ 600 ÷ 300 kg = R$ 2/kg
    [item] = _historico(client, gestor, ciclo["viveiro_id"])
    semanas = item["racao_por_semana"]
    assert [(s["inicio"], s["fim"], s["kg"], s["custo_rs"]) for s in semanas] == [
        ("2026-08-01", "2026-08-07", 150.0, 300.0),
        ("2026-08-08", "2026-08-14", 0.0, 0.0),
        ("2026-08-15", "2026-08-21", 150.0, 300.0),
    ]
    assert all(s["fca_parcial"] is None for s in semanas)  # sem biometria
    metricas = client.get(f"/api/v1/ciclos/{ciclo['id']}/metricas-atuais", headers=gestor).json()
    assert sum(s["kg"] for s in semanas) == metricas["racao_acumulada_kg"] == item["racao_total_kg"]


def test_fca_parcial_com_biometria(client, gestor, novo_ciclo):
    ciclo = novo_ciclo(data_povoamento="2026-08-01")
    _biometria(client, gestor, ciclo["id"], 2, data="2026-08-05")
    _manejo(client, gestor, ciclo["id"], "2026-08-06", 300)
    [item] = _historico(client, gestor, ciclo["viveiro_id"])
    [semana] = item["racao_por_semana"]
    # população × 2 g: a sobrevivência vem do manejo (fuzzy), lida no ponto em que fica gravada
    manejo = client.get(f"/api/v1/ciclos/{ciclo['id']}/manejos-alimentares/", headers=gestor).json()[0]
    biomassa = int(300_000 * manejo["taxa_sobrevivencia_estimada_fuzzy"] / 100) * 2 / 1000
    assert semana["fca_parcial"] == pytest.approx(300 / biomassa, abs=0.001)


def test_sem_racao_registrada_o_fca_fica_vazio(client, gestor, novo_ciclo):
    ciclo = novo_ciclo(data_povoamento="2026-08-01")
    _biometria(client, gestor, ciclo["id"], 5, data="2026-08-05")
    [item] = _historico(client, gestor, ciclo["viveiro_id"])
    assert item["racao_total_kg"] == 0 and item["fca"] is None and item["racao_por_semana"] == []


def test_semana_sem_racao_acumulada_nao_tem_fca_parcial(client, gestor, novo_ciclo):
    ciclo = novo_ciclo(data_povoamento="2026-08-01")
    _biometria(client, gestor, ciclo["id"], 2, data="2026-08-02")
    _manejo(client, gestor, ciclo["id"], "2026-08-10", 300)  # só na semana 2
    [item] = _historico(client, gestor, ciclo["viveiro_id"])
    primeira, segunda = item["racao_por_semana"]
    assert primeira["kg"] == 0 and primeira["fca_parcial"] is None
    assert segunda["fca_parcial"] is not None


def test_insumo_sem_nenhum_uso_com_valor_vem_sem_custo_no_historico(client, gestor, novo_ciclo):
    ciclo = novo_ciclo()
    insumo = _insumo(client, gestor)
    _usar(client, gestor, ciclo["id"], insumo["id"], 50)  # sem compra: uso pendente de valor, sem custo
    [item] = _historico(client, gestor, ciclo["viveiro_id"])
    [usado] = item["insumos"]
    assert usado["quantidade_total"] == 50
    assert usado["custo_total_rs"] is None  # R$ 0,00 pareceria insumo de graça
