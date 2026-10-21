"""SAD Carcinicultura — Rotas de Organizações (RF-002, RF-003, RN-001)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.dependencies import require_gestor, get_current_usuario
from src.models.organizacao import Organizacao
from src.models.usuario import Usuario
from src.schemas.organizacao import (
    OrganizacaoCreate,
    OrganizacaoResponse,
    OrganizacaoUpdate,
)
from src.services.audit import registrar_auditoria

router = APIRouter(prefix="/api/v1/organizacoes", tags=["Organizações"])


@router.get("", response_model=list[OrganizacaoResponse])
@router.get("/", response_model=list[OrganizacaoResponse])
def listar_organizacoes(
    db: Session = Depends(get_db),
    _user: Usuario = Depends(get_current_usuario),
):
    """Lista organizações cadastradas."""
    return list(db.scalars(select(Organizacao).order_by(Organizacao.nome)).all())


@router.get("/{org_id}", response_model=OrganizacaoResponse)
def obter_organizacao(
    org_id: UUID,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(get_current_usuario),
):
    """Obtém detalhes de uma organização."""
    org = db.get(Organizacao, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organização não encontrada")
    return org


@router.post("", response_model=OrganizacaoResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=OrganizacaoResponse, status_code=status.HTTP_201_CREATED)
def criar_organizacao(
    payload: OrganizacaoCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_gestor),
):
    """Cria uma organização (apenas GESTOR)."""
    org = Organizacao(
        nome=payload.nome,
        identificador=payload.identificador,
        moeda=payload.moeda,
        status_ativo=True,
    )
    db.add(org)
    db.flush()

    registrar_auditoria(
        db=db,
        acao="CRIAR",
        entidade="Organizacao",
        registro_id=org.id,
        usuario=user,
        dados_novos={
            "nome": org.nome,
            "identificador": org.identificador,
            "moeda": org.moeda,
        },
    )
    db.commit()
    db.refresh(org)
    return org


@router.put("/{org_id}", response_model=OrganizacaoResponse)
def atualizar_organizacao(
    org_id: UUID,
    payload: OrganizacaoUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_gestor),
):
    """Atualiza uma organização (apenas GESTOR)."""
    org = db.get(Organizacao, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organização não encontrada")

    dados_ant = {
        "nome": org.nome,
        "identificador": org.identificador,
        "moeda": org.moeda,
        "status_ativo": org.status_ativo,
    }

    if payload.nome is not None:
        org.nome = payload.nome
    if payload.identificador is not None:
        org.identificador = payload.identificador
    if payload.moeda is not None:
        org.moeda = payload.moeda
    if payload.status_ativo is not None:
        org.status_ativo = payload.status_ativo

    registrar_auditoria(
        db=db,
        acao="ATUALIZAR",
        entidade="Organizacao",
        registro_id=org.id,
        usuario=user,
        dados_anteriores=dados_ant,
        dados_novos={
            "nome": org.nome,
            "identificador": org.identificador,
            "moeda": org.moeda,
            "status_ativo": org.status_ativo,
        },
    )
    db.commit()
    db.refresh(org)
    return org
