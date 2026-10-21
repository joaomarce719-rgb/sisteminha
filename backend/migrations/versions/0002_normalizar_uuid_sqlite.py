"""normaliza UUIDs gravados com hífen no SQLite

O tipo UUID do SQLAlchemy grava no SQLite 32 dígitos hexadecimais sem hífen.
Linhas inseridas por scripts externos ficaram com o formato de 36 caracteres e
não eram encontradas pelo ORM nem satisfaziam as chaves estrangeiras.

Revision ID: 0002
Revises: 0001
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Colunas terminadas em _id que guardam texto livre, não UUID
_NAO_UUID = {("logs_auditoria", "registro_id")}


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return
    # Pais e filhos são atualizados em sequência: a checagem de FK fica para o commit
    op.execute("PRAGMA defer_foreign_keys = ON")
    inspetor = sa.inspect(bind)
    for tabela in inspetor.get_table_names():
        if tabela == "alembic_version":
            continue
        for coluna in inspetor.get_columns(tabela):
            nome = coluna["name"]
            if (nome == "id" or nome.endswith("_id")) and (tabela, nome) not in _NAO_UUID:
                op.execute(
                    f'UPDATE "{tabela}" SET "{nome}" = REPLACE("{nome}", \'-\', \'\') '
                    f'WHERE length("{nome}") = 36'
                )


def downgrade() -> None:
    # Normalização de dados irreversível (e sem efeito fora do SQLite)
    pass
