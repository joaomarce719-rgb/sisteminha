"""Vendas do ciclo (desbaste e despesca final): cálculo, regras de data e status, permissões e efeito na população."""

from datetime import date, timedelta
from uuid import UUID

import pytest

from tests.conftest import unico

HOJE = date.today().isoformat()
ONTEM = (date.today() - timedelta(days=1)).isoformat()
AMANHA = (date.today() + timedelta(days=1)).isoformat()


def _vender(client, headers, ciclo_id, **extra):
    corpo = {"data_venda": HOJE, "tipo": "DESBASTE", "biomassa_kg": 200, "peso_medio_g": 20, "preco_kg": 20, **extra}
    return client.post(f"/api/v1/ciclos/{ciclo_id}/vendas", json=corpo, headers=headers)


def _criar(client, gestor, ciclo_id, **extra):
    r = _vender(client, gestor, ciclo_id, **extra)
    assert r.status_code == 201, r.text
    return r.json()


def _ciclo_da_api(client, gestor, ciclo_id):
    return client.get(f"/api/v1/ciclos/{ciclo_id}", headers=gestor).json()


def _mudar_status(ciclo_id, status):
    from src.database import SessionLocal
    from src.models.ciclo_produtivo import CicloProdutivo
    from src.models.enums import StatusCiclo

    with SessionLocal() as db:
        db.get(CicloProdutivo, UUID(ciclo_id)).status = StatusCiclo(status)
        db.commit()


def _auditoria(client, headers, registro_id):
    r = client.get("/api/v1/auditoria/", params={"limite": 200, "entidade": "VendaCiclo"}, headers=headers)
    assert r.status_code == 200
    return {log["acao"]: log for log in r.json()["items"] if log["registro_id"] == registro_id}


@pytest.fixture
def ciclo(novo_ciclo):
    return novo_ciclo()


@pytest.fixture(scope="module")
def gestor_outra_org(client, admin, login):
    org = client.post("/api/v1/organizacoes/", json={"nome": "Fazenda Vendas", "identificador": unico("VEN")},
                      headers=admin)
    assert org.status_code == 201, org.text
    email = f"{unico('gestorven')}@x.com"
    r = client.post("/api/v1/admin/gestores", json={"nome_completo": "Gestor Vendas", "email": email,
                                                    "senha": "abc12345", "organizacao_id": org.json()["id"]},
                    headers=admin)
    assert r.status_code == 201, r.text
    return login(email, "abc12345")


# ── Cálculo e preço ──

def test_desbaste_calcula_animais_e_valor(client, gestor, ciclo):
    venda = _criar(client, gestor, ciclo["id"], comprador="Peixaria Mar")
    assert venda["animais_estimados"] == 10_000  # 200 kg ÷ 20 g
    assert venda["valor_total_rs"] == 4_000.0  # 200 kg × R$ 20
    assert venda["tipo"] == "DESBASTE" and venda["preco_kg"] == 20.0 and venda["retroativo"] is False
    assert venda["comprador"] == "Peixaria Mar"

    lista = client.get(f"/api/v1/ciclos/{ciclo['id']}/vendas", headers=gestor).json()
    assert [v["id"] for v in lista] == [venda["id"]]


def test_varias_despescas_finais_e_desbastes_no_mesmo_ciclo(client, gestor, ciclo):
    ids = {_criar(client, gestor, ciclo["id"], tipo=t)["id"]
           for t in ("DESBASTE", "DESBASTE", "DESPESCA_FINAL", "DESPESCA_FINAL")}
    assert len(ids) == 4
    assert len(client.get(f"/api/v1/ciclos/{ciclo['id']}/vendas", headers=gestor).json()) == 4


def test_preco_omitido_usa_a_tabela_de_precos(client, gestor, ciclo):
    corpo = {"data_venda": HOJE, "tipo": "DESBASTE", "biomassa_kg": 100, "peso_medio_g": 10.5}
    r = client.post(f"/api/v1/ciclos/{ciclo['id']}/vendas", json=corpo, headers=gestor)
    assert r.status_code == 201, r.text
    # 10,5 g arredonda para 10 g (regra da organização), faixa de 10 a 12 g: R$ 21,00/kg
    assert r.json()["preco_kg"] == 21.0 and r.json()["valor_total_rs"] == 2_100.0

    sugerido = client.get(f"/api/v1/ciclos/{ciclo['id']}/vendas/preco-sugerido", params={"peso_medio_g": 10.5},
                          headers=gestor)
    assert sugerido.status_code == 200 and sugerido.json() == {"preco_kg": 21.0}


