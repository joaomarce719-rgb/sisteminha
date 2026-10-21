"""SAD Carcinicultura — Isolamento de dados por organização (RF-002, RN-001, RNF-005).

Todo dado operacional pertence a uma organização através do viveiro
(Viveiro.organizacao_id). Recursos de outra organização respondem 404, para não
revelar sua existência.
"""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.ciclo_produtivo import CicloProdutivo
from src.models.usuario import Usuario
from src.models.viveiro import Viveiro
from src.services.auth_service import get_current_user


def org_do_usuario(user: Usuario) -> UUID:
    if user.organizacao_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta sem organização vinculada. Solicite o vínculo a um gestor.",
        )
    return user.organizacao_id


def viveiro_da_organizacao(db: Session, viveiro_id: UUID, user: Usuario) -> Viveiro:
    viveiro = db.get(Viveiro, viveiro_id)
    if not viveiro or viveiro.organizacao_id != org_do_usuario(user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Viveiro não encontrado.")
    return viveiro


def ciclo_da_organizacao(db: Session, ciclo_id: UUID, user: Usuario) -> CicloProdutivo:
    ciclo = db.get(CicloProdutivo, ciclo_id)
    if not ciclo or ciclo.viveiro.organizacao_id != org_do_usuario(user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ciclo não encontrado.")
    return ciclo


def ids_ciclos_da_organizacao(user: Usuario) -> Select:
    """Subconsulta com os IDs de ciclos da organização do usuário (para filtros IN)."""
    return (
        select(CicloProdutivo.id)
        .join(Viveiro, CicloProdutivo.viveiro_id == Viveiro.id)
        .where(Viveiro.organizacao_id == org_do_usuario(user))
    )


def verificar_ciclo_da_organizacao(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> None:
    """Dependência para rotas sob /ciclos/{ciclo_id}: 404 se o ciclo for de outra organização."""
    ciclo_da_organizacao(db, ciclo_id, user)
