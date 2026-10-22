"""SAD Carcinicultura — Rotas de Propriedades / Fazendas (RF-002, RF-003, RN-001)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.dependencies import require_gestor, get_current_usuario
from src.models.propriedade import Propriedade
from src.models.usuario import Usuario
from src.schemas.propriedade import (
    PropriedadeCreate,
    PropriedadeResponse,
    PropriedadeUpdate,
)
from src.services.audit import registrar_auditoria
from src.services.auth_service import is_superadmin
from src.services.escopo import org_do_usuario

router = APIRouter(prefix="/api/v1/propriedades", tags=["Propriedades"])


@router.get("", response_model=list[PropriedadeResponse])
@router.get("/", response_model=list[PropriedadeResponse])
def listar_propriedades(
    db: Session = Depends(get_db),
    _user: Usuario = Depends(get_current_usuario),
    organizacao_id: UUID | None = Query(None, description="Filtrar por organização"),
):
    """Lista propriedades rurais cadastradas."""
    query = select(Propriedade).order_by(Propriedade.nome)
    if not is_superadmin(_user):
        query = query.where(Propriedade.organizacao_id == org_do_usuario(_user))
    if organizacao_id:
        query = query.where(Propriedade.organizacao_id == organizacao_id)
    return list(db.scalars(query).all())


def _propriedade_acessivel(db: Session, prop_id: UUID, user: Usuario) -> Propriedade:
    prop = db.get(Propriedade, prop_id)
    if not prop or (prop.organizacao_id != user.organizacao_id and not is_superadmin(user)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Propriedade não encontrada")
    return prop


@router.get("/{prop_id}", response_model=PropriedadeResponse)
def obter_propriedade(
    prop_id: UUID,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(get_current_usuario),
):
    """Obtém detalhes de uma propriedade."""
    prop = _propriedade_acessivel(db, prop_id, _user)
    return prop


@router.post("", response_model=PropriedadeResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=PropriedadeResponse, status_code=status.HTTP_201_CREATED)
def criar_propriedade(
    payload: PropriedadeCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_gestor),
):
    """Cria uma propriedade na organização do GESTOR (superadmin escolhe a organização)."""
    org_id = payload.organizacao_id if is_superadmin(user) else org_do_usuario(user)
    prop = Propriedade(
        organizacao_id=org_id,
        nome=payload.nome,
        localizacao=payload.localizacao,
        area_total_ha=payload.area_total_ha,
        status_ativo=True,
    )
    db.add(prop)
    db.flush()

    registrar_auditoria(
        db=db,
        acao="CRIAR",
        entidade="Propriedade",
        registro_id=prop.id,
        usuario=user,
        dados_novos={
            "organizacao_id": str(prop.organizacao_id),
            "nome": prop.nome,
            "localizacao": prop.localizacao,
            "area_total_ha": prop.area_total_ha,
        },
    )
    db.commit()
    db.refresh(prop)
    return prop


@router.put("/{prop_id}", response_model=PropriedadeResponse)
def atualizar_propriedade(
    prop_id: UUID,
    payload: PropriedadeUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_gestor),
):
    """Atualiza uma propriedade rural (apenas GESTOR)."""
    prop = _propriedade_acessivel(db, prop_id, user)

    dados_ant = {
        "nome": prop.nome,
        "localizacao": prop.localizacao,
        "area_total_ha": prop.area_total_ha,
        "status_ativo": prop.status_ativo,
    }

    if payload.nome is not None:
        prop.nome = payload.nome
    if payload.localizacao is not None:
        prop.localizacao = payload.localizacao
    if payload.area_total_ha is not None:
        prop.area_total_ha = payload.area_total_ha
    if payload.status_ativo is not None:
        prop.status_ativo = payload.status_ativo

    registrar_auditoria(
        db=db,
        acao="ATUALIZAR",
        entidade="Propriedade",
        registro_id=prop.id,
        usuario=user,
        dados_anteriores=dados_ant,
        dados_novos={
            "nome": prop.nome,
            "localizacao": prop.localizacao,
            "area_total_ha": prop.area_total_ha,
            "status_ativo": prop.status_ativo,
        },
    )
    db.commit()
    db.refresh(prop)
    return prop
