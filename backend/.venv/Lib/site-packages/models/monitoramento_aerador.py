"""SAD Carcinicultura — Modelo de Monitoramento de Aeradores."""

import uuid

from sqlalchemy import Boolean, Integer, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import AuditMixin
from src.models.enums import StatusEnergia


class MonitoramentoAerador(AuditMixin, Base):
    """Registro do estado dos aeradores durante uma ronda noturna."""

    __tablename__ = "monitoramento_aeradores"

    ronda_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rondas_noturnas.id", ondelete="CASCADE"),
        nullable=False,
    )
    viveiro_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("viveiros.id"),
        nullable=False,
    )
    aeradores_instalados: Mapped[int] = mapped_column(Integer, nullable=False)
    aeradores_ligados: Mapped[int] = mapped_column(Integer, nullable=False)
    fonte_energia: Mapped[StatusEnergia] = mapped_column(
        SAEnum(StatusEnergia, name="status_energia", create_constraint=True),
        nullable=False,
        default=StatusEnergia.REDE_CONCESSIONARIA,
    )
    falha_mecanica_detectada: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    detalhes_falha: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relacionamentos
    ronda = relationship("RondaNoturna", back_populates="monitoramento_aeradores")
    viveiro = relationship("Viveiro", lazy="selectin")