def test_sem_preco_na_tabela_e_sem_preco_da_422(client, gestor, ciclo):
    corpo = {"data_venda": HOJE, "tipo": "DESBASTE", "biomassa_kg": 100, "peso_medio_g": 4}
    r = client.post(f"/api/v1/ciclos/{ciclo['id']}/vendas", json=corpo, headers=gestor)
    assert r.status_code == 422 and "preço" in r.json()["detail"]
    sugerido = client.get(f"/api/v1/ciclos/{ciclo['id']}/vendas/preco-sugerido", params={"peso_medio_g": 4},
                          headers=gestor)
    assert sugerido.status_code == 200 and sugerido.json() == {"preco_kg": None}
    # informando o preço, a venda é aceita mesmo sem faixa na tabela
    assert _vender(client, gestor, ciclo["id"], peso_medio_g=4, preco_kg=15).status_code == 201


def test_preco_zero_e_aceito_e_nao_cai_na_tabela(client, gestor, ciclo):
    venda = _criar(client, gestor, ciclo["id"], preco_kg=0)
    assert venda["preco_kg"] == 0 and venda["valor_total_rs"] == 0


# ── Datas ──

def test_data_passada_exige_retroativo(client, gestor, ciclo):
    r = _vender(client, gestor, ciclo["id"], data_venda=ONTEM)
    assert r.status_code == 422 and "retroativo" in r.json()["detail"]

    venda = _vender(client, gestor, ciclo["id"], data_venda=ONTEM, retroativo=True)
    assert venda.status_code == 201, venda.text
    assert venda.json()["retroativo"] is True and venda.json()["data_venda"] == ONTEM


def test_data_futura_e_anterior_ao_povoamento_sao_recusadas(client, gestor, ciclo):
    assert _vender(client, gestor, ciclo["id"], data_venda=AMANHA, retroativo=True).status_code == 422
    antes = _vender(client, gestor, ciclo["id"], data_venda="2026-07-31", retroativo=True)
    assert antes.status_code == 422 and "povoamento" in antes.json()["detail"]


# ── Status do ciclo ──

def test_desbaste_em_ciclo_finalizado_da_400(client, gestor, ciclo):
    _mudar_status(ciclo["id"], "FINALIZADO")
    r = _vender(client, gestor, ciclo["id"], tipo="DESBASTE")
    assert r.status_code == 400
    # a despesca final ainda pode ser lançada para corrigir o ciclo encerrado
    assert _vender(client, gestor, ciclo["id"], tipo="DESPESCA_FINAL").status_code == 201


@pytest.mark.parametrize("status", ["PLANEJADO", "CANCELADO"])
@pytest.mark.parametrize("tipo", ["DESBASTE", "DESPESCA_FINAL"])
def test_ciclo_planejado_ou_cancelado_recusa_vendas(client, gestor, ciclo, status, tipo):
    _mudar_status(ciclo["id"], status)
    assert _vender(client, gestor, ciclo["id"], tipo=tipo).status_code == 400


def test_ciclo_pausado_aceita_vendas(client, gestor, ciclo):
    _mudar_status(ciclo["id"], "PAUSADO")
    assert _vender(client, gestor, ciclo["id"], tipo="DESBASTE").status_code == 201
    assert _vender(client, gestor, ciclo["id"], tipo="DESPESCA_FINAL").status_code == 201


