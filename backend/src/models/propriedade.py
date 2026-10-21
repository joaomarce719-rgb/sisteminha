"""SAD Carcinicultura — Modelo de Propriedade / Fazenda (RF-002, RF-003, RN-001)."""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import AuditMixin


class Propriedade(AuditMixin, Base):
    """Propriedade rural ou fazenda onde estão situados os viveiros."""

    __tablename__ = "propriedades"

    organizacao_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizacoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    localizacao: Mapped[str | None] = mapped_column(String(255), nullable=True)  # ex: Município, UF
    area_total_ha: Mapped[float | None] = mapped_column(Float, nullable=True)
    status_ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relacionamentos
    organizacao = relationship("Organizacao", back_populates="propriedades", lazy="selectin")
    viveiros = relationship("Viveiro", back_populates="propriedade", lazy="selectin")
