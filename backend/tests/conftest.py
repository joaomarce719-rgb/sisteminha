"""Fixtures dos testes de API.

As variáveis de ambiente são definidas antes de qualquer import de `src`, pois
o engine do banco é criado na importação de `src.database`.
"""

import os
import shutil
import tempfile
import uuid

_DB_DIR = tempfile.mkdtemp(prefix="sad_tests_")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_DB_DIR, "test.db").replace("\\", "/")
os.environ["APP_DEBUG"] = "true"
os.environ["DB_ECHO"] = "false"
os.environ["DB_FALLBACK_SQLITE"] = "false"
os.environ["JWT_SECRET_KEY"] = "chave-exclusiva-dos-testes"
os.environ["SUPERADMIN_EMAILS"] = "admin@sad.com"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

SENHA_SEED = "senha123"


def unico(prefixo: str) -> str:
    return f"{prefixo}-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def client():
    from src.main import app

    with TestClient(app) as c:
        yield c
    from src.database import engine

    engine.dispose()
    shutil.rmtree(_DB_DIR, ignore_errors=True)


def _login(client, email: str, senha: str = SENHA_SEED) -> dict[str, str]:
    r = client.post("/api/v1/auth/login", json={"email": email, "senha": senha})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def login(client):
    return lambda email, senha=SENHA_SEED: _login(client, email, senha)


@pytest.fixture(scope="session")
def gestor(client):
    return _login(client, "gestor@sad.com")


@pytest.fixture(scope="session")
def admin(client):
    return _login(client, "admin@sad.com")


@pytest.fixture(scope="session")
def campo(client):
    return _login(client, "campo@sad.com")


@pytest.fixture(scope="session")
def vigia(client):
    return _login(client, "vigia@sad.com")


@pytest.fixture
def novo_viveiro(client, gestor):
    def _criar(area_m2: float = 10_000.0) -> dict:
        r = client.post(
            "/api/v1/viveiros/",
            json={"identificacao": unico("VIV"), "area_util_m2": area_m2},
            headers=gestor,
        )
        assert r.status_code == 201, r.text
        return r.json()

    return _criar


@pytest.fixture
def novo_ciclo(client, gestor, novo_viveiro):
    def _criar(
        data_povoamento: str = "2026-08-01",
        pls: int = 300_000,
        custo_pl: float = 3_000.0,
    ) -> dict:
        viveiro = novo_viveiro()
        r = client.post(
            "/api/v1/ciclos/",
            json={
                "viveiro_id": viveiro["id"],
                "data_povoamento": data_povoamento,
                "quantidade_pos_larvas": pls,
                "custo_aquisicao_pl": custo_pl,
            },
            headers=gestor,
        )
        assert r.status_code == 201, r.text
        return r.json()

    return _criar
