"""vendas do ciclo (desbaste e despesca final)

Cria vendas: cada venda de um ciclo com data, tipo (DESBASTE ou DESPESCA_FINAL, texto e não
enum nativo), biomassa, peso médio, animais estimados, preço por kg e valor total. A soma das
vendas é a receita realizada e os animais vendidos saem da população do ciclo.

Só cria o que faltar (conferido pelo inspetor): bancos criados antes do Alembic podem já ter
a tabela (ver src.database.executar_migracoes).

Revision ID: 0010
Revises: 0009
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, Sequence[str], None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspetor():
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    if "vendas" in _inspetor().get_table_names():
        return
    op.create_table(
        "vendas",
        sa.Column("ciclo_id", sa.UUID(), nullable=False),
        sa.Column("data_venda", sa.Date(), nullable=False),
        sa.Column("tipo", sa.String(14), nullable=False),
        sa.Column("biomassa_kg", sa.Numeric(12, 2), nullable=False),
        sa.Column("peso_medio_g", sa.Numeric(8, 2), nullable=False),
        sa.Column("animais_estimados", sa.Integer(), nullable=False),
        sa.Column("preco_kg", sa.Numeric(10, 2), nullable=False),
        sa.Column("valor_total_rs", sa.Numeric(12, 2), nullable=False),
        sa.Column("comprador", sa.String(120), nullable=True),
        sa.Column("observacao", sa.String(500), nullable=True),
        sa.Column("retroativo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("id", sa.UUID(), server_default=sa.text("(gen_random_uuid())"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["ciclo_id"], ["ciclos_produtivos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vendas_ciclo_id", "vendas", ["ciclo_id"])


def downgrade() -> None:
    op.drop_table("vendas")
