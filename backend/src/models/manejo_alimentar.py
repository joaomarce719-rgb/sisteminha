"""SAD Carcinicultura — Modelo de Manejo Alimentar."""

import uuid
from datetime import date

from sqlalchemy import Date, Float
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import AuditMixin
from src.models.enums import NivelSobraBandeja, StatusAlimentar


class ManejoAlimentar(AuditMixin, Base):
    """Registro diário de arraçoamento e verificação de bandejas."""

    __tablename__ = "manejos_alimentares"

    ciclo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ciclos_produtivos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_registro: Mapped[date] = mapped_column(Date, nullable=False)
    quantidade_racao_kg: Mapped[float] = mapped_column(Float, nullable=False)
    taxa_alimentar_calculada_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    sobra_bandeja_nivel: Mapped[NivelSobraBandeja] = mapped_column(
        SAEnum(NivelSobraBandeja, name="nivel_sobra_bandeja", create_constraint=True),
        nullable=False,
        default=NivelSobraBandeja.SEM_SOBRA,
    )
    status_alimentar_ajustado: Mapped[StatusAlimentar | None] = mapped_column(
        SAEnum(StatusAlimentar, name="status_alimentar", create_constraint=True),
        nullable=True,
    )
    taxa_sobrevivencia_estimada_fuzzy: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    # Relacionamento
    ciclo = relationship("CicloProdutivo", back_populates="manejos_alimentares")
