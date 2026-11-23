"""SAD Carcinicultura — Modelo de etapa do preparo do viveiro antes do povoamento."""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import AuditMixin


class EtapaPreparo(AuditMixin, Base):
    """Etapa do preparo (secagem, calagem...); o povoamento exige todas concluídas ou não realizadas."""

    __tablename__ = "etapas_preparo"

    ciclo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ciclos_produtivos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # tipo e status são texto validado no schema (não enum nativo)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    data_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(14), nullable=False, default="PENDENTE", server_default="PENDENTE")
    observacao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)

    ciclo = relationship("CicloProdutivo", back_populates="etapas_preparo")
