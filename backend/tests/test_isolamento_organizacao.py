"""Isolamento entre organizações (RF-002, RN-001, RNF-005).

A organização A é a seed (gestor@sad.com, campo@sad.com, vigia@sad.com).
A organização B é criada pela Administração Central com um gestor próprio.
"""

import pytest

from tests.conftest import unico


@pytest.fixture(scope="module")
def org_b(client, admin, login):
    codigo = unico("ORGB")
    org = client.post(
        "/api/v1/organizacoes/", json={"nome": "Fazenda B", "identificador": codigo}, headers=admin
    )
    assert org.status_code == 201, org.text
    email = f"{unico('gestorb')}@x.com"
    r = client.post(
        "/api/v1/admin/gestores",
        json={
            "nome_completo": "Gestor B",
            "email": email,
            "senha": "abc12345",
            "organizacao_id": org.json()["id"],
        },
        headers=admin,
    )
    assert r.status_code == 201, r.text
    return {"id": org.json()["id"], "codigo": codigo, "gestor": login(email, "abc12345")}


@pytest.fixture
def ciclo_a(client, gestor, novo_ciclo):
    ciclo = novo_ciclo()
    r = client.post(
        f"/api/v1/ciclos/{ciclo['id']}/biometrias/",
        json={"data_medicao": "2026-09-01", "quantidade_amostrada": 30, "peso_medio_g": 9.0},
        headers=gestor,
    )
    assert r.status_code == 201
    return ciclo


def test_viveiro_de_outra_organizacao_invisivel(client, org_b, ciclo_a):
    gb = org_b["gestor"]
    viveiro_id = ciclo_a["viveiro_id"]
    assert viveiro_id not in [v["id"] for v in client.get("/api/v1/viveiros/", headers=gb).json()["items"]]
    assert client.get(f"/api/v1/viveiros/{viveiro_id}", headers=gb).status_code == 404
    assert client.put(f"/api/v1/viveiros/{viveiro_id}", json={"area_util_m2": 1}, headers=gb).status_code == 404
    assert client.delete(f"/api/v1/viveiros/{viveiro_id}", headers=gb).status_code == 404


def test_ciclo_de_outra_organizacao_inacessivel(client, org_b, ciclo_a):
    gb = org_b["gestor"]
    base = f"/api/v1/ciclos/{ciclo_a['id']}"
    assert ciclo_a["id"] not in [c["id"] for c in client.get("/api/v1/ciclos/", headers=gb).json()]
    for url in (base, f"{base}/metricas-atuais", f"{base}/exportar-csv", f"{base}/biometrias/",
                f"{base}/custos/", f"{base}/manejos-alimentares/"):
        assert client.get(url, headers=gb).status_code == 404, url
    assert client.post(f"{base}/pausar", headers=gb).status_code == 404
    assert client.delete(base, headers=gb).status_code == 404


def test_escrita_em_ciclo_alheio_bloqueada(client, org_b, ciclo_a):
    gb = org_b["gestor"]
    bio = {"ciclo_id": ciclo_a["id"], "data_medicao": "2026-09-05", "quantidade_amostrada": 30, "peso_medio_g": 9.5}
    assert client.post(f"/api/v1/ciclos/{ciclo_a['id']}/biometrias/", json=bio, headers=gb).status_code == 404
    assert client.post("/api/v1/biometrias/", json=bio, headers=gb).status_code == 404
    custo = {"ciclo_id": ciclo_a["id"], "data_lancamento": "2026-09-05", "categoria": "RACAO",
             "descricao": "Ração", "valor_rs": 10}
    assert client.post("/api/v1/custos/", json=custo, headers=gb).status_code == 404
    assert client.post("/api/v1/simulacao/", json={"ciclo_id": ciclo_a["id"]}, headers=gb).status_code == 404


