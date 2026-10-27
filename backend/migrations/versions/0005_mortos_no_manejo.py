"""camarões mortos encontrados no manejo alimentar

Adiciona manejos_alimentares.camaroes_mortos: contagem informada pelo raçoador
em cada trato, usada como piso da perda na sobrevivência estimada.

Revision ID: 0005
Revises: 0004
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _colunas(tabela: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(tabela)}


def upgrade() -> None:
    if "camaroes_mortos" not in _colunas("manejos_alimentares"):
        with op.batch_alter_table("manejos_alimentares") as batch:
            batch.add_column(sa.Column("camaroes_mortos", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("manejos_alimentares") as batch:
        batch.drop_column("camaroes_mortos")
