"""SAD Carcinicultura — Rotas de insumos: cadastro, saldo e compras (preço médio ponderado móvel)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database import get_db
from src.dependencies import require_gestor
from src.models.enums import RoleUsuario
from src.models.insumo import CompraInsumo, Insumo
from src.models.usuario import Usuario
from src.schemas.insumo import (
    CompraCreate,
    CompraResponse,
    InsumoCreate,
    InsumoResponse,
    InsumoUpdate,
)
from src.services.audit import registrar_auditoria, snapshot
from src.services.auth_service import has_role
from src.services.escopo import insumo_da_organizacao, org_do_usuario
from src.services.insumos import chave_do_nome, reprocessar_insumo, situacao_do_insumo
from src.services.regras_data import exigir_retroativo_para_data_passada

router = APIRouter(prefix="/api/v1/insumos", tags=["Insumos"])


def _resposta(db: Session, insumo: Insumo, user: Usuario) -> InsumoResponse:
    """VIGIA vê só o cadastro; CAMPO soma o saldo; GESTOR vê também preço médio e alerta de saldo negativo."""
    resposta = InsumoResponse.model_validate(insumo)
    if user.papel != RoleUsuario.VIGIA:
        preco_medio, saldo = situacao_do_insumo(db, insumo.id)
        resposta.saldo = round(saldo, 4)
        if user.papel == RoleUsuario.GESTOR:
            resposta.preco_medio_rs = None if preco_medio is None else round(preco_medio, 4)
            resposta.saldo_negativo = resposta.saldo < 0
    return resposta


def _gravar(db: Session) -> None:
    """Flush que traduz a violação da unicidade (organização, nome) em 409."""
    try:
        db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Já existe um insumo com esse nome na organização.") from None


def _compra_do_insumo(db: Session, insumo: Insumo, compra_id: UUID) -> CompraInsumo:
    compra = db.get(CompraInsumo, compra_id)
    if not compra or compra.insumo_id != insumo.id:
        raise HTTPException(status_code=404, detail="Compra não encontrada.")
    return compra


@router.post("", response_model=InsumoResponse, status_code=201)
@router.post("/", response_model=InsumoResponse, status_code=201)
def criar_insumo(
    payload: InsumoCreate,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_gestor),
):
    """Cadastra um insumo da organização (somente GESTOR)."""
    insumo = Insumo(
        organizacao_id=org_do_usuario(_user),
        nome=payload.nome,
        nome_chave=chave_do_nome(payload.nome),
        unidade_uso=payload.unidade_uso,
        categoria=payload.categoria.value,
    )
    db.add(insumo)
    _gravar(db)
    registrar_auditoria(db, "CRIAR_INSUMO", "Insumo", insumo.id, _user, dados_novos=snapshot(insumo))
    return _resposta(db, insumo, _user)


@router.get("", response_model=list[InsumoResponse])
@router.get("/", response_model=list[InsumoResponse])
def listar_insumos(
    db: Session = Depends(get_db),
    _user: Usuario = Depends(has_role([RoleUsuario.GESTOR, RoleUsuario.CAMPO, RoleUsuario.VIGIA])),
):
    """Lista os insumos da organização; CAMPO e VIGIA só veem os ativos."""
    consulta = select(Insumo).where(Insumo.organizacao_id == org_do_usuario(_user)).order_by(Insumo.nome_chave)
    if _user.papel != RoleUsuario.GESTOR:
        consulta = consulta.where(Insumo.ativo.is_(True))
    return [_resposta(db, i, _user) for i in db.scalars(consulta).all()]


@router.put("/{insumo_id}", response_model=InsumoResponse)
def atualizar_insumo(
    insumo_id: UUID,
    payload: InsumoUpdate,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_gestor),
):
    """Edita nome, unidade, categoria ou situação do insumo (somente GESTOR)."""
    insumo = insumo_da_organizacao(db, insumo_id, _user)
    antes = snapshot(insumo)
    for campo, valor in payload.model_dump(mode="json", exclude_none=True).items():
        setattr(insumo, campo, valor)
    insumo.nome_chave = chave_do_nome(insumo.nome)
    _gravar(db)
    registrar_auditoria(
        db, "ATUALIZAR_INSUMO", "Insumo", insumo.id, _user, dados_anteriores=antes, dados_novos=snapshot(insumo)
    )
    return _resposta(db, insumo, _user)


@router.post("/{insumo_id}/compras", response_model=CompraResponse, status_code=201)
def criar_compra(
    insumo_id: UUID,
    payload: CompraCreate,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_gestor),
):
    """Registra uma compra; ela entra no preço médio e pode reprocessar usos já lançados."""
    insumo = insumo_da_organizacao(db, insumo_id, _user)
    exigir_retroativo_para_data_passada(payload.data_compra, payload.retroativo, "A data da compra")
    compra = CompraInsumo(insumo_id=insumo.id, **payload.model_dump())
    db.add(compra)
    db.flush()
    reprocessar_insumo(db, insumo.id, _user)
    registrar_auditoria(db, "CRIAR_COMPRA_INSUMO", "CompraInsumo", compra.id, _user, dados_novos=snapshot(compra))
    return compra


@router.get("/{insumo_id}/compras", response_model=list[CompraResponse])
def listar_compras(
    insumo_id: UUID,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_gestor),
):
    """Compras do insumo, da mais recente para a mais antiga."""
    insumo = insumo_da_organizacao(db, insumo_id, _user)
    return db.scalars(
        select(CompraInsumo)
        .where(CompraInsumo.insumo_id == insumo.id)
        .order_by(CompraInsumo.data_compra.desc(), CompraInsumo.created_at.desc())
    ).all()


@router.put("/{insumo_id}/compras/{compra_id}", response_model=CompraResponse)
def atualizar_compra(
    insumo_id: UUID,
    compra_id: UUID,
    payload: CompraCreate,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_gestor),
):
    """Corrige uma compra (reenvia os campos); o preço médio e os usos são reprocessados."""
    insumo = insumo_da_organizacao(db, insumo_id, _user)
    compra = _compra_do_insumo(db, insumo, compra_id)
    exigir_retroativo_para_data_passada(payload.data_compra, payload.retroativo, "A data da compra")
    antes = snapshot(compra)
    for campo, valor in payload.model_dump().items():
        setattr(compra, campo, valor)
    db.flush()
    reprocessar_insumo(db, insumo.id, _user)
    registrar_auditoria(
        db, "ATUALIZAR_COMPRA_INSUMO", "CompraInsumo", compra.id, _user,
        dados_anteriores=antes, dados_novos=snapshot(compra),
    )
    return compra


@router.delete("/{insumo_id}/compras/{compra_id}", status_code=204)
def excluir_compra(
    insumo_id: UUID,
    compra_id: UUID,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_gestor),
):
    """Exclui uma compra (lançamento errado); o preço médio e os usos são reprocessados."""
    insumo = insumo_da_organizacao(db, insumo_id, _user)
    compra = _compra_do_insumo(db, insumo, compra_id)
    antes = snapshot(compra)
    db.delete(compra)
    db.flush()
    reprocessar_insumo(db, insumo.id, _user)
    registrar_auditoria(db, "EXCLUIR_COMPRA_INSUMO", "CompraInsumo", compra_id, _user, dados_anteriores=antes)
