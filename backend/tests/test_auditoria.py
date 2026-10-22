"""Trilha de auditoria (RF-027, RNF-017)."""

from tests.conftest import unico


def _logs(client, headers, **filtros):
    r = client.get("/api/v1/auditoria/", params={"limite": 200, **filtros}, headers=headers)
    assert r.status_code == 200
    return r.json()


def test_falha_de_login_registrada(client, gestor, admin):
    # E-mail inexistente: sem organização, visível apenas para a Administração Central
    email = f"{unico('ninguem')}@x.com"
    client.post("/api/v1/auth/login", json={"email": email, "senha": "errada"})
    assert any(log["dados_novos"]["email"] == email for log in _logs(client, admin, acao="LOGIN_FALHA")["items"])
    assert not any(log["dados_novos"]["email"] == email for log in _logs(client, gestor, acao="LOGIN_FALHA")["items"])

    # Conta existente: aparece para o gestor da organização dela
    client.post("/api/v1/auth/login", json={"email": "campo@sad.com", "senha": "errada"})
    assert any(log["dados_novos"]["email"] == "campo@sad.com" for log in _logs(client, gestor, acao="LOGIN_FALHA")["items"])


def test_ciclo_de_vida_do_viveiro_auditado(client, gestor):
    r = client.post(
        "/api/v1/viveiros/", json={"identificacao": unico("AUD"), "area_util_m2": 500}, headers=gestor
    )
    viveiro_id = r.json()["id"]
    client.put(f"/api/v1/viveiros/{viveiro_id}", json={"area_util_m2": 600}, headers=gestor)
    client.delete(f"/api/v1/viveiros/{viveiro_id}", headers=gestor)

    logs = [log for log in _logs(client, gestor, entidade="Viveiro")["items"] if log["registro_id"] == viveiro_id]
    assert {log["acao"] for log in logs} == {"CRIAR", "ATUALIZAR", "EXCLUIR"}
    atualizacao = next(log for log in logs if log["acao"] == "ATUALIZAR")
    assert atualizacao["dados_anteriores"]["area_util_m2"] == 500
    assert atualizacao["dados_novos"]["area_util_m2"] == 600


def test_exportacao_auditada(client, gestor, novo_ciclo):
    ciclo = novo_ciclo()
    assert client.get(f"/api/v1/ciclos/{ciclo['id']}/exportar-csv", headers=gestor).status_code == 200
    logs = _logs(client, gestor, acao="EXPORTAR")["items"]
    assert any(log["registro_id"] == ciclo["id"] for log in logs)


def test_trilha_nao_expoe_hash_de_senha(client, gestor):
    client.post(
        "/api/v1/admin/operadores",
        json={"nome_completo": "Op Aud", "email": f"{unico('aud')}@x.com", "senha": "abc12345"},
        headers=gestor,
    )
    for log in _logs(client, gestor, entidade="Usuario")["items"]:
        for dados in (log["dados_anteriores"], log["dados_novos"]):
            assert "senha_hash" not in (dados or {})


def test_total_e_contagem_real(client, gestor):
    body = client.get("/api/v1/auditoria/", params={"limite": 1}, headers=gestor).json()
    assert len(body["items"]) == 1
    assert body["total"] > 1


def test_auditoria_restrita_ao_gestor(client, campo):
    assert client.get("/api/v1/auditoria/", headers=campo).status_code == 403
