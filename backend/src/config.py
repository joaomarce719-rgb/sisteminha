"""SAD Carcinicultura — Configuração centralizada via Pydantic Settings."""

from functools import lru_cache
from typing import List, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_JWT_PLACEHOLDER = "TROQUE-POR-UMA-CHAVE-SEGURA-DE-64-CARACTERES"


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
    jwt_secret_key: str = _JWT_PLACEHOLDER
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480

    # ── App ──────────────────────────────────────────
    app_title: str = "SAD Carcinicultura"
    app_version: str = "4.0.0"
    app_debug: bool = True
    # Loga todo SQL com parâmetros (inclui hashes e e-mails) — manter desligado fora de depuração.
    db_echo: bool = False
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ── Governança ───────────────────────────────────
    # E-mails (separados por vírgula) com acesso ao painel de Administração Central.
    superadmin_emails: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def superadmin_emails_set(self) -> set[str]:
        return {e.strip().lower() for e in self.superadmin_emails.split(",") if e.strip()}

    @model_validator(mode="after")
    def _exigir_segredo_em_producao(self) -> "Settings":
        if not self.app_debug and self.jwt_secret_key == _JWT_PLACEHOLDER:
            raise ValueError("Defina JWT_SECRET_KEY no .env antes de rodar com APP_DEBUG=false.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
