"""SAD Carcinicultura — Modelo de Biometria."""

import uuid
from datetime import date

from sqlalchemy import Date, Float, Text
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import AuditMixin


class Biometria(AuditMixin, Base):
    """Registro de amostragem biométrica de peso médio do lote."""

    __tablename__ = "biometrias"

    ciclo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ciclos_produtivos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_medicao: Mapped[date] = mapped_column(Date, nullable=False)
    peso_medio_g: Mapped[float] = mapped_column(Float, nullable=False)
    ganho_medio_semanal_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    uniformidade_percentual: Mapped[float | None] = mapped_column(Float, nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relacionamento
    ciclo = relationship("CicloProdutivo", back_populates="biometrias")