def test_listas_globais_filtradas(client, gestor, org_b, ciclo_a):
    gb = org_b["gestor"]
    assert any(b["ciclo_id"] == ciclo_a["id"] for b in client.get("/api/v1/biometrias/", headers=gestor).json())
    assert not any(b["ciclo_id"] == ciclo_a["id"] for b in client.get("/api/v1/biometrias/", headers=gb).json())
    assert not any(c["ciclo_id"] == ciclo_a["id"] for c in client.get("/api/v1/custos/", headers=gb).json()["items"])


def test_identificacao_de_viveiro_unica_por_organizacao(client, gestor, org_b):
    nome = unico("MESMO")
    for headers in (gestor, org_b["gestor"]):
        r = client.post("/api/v1/viveiros/", json={"identificacao": nome, "area_util_m2": 100}, headers=headers)
        assert r.status_code == 201
    r = client.post("/api/v1/viveiros/", json={"identificacao": nome, "area_util_m2": 100}, headers=gestor)
    assert r.status_code == 409


def test_usuarios_de_outra_organizacao(client, gestor, org_b):
    gb = org_b["gestor"]
    emails_b = {u["email"] for u in client.get("/api/v1/admin/usuarios", headers=gb).json()}
    assert "campo@sad.com" not in emails_b
    campo_a = next(u for u in client.get("/api/v1/admin/usuarios", headers=gestor).json() if u["email"] == "campo@sad.com")
    assert client.put(f"/api/v1/admin/usuarios/{campo_a['id']}", json={"ativo": False}, headers=gb).status_code == 404
    assert client.post(f"/api/v1/admin/usuarios/{campo_a['id']}/resetar-senha", headers=gb).status_code == 404


def test_cadastro_com_codigo_vai_para_a_organizacao(client, gestor, org_b):
    email = f"{unico('candidato')}@x.com"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "senha": "abc12345", "codigo_organizacao": org_b["codigo"]},
    )
    assert r.status_code == 201
    assert email in {u["email"] for u in client.get("/api/v1/admin/usuarios", headers=org_b["gestor"]).json()}
    assert email not in {u["email"] for u in client.get("/api/v1/admin/usuarios", headers=gestor).json()}
    r = client.post("/api/v1/auth/register", json={"email": f"{unico('x')}@x.com", "senha": "abc12345",
                                                    "codigo_organizacao": "NAO-EXISTE"})
    assert r.status_code == 422


def test_auditoria_isolada(client, gestor, org_b, ciclo_a):
    ids = {log["registro_id"] for log in client.get("/api/v1/auditoria/", params={"limite": 200},
                                                    headers=org_b["gestor"]).json()["items"]}
    assert ciclo_a["id"] not in ids


def test_tabelas_alimentares(client, gestor, org_b):
    gb = org_b["gestor"]
    propria = client.post(
        "/api/v1/tabelas-alimentares/",
        json={"nome": unico("TabA"), "faixas": [{"peso_g": 2, "taxa_pct": 7}, {"peso_g": 20, "taxa_pct": 3}]},
        headers=gestor,
    ).json()
    visiveis_b = client.get("/api/v1/tabelas-alimentares/", headers=gb).json()
    assert propria["id"] not in [t["id"] for t in visiveis_b]
    global_ = next(t for t in visiveis_b if t["nome"].startswith("Clifford"))
    assert client.put(f"/api/v1/tabelas-alimentares/{global_['id']}", json={"ativo": False}, headers=gb).status_code == 403
    assert client.get(f"/api/v1/tabelas-alimentares/{propria['id']}", headers=gb).status_code == 404


def test_organizacoes_visiveis(client, gestor, admin, org_b):
    assert len(client.get("/api/v1/organizacoes/", headers=gestor).json()) == 1
    assert len(client.get("/api/v1/organizacoes/", headers=admin).json()) >= 2
    assert client.get(f"/api/v1/organizacoes/{org_b['id']}", headers=gestor).status_code == 404
    assert client.post("/api/v1/organizacoes/", json={"nome": "Nova"}, headers=gestor).status_code == 403


def test_precos_por_organizacao(client, gestor, org_b):
    assert client.get("/api/v1/precos-mercado/", headers=org_b["gestor"]).json() == []
    assert len(client.get("/api/v1/precos-mercado/", headers=gestor).json()) >= 1
