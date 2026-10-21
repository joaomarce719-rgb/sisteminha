"""Ambiente do Alembic: usa o engine e o metadata da aplicação.

A URL do banco vem de DATABASE_URL (src.config), a mesma usada pela API.
`render_as_batch` permite ALTER TABLE no SQLite (recria a tabela por baixo).
"""

from logging.config import fileConfig

from alembic import context

import src.models  # noqa: F401  (registra todos os modelos no metadata)
from src.database import Base, engine

config = context.config

if config.config_file_name is not None and config.attributes.get("configurar_logging", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Gera o SQL sem conectar ao banco (`alembic upgrade head --sql`)."""
    context.configure(
        url=str(engine.url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=engine.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    conexao = config.attributes.get("connection")
    if conexao is not None:
        _executar(conexao)
        return
    with engine.connect() as connection:
        _executar(connection)


def _executar(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite",
        # No SQLite o UUID é refletido como NUMERIC: comparar tipos gera falsos positivos
        compare_type=connection.dialect.name != "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
