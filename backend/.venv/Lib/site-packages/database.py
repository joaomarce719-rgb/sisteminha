"""SAD Carcinicultura — Conexão síncrona com o PostgreSQL."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from src.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=settings.app_debug,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    """Classe base para todos os modelos SQLAlchemy."""
    pass

def get_db():
    """Dependency injection para obter sessão do banco."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db() -> None:
    """Cria as tabelas no banco (apenas para desenvolvimento)."""
    Base.metadata.create_all(bind=engine)
