import os
import glob
import re

# 1. Update pyproject.toml
toml_path = "c:/Users/jm_montmaia/Desktop/sisteminha/backend/pyproject.toml"
with open(toml_path, 'r', encoding='utf-8') as f:
    toml = f.read()
toml = toml.replace('"sqlalchemy[asyncio]>=2.0.35",', '"sqlalchemy>=2.0.35",')
toml = toml.replace('"asyncpg>=0.30.0",', '"pg8000>=1.31.2",')
with open(toml_path, 'w', encoding='utf-8') as f:
    f.write(toml)

# 2. Update config.py
config_path = "c:/Users/jm_montmaia/Desktop/sisteminha/backend/src/config.py"
with open(config_path, 'r', encoding='utf-8') as f:
    config = f.read()
config = config.replace('postgresql+asyncpg://', 'postgresql+pg8000://')
config = config.replace('database_url: str = "postgresql+pg8000://sad_user:sad_pass@localhost:5432/sad_carcinicultura"', 'database_url: str = "postgresql+pg8000://postgres.qqctuxmuixvjkniyaclt:dkYSi4oUP3jFUoXM@aws-0-us-west-2.pooler.supabase.com:6543/postgres"')
with open(config_path, 'w', encoding='utf-8') as f:
    f.write(config)

# 3. Update database.py
database_code = """\"\"\"SAD Carcinicultura — Conexão síncrona com o PostgreSQL.\"\"\"

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
    \"\"\"Classe base para todos os modelos SQLAlchemy.\"\"\"
    pass

def get_db():
    \"\"\"Dependency injection para obter sessão do banco.\"\"\"
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
    \"\"\"Cria as tabelas no banco (apenas para desenvolvimento).\"\"\"
    Base.metadata.create_all(bind=engine)
"""
db_path = "c:/Users/jm_montmaia/Desktop/sisteminha/backend/src/database.py"
with open(db_path, 'w', encoding='utf-8') as f:
    f.write(database_code)

# 4. Update main.py
main_path = "c:/Users/jm_montmaia/Desktop/sisteminha/backend/src/main.py"
with open(main_path, 'r', encoding='utf-8') as f:
    main_code = f.read()
main_code = main_code.replace("await init_db()", "init_db()")
with open(main_path, 'w', encoding='utf-8') as f:
    f.write(main_code)

# 5. Update routers and services
for folder in ["routers", "services"]:
    for filepath in glob.glob(f"c:/Users/jm_montmaia/Desktop/sisteminha/backend/src/{folder}/*.py"):
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Imports
        code = code.replace("from sqlalchemy.ext.asyncio import AsyncSession", "from sqlalchemy.orm import Session")
        
        # Type hints
        code = code.replace("db: AsyncSession", "db: Session")
        
        # Awaits
        code = code.replace("await db.execute", "db.execute")
        code = code.replace("await db.flush", "db.flush")
        code = code.replace("await db.refresh", "db.refresh")
        code = code.replace("await db.commit", "db.commit")
        
        code = code.replace("await session.execute", "session.execute")
        code = code.replace("await session.flush", "session.flush")
        code = code.replace("await session.refresh", "session.refresh")
        code = code.replace("await session.commit", "session.commit")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)

print("Conversão concluída!")
