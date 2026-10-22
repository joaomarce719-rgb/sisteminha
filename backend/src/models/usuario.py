import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import AuditMixin
from src.models.enums import RoleUsuario


class Usuario(AuditMixin, Base):
    """Usuário do sistema com controle de papel (CAMPO, VIGIA, GESTOR)."""

    __tablename__ = "usuarios"

    organizacao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizacoes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    nome_completo: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    papel: Mapped[RoleUsuario] = mapped_column(
        SAEnum(RoleUsuario, name="role_usuario", create_constraint=True),
        nullable=False,
        default=RoleUsuario.CAMPO,
    )
    telefone_emergencia: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relacionamentos
    organizacao = relationship("Organizacao", back_populates="usuarios")
