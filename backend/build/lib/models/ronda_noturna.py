"""SAD Carcinicultura — Modelo de Ronda Noturna."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import AuditMixin
from src.models.enums import ComportamentoCamarao


class RondaNoturna(AuditMixin, Base):
    """Registro de ronda noturna feita pelo vigia com parâmetros de qualidade da água."""

    __tablename__ = "rondas_noturnas"

    ciclo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ciclos_produtivos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vigia_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id"),
        nullable=False,
    )
    data_hora_ronda: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    oxigenio_dissolvido_mg_l: Mapped[float] = mapped_column(
        Numeric(4, 2), nullable=False
    )
    temperatura_agua_c: Mapped[float] = mapped_column(
        Numeric(4, 2), nullable=False
    )
    comportamento: Mapped[ComportamentoCamarao] = mapped_column(
        SAEnum(ComportamentoCamarao, name="comportamento_camarao", create_constraint=True),
        nullable=False,
        default=ComportamentoCamarao.NORMAL_FUNDO,
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relacionamentos
    ciclo = relationship("CicloProdutivo", back_populates="rondas_noturnas")
    vigia = relationship("Usuario", lazy="selectin")
    monitoramento_aeradores = relationship(
        "MonitoramentoAerador", back_populates="ronda", lazy="selectin"
    )
