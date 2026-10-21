import logging
import sqlite3
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from src.config import get_settings

logger = logging.getLogger("uvicorn.error")
settings = get_settings()

def get_engine():
    db_url = settings.database_url
    if db_url.startswith("sqlite"):
        return create_engine(
            db_url,
            echo=settings.app_debug,
            connect_args={"check_same_thread": False, "timeout": 60},
        )
    try:
        eng = create_engine(
            db_url,
            echo=settings.app_debug,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            connect_args={"timeout": 15} if "pg8000" in db_url else {},
        )
        with eng.connect() as conn:
            pass
        return eng
    except Exception as e:
        logger.warning(
            f"Aviso: Conexão remota falhou ({e}). Utilizando SQLite local (local_dev.db) para testes/desenvolvimento."
        )
        return create_engine(
            "sqlite:///./local_dev.db",
            echo=settings.app_debug,
            connect_args={"check_same_thread": False, "timeout": 60},
        )

engine = get_engine()

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=60000")
        cursor.close()

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
    """Cria tabelas e garante a existência dos usuários e dados essenciais."""
    Base.metadata.create_all(bind=engine)
    
    # Importações postergadas para evitar importação circular
    from datetime import date
    from sqlalchemy import select, func
    from src.models.enums import RoleUsuario
    from src.models.usuario import Usuario
    from src.models.organizacao import Organizacao
    from src.models.propriedade import Propriedade
    from src.models.viveiro import Viveiro
    from src.models.tabela_preco import TabelaPrecoMercado
    from src.services.auth_service import hash_password

    with SessionLocal() as db:
        try:
            # 1. Organização e Fazenda Padrão
            org = db.scalars(select(Organizacao)).first()
            if not org:
                org = Organizacao(
                    nome="Grupo SAD Carcinicultura",
                    identificador="SAD-MATRIZ",
                    status_ativo=True,
                )
                db.add(org)
                db.flush()

            prop = db.scalars(select(Propriedade)).first()
            if not prop:
                prop = Propriedade(
                    organizacao_id=org.id,
                    nome="Fazenda Principal",
                    localizacao="Litoral Potiguar - RN",
                    area_total_ha=50.0,
                    status_ativo=True,
                )
                db.add(prop)
                db.flush()

            # 2. Usuários Essenciais do Sistema
            usuarios_base = [
                ("admin@sad.com", "Administrador Central", RoleUsuario.GESTOR),
                ("gestor@sad.com", "Gestor da Fazenda", RoleUsuario.GESTOR),
                ("testedoapp1@gmail.com", "Administrador da Equipe", RoleUsuario.GESTOR),
                ("campo@sad.com", "Operador de Campo", RoleUsuario.CAMPO),
                ("vigia@sad.com", "Vigia Noturno", RoleUsuario.VIGIA),
            ]

            senha_padrao_hash = hash_password("senha123")
            for email, nome, papel in usuarios_base:
                user = db.scalars(select(Usuario).where(func.lower(Usuario.email) == email.lower())).first()
                if not user:
                    user = Usuario(
                        organizacao_id=org.id,
                        nome_completo=nome,
                        email=email.lower(),
                        senha_hash=senha_padrao_hash,
                        papel=papel,
                        ativo=True,
                    )
                    db.add(user)
                else:
                    user.senha_hash = senha_padrao_hash
                    user.ativo = True
                    user.papel = papel
                    db.add(user)

            # 3. Viveiros (Apenas os criados pelo usuário)

            # 4. Tabela de Preços
            preco = db.scalars(select(TabelaPrecoMercado)).first()
            if not preco:
                db.add_all([
                    TabelaPrecoMercado(faixa_gramatura_min=8.0, faixa_gramatura_max=10.0, preco_por_kg=18.50, vigencia_inicio=date.today()),
                    TabelaPrecoMercado(faixa_gramatura_min=10.0, faixa_gramatura_max=12.0, preco_por_kg=21.00, vigencia_inicio=date.today()),
                    TabelaPrecoMercado(faixa_gramatura_min=12.0, faixa_gramatura_max=14.0, preco_por_kg=24.50, vigencia_inicio=date.today()),
                    TabelaPrecoMercado(faixa_gramatura_min=14.0, faixa_gramatura_max=16.0, preco_por_kg=28.00, vigencia_inicio=date.today()),
                    TabelaPrecoMercado(faixa_gramatura_min=16.0, faixa_gramatura_max=20.0, preco_por_kg=32.00, vigencia_inicio=date.today()),
                ])

            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao inicializar dados essenciais no banco: {e}")

