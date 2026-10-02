"""SAD Carcinicultura — Modelo de Custo Operacional."""

import uuid
from datetime import date

from sqlalchemy import Date, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import AuditMixin
from src.models.enums import CategoriaCusto


class CustoOperacional(AuditMixin, Base):
    """Lançamento de despesa operacional vinculada a um ciclo produtivo."""

    __tablename__ = "custos_operacionais"

    ciclo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ciclos_produtivos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data_lancamento: Mapped[date] = mapped_column(Date, nullable=False)
    categoria: Mapped[CategoriaCusto] = mapped_column(
        SAEnum(CategoriaCusto, name="categoria_custo", create_constraint=True),
        nullable=False,
    )
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    valor_rs: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    # Relacionamento
    ciclo = relationship("CicloProdutivo", back_populates="custos_operacionais")
