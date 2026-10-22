"""SAD Carcinicultura — Regras de consistência compartilhadas pelos registros de um ciclo."""

from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.ciclo_produtivo import CicloProdutivo
from src.models.enums import StatusCiclo

# Um viveiro só pode ter um ciclo nestes estados ao mesmo tempo
STATUS_CICLO_ABERTO = (StatusCiclo.ATIVO, StatusCiclo.PAUSADO)


def obter_ciclo(db: Session, ciclo_id: UUID) -> CicloProdutivo:
    ciclo = db.get(CicloProdutivo, ciclo_id)
    if not ciclo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ciclo não encontrado.")
    return ciclo


def ciclo_aberto_do_viveiro(
    db: Session, viveiro_id: UUID, exceto_id: UUID | None = None
) -> CicloProdutivo | None:
    query = select(CicloProdutivo).where(
        CicloProdutivo.viveiro_id == viveiro_id,
        CicloProdutivo.status.in_(STATUS_CICLO_ABERTO),
    )
    if exceto_id is not None:
        query = query.where(CicloProdutivo.id != exceto_id)
    return db.scalars(query.limit(1)).first()


def validar_data_no_ciclo(ciclo: CicloProdutivo, data_registro: date, rotulo: str) -> None:
    """Rejeita datas anteriores ao povoamento ou no futuro (RNF-008)."""
    if data_registro < ciclo.data_povoamento:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{rotulo} não pode ser anterior ao povoamento ({ciclo.data_povoamento:%d/%m/%Y}).",
        )
    if data_registro > date.today():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{rotulo} não pode estar no futuro.",
        )
