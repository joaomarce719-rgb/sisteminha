"""Migração 0007: completa o esquema de bancos criados antes do Alembic (Supabase).

O Postgres não roda nos testes, então `op` e o inspetor são simulados: a migração deve
criar só o que falta e não tocar no que já existe.
"""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


def _migracao():
    caminho = Path(__file__).resolve().parents[1] / "migrations" / "versions" / "0007_completa_esquema_legado.py"
    spec = importlib.util.spec_from_file_location("migracao_0007", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class _Inspetor:
    def __init__(self, indices=(), chaves=(), amostra_nula=True):
        self._indices, self._chaves, self._amostra_nula = set(indices), set(chaves), amostra_nula

    def get_indexes(self, tabela):
        return [{"name": nome} for nome, t in self._indices if t == tabela]

    def get_foreign_keys(self, tabela):
        return [{"constrained_columns": [c], "referred_table": r} for t, c, r in self._chaves if t == tabela]

    def get_columns(self, tabela):
        return [{"name": "quantidade_amostrada", "nullable": self._amostra_nula}]


def _preparar(monkeypatch, dialeto, inspetor, nulos=0):
    modulo = _migracao()
    chamadas = []
    bind = SimpleNamespace(
        dialect=SimpleNamespace(name=dialeto),
        execute=lambda _sql: SimpleNamespace(scalar=lambda: nulos),
    )
    monkeypatch.setattr(modulo.op, "get_bind", lambda: bind)
    monkeypatch.setattr(modulo, "_inspetor", lambda: inspetor)
    monkeypatch.setattr(modulo.op, "get_context", lambda: pytest.fail("não usar autocommit_block"))
    for nome in ("create_index", "create_foreign_key", "alter_column"):
        monkeypatch.setattr(modulo.op, nome, lambda *a, _n=nome, **k: chamadas.append((_n, a, k)))
    return modulo, chamadas


def test_banco_legado_no_postgres_recebe_tudo_que_falta(monkeypatch):
    modulo, chamadas = _preparar(monkeypatch, "postgresql", _Inspetor())
    modulo.upgrade()

    indices = [a for n, a, _ in chamadas if n == "create_index"]
    assert indices == [("ix_usuarios_organizacao_id", "usuarios", ["organizacao_id"]),
                       ("ix_viveiros_propriedade_id", "viveiros", ["propriedade_id"])]
    chaves = {a[0]: (a[1], a[2], a[3], k["ondelete"]) for n, a, k in chamadas if n == "create_foreign_key"}
    assert chaves == {
        "biometrias_responsavel_id_fkey": ("biometrias", "usuarios", ["responsavel_id"], None),
        "ciclos_produtivos_tabela_alimentar_id_fkey": ("ciclos_produtivos", "tabelas_alimentares", ["tabela_alimentar_id"], "SET NULL"),
        "usuarios_organizacao_id_fkey": ("usuarios", "organizacoes", ["organizacao_id"], "SET NULL"),
        "viveiros_propriedade_id_fkey": ("viveiros", "propriedades", ["propriedade_id"], "SET NULL"),
    }
    assert [(n, a[:2], k["nullable"]) for n, a, k in chamadas if n == "alter_column"] == [
        ("alter_column", ("biometrias", "quantidade_amostrada"), False)
    ]


def test_banco_completo_nao_e_alterado(monkeypatch):
    completo = _Inspetor(
        indices={(n, t) for n, t, _ in _migracao().INDICES},
        chaves={(t, c, r) for t, c, r, _ in _migracao().CHAVES},
        amostra_nula=False,
    )
    modulo, chamadas = _preparar(monkeypatch, "postgresql", completo)
    modulo.upgrade()
    assert chamadas == []


def test_amostra_nula_existente_interrompe_sem_inventar_valor(monkeypatch):
    modulo, chamadas = _preparar(monkeypatch, "postgresql", _Inspetor(), nulos=2)
    with pytest.raises(RuntimeError, match="2 biometria"):
        modulo.upgrade()
    assert not any(n == "alter_column" for n, _, _ in chamadas)


def test_no_sqlite_so_confere_os_indices(monkeypatch):
    modulo, chamadas = _preparar(monkeypatch, "sqlite", _Inspetor(indices={("ix_viveiros_propriedade_id", "viveiros")}))
    modulo.upgrade()
    assert [(n, a[0]) for n, a, _ in chamadas] == [("create_index", "ix_usuarios_organizacao_id")]
