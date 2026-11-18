"""Tipos enumerados do Postgres em dia com o código.

Bancos criados antes do Alembic podem ter listas de valores antigas (o Supabase estava sem
PAUSADO em status_ciclo, o que derrubava a criação de ciclos), e o SQLite dos testes não acusa isso.
"""

import logging
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from src import database
from src.database import diferencas_enums, enums_do_codigo, verificar_enums_do_banco


def _banco_igual_ao_codigo() -> dict[str, list[str]]:
    return {nome: list(valores) for nome, valores in enums_do_codigo().items()}


def test_codigo_declara_os_enums_dos_modelos():
    codigo = enums_do_codigo()
    assert "PAUSADO" in codigo["status_ciclo"]
    assert {"categoria_custo", "nivel_sobra_bandeja", "status_alimentar", "role_usuario"} <= set(codigo)


def test_banco_completo_nao_tem_diferencas():
    assert diferencas_enums(_banco_igual_ao_codigo(), enums_do_codigo()) == []


def test_valor_que_falta_no_banco_e_apontado():
    banco = _banco_igual_ao_codigo()
    banco["status_ciclo"] = [v for v in banco["status_ciclo"] if v != "PAUSADO"]
    assert diferencas_enums(banco, enums_do_codigo()) == ["o tipo 'status_ciclo' não tem os valores PAUSADO"]


def test_tipo_ausente_no_banco_e_apontado():
    banco = _banco_igual_ao_codigo()
    del banco["categoria_custo"]
    assert diferencas_enums(banco, enums_do_codigo()) == ["o tipo 'categoria_custo' não existe no banco"]


def test_valor_a_mais_no_banco_nao_e_problema():
    banco = _banco_igual_ao_codigo()
    banco["status_ciclo"].append("ARQUIVADO")
    assert diferencas_enums(banco, enums_do_codigo()) == []


class _Conexao:
    def __init__(self, linhas):
        self._linhas = linhas

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, _consulta):
        return iter(self._linhas)


class _PostgresSimulado:
    class dialect:  # noqa: N801
        name = "postgresql"

    def __init__(self, banco):
        self._linhas = [(tipo, valor) for tipo, valores in banco.items() for valor in valores]

    def connect(self):
        return _Conexao(self._linhas)


def test_verificacao_no_postgres_registra_o_erro(monkeypatch, caplog):
    banco = _banco_igual_ao_codigo()
    banco["status_ciclo"] = [v for v in banco["status_ciclo"] if v != "PAUSADO"]
    monkeypatch.setattr(database, "engine", _PostgresSimulado(banco))
    with caplog.at_level(logging.ERROR, logger="uvicorn.error"):
        verificar_enums_do_banco()
    mensagens = [r.getMessage() for r in caplog.records]
    assert any("status_ciclo" in m and "PAUSADO" in m and "alembic upgrade head" in m for m in mensagens)


def test_verificacao_no_postgres_em_dia_nao_registra_erro(monkeypatch, caplog):
    monkeypatch.setattr(database, "engine", _PostgresSimulado(_banco_igual_ao_codigo()))
    with caplog.at_level(logging.ERROR, logger="uvicorn.error"):
        verificar_enums_do_banco()
    assert not caplog.records


def test_verificacao_no_sqlite_e_silenciosa(caplog):
    with caplog.at_level(logging.ERROR, logger="uvicorn.error"):
        verificar_enums_do_banco()
    assert not caplog.records


def _head_das_migracoes() -> str:
    from pathlib import Path

    from alembic.config import Config
    from alembic.script import ScriptDirectory

    raiz = Path(__file__).resolve().parents[1]
    cfg = Config(str(raiz / "alembic.ini"))
    cfg.set_main_option("script_location", str(raiz / "migrations"))
    return ScriptDirectory.from_config(cfg).get_current_head()


def test_banco_de_teste_esta_na_ultima_revisao(client):
    # O app sobe e aplica as migrações até a mais nova (no SQLite a 0006 não faz nada)
    with database.engine.connect() as conn:
        assert conn.execute(text("select version_num from alembic_version")).scalar() == _head_das_migracoes()


def _migracao_0006():
    import importlib.util
    from pathlib import Path

    caminho = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0006_status_ciclo_pausado.py"
    spec = importlib.util.spec_from_file_location("migracao_0006", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_migracao_0006_no_postgres_so_acrescenta_o_valor_sem_autocommit(monkeypatch):
    """O autocommit_block do Alembic falha quando executar_migracoes já abriu a transação (AssertionError)."""
    modulo = _migracao_0006()
    executados = []
    monkeypatch.setattr(modulo.op, "get_bind", lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")))
    monkeypatch.setattr(modulo.op, "execute", executados.append)
    monkeypatch.setattr(modulo.op, "get_context", lambda: pytest.fail("não usar autocommit_block na 0006"))
    modulo.upgrade()
    assert executados == ["ALTER TYPE status_ciclo ADD VALUE IF NOT EXISTS 'PAUSADO'"]


def test_migracao_0006_no_sqlite_nao_faz_nada(monkeypatch):
    modulo = _migracao_0006()
    monkeypatch.setattr(modulo.op, "get_bind", lambda: SimpleNamespace(dialect=SimpleNamespace(name="sqlite")))
    monkeypatch.setattr(modulo.op, "execute", lambda *_: pytest.fail("SQLite não tem enum nativo"))
    modulo.upgrade()
