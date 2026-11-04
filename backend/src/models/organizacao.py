"""SAD Carcinicultura — Modelo de Organização (RF-002, RF-003, RN-001)."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import AuditMixin


class Organizacao(AuditMixin, Base):
    """Entidade jurídica ou grupo produtor multi-tenant."""

    __tablename__ = "organizacoes"

    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    identificador: Mapped[str | None] = mapped_column(String(30), unique=True, nullable=True)  # CNPJ ou código
    moeda: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    status_ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Acordo de gramatura com o comprador: PARA_BAIXO, PARA_CIMA ou PROPORCIONAL (texto, não enum nativo)
    regra_arredondamento: Mapped[str] = mapped_column(
        String(12), nullable=False, default="PARA_BAIXO", server_default="PARA_BAIXO"
    )

    # Relacionamentos
    propriedades = relationship("Propriedade", back_populates="organizacao")
    usuarios = relationship("Usuario", back_populates="organizacao")
