"""SAD Carcinicultura — Modelo de Tabela Alimentar Parametrizável e Versionada (RF-010, Critério 5)."""

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from src.database import Base
from src.models.base import AuditMixin


class TabelaAlimentar(AuditMixin, Base):
    """Tabela de arraçoamento paramétrica e versionada para cálculo de ração diária."""

    __tablename__ = "tabelas_alimentares"

    # NULL = tabela de referência global (ex.: Clifford 1992), somente leitura
    organizacao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizacoes.id"),
        nullable=True,
        index=True,
    )
    nome: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    versao: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_padrao: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    
    # Lista de pontos de calibração: [{"peso_g": float, "taxa_pct": float}]
    faixas: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
