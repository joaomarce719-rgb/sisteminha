"""SAD Carcinicultura — Modelo de Ciclo Produtivo."""

import uuid
from datetime import date

from sqlalchemy import Date, Float, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import AuditMixin
from src.models.enums import StatusCiclo


class CicloProdutivo(AuditMixin, Base):
    """Ciclo de produção de um lote de L. vannamei em um viveiro."""

    __tablename__ = "ciclos_produtivos"

    viveiro_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("viveiros.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_povoamento: Mapped[date] = mapped_column(Date, nullable=False)
    quantidade_pos_larvas: Mapped[int] = mapped_column(Integer, nullable=False)
    custo_aquisicao_pl: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    laboratorio_origem: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[StatusCiclo] = mapped_column(
        SAEnum(StatusCiclo, name="status_ciclo", create_constraint=True),
        nullable=False,
        default=StatusCiclo.PLANEJADO,
    )
    data_despesca_real: Mapped[date | None] = mapped_column(Date, nullable=True)
    biomassa_colhida_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    receita_real_rs: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    tabela_alimentar_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tabelas_alimentares.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relacionamentos
    tabela_alimentar = relationship("TabelaAlimentar", lazy="selectin")
    viveiro = relationship("Viveiro", back_populates="ciclos", lazy="selectin")
    biometrias = relationship(
        "Biometria", back_populates="ciclo", lazy="selectin",
        order_by="Biometria.data_medicao",
        cascade="all, delete-orphan",
    )
    manejos_alimentares = relationship(
        "ManejoAlimentar", back_populates="ciclo", lazy="selectin",
        order_by="ManejoAlimentar.data_registro",
        cascade="all, delete-orphan",
    )
    custos_operacionais = relationship(
        "CustoOperacional", back_populates="ciclo", lazy="selectin",
        cascade="all, delete-orphan",
    )
    simulacoes = relationship(
        "SimulacaoDespesca", back_populates="ciclo", lazy="selectin",
        cascade="all, delete-orphan",
    )
    rondas_noturnas = relationship(
        "RondaNoturna", back_populates="ciclo", lazy="selectin"
    )
