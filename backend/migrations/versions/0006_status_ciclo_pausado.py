"""valor PAUSADO no tipo status_ciclo do Postgres

Bancos criados antes do Alembic têm o tipo enumerado status_ciclo sem o valor
PAUSADO, que o código usa (consulta "um ciclo aberto por viveiro", pausar e
retomar ciclo). Sem ele, criar ou pausar um ciclo falha com
"invalid input value for enum status_ciclo". Bancos criados pela revisão 0001
já têm o valor, e o IF NOT EXISTS torna a operação segura nos dois casos.

No SQLite não há tipo enumerado nativo (a coluna é texto com CHECK gerado dos
modelos), então não há o que fazer. O Postgres não remove valor de enum, por
isso o downgrade é vazio; manter um valor a mais é inofensivo.

Revision ID: 0006
Revises: 0005
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    # ADD VALUE não pode rodar dentro da transação da migração em todas as versões do Postgres
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE status_ciclo ADD VALUE IF NOT EXISTS 'PAUSADO'")


def downgrade() -> None:
    pass
