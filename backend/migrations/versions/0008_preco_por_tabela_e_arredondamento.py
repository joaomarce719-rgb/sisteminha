"""preço por tabela de 10 g e regra de arredondamento do peso

tabela_precos_mercado.incremento_por_g: R$/kg somados a cada grama acima de 10 g
(preco_por_kg passa a ser o preço de 10 g); 0 nas faixas antigas mantém o preço fixo.
organizacoes.regra_arredondamento: acordo de gramatura com o comprador
(PARA_BAIXO, PARA_CIMA ou PROPORCIONAL), texto e não enum nativo.

Revision ID: 0008
Revises: 0007
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _colunas(tabela: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(tabela)}


def upgrade() -> None:
    if "incremento_por_g" not in _colunas("tabela_precos_mercado"):
        with op.batch_alter_table("tabela_precos_mercado") as batch:
            batch.add_column(
                sa.Column("incremento_por_g", sa.Numeric(10, 2), nullable=False, server_default="0")
            )
    if "regra_arredondamento" not in _colunas("organizacoes"):
        with op.batch_alter_table("organizacoes") as batch:
            batch.add_column(
                sa.Column("regra_arredondamento", sa.String(12), nullable=False, server_default="PARA_BAIXO")
            )


def downgrade() -> None:
    with op.batch_alter_table("organizacoes") as batch:
        batch.drop_column("regra_arredondamento")
    with op.batch_alter_table("tabela_precos_mercado") as batch:
        batch.drop_column("incremento_por_g")
