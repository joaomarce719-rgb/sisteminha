"""SAD Carcinicultura — Configuração centralizada via Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações globais carregadas de variáveis de ambiente / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── PostgreSQL ──────────────────────────────────
    database_url: str = "postgresql+asyncpg://sad_user:sad_pass@localhost:5432/sad_carcinicultura"
    database_url_sync: str = "postgresql://sad_user:sad_pass@localhost:5432/sad_carcinicultura"

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
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
