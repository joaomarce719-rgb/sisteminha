"""SAD Carcinicultura — Modelo de Tabela de Preços de Mercado."""

from datetime import date

from sqlalchemy import Date, Float, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.base import AuditMixin


class TabelaPrecoMercado(AuditMixin, Base):
    """Faixa de preço vigente por gramatura do camarão no mercado/frigorífico."""

    __tablename__ = "tabela_precos_mercado"

    faixa_gramatura_min: Mapped[float] = mapped_column(Float, nullable=False)
    faixa_gramatura_max: Mapped[float] = mapped_column(Float, nullable=False)
    preco_por_kg: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    vigencia_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    vigencia_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
