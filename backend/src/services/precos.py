"""Tabela de preços de mercado vigente, lida da mesma forma por métricas e simulação."""

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.tabela_preco import TabelaPrecoMercado


def tabela_vigente(db: Session, organizacao_id: UUID, hoje: date) -> list[dict]:
    """Faixas de preço da organização vigentes em `hoje`, no formato de `buscar_preco_por_gramatura`."""
    faixas = db.execute(
        select(TabelaPrecoMercado).where(
            TabelaPrecoMercado.organizacao_id == organizacao_id,
            TabelaPrecoMercado.vigencia_inicio <= hoje,
            (TabelaPrecoMercado.vigencia_fim.is_(None)) | (TabelaPrecoMercado.vigencia_fim >= hoje),
        )
    ).scalars().all()
    return [
        {
            "faixa_gramatura_min": f.faixa_gramatura_min,
            "faixa_gramatura_max": f.faixa_gramatura_max,
            "preco_por_kg": float(f.preco_por_kg),
            "vigencia_inicio": f.vigencia_inicio,
        }
        for f in faixas
    ]
