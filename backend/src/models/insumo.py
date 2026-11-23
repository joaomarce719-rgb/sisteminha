"""SAD Carcinicultura — Modelos de Insumo, compras e usos (custo médio ponderado)."""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, false
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.base import AuditMixin


class Insumo(AuditMixin, Base):
    """Produto usado no cultivo (cal, probiótico, adubo...), cadastrado por organização."""

    __tablename__ = "insumos"
    __table_args__ = (UniqueConstraint("organizacao_id", "nome_chave", name="uq_insumos_organizacao_nome_chave"),)

    organizacao_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizacoes.id"), nullable=False, index=True
    )
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    # nome sem diferenciar maiúsculas/acentos, para a unicidade por organização
    nome_chave: Mapped[str] = mapped_column(String(120), nullable=False)
    unidade_uso: Mapped[str] = mapped_column(String(20), nullable=False)
    # valor de CategoriaCusto (menos RACAO e POS_LARVAS), validado no schema
    categoria: Mapped[str] = mapped_column(String(30), nullable=False, default="OUTROS", server_default="OUTROS")
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CompraInsumo(AuditMixin, Base):
    """Compra de um insumo: quantidade e valor total que alimentam o preço médio."""

    __tablename__ = "compras_insumo"

    insumo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("insumos.id"), nullable=False, index=True
    )
    data_compra: Mapped[date] = mapped_column(Date, nullable=False)
    quantidade: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    valor_total_rs: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    fornecedor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    observacao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retroativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())


class ConsumoInsumo(AuditMixin, Base):
    """Uso de um insumo num ciclo; o custo gerado fica em CustoOperacional (`custo_id`)."""

    __tablename__ = "consumos_insumo"

    ciclo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ciclos_produtivos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    insumo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("insumos.id"), nullable=False, index=True
    )
    data_uso: Mapped[date] = mapped_column(Date, nullable=False)
    quantidade: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    fase: Mapped[str] = mapped_column(String(10), nullable=False, default="CULTIVO", server_default="CULTIVO")
    custo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("custos_operacionais.id", ondelete="SET NULL"), nullable=True, index=True
    )
    etapa_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("etapas_preparo.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # R$ por unidade de uso aplicado no momento do registro; nulo = pendente de valor
    preco_unitario_rs: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # preço após o recálculo por compra retroativa
    preco_corrigido_rs: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    registrado_por: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True
    )
    observacao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retroativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    recalculado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