def test_corrigir_e_excluir_venda_em_ciclo_finalizado(client, gestor, ciclo):
    desbaste = _criar(client, gestor, ciclo["id"], tipo="DESBASTE")
    final = _criar(client, gestor, ciclo["id"], tipo="DESPESCA_FINAL")
    _mudar_status(ciclo["id"], "FINALIZADO")
    base = f"/api/v1/ciclos/{ciclo['id']}/vendas"
    corpo = {"data_venda": HOJE, "biomassa_kg": 100, "peso_medio_g": 20, "preco_kg": 20}

    assert client.put(f"{base}/{desbaste['id']}", json={**corpo, "tipo": "DESBASTE"}, headers=gestor).status_code == 200
    assert client.put(f"{base}/{final['id']}", json={**corpo, "tipo": "DESBASTE"}, headers=gestor).status_code == 400
    assert client.put(f"{base}/{desbaste['id']}", json={**corpo, "tipo": "DESPESCA_FINAL"},
                      headers=gestor).status_code == 200
    assert client.delete(f"{base}/{final['id']}", headers=gestor).status_code == 204


# ── Totais do ciclo finalizado ──

def test_totais_do_ciclo_so_seguem_as_vendas_quando_finalizado(client, gestor, ciclo):
    _criar(client, gestor, ciclo["id"], tipo="DESPESCA_FINAL")
    ativo = _ciclo_da_api(client, gestor, ciclo["id"])
    assert ativo["biomassa_colhida_kg"] is None and ativo["receita_real_rs"] is None


def test_excluir_venda_de_ciclo_finalizado_ressincroniza_totais(client, gestor, ciclo):
    primeira = _criar(client, gestor, ciclo["id"], tipo="DESPESCA_FINAL", biomassa_kg=300, preco_kg=20)
    _mudar_status(ciclo["id"], "FINALIZADO")
    base = f"/api/v1/ciclos/{ciclo['id']}/vendas"

    segunda = client.post(base, json={"data_venda": HOJE, "tipo": "DESPESCA_FINAL", "biomassa_kg": 100,
                                      "peso_medio_g": 20, "preco_kg": 30}, headers=gestor).json()
    total = _ciclo_da_api(client, gestor, ciclo["id"])
    assert total["biomassa_colhida_kg"] == 400 and total["receita_real_rs"] == 9_000.0  # 6.000 + 3.000

    assert client.delete(f"{base}/{primeira['id']}", headers=gestor).status_code == 204
    resto = _ciclo_da_api(client, gestor, ciclo["id"])
    assert resto["biomassa_colhida_kg"] == 100 and resto["receita_real_rs"] == 3_000.0

    corrigida = client.put(f"{base}/{segunda['id']}", json={"data_venda": HOJE, "tipo": "DESPESCA_FINAL",
                                                           "biomassa_kg": 150, "peso_medio_g": 20, "preco_kg": 30},
                           headers=gestor)
    assert corrigida.status_code == 200, corrigida.text
    final = _ciclo_da_api(client, gestor, ciclo["id"])
    assert final["biomassa_colhida_kg"] == 150 and final["receita_real_rs"] == 4_500.0


# ── Permissões e isolamento ──

def test_campo_nao_acessa_vendas(client, gestor, campo, vigia, ciclo):
    venda = _criar(client, gestor, ciclo["id"])
    base = f"/api/v1/ciclos/{ciclo['id']}/vendas"
    corpo = {"data_venda": HOJE, "tipo": "DESBASTE", "biomassa_kg": 200, "peso_medio_g": 20, "preco_kg": 20}
    for headers in (campo, vigia):
        assert client.get(base, headers=headers).status_code == 403
        assert client.post(base, json=corpo, headers=headers).status_code == 403
        assert client.put(f"{base}/{venda['id']}", json=corpo, headers=headers).status_code == 403
        assert client.delete(f"{base}/{venda['id']}", headers=headers).status_code == 403
        assert client.get(f"{base}/preco-sugerido", params={"peso_medio_g": 20}, headers=headers).status_code == 403


def test_venda_de_outra_organizacao_da_404(client, gestor, gestor_outra_org, ciclo):
    venda = _criar(client, gestor, ciclo["id"])
    base = f"/api/v1/ciclos/{ciclo['id']}/vendas"
    corpo = {"data_venda": HOJE, "tipo": "DESBASTE", "biomassa_kg": 200, "peso_medio_g": 20, "preco_kg": 20}
    assert client.get(base, headers=gestor_outra_org).status_code == 404
    assert client.post(base, json=corpo, headers=gestor_outra_org).status_code == 404
    assert client.put(f"{base}/{venda['id']}", json=corpo, headers=gestor_outra_org).status_code == 404
    assert client.delete(f"{base}/{venda['id']}", headers=gestor_outra_org).status_code == 404
    assert client.get(f"{base}/preco-sugerido", params={"peso_medio_g": 20}, headers=gestor_outra_org).status_code == 404
    assert len(client.get(base, headers=gestor).json()) == 1


