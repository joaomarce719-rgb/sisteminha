"""Autenticação, cadastro e governança de usuários."""

from tests.conftest import unico


def _usuarios(client, headers) -> dict[str, str]:
    r = client.get("/api/v1/admin/usuarios", headers=headers)
    assert r.status_code == 200
    return {u["email"]: u["id"] for u in r.json()}


def test_login_invalido_rejeitado(client):
    r = client.post("/api/v1/auth/login", json={"email": "gestor@sad.com", "senha": "errada"})
    assert r.status_code == 401


def test_rota_protegida_sem_token(client):
    assert client.get("/api/v1/viveiros/").status_code == 401


def test_autocadastro_ignora_papel_e_nasce_inativo(client):
    email = f"{unico('novo')}@x.com"
    r = client.post(
        "/api/v1/auth/register", json={"email": email, "senha": "abc12345", "papel": "GESTOR"}
    )
    assert r.status_code == 201
    assert r.json()["papel"] == "CAMPO"
    assert r.json()["ativo"] is False

    r = client.post("/api/v1/auth/login", json={"email": email, "senha": "abc12345"})
    assert r.status_code == 403


def test_autocadastro_email_existente_nao_vaza_dados(client):
    r = client.post("/api/v1/auth/register", json={"email": "gestor@sad.com", "senha": "abcdef"})
    assert r.status_code == 409
    assert "id" not in r.json()


def test_aprovacao_define_papel(client, gestor, login):
    email = f"{unico('aprov')}@x.com"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "senha": "abc12345", "codigo_organizacao": "SAD-MATRIZ"},
    )
    assert r.status_code == 201
    user_id = _usuarios(client, gestor)[email]

    r = client.put(
        f"/api/v1/admin/usuarios/{user_id}/aprovar",
        json={"papel": "VIGIA", "ativo": True},
        headers=gestor,
    )
    assert r.status_code == 200
    me = client.get("/api/v1/auth/me", headers=login(email, "abc12345")).json()
    assert me["papel"] == "VIGIA"


def test_superadmin_vem_da_configuracao(client):
    for email, esperado in (("admin@sad.com", True), ("gestor@sad.com", False)):
        r = client.post("/api/v1/auth/login", json={"email": email, "senha": "senha123"})
        assert r.json()["is_superadmin"] is esperado


def test_painel_superadmin_bloqueado_para_gestor_comum(client, gestor, admin):
    assert client.get("/api/v1/admin/metricas-globais", headers=gestor).status_code == 403
    assert client.get("/api/v1/admin/metricas-globais", headers=admin).status_code == 200


def test_gestor_comum_nao_altera_superadmin(client, gestor):
    admin_id = _usuarios(client, gestor)["admin@sad.com"]
    assert (
        client.post(f"/api/v1/admin/usuarios/{admin_id}/resetar-senha", headers=gestor).status_code
        == 403
    )
    assert (
        client.put(f"/api/v1/admin/usuarios/{admin_id}", json={"ativo": False}, headers=gestor).status_code
        == 403
    )
    assert client.delete(f"/api/v1/admin/usuarios/{admin_id}", headers=gestor).status_code == 403


def test_nao_exclui_a_propria_conta(client, gestor):
    gestor_id = client.get("/api/v1/auth/me", headers=gestor).json()["id"]
    assert client.delete(f"/api/v1/admin/usuarios/{gestor_id}", headers=gestor).status_code == 400


def test_reset_gera_senha_temporaria_aleatoria(client, gestor, login):
    email = f"{unico('reset')}@x.com"
    r = client.post(
        "/api/v1/admin/operadores",
        json={"nome_completo": "Op Reset", "email": email, "senha": "inicial123"},
        headers=gestor,
    )
    assert r.status_code == 201
    user_id = r.json()["id"]
    r1 = client.post(f"/api/v1/admin/usuarios/{user_id}/resetar-senha", headers=gestor).json()
    r2 = client.post(f"/api/v1/admin/usuarios/{user_id}/resetar-senha", headers=gestor).json()
    assert r1["senha_temporaria"] != r2["senha_temporaria"]
    assert login(email, r2["senha_temporaria"])


def test_criar_usuario_exige_senha(client, gestor):
    r = client.post(
        "/api/v1/admin/usuarios",
        json={"email": f"{unico('sem')}@x.com", "nome_completo": "Sem Senha"},
        headers=gestor,
    )
    assert r.status_code == 422
