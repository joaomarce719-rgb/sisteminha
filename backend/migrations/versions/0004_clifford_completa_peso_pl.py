"""tabela de Clifford completa e peso da PL no povoamento

Adiciona ciclos_produtivos.peso_medio_pl_g, base da biomassa inicial do FCA.
Tabelas alimentares que ainda têm exatamente os 5 pontos antigos de Clifford
passam a ter os 19 pontos da Tabela 1 do documento de referência; tabelas
editadas pelo usuário não são alteradas.

Revision ID: 0004
Revises: 0003
"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PONTOS_ANTIGOS = [(2.0, 7.15), (5.0, 5.05), (10.0, 3.88), (15.0, 3.33), (20.0, 2.98)]
_PONTOS_NOVOS = [
    (2.0, 7.15), (3.0, 6.13), (4.0, 5.50), (5.0, 5.05), (6.0, 4.71),
    (7.0, 4.44), (8.0, 4.22), (9.0, 4.04), (10.0, 3.88), (11.0, 3.74),
    (12.0, 3.62), (13.0, 3.51), (14.0, 3.42), (15.0, 3.33), (16.0, 3.25),
    (17.0, 3.17), (18.0, 3.10), (19.0, 3.04), (20.0, 2.98),
]


def _colunas(tabela: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(tabela)}


def _pontos(faixas) -> list[tuple[float, float]]:
    if isinstance(faixas, str):
        faixas = json.loads(faixas)
    return sorted((float(f["peso_g"]), float(f["taxa_pct"])) for f in faixas or [])


def _trocar_faixas(de: list[tuple[float, float]], para: list[tuple[float, float]]) -> None:
    bind = op.get_bind()
    novas = [{"peso_g": p, "taxa_pct": t} for p, t in para]
    atualizar = sa.text("UPDATE tabelas_alimentares SET faixas = :faixas WHERE id = :id").bindparams(
        sa.bindparam("faixas", type_=sa.JSON)
    )
    for tabela_id, faixas in bind.execute(sa.text("SELECT id, faixas FROM tabelas_alimentares")).fetchall():
        if _pontos(faixas) == de:
            bind.execute(atualizar, {"faixas": novas, "id": tabela_id})


def upgrade() -> None:
    if "peso_medio_pl_g" not in _colunas("ciclos_produtivos"):
        with op.batch_alter_table("ciclos_produtivos") as batch:
            batch.add_column(sa.Column("peso_medio_pl_g", sa.Float(), nullable=True))
    _trocar_faixas(_PONTOS_ANTIGOS, _PONTOS_NOVOS)


def downgrade() -> None:
    _trocar_faixas(_PONTOS_NOVOS, _PONTOS_ANTIGOS)
    with op.batch_alter_table("ciclos_produtivos") as batch:
        batch.drop_column("peso_medio_pl_g")
