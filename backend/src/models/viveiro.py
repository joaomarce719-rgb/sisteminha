import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import AuditMixin


class Viveiro(AuditMixin, Base):
    """Viveiro escavado da propriedade, unidade física de cultivo."""

    __tablename__ = "viveiros"
    __table_args__ = (
        UniqueConstraint("organizacao_id", "identificacao", name="uq_viveiros_organizacao_identificacao"),
    )

    organizacao_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizacoes.id"),
        nullable=False,
        index=True,
    )
    propriedade_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("propriedades.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    identificacao: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    area_util_m2: Mapped[float] = mapped_column(Float, nullable=False)
    profundidade_media_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    localizacao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status_ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relacionamentos
    propriedade = relationship("Propriedade", back_populates="viveiros")
    ciclos = relationship("CicloProdutivo", back_populates="viveiro", cascade="all, delete-orphan")