def test_venda_de_outro_ciclo_da_404(client, gestor, novo_ciclo, ciclo):
    venda = _criar(client, gestor, ciclo["id"])
    outro = novo_ciclo()
    r = client.delete(f"/api/v1/ciclos/{outro['id']}/vendas/{venda['id']}", headers=gestor)
    assert r.status_code == 404
    assert len(client.get(f"/api/v1/ciclos/{ciclo['id']}/vendas", headers=gestor).json()) == 1


# ── Validação de entrada (limites das colunas: 422, nunca 500) ──

@pytest.mark.parametrize("campo, valor", [
    ("tipo", "OUTRO"),
    ("biomassa_kg", 0),
    ("biomassa_kg", 0.001),
    ("biomassa_kg", 10_000_000_000),
    ("peso_medio_g", 0),
    ("peso_medio_g", 0.001),
    ("peso_medio_g", 1_000_000),
    ("preco_kg", -1),
    ("preco_kg", 100_000_000),
    ("comprador", "C" * 121),
    ("observacao", "O" * 501),
])
def test_entrada_fora_dos_limites_da_coluna_da_422(client, gestor, ciclo, campo, valor):
    assert _vender(client, gestor, ciclo["id"], **{campo: valor}).status_code == 422


def test_total_ou_animais_acima_da_coluna_da_422(client, gestor, ciclo):
    # 9.999.999.999 kg × R$ 99.999.999/kg não cabe em Numeric(12,2)
    valor = _vender(client, gestor, ciclo["id"], biomassa_kg=9_999_999_999, preco_kg=99_999_999)
    assert valor.status_code == 422
    # 100.000 kg ÷ 0,01 g = 10 bilhões de animais, acima do Integer
    animais = _vender(client, gestor, ciclo["id"], biomassa_kg=100_000, peso_medio_g=0.01, preco_kg=1)
    assert animais.status_code == 422


# ── Edição, exclusão e auditoria ──

def test_corrigir_venda_recalcula_animais_e_valor(client, gestor, ciclo):
    venda = _criar(client, gestor, ciclo["id"])
    url = f"/api/v1/ciclos/{ciclo['id']}/vendas/{venda['id']}"
    r = client.put(url, json={"data_venda": HOJE, "tipo": "DESPESCA_FINAL", "biomassa_kg": 150, "peso_medio_g": 15,
                              "preco_kg": 28.5, "comprador": "Outro", "retroativo": False}, headers=gestor)
    assert r.status_code == 200, r.text
    corrigida = r.json()
    assert corrigida["animais_estimados"] == 10_000 and corrigida["valor_total_rs"] == 4_275.0
    assert corrigida["tipo"] == "DESPESCA_FINAL" and corrigida["comprador"] == "Outro"
    # a data passada na edição também exige a marca de retroativo
    passado = client.put(url, json={"data_venda": ONTEM, "tipo": "DESBASTE", "biomassa_kg": 150, "peso_medio_g": 15,
                                    "preco_kg": 28.5}, headers=gestor)
    assert passado.status_code == 422
    assert client.put(f"/api/v1/ciclos/{ciclo['id']}/vendas/{ciclo['id']}", json={
        "data_venda": HOJE, "tipo": "DESBASTE", "biomassa_kg": 1, "peso_medio_g": 1, "preco_kg": 1}, headers=gestor
    ).status_code == 404


def test_excluir_venda_devolve_a_populacao(client, gestor, ciclo):
    url = f"/api/v1/ciclos/{ciclo['id']}"
    antes = client.get(f"{url}/metricas-atuais", headers=gestor).json()["populacao_estimada"]
    venda = _criar(client, gestor, ciclo["id"])
    assert client.get(f"{url}/metricas-atuais", headers=gestor).json()["populacao_estimada"] == antes - 10_000
    assert client.delete(f"{url}/vendas/{venda['id']}", headers=gestor).status_code == 204
    assert client.get(f"{url}/metricas-atuais", headers=gestor).json()["populacao_estimada"] == antes
    assert client.get(f"{url}/vendas", headers=gestor).json() == []


