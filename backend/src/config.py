"""SAD Carcinicultura — Configuração centralizada via Pydantic Settings."""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações globais carregadas de variáveis de ambiente / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Banco de dados ───────────────────────────────
    # Credenciais reais ficam somente no .env (nunca no código).
    database_url: str = "sqlite:///./local_dev.db"
    database_url_sync: str = "sqlite:///./local_dev.db"
    # Usa local_dev.db se o banco remoto estiver inacessível (somente desenvolvimento).
    db_fallback_sqlite: bool = False

    # ── JWT ──────────────────────────────────────────
    jwt_secret_key: str = "TROQUE-POR-UMA-CHAVE-SEGURA-DE-64-CARACTERES"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480

    # ── App ──────────────────────────────────────────
    app_title: str = "SAD Carcinicultura"
    app_version: str = "4.0.0"
    app_debug: bool = True
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
