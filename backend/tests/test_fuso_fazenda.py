"""'Hoje' nas regras de data é o dia da fazenda, não o do servidor (que pode rodar em UTC)."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.services import regras_ciclo, regras_data
from tests.conftest import unico

HOJE_FAZENDA = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
ONTEM_FAZENDA = HOJE_FAZENDA - timedelta(days=1)


class _DataDoServidorUtc(date):
    """Servidor em UTC depois das 21h de Brasília: para ele já é o dia seguinte."""

    @classmethod
    def today(cls):
        return HOJE_FAZENDA + timedelta(days=1)


@pytest.fixture
def servidor_um_dia_a_frente(monkeypatch):
    for modulo in (regras_data, regras_ciclo):
        monkeypatch.setattr(modulo, "date", _DataDoServidorUtc)


@pytest.fixture
def ciclo(novo_ciclo):
    return novo_ciclo()


@pytest.fixture
def insumo(client, gestor):
    r = client.post("/api/v1/insumos/", json={"nome": unico("Cal"), "unidade_uso": "kg"}, headers=gestor)
    assert r.status_code == 201, r.text
    return r.json()


def _comprar(client, gestor, insumo_id, data, retroativo=False):
    return client.post(
        f"/api/v1/insumos/{insumo_id}/compras",
        json={"data_compra": data.isoformat(), "quantidade": 100, "valor_total_rs": 400, "retroativo": retroativo},
        headers=gestor,
    )


def test_hoje_da_fazenda_usa_o_fuso_configurado():
    assert regras_data.hoje_da_fazenda() == HOJE_FAZENDA


def test_compra_uso_e_venda_do_dia_da_fazenda_sem_retroativo(client, gestor, ciclo, insumo, servidor_um_dia_a_frente):
    assert _comprar(client, gestor, insumo["id"], HOJE_FAZENDA).status_code == 201

    uso = client.post(
        f"/api/v1/ciclos/{ciclo['id']}/usos-insumo",
        json={"insumo_id": insumo["id"], "data_uso": HOJE_FAZENDA.isoformat(), "quantidade": 10, "fase": "CULTIVO"},
        headers=gestor,
    )
    assert uso.status_code == 201, uso.text

    venda = client.post(
        f"/api/v1/ciclos/{ciclo['id']}/vendas",
        json={"data_venda": HOJE_FAZENDA.isoformat(), "tipo": "DESBASTE", "biomassa_kg": 200,
              "peso_medio_g": 20, "preco_kg": 20},
        headers=gestor,
    )
    assert venda.status_code == 201, venda.text


def test_ontem_da_fazenda_continua_exigindo_retroativo(client, gestor, insumo, servidor_um_dia_a_frente):
    r = _comprar(client, gestor, insumo["id"], ONTEM_FAZENDA)
    assert r.status_code == 422 and "retroativo" in r.json()["detail"]
    assert _comprar(client, gestor, insumo["id"], ONTEM_FAZENDA, retroativo=True).status_code == 201


def test_amanha_da_fazenda_e_futuro(client, gestor, insumo):
    r = _comprar(client, gestor, insumo["id"], HOJE_FAZENDA + timedelta(days=1), retroativo=True)
    assert r.status_code == 422 and "futuro" in r.json()["detail"]


# ── Povoamento com data real no futuro ──

def _ciclo_pronto_para_povoar(client, gestor, viveiro_id):
    r = client.post("/api/v1/ciclos/", json={"viveiro_id": viveiro_id, "data_povoamento": HOJE_FAZENDA.isoformat()},
                    headers=gestor)
    assert r.status_code == 201, r.text
    ciclo_id = r.json()["id"]
    for etapa in client.get(f"/api/v1/ciclos/{ciclo_id}/etapas-preparo", headers=gestor).json():
        r = client.patch(f"/api/v1/ciclos/{ciclo_id}/etapas-preparo/{etapa['id']}",
                         json={"status": "NAO_REALIZADA"}, headers=gestor)
        assert r.status_code == 200, r.text
    return ciclo_id


def _povoar(client, gestor, ciclo_id, data):
    return client.post(
        f"/api/v1/ciclos/{ciclo_id}/povoar",
        json={"data_povoamento": data.isoformat(), "quantidade_pos_larvas": 100_000, "custo_aquisicao_pl": 1_000},
        headers=gestor,
    )


def test_povoar_com_data_futura_da_422(client, gestor, novo_viveiro):
    ciclo_id = _ciclo_pronto_para_povoar(client, gestor, novo_viveiro()["id"])
    r = _povoar(client, gestor, ciclo_id, HOJE_FAZENDA + timedelta(days=1))
    assert r.status_code == 422 and "futuro" in r.json()["detail"]
    r = _povoar(client, gestor, ciclo_id, HOJE_FAZENDA)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ATIVO"


def test_fuso_desconhecido_falha_na_carga_do_setting():
    from src.config import Settings

    with pytest.raises(ValueError):
        Settings(fazenda_fuso_horario="America/Sao_Paul")


def test_metricas_contam_os_dias_pelo_dia_da_fazenda(client, gestor, ciclo, monkeypatch):
    povoamento = date.fromisoformat(ciclo["data_povoamento"])
    monkeypatch.setattr("src.routers.ciclos.hoje_da_fazenda", lambda: povoamento + timedelta(days=10))
    r = client.get(f"/api/v1/ciclos/{ciclo['id']}/metricas-atuais", headers=gestor)
    assert r.status_code == 200, r.text
    assert r.json()["dias_cultivo"] == 10


def test_recomendacao_alimentar_acha_o_manejo_do_dia_da_fazenda(client, gestor, ciclo, monkeypatch):
    r = client.post(
        f"/api/v1/ciclos/{ciclo['id']}/manejos-alimentares/",
        json={"data_registro": HOJE_FAZENDA.isoformat(), "quantidade_racao_kg": 5, "sobra_bandeja_nivel": "SEM_SOBRA"},
        headers=gestor,
    )
    assert r.status_code == 201, r.text
    url = f"/api/v1/ciclos/{ciclo['id']}/manejos-alimentares/recomendacao"
    assert client.get(url, headers=gestor).json()["racao_lancada_hoje_kg"] == 5
    # o "hoje" da recomendação é o da fazenda: com outro dia, o manejo de hoje não conta
    monkeypatch.setattr("src.routers.manejos.hoje_da_fazenda", lambda: ONTEM_FAZENDA)
    assert client.get(url, headers=gestor).json()["racao_lancada_hoje_kg"] == 0
