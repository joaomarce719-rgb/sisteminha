"""completa o esquema de bancos criados antes do Alembic

O banco de produção (Supabase) nasceu antes das migrações: colunas acrescentadas
depois ficaram sem as chaves estrangeiras e os índices que a revisão 0001 cria num
banco novo, e biometrias.quantidade_amostrada ficou aceitando nulo. Sem as chaves,
o banco não impede referência quebrada e o ON DELETE SET NULL não acontece; os
testes (SQLite com chaves ligadas) não mostram a diferença.

Só cria o que faltar (conferido pelo inspetor), com os mesmos nomes que o Postgres
dá num banco novo, então é segura em bancos legados e novos. Roda na transação da
migração (sem autocommit_block, que falha em executar_migracoes; ver 0006).

No SQLite as chaves e a obrigatoriedade já vêm da 0001 (mudá-las exigiria recriar
as tabelas); ali só os índices são conferidos. O downgrade é vazio: desfazer
recriaria a diferença com os bancos novos.

Revision ID: 0007
Revises: 0006
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (tabela, coluna, tabela referida, regra ao excluir) — iguais aos modelos e à 0001
CHAVES = [
    ("biometrias", "responsavel_id", "usuarios", None),
    ("ciclos_produtivos", "tabela_alimentar_id", "tabelas_alimentares", "SET NULL"),
    ("usuarios", "organizacao_id", "organizacoes", "SET NULL"),
    ("viveiros", "propriedade_id", "propriedades", "SET NULL"),
]
INDICES = [
    ("ix_usuarios_organizacao_id", "usuarios", "organizacao_id"),
    ("ix_viveiros_propriedade_id", "viveiros", "propriedade_id"),
]


def _inspetor():
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    inspetor = _inspetor()

    for nome, tabela, coluna in INDICES:
        if nome not in {i["name"] for i in inspetor.get_indexes(tabela)}:
            op.create_index(nome, tabela, [coluna])

    if op.get_bind().dialect.name != "postgresql":
        return

    for tabela, coluna, referida, ao_excluir in CHAVES:
        existentes = {
            tuple(fk["constrained_columns"])
            for fk in inspetor.get_foreign_keys(tabela)
            if fk["referred_table"] == referida
        }
        if (coluna,) not in existentes:
            op.create_foreign_key(f"{tabela}_{coluna}_fkey", tabela, referida, [coluna], ["id"], ondelete=ao_excluir)

    amostra = next(c for c in inspetor.get_columns("biometrias") if c["name"] == "quantidade_amostrada")
    if amostra["nullable"]:
        nulos = op.get_bind().execute(
            sa.text("SELECT COUNT(*) FROM biometrias WHERE quantidade_amostrada IS NULL")
        ).scalar()
        if nulos:
            raise RuntimeError(
                f"{nulos} biometria(s) sem quantidade_amostrada. Informe o tamanho real dessas amostras "
                "antes de rodar esta migração (ela não inventa valor)."
            )
        op.alter_column("biometrias", "quantidade_amostrada", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    pass
