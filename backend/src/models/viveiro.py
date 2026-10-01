"""SAD Carcinicultura — Modelo de Viveiro."""

from sqlalchemy import Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import AuditMixin


class Viveiro(AuditMixin, Base):
    """Viveiro escavado da propriedade, unidade física de cultivo."""

    __tablename__ = "viveiros"

    identificacao: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    area_util_m2: Mapped[float] = mapped_column(Float, nullable=False)
    profundidade_media_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    localizacao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status_ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relacionamentos
    ciclos = relationship("CicloProdutivo", back_populates="viveiro", lazy="selectin")
