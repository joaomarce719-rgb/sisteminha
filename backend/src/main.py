"""SAD Carcinicultura — Ponto de entrada da aplicação FastAPI.

Registra todos os routers, configura CORS, e expõe a documentação
Swagger/OpenAPI em /docs e /redoc (RNF-06).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.database import init_db

# Importar modelos para que o metadata os registre
import src.models  # noqa: F401

from src.routers import (
    admin,
    auth,
    biometrias,
    ciclos,
    custos,
    manejos,
    precos,
    rondas,
    simulacao,
    viveiros,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle: cria tabelas no startup (dev)."""
    if settings.app_debug:
        await init_db()
    yield


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=(
        "Sistema de Apoio à Decisão Bioeconômico para Carcinicultura "
        "(Litopenaeus vannamei) — API REST com motor de inferência fuzzy "
        "e algoritmo preditivo ΔV para decisão de despesca."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────
app.include_router(auth.router)
app.include_router(viveiros.router)
app.include_router(ciclos.router)
app.include_router(biometrias.router)
app.include_router(manejos.router)
app.include_router(custos.router)
app.include_router(precos.router)
app.include_router(simulacao.router)
app.include_router(rondas.router)
app.include_router(admin.router)


@app.get("/", tags=["Health"])
async def health_check():
    """Endpoint de verificação de saúde da API."""
    return {
        "status": "online",
        "sistema": "SAD Carcinicultura",
        "versao": settings.app_version,
    }
