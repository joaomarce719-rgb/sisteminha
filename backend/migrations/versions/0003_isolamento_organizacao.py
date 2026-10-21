"""isolamento por organização

Adiciona organizacao_id a viveiros, tabela de preços, tabelas alimentares e
logs de auditoria; a identificação do viveiro passa a ser única por organização.
Dados existentes são atribuídos à organização de origem (propriedade, autor) ou,
na falta dela, à organização mais antiga. Usuários ativos sem organização são
vinculados à mesma organização; cadastros pendentes continuam sem vínculo.

As operações são idempotentes porque bancos anteriores ao Alembic podem ter
recebido tabelas já no formato atual (ver src.database.executar_migracoes).

Revision ID: 0003
Revises: 0002
"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _colunas(tabela: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(tabela)}


def _org_padrao(precisa: bool) -> str | None:
    bind = op.get_bind()
    org = bind.execute(sa.text("SELECT id FROM organizacoes ORDER BY created_at LIMIT 1")).scalar()
    if org is not None or not precisa:
        return org
    novo = uuid.uuid4()
    org = novo.hex if bind.dialect.name == "sqlite" else str(novo)
    bind.execute(
        sa.text(
            "INSERT INTO organizacoes (id, nome, moeda, status_ativo, created_at, updated_at) "
            "VALUES (:id, 'Organização Padrão', 'BRL', :ativo, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {"id": org, "ativo": True},
    )
    return org


def upgrade() -> None:
    bind = op.get_bind()
    uuid_t = sa.UUID()

    novas = {
        "viveiros": "organizacao_id" not in _colunas("viveiros"),
        "tabela_precos_mercado": "organizacao_id" not in _colunas("tabela_precos_mercado"),
        "tabelas_alimentares": "organizacao_id" not in _colunas("tabelas_alimentares"),
        "logs_auditoria": "organizacao_id" not in _colunas("logs_auditoria"),
    }
    for tabela, adicionar in novas.items():
        if adicionar:
            with op.batch_alter_table(tabela) as batch:
                batch.add_column(sa.Column("organizacao_id", uuid_t, nullable=True))

    tem_dados = any(
        bind.execute(sa.text(f"SELECT COUNT(*) FROM {t}")).scalar()
        for t in ("viveiros", "tabela_precos_mercado", "usuarios")
    )
    org = _org_padrao(precisa=tem_dados)

    if org is not None:
        bind.execute(
            sa.text(
                "UPDATE viveiros SET organizacao_id = COALESCE("
                "(SELECT p.organizacao_id FROM propriedades p WHERE p.id = viveiros.propriedade_id), :org) "
                "WHERE organizacao_id IS NULL"
            ),
            {"org": org},
        )
        bind.execute(
            sa.text("UPDATE tabela_precos_mercado SET organizacao_id = :org WHERE organizacao_id IS NULL"),
            {"org": org},
        )
        bind.execute(
            sa.text(
                "UPDATE tabelas_alimentares SET organizacao_id = COALESCE("
                "(SELECT u.organizacao_id FROM usuarios u WHERE u.id = tabelas_alimentares.created_by_id), :org) "
                "WHERE organizacao_id IS NULL AND created_by_id IS NOT NULL"
            ),
            {"org": org},
        )
        bind.execute(
            sa.text("UPDATE usuarios SET organizacao_id = :org WHERE organizacao_id IS NULL AND ativo = :ativo"),
            {"org": org, "ativo": True},
        )
    bind.execute(
        sa.text(
            "UPDATE logs_auditoria SET organizacao_id = "
            "(SELECT u.organizacao_id FROM usuarios u WHERE u.id = logs_auditoria.usuario_id) "
            "WHERE organizacao_id IS NULL"
        )
    )

    indices_viveiros = {i["name"]: i for i in sa.inspect(bind).get_indexes("viveiros")}
    uniques_viveiros = {u["name"] for u in sa.inspect(bind).get_unique_constraints("viveiros")}
    with op.batch_alter_table("viveiros") as batch:
        batch.alter_column("organizacao_id", existing_type=uuid_t, nullable=False)
        if novas["viveiros"]:
            batch.create_foreign_key("fk_viveiros_organizacao", "organizacoes", ["organizacao_id"], ["id"])
        if indices_viveiros.get("ix_viveiros_identificacao", {}).get("unique"):
            batch.drop_index("ix_viveiros_identificacao")
            batch.create_index("ix_viveiros_identificacao", ["identificacao"], unique=False)
        if "ix_viveiros_organizacao_id" not in indices_viveiros:
            batch.create_index("ix_viveiros_organizacao_id", ["organizacao_id"])
        if "uq_viveiros_organizacao_identificacao" not in uniques_viveiros:
            batch.create_unique_constraint(
                "uq_viveiros_organizacao_identificacao", ["organizacao_id", "identificacao"]
            )

    for tabela, nullable in (("tabela_precos_mercado", False), ("tabelas_alimentares", True)):
        indices = {i["name"] for i in sa.inspect(bind).get_indexes(tabela)}
        with op.batch_alter_table(tabela) as batch:
            if not nullable:
                batch.alter_column("organizacao_id", existing_type=uuid_t, nullable=False)
            if novas[tabela]:
                batch.create_foreign_key(f"fk_{tabela}_organizacao", "organizacoes", ["organizacao_id"], ["id"])
            if f"ix_{tabela}_organizacao_id" not in indices:
                batch.create_index(f"ix_{tabela}_organizacao_id", ["organizacao_id"])

    if "ix_logs_auditoria_organizacao_id" not in {i["name"] for i in sa.inspect(bind).get_indexes("logs_auditoria")}:
        op.create_index("ix_logs_auditoria_organizacao_id", "logs_auditoria", ["organizacao_id"])


def downgrade() -> None:
    op.drop_index("ix_logs_auditoria_organizacao_id", table_name="logs_auditoria")
    with op.batch_alter_table("logs_auditoria") as batch:
        batch.drop_column("organizacao_id")
    for tabela in ("tabelas_alimentares", "tabela_precos_mercado"):
        with op.batch_alter_table(tabela) as batch:
            batch.drop_index(f"ix_{tabela}_organizacao_id")
            batch.drop_constraint(f"fk_{tabela}_organizacao", type_="foreignkey")
            batch.drop_column("organizacao_id")
    with op.batch_alter_table("viveiros") as batch:
        batch.drop_constraint("uq_viveiros_organizacao_identificacao", type_="unique")
        batch.drop_index("ix_viveiros_organizacao_id")
        batch.drop_index("ix_viveiros_identificacao")
        batch.create_index("ix_viveiros_identificacao", ["identificacao"], unique=True)
        batch.drop_constraint("fk_viveiros_organizacao", type_="foreignkey")
        batch.drop_column("organizacao_id")
