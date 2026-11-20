"""ciclo em preparo: etapas do preparo e pós-larvas vazias até o povoamento

Todo ciclo novo nasce PLANEJADO e só recebe pós-larvas no povoamento, por isso
quantidade_pos_larvas e custo_aquisicao_pl de ciclos_produtivos passam a aceitar vazio
(no Postgres, ALTER COLUMN ... DROP NOT NULL; no SQLite o batch recria a tabela).
Cria etapas_preparo (tipo e status em texto, não enum nativo) e liga o uso de insumo
à etapa (consumos_insumo.etapa_id, SET NULL ao excluir a etapa).

Só altera o que faltar (conferido pelo inspetor): bancos criados antes do Alembic
podem já estar no formato novo (ver src.database.executar_migracoes).

No Postgres garante os valores PLANEJADO e CANCELADO no tipo enumerado status_ciclo,
que este código é o primeiro a gravar (bancos legados criaram o tipo fora do Alembic;
ver 0006, cujo padrão se repete: ADD VALUE IF NOT EXISTS dentro da transação da
migração, sem autocommit_block). No SQLite não há tipo enumerado nativo. O Postgres
não remove valor de enum, então o downgrade os mantém.

Revision ID: 0011
Revises: 0010
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, Sequence[str], None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUNAS_DO_POVOAMENTO = {"quantidade_pos_larvas": sa.Integer(), "custo_aquisicao_pl": sa.Numeric(12, 2)}


def _inspetor():
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE status_ciclo ADD VALUE IF NOT EXISTS 'PLANEJADO'")
        op.execute("ALTER TYPE status_ciclo ADD VALUE IF NOT EXISTS 'CANCELADO'")

    colunas = {c["name"]: c for c in _inspetor().get_columns("ciclos_produtivos")}
    obrigatorias = [nome for nome in _COLUNAS_DO_POVOAMENTO if not colunas[nome]["nullable"]]
    if obrigatorias:
        with op.batch_alter_table("ciclos_produtivos") as batch:
            for nome in obrigatorias:
                batch.alter_column(nome, existing_type=_COLUNAS_DO_POVOAMENTO[nome], nullable=True)

    if "etapas_preparo" not in _inspetor().get_table_names():
        op.create_table(
            "etapas_preparo",
            sa.Column("ciclo_id", sa.UUID(), nullable=False),
            sa.Column("tipo", sa.String(20), nullable=False),
            sa.Column("data_inicio", sa.Date(), nullable=True),
            sa.Column("data_fim", sa.Date(), nullable=True),
            sa.Column("status", sa.String(14), nullable=False, server_default="PENDENTE"),
            sa.Column("observacao", sa.String(255), nullable=True),
            sa.Column("ordem", sa.Integer(), nullable=False),
            sa.Column("id", sa.UUID(), server_default=sa.text("(gen_random_uuid())"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["ciclo_id"], ["ciclos_produtivos.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_etapas_preparo_ciclo_id", "etapas_preparo", ["ciclo_id"])

    if "etapa_id" not in {c["name"] for c in _inspetor().get_columns("consumos_insumo")}:
        with op.batch_alter_table("consumos_insumo") as batch:
            batch.add_column(sa.Column("etapa_id", sa.UUID(), nullable=True))
            batch.create_foreign_key(
                "fk_consumos_insumo_etapa_id", "etapas_preparo", ["etapa_id"], ["id"], ondelete="SET NULL"
            )
            batch.create_index("ix_consumos_insumo_etapa_id", ["etapa_id"])


def downgrade() -> None:
    """Ciclos ainda sem pós-larvas (PLANEJADO/CANCELADO antes do povoamento) impedem a volta do NOT NULL."""
    with op.batch_alter_table("consumos_insumo") as batch:
        batch.drop_index("ix_consumos_insumo_etapa_id")
        batch.drop_constraint("fk_consumos_insumo_etapa_id", type_="foreignkey")
        batch.drop_column("etapa_id")
    op.drop_table("etapas_preparo")
    with op.batch_alter_table("ciclos_produtivos") as batch:
        for nome, tipo in _COLUNAS_DO_POVOAMENTO.items():
            batch.alter_column(nome, existing_type=tipo, nullable=False)
