"""SAD Carcinicultura — Router de Tabelas Alimentares (RF-010, Critério 5)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.database import get_db
from src.dependencies import get_current_usuario, require_gestor
from src.models.tabela_alimentar import TabelaAlimentar
from src.models.usuario import Usuario
from src.schemas.tabela_alimentar import (
    FaixaAlimentarItem,
    TabelaAlimentarCreate,
    TabelaAlimentarResponse,
    TabelaAlimentarUpdate,
)
from src.services.audit import registrar_auditoria

router = APIRouter(prefix="/api/v1/tabelas-alimentares", tags=["Tabelas Alimentares"])

# Pontos padrão de Clifford (1992)
_CLIFFORD_DEFAULT_FAIXAS = [
    {"peso_g": 2.0, "taxa_pct": 7.15},
    {"peso_g": 5.0, "taxa_pct": 5.05},
    {"peso_g": 10.0, "taxa_pct": 3.88},
    {"peso_g": 15.0, "taxa_pct": 3.33},
    {"peso_g": 20.0, "taxa_pct": 2.98},
]


def garantir_tabela_padrao(db: Session) -> None:
    """Cria a tabela padrão de Clifford (1992) se o banco estiver vazio (chamada pelo init_db)."""
    existente = db.scalar(select(TabelaAlimentar.id).limit(1))
    if not existente:
        padrao = TabelaAlimentar(
            nome="Clifford (1992) - Padrão",
            versao=1,
            descricao="Tabela clássica de Clifford (1992) para Litopenaeus vannamei",
            is_padrao=True,
            ativo=True,
            faixas=_CLIFFORD_DEFAULT_FAIXAS,
        )
        db.add(padrao)


@router.get("", response_model=list[TabelaAlimentarResponse])
@router.get("/", response_model=list[TabelaAlimentarResponse])
def listar_tabelas_alimentares(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[Usuario, Depends(get_current_usuario)],
    apenas_ativas: bool = Query(True, description="Filtrar apenas tabelas ativas"),
):
    """Lista as tabelas alimentares cadastradas."""
    query = select(TabelaAlimentar).order_by(desc(TabelaAlimentar.is_padrao), TabelaAlimentar.nome)
    if apenas_ativas:
        query = query.where(TabelaAlimentar.ativo.is_(True))
    return list(db.scalars(query).all())


@router.get("/{tabela_id}", response_model=TabelaAlimentarResponse)
def obter_tabela_alimentar(
    tabela_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[Usuario, Depends(get_current_usuario)],
):
    """Obtém os detalhes de uma tabela alimentar específica."""
    tabela = db.get(TabelaAlimentar, tabela_id)
    if not tabela:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tabela alimentar não encontrada")
    return tabela


@router.post("", response_model=TabelaAlimentarResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=TabelaAlimentarResponse, status_code=status.HTTP_201_CREATED)
def criar_tabela_alimentar(
    payload: TabelaAlimentarCreate,
    db: Annotated[Session, Depends(get_db)],
    usuario: Annotated[Usuario, Depends(require_gestor)],
):
    """Cria uma nova tabela alimentar (apenas GESTOR)."""
    # Se marcada como padrão, remove padrão das outras
    if payload.is_padrao:
        outras = db.scalars(select(TabelaAlimentar).where(TabelaAlimentar.is_padrao.is_(True))).all()
        for t in outras:
            t.is_padrao = False

    # Determinar versão incremental para o mesmo nome
    ultima_versao = db.scalar(
        select(TabelaAlimentar.versao)
        .where(TabelaAlimentar.nome == payload.nome)
        .order_by(desc(TabelaAlimentar.versao))
        .limit(1)
    )
    nova_versao = (ultima_versao or 0) + 1

    faixas_ordenadas = sorted([f.model_dump() for f in payload.faixas], key=lambda x: x["peso_g"])

    tabela = TabelaAlimentar(
        nome=payload.nome,
        versao=nova_versao,
        descricao=payload.descricao,
        is_padrao=payload.is_padrao,
        ativo=True,
        faixas=faixas_ordenadas,
        created_by_id=usuario.id,
    )
    db.add(tabela)
    db.flush()

    registrar_auditoria(
        db=db,
        acao="CRIAR",
        entidade="TabelaAlimentar",
        registro_id=tabela.id,
        usuario=usuario,
        dados_novos={
            "nome": tabela.nome,
            "versao": tabela.versao,
            "is_padrao": tabela.is_padrao,
            "faixas": tabela.faixas,
        },
    )
    db.commit()
    db.refresh(tabela)
    return tabela


@router.put("/{tabela_id}", response_model=TabelaAlimentarResponse)
def atualizar_tabela_alimentar(
    tabela_id: uuid.UUID,
    payload: TabelaAlimentarUpdate,
    db: Annotated[Session, Depends(get_db)],
    usuario: Annotated[Usuario, Depends(require_gestor)],
):
    """Atualiza metadados/status; alterar faixas gera uma NOVA versão (RF-010, RN-017).

    A versão anterior é preservada (inativa) para que ciclos e resultados que a
    referenciam continuem reproduzíveis.
    """
    tabela = db.get(TabelaAlimentar, tabela_id)
    if not tabela:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tabela alimentar não encontrada")

    dados_ant = {
        "nome": tabela.nome,
        "versao": tabela.versao,
        "is_padrao": tabela.is_padrao,
        "ativo": tabela.ativo,
        "faixas": tabela.faixas,
    }

    if payload.is_padrao is True:
        outras = db.scalars(select(TabelaAlimentar).where(TabelaAlimentar.is_padrao.is_(True))).all()
        for t in outras:
            t.is_padrao = False
        tabela.is_padrao = True

    if payload.nome is not None:
        tabela.nome = payload.nome
    if payload.descricao is not None:
        tabela.descricao = payload.descricao
    if payload.ativo is not None:
        tabela.ativo = payload.ativo
    faixas_novas = (
        sorted([f.model_dump() for f in payload.faixas], key=lambda x: x["peso_g"])
        if payload.faixas is not None
        else None
    )
    if faixas_novas is not None and faixas_novas != tabela.faixas:
        ultima_versao = db.scalar(
            select(TabelaAlimentar.versao)
            .where(TabelaAlimentar.nome == tabela.nome)
            .order_by(desc(TabelaAlimentar.versao))
            .limit(1)
        )
        nova = TabelaAlimentar(
            nome=tabela.nome,
            versao=(ultima_versao or tabela.versao) + 1,
            descricao=tabela.descricao,
            is_padrao=tabela.is_padrao,
            ativo=True,
            faixas=faixas_novas,
            created_by_id=usuario.id,
        )
        tabela.is_padrao = False
        tabela.ativo = False
        db.add(nova)
        db.flush()
        registrar_auditoria(
            db=db,
            acao="NOVA_VERSAO",
            entidade="TabelaAlimentar",
            registro_id=nova.id,
            usuario=usuario,
            dados_anteriores={**dados_ant, "id": str(tabela.id)},
            dados_novos={"nome": nova.nome, "versao": nova.versao, "faixas": nova.faixas},
        )
        db.commit()
        db.refresh(nova)
        return nova

    registrar_auditoria(
        db=db,
        acao="ATUALIZAR",
        entidade="TabelaAlimentar",
        registro_id=tabela.id,
        usuario=usuario,
        dados_anteriores=dados_ant,
        dados_novos={
            "nome": tabela.nome,
            "versao": tabela.versao,
            "is_padrao": tabela.is_padrao,
            "ativo": tabela.ativo,
            "faixas": tabela.faixas,
        },
    )
    db.commit()
    db.refresh(tabela)
    return tabela
