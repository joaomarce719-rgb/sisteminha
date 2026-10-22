"""SAD Carcinicultura — Modelo de Alerta de Manejo (RF-021)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import AuditMixin
from src.models.enums import NivelAlerta, StatusAlerta


class Alerta(AuditMixin, Base):
    """Alerta gerado por regra (ex.: O₂ crítico na ronda), com status de tratamento."""

    __tablename__ = "alertas"

    ciclo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ciclos_produtivos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    viveiro_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("viveiros.id"), nullable=False
    )
    ronda_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rondas_noturnas.id", ondelete="CASCADE"),
        nullable=True,
    )
    nivel: Mapped[NivelAlerta] = mapped_column(
        SAEnum(NivelAlerta, name="nivel_alerta", create_constraint=True), nullable=False
    )
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    titulo: Mapped[str] = mapped_column(String(120), nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[StatusAlerta] = mapped_column(
        SAEnum(StatusAlerta, name="status_alerta", create_constraint=True),
        nullable=False,
        default=StatusAlerta.ABERTO,
        index=True,
    )
    resolvido_por_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    resolvido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observacao_resolucao: Mapped[str | None] = mapped_column(Text, nullable=True)

    ciclo = relationship("CicloProdutivo", back_populates="alertas")
    viveiro = relationship("Viveiro", lazy="selectin")
