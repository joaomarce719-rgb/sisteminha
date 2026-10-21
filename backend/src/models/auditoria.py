"""SAD Carcinicultura — Modelo de Log de Auditoria (RF-027, RNF-017, Critério 10)."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.database import Base


class LogAuditoria(Base):
    """Trilha de auditoria persistente com registro do estado antes e depois das operações."""

    __tablename__ = "logs_auditoria"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    organizacao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    usuario_nome: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )
    acao: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # CRIAR, EDITAR, EXCLUIR, ENCERRAR_CICLO
    entidade: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        index=True,
    )  # CicloProdutivo, CustoOperacional, TabelaAlimentar, etc.
    registro_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    dados_anteriores: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    dados_novos: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    ip_origem: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        index=True,
    )
