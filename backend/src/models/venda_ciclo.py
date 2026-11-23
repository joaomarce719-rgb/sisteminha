"""SAD Carcinicultura — Modelo de venda do ciclo (desbaste ou despesca final)."""

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, false
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import AuditMixin


class VendaCiclo(AuditMixin, Base):
    """Camarão vendido de um ciclo; a soma das vendas é a receita realizada e retira animais da água."""

    __tablename__ = "vendas"

    ciclo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ciclos_produtivos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # `date` (não datetime): o filtro da população compara com datas
    data_venda: Mapped[date] = mapped_column(Date, nullable=False)
    # DESBASTE ou DESPESCA_FINAL, validado no schema
    tipo: Mapped[str] = mapped_column(String(14), nullable=False)
    biomassa_kg: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    peso_medio_g: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    # biomassa × 1000 ÷ peso médio, arredondado
    animais_estimados: Mapped[int] = mapped_column(Integer, nullable=False)
    preco_kg: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    # biomassa × preço por kg
    valor_total_rs: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    comprador: Mapped[str | None] = mapped_column(String(120), nullable=True)
    observacao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retroativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())

    ciclo = relationship("CicloProdutivo", back_populates="vendas")