def test_excluir_ciclo_leva_as_vendas(client, gestor, ciclo):
    _criar(client, gestor, ciclo["id"])
    assert client.delete(f"/api/v1/ciclos/{ciclo['id']}", headers=gestor).status_code == 200
    assert client.get(f"/api/v1/ciclos/{ciclo['id']}/vendas", headers=gestor).status_code == 404


def test_vendas_ficam_na_auditoria(client, gestor, ciclo):
    venda = _criar(client, gestor, ciclo["id"], biomassa_kg=200)
    url = f"/api/v1/ciclos/{ciclo['id']}/vendas/{venda['id']}"
    client.put(url, json={"data_venda": HOJE, "tipo": "DESBASTE", "biomassa_kg": 120, "peso_medio_g": 20,
                          "preco_kg": 20}, headers=gestor)
    client.delete(url, headers=gestor)

    logs = _auditoria(client, gestor, venda["id"])
    assert set(logs) == {"CRIAR_VENDA", "ATUALIZAR_VENDA", "EXCLUIR_VENDA"}
    assert logs["CRIAR_VENDA"]["dados_novos"]["biomassa_kg"] == 200
    assert logs["ATUALIZAR_VENDA"]["dados_anteriores"]["biomassa_kg"] == 200
    assert logs["ATUALIZAR_VENDA"]["dados_novos"]["biomassa_kg"] == 120
    assert logs["EXCLUIR_VENDA"]["dados_anteriores"]["biomassa_kg"] == 120


# ── Efeito nos cálculos do ciclo ──

def test_populacao_da_metrica_cai_depois_do_desbaste(client, gestor, ciclo):
    url = f"/api/v1/ciclos/{ciclo['id']}/metricas-atuais"
    antes = client.get(url, headers=gestor).json()
    assert antes["receita_realizada_rs"] == 0

    venda = _criar(client, gestor, ciclo["id"])  # 200 kg a 20 g = 10.000 animais, R$ 4.000
    depois = client.get(url, headers=gestor).json()

    assert depois["populacao_estimada"] == antes["populacao_estimada"] - venda["animais_estimados"]
    assert depois["densidade_atual"] < antes["densidade_atual"]
    assert depois["densidade_atual"] == pytest.approx(depois["populacao_estimada"] / 10_000, abs=0.01)
    assert depois["densidade_estocagem"] == antes["densidade_estocagem"]  # a de povoamento não muda
    assert depois["receita_realizada_rs"] == 4_000.0


def test_manejo_ronda_e_simulacao_leem_as_vendas(client, gestor, vigia, ciclo):
    url = f"/api/v1/ciclos/{ciclo['id']}"
    for dia, peso in (("2026-09-01", 9.0), ("2026-09-15", 11.0)):
        r = client.post(f"{url}/biometrias/", json={"data_medicao": dia, "quantidade_amostrada": 50,
                                                    "peso_medio_g": peso}, headers=gestor)
        assert r.status_code == 201, r.text
    def simular():
        return client.post(f"{url}/simular-despesca/", json={"dias_horizonte": 7, "custo_diario_rs": 100},
                           headers=gestor)

    antes = simular()
    assert antes.status_code == 200, antes.text

    _criar(client, gestor, ciclo["id"], data_venda="2026-09-20", retroativo=True)
    manejo = client.post(f"{url}/manejos-alimentares/", json={"data_registro": "2026-09-25", "quantidade_racao_kg": 100,
                                                              "sobra_bandeja_nivel": "SEM_SOBRA"}, headers=gestor)
    assert manejo.status_code == 201, manejo.text
    ronda = client.post("/api/v1/rondas-noturnas/", json={
        "ciclo_id": ciclo["id"], "data_hora_ronda": "2026-10-20T02:00:00", "oxigenio_dissolvido_mg_l": 5.0,
        "temperatura_agua_c": 28, "aeradores_instalados": 4, "aeradores_ligados": 4}, headers=vigia)
    assert ronda.status_code == 201, ronda.text

    depois = simular()
    assert depois.status_code == 200, depois.text
    assert depois.json()["biomassa_atual_kg"] < antes.json()["biomassa_atual_kg"]
