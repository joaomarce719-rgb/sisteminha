"""insumos, compras, usos e fase dos custos

Cria insumos (cadastro por organização, nome único sem diferenciar maiúsculas),
compras_insumo (base do preço médio ponderado) e consumos_insumo (uso por ciclo,
ligado ao custo operacional gerado). custos_operacionais.fase (PREPARO, CULTIVO ou
DESPESCA) é texto e não enum nativo; os custos existentes ficam em CULTIVO.

Só cria o que faltar (conferido pelo inspetor): bancos criados antes do Alembic
podem já ter as tabelas (ver src.database.executar_migracoes).

Revision ID: 0009
Revises: 0008
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, Sequence[str], None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspetor():
    return sa.inspect(op.get_bind())


def _colunas_base() -> list[sa.Column]:
    return [
        sa.Column("id", sa.UUID(), server_default=sa.text("(gen_random_uuid())"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
    ]


def upgrade() -> None:
    tabelas = set(_inspetor().get_table_names())

    if "fase" not in {c["name"] for c in _inspetor().get_columns("custos_operacionais")}:
        with op.batch_alter_table("custos_operacionais") as batch:
            batch.add_column(sa.Column("fase", sa.String(10), nullable=False, server_default="CULTIVO"))

    if "insumos" not in tabelas:
        op.create_table(
            "insumos",
            sa.Column("organizacao_id", sa.UUID(), nullable=False),
            sa.Column("nome", sa.String(120), nullable=False),
            sa.Column("nome_chave", sa.String(120), nullable=False),
            sa.Column("unidade_uso", sa.String(20), nullable=False),
            sa.Column("categoria", sa.String(30), nullable=False, server_default="OUTROS"),
            sa.Column("ativo", sa.Boolean(), nullable=False),
            *_colunas_base(),
            sa.ForeignKeyConstraint(["organizacao_id"], ["organizacoes.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organizacao_id", "nome_chave", name="uq_insumos_organizacao_nome_chave"),
        )
        op.create_index("ix_insumos_organizacao_id", "insumos", ["organizacao_id"])

    if "compras_insumo" not in tabelas:
        op.create_table(
            "compras_insumo",
            sa.Column("insumo_id", sa.UUID(), nullable=False),
            sa.Column("data_compra", sa.Date(), nullable=False),
            sa.Column("quantidade", sa.Numeric(14, 4), nullable=False),
            sa.Column("valor_total_rs", sa.Numeric(12, 2), nullable=False),
            sa.Column("fornecedor", sa.String(120), nullable=True),
            sa.Column("observacao", sa.String(500), nullable=True),
            sa.Column("retroativo", sa.Boolean(), nullable=False, server_default=sa.false()),
            *_colunas_base(),
            sa.ForeignKeyConstraint(["insumo_id"], ["insumos.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_compras_insumo_insumo_id", "compras_insumo", ["insumo_id"])

    if "consumos_insumo" not in tabelas:
        op.create_table(
            "consumos_insumo",
            sa.Column("ciclo_id", sa.UUID(), nullable=False),
            sa.Column("insumo_id", sa.UUID(), nullable=False),
            sa.Column("data_uso", sa.Date(), nullable=False),
            sa.Column("quantidade", sa.Numeric(14, 4), nullable=False),
            sa.Column("fase", sa.String(10), nullable=False, server_default="CULTIVO"),
            sa.Column("custo_id", sa.UUID(), nullable=True),
            sa.Column("preco_unitario_rs", sa.Numeric(12, 4), nullable=True),
            sa.Column("preco_corrigido_rs", sa.Numeric(12, 4), nullable=True),
            sa.Column("registrado_por", sa.UUID(), nullable=True),
            sa.Column("observacao", sa.String(500), nullable=True),
            sa.Column("retroativo", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("recalculado_em", sa.DateTime(timezone=True), nullable=True),
            *_colunas_base(),
            sa.ForeignKeyConstraint(["ciclo_id"], ["ciclos_produtivos.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["insumo_id"], ["insumos.id"]),
            sa.ForeignKeyConstraint(["custo_id"], ["custos_operacionais.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["registrado_por"], ["usuarios.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_consumos_insumo_ciclo_id", "consumos_insumo", ["ciclo_id"])
        op.create_index("ix_consumos_insumo_insumo_id", "consumos_insumo", ["insumo_id"])


def downgrade() -> None:
    op.drop_table("consumos_insumo")
    op.drop_table("compras_insumo")
    op.drop_table("insumos")
    with op.batch_alter_table("custos_operacionais") as batch:
        batch.drop_column("fase")
