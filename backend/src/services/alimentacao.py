"""Tabela alimentar usada no confronto da ração real com a ração esperada."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.ciclo_produtivo import CicloProdutivo
from src.models.tabela_alimentar import TabelaAlimentar


def pontos_alimentares(ciclo: CicloProdutivo, db: Session) -> list[tuple[float, float]] | None:
    """Pontos (peso_g, taxa_pct) da tabela do ciclo ou da tabela padrão; None usa a de Clifford."""
    if ciclo.tabela_alimentar and ciclo.tabela_alimentar.faixas:
        return [(float(f["peso_g"]), float(f["taxa_pct"])) for f in ciclo.tabela_alimentar.faixas]
    org_id = ciclo.viveiro.organizacao_id
    padrao = db.scalar(
        select(TabelaAlimentar)
        .where(
            TabelaAlimentar.is_padrao.is_(True),
            TabelaAlimentar.ativo.is_(True),
            (TabelaAlimentar.organizacao_id == org_id) | TabelaAlimentar.organizacao_id.is_(None),
        )
        # A padrão da organização tem precedência sobre a referência global
        .order_by(TabelaAlimentar.organizacao_id.is_(None))
        .limit(1)
    )
    if padrao and padrao.faixas:
        return [(float(f["peso_g"]), float(f["taxa_pct"])) for f in padrao.faixas]
    return None
