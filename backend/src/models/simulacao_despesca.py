"""SAD Carcinicultura — Modelo de Simulação de Despesca."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, Numeric
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import AuditMixin
from src.models.enums import RecomendacaoDespesca


class SimulacaoDespesca(AuditMixin, Base):
    """Resultado de uma simulação do algoritmo Delta V para decisão de despesca."""

    __tablename__ = "simulacoes_despesca"

    ciclo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ciclos_produtivos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_simulacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    dias_projecao: Mapped[int] = mapped_column(Integer, nullable=False)
    peso_medio_projetado_g: Mapped[float] = mapped_column(Float, nullable=False)
    biomassa_projetada_kg: Mapped[float] = mapped_column(Float, nullable=False)
    receita_projetada_rs: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    custo_adicional_projetado_rs: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    lucro_projetado_rs: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    delta_v_rs: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    recomendacao: Mapped[RecomendacaoDespesca] = mapped_column(
        SAEnum(RecomendacaoDespesca, name="recomendacao_despesca", create_constraint=True),
        nullable=False,
    )

    # Relacionamento
    ciclo = relationship("CicloProdutivo", back_populates="simulacoes")
