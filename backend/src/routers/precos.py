"""SAD Carcinicultura — Rotas de Tabela de Preços de Mercado (RF-07)."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.escopo import org_do_usuario
from src.services.audit import registrar_auditoria, snapshot
from src.models.enums import RoleUsuario
from src.models.tabela_preco import TabelaPrecoMercado
from src.schemas.preco import PrecoCreate, PrecoResponse, PrecoUpdate
from src.services.auth_service import has_role

router = APIRouter(prefix="/api/v1/precos-mercado", tags=["Preços de Mercado"])


@router.post("", response_model=PrecoResponse, status_code=201)
@router.post("/", response_model=PrecoResponse, status_code=201)
def criar_faixa_preco(
    payload: PrecoCreate,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Cria nova faixa de preço por gramatura (RF-07, somente GESTOR)."""
    if payload.faixa_gramatura_min >= payload.faixa_gramatura_max:
        raise HTTPException(
            status_code=400,
            detail="faixa_gramatura_min deve ser menor que faixa_gramatura_max.",
        )

    preco = TabelaPrecoMercado(**payload.model_dump(), organizacao_id=org_do_usuario(_user))
    db.add(preco)
    db.flush()
    db.refresh(preco)
    registrar_auditoria(db, "CRIAR", "TabelaPrecoMercado", preco.id, _user, dados_novos=snapshot(preco))
    return preco


@router.get("", response_model=list[PrecoResponse])
@router.get("/", response_model=list[PrecoResponse])
def listar_precos(
    vigentes: bool = True,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Lista faixas de preço (somente GESTOR — RN-11)."""
    query = (
        select(TabelaPrecoMercado)
        .where(TabelaPrecoMercado.organizacao_id == org_do_usuario(_user))
        .order_by(TabelaPrecoMercado.faixa_gramatura_min)
    )
    if vigentes:
        hoje = date.today()
        query = query.where(
            TabelaPrecoMercado.vigencia_inicio <= hoje,
            (TabelaPrecoMercado.vigencia_fim.is_(None))
            | (TabelaPrecoMercado.vigencia_fim >= hoje),
        )
    result = db.execute(query)
    return result.scalars().all()


@router.put("/{preco_id}", response_model=PrecoResponse)
def atualizar_preco(
    preco_id: UUID,
    payload: PrecoUpdate,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Atualiza preço ou vigência de uma faixa."""
    result = db.execute(
        select(TabelaPrecoMercado).where(TabelaPrecoMercado.id == preco_id)
    )
    preco = result.scalar_one_or_none()
    if not preco or preco.organizacao_id != org_do_usuario(_user):
        raise HTTPException(status_code=404, detail="Faixa de preço não encontrada.")

    antes = snapshot(preco)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(preco, field, value)

    db.add(preco)
    db.flush()
    db.refresh(preco)
    registrar_auditoria(db, "ATUALIZAR", "TabelaPrecoMercado", preco.id, _user, antes, snapshot(preco))
    return preco
