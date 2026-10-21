"""SAD Carcinicultura — Rotas Administrativas e Governança (RF-002, RF-003, RF-014)."""

import secrets
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.enums import RoleUsuario
from src.models.organizacao import Organizacao
from src.models.propriedade import Propriedade
from src.models.usuario import Usuario
from src.models.viveiro import Viveiro
from src.schemas.auth import UsuarioCreate, UsuarioResponse, UsuarioUpdate
from src.routers.auth import excluir_usuario_por_id, verificar_alvo_gerenciavel
from src.services.auth_service import has_role, hash_password, require_superadmin

router = APIRouter(prefix="/api/v1/admin", tags=["Administração & Governança"])


# ── Schemas de Administração ──────────────────────────────────
class FazendaAdminCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=120)
    localizacao: str | None = Field(None, max_length=255)
    area_total_ha: float | None = Field(None, gt=0)
    organizacao_nome: str | None = None
    identificador: str | None = None


class FazendaAdminResponse(BaseModel):
    id: UUID
    nome: str
    localizacao: str | None = None
    area_total_ha: float | None = None
    status_ativo: bool
    total_viveiros: int
    organizacao_nome: str | None = None
    created_at: datetime


class MetricasGlobaisAdmin(BaseModel):
    total_usuarios: int
    gestores: int
    operadores_campo: int
    vigias: int
    usuarios_ativos: int
    usuarios_bloqueados: int
    total_fazendas: int
    fazendas_ativas: int
    area_total_ha: float
    total_viveiros: int


class AprovarUsuarioRequest(BaseModel):
    papel: RoleUsuario = RoleUsuario.CAMPO
    ativo: bool = True


class GestorAdminCreate(BaseModel):
    nome_completo: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=5, max_length=120)
    senha: str = Field(..., min_length=6, max_length=128)
    telefone_emergencia: str | None = None
    organizacao_id: UUID | None = None
    nome_fazenda: str | None = None


class GestorAdminResponse(BaseModel):
    id: UUID
    nome_completo: str
    email: str
    papel: RoleUsuario
    telefone_emergencia: str | None = None
    ativo: bool
    organizacao_id: UUID | None = None
    organizacao_nome: str | None = None
    created_at: datetime


class OperadorCreate(BaseModel):
    nome_completo: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=5, max_length=120)
    senha: str = Field(..., min_length=6, max_length=128)
    papel: RoleUsuario = RoleUsuario.CAMPO
    telefone_emergencia: str | None = None


# ── 1. Métricas Globais do Sistema ────────────────────────────
@router.get("/metricas-globais", response_model=MetricasGlobaisAdmin)
async def obter_metricas_globais(
    db: Session = Depends(get_db),
    _user=Depends(require_superadmin),
):
    """Retorna visão consolidada da governança da plataforma."""
    usuarios = db.scalars(select(Usuario)).all()
    propriedades = db.scalars(select(Propriedade)).all()
    viveiros_count = db.scalar(select(func.count(Viveiro.id))) or 0

    total_usuarios = len(usuarios)
    gestores = sum(1 for u in usuarios if u.papel == RoleUsuario.GESTOR)
    operadores_campo = sum(1 for u in usuarios if u.papel == RoleUsuario.CAMPO)
    vigias = sum(1 for u in usuarios if u.papel == RoleUsuario.VIGIA)
    usuarios_ativos = sum(1 for u in usuarios if u.ativo)
    usuarios_bloqueados = sum(1 for u in usuarios if not u.ativo)

    total_fazendas = len(propriedades)
    fazendas_ativas = sum(1 for p in propriedades if p.status_ativo)
    area_total_ha = sum(p.area_total_ha or 0.0 for p in propriedades)

    return MetricasGlobaisAdmin(
        total_usuarios=total_usuarios,
        gestores=gestores,
        operadores_campo=operadores_campo,
        vigias=vigias,
        usuarios_ativos=usuarios_ativos,
        usuarios_bloqueados=usuarios_bloqueados,
        total_fazendas=total_fazendas,
        fazendas_ativas=fazendas_ativas,
        area_total_ha=round(area_total_ha, 2),
        total_viveiros=viveiros_count,
    )


# ── 2. Gestão de Fazendas (Propriedades / Tenants) ────────────
@router.get("/fazendas", response_model=list[FazendaAdminResponse])
async def listar_fazendas_admin(
    db: Session = Depends(get_db),
    _user=Depends(require_superadmin),
):
    """Lista todas as fazendas da plataforma com estatísticas operacionais."""
    props = db.scalars(select(Propriedade).order_by(Propriedade.nome)).all()
    resultado = []
    for p in props:
        total_v = db.scalar(select(func.count(Viveiro.id)).where(Viveiro.propriedade_id == p.id)) or 0
        org_nome = p.organizacao.nome if p.organizacao else None
        resultado.append(
            FazendaAdminResponse(
                id=p.id,
                nome=p.nome,
                localizacao=p.localizacao,
                area_total_ha=p.area_total_ha,
                status_ativo=p.status_ativo,
                total_viveiros=total_v,
                organizacao_nome=org_nome,
                created_at=p.created_at,
            )
        )
    return resultado


@router.post("/fazendas", response_model=FazendaAdminResponse, status_code=status.HTTP_201_CREATED)
async def criar_fazenda_admin(
    payload: FazendaAdminCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_superadmin),
):
    """Cadastra ou aprova uma nova fazenda/propriedade na plataforma."""
    # Obter ou criar organização associada
    org = db.scalars(select(Organizacao)).first()
    if not org or payload.organizacao_nome:
        nome_org = payload.organizacao_nome or f"Grupo {payload.nome}"
        org = Organizacao(
            nome=nome_org,
            identificador=payload.identificador,
            status_ativo=True,
        )
        db.add(org)
        db.flush()

    nova_fazenda = Propriedade(
        organizacao_id=org.id,
        nome=payload.nome,
        localizacao=payload.localizacao,
        area_total_ha=payload.area_total_ha,
        status_ativo=True,
    )
    db.add(nova_fazenda)
    db.flush()
    db.refresh(nova_fazenda)

    return FazendaAdminResponse(
        id=nova_fazenda.id,
        nome=nova_fazenda.nome,
        localizacao=nova_fazenda.localizacao,
        area_total_ha=nova_fazenda.area_total_ha,
        status_ativo=nova_fazenda.status_ativo,
        total_viveiros=0,
        organizacao_nome=org.nome,
        created_at=nova_fazenda.created_at,
    )


@router.put("/fazendas/{fazenda_id}/status", response_model=FazendaAdminResponse)
async def alternar_status_fazenda(
    fazenda_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_superadmin),
):
    """Ativa, aprova ou suspende uma fazenda na plataforma."""
    fazenda = db.get(Propriedade, fazenda_id)
    if not fazenda:
        raise HTTPException(status_code=404, detail="Fazenda não encontrada.")

    fazenda.status_ativo = not fazenda.status_ativo
    db.add(fazenda)
    db.flush()

    total_v = db.scalar(select(func.count(Viveiro.id)).where(Viveiro.propriedade_id == fazenda.id)) or 0
    org_nome = fazenda.organizacao.nome if fazenda.organizacao else None

    return FazendaAdminResponse(
        id=fazenda.id,
        nome=fazenda.nome,
        localizacao=fazenda.localizacao,
        area_total_ha=fazenda.area_total_ha,
        status_ativo=fazenda.status_ativo,
        total_viveiros=total_v,
        organizacao_nome=org_nome,
        created_at=fazenda.created_at,
    )


# ── 3. Gestão e Aprovação de Usuários (Método 1 Mantido) ───────
@router.post("/usuarios", response_model=UsuarioResponse, status_code=201)
async def criar_usuario(
    payload: UsuarioCreate,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Cria novo usuário com perfil definido (Método 1, somente GESTOR)."""
    exists = db.execute(select(Usuario).where(Usuario.email == payload.email))
    if exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email já cadastrado.",
        )

    senha_bruta = payload.senha or payload.password
    if not senha_bruta or len(senha_bruta) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe uma senha com pelo menos 6 caracteres.",
        )
    user = Usuario(
        nome_completo=payload.nome_completo,
        email=payload.email,
        senha_hash=hash_password(senha_bruta),
        papel=payload.papel,
        telefone_emergencia=payload.telefone_emergencia,
        ativo=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


@router.get("/usuarios", response_model=list[UsuarioResponse])
async def listar_usuarios(
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Lista todos os usuários do sistema (somente GESTOR)."""
    result = db.execute(select(Usuario).order_by(Usuario.nome_completo))
    return result.scalars().all()


@router.put("/usuarios/{user_id}", response_model=UsuarioResponse)
async def atualizar_usuario(
    user_id: UUID,
    payload: UsuarioUpdate,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Atualiza dados/perfil de um usuário (somente GESTOR)."""
    user = db.get(Usuario, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    verificar_alvo_gerenciavel(user, _user)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.add(user)
    db.flush()
    db.refresh(user)
    return user


@router.put("/usuarios/{user_id}/aprovar", response_model=UsuarioResponse)
async def aprovar_usuario(
    user_id: UUID,
    payload: AprovarUsuarioRequest,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Aprova e ativa o usuário, definindo seu papel operacional oficial."""
    user = db.get(Usuario, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    verificar_alvo_gerenciavel(user, _user)

    user.papel = payload.papel
    user.ativo = payload.ativo
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


@router.post("/usuarios/{user_id}/resetar-senha")
async def resetar_senha(
    user_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Gera uma senha temporária aleatória, exibida uma única vez ao GESTOR (somente GESTOR)."""
    user = db.get(Usuario, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    verificar_alvo_gerenciavel(user, _user)

    senha_temporaria = secrets.token_urlsafe(9)
    user.senha_hash = hash_password(senha_temporaria)
    db.add(user)
    db.flush()
    return {
        "detail": f"Senha de {user.nome_completo} redefinida. Repasse a senha temporária ao usuário.",
        "senha_temporaria": senha_temporaria,
    }


@router.delete("/usuarios/{user_id}", status_code=204)
async def excluir_usuario(
    user_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Remove permanentemente um usuário (somente GESTOR)."""
    excluir_usuario_por_id(db, user_id, _user)
    return None


# ── 4. Gestão de Usuários Administrativos (Exclusivo Superadmin) ───
@router.get("/gestores", response_model=list[GestorAdminResponse])
async def listar_gestores_admin(
    db: Session = Depends(get_db),
    _user=Depends(require_superadmin),
):
    """Lista todos os gestores administrativos com suas fazendas associadas."""
    gestores = db.scalars(
        select(Usuario).where(Usuario.papel == RoleUsuario.GESTOR).order_by(Usuario.nome_completo)
    ).all()
    resultado = []
    for g in gestores:
        org_nome = g.organizacao.nome if g.organizacao else None
        resultado.append(
            GestorAdminResponse(
                id=g.id,
                nome_completo=g.nome_completo,
                email=g.email,
                papel=g.papel,
                telefone_emergencia=g.telefone_emergencia,
                ativo=g.ativo,
                organizacao_id=g.organizacao_id,
                organizacao_nome=org_nome,
                created_at=g.created_at,
            )
        )
    return resultado


@router.post("/gestores", response_model=GestorAdminResponse, status_code=status.HTTP_201_CREATED)
async def criar_gestor_admin(
    payload: GestorAdminCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_superadmin),
):
    """Cria um novo usuário administrativo (Gestor de Fazenda) vinculado a uma organização/fazenda."""
    exists = db.execute(select(Usuario).where(Usuario.email == payload.email))
    if exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email já cadastrado.",
        )

    org_id = payload.organizacao_id
    org_nome = None
    if org_id:
        org = db.get(Organizacao, org_id)
        if org:
            org_nome = org.nome
    elif payload.nome_fazenda:
        prop = db.scalars(select(Propriedade).where(Propriedade.nome == payload.nome_fazenda)).first()
        if prop:
            org_id = prop.organizacao_id
            org_nome = prop.nome

    if not org_id:
        primeira_org = db.scalars(select(Organizacao)).first()
        if primeira_org:
            org_id = primeira_org.id
            org_nome = primeira_org.nome

    user = Usuario(
        nome_completo=payload.nome_completo,
        email=payload.email,
        senha_hash=hash_password(payload.senha),
        papel=RoleUsuario.GESTOR,
        telefone_emergencia=payload.telefone_emergencia,
        organizacao_id=org_id,
        ativo=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)

    return GestorAdminResponse(
        id=user.id,
        nome_completo=user.nome_completo,
        email=user.email,
        papel=user.papel,
        telefone_emergencia=user.telefone_emergencia,
        ativo=user.ativo,
        organizacao_id=user.organizacao_id,
        organizacao_nome=org_nome,
        created_at=user.created_at,
    )


# ── 5. Gestão de Operadores Normais de Campo (Método 1 Mantido) ───
@router.get("/operadores", response_model=list[UsuarioResponse])
async def listar_operadores_campo(
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Lista apenas operadores normais de campo e vigias."""
    operadores = db.scalars(
        select(Usuario)
        .where(Usuario.papel.in_([RoleUsuario.CAMPO, RoleUsuario.VIGIA]))
        .order_by(Usuario.nome_completo)
    ).all()
    return list(operadores)


@router.post("/operadores", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def criar_operador_normal(
    payload: OperadorCreate,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Cria colaborador normal de campo ou vigia (Método 1 para gestor da fazenda)."""
    exists = db.execute(select(Usuario).where(Usuario.email == payload.email))
    if exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email já cadastrado.",
        )

    papel = payload.papel if payload.papel in [RoleUsuario.CAMPO, RoleUsuario.VIGIA] else RoleUsuario.CAMPO

    user = Usuario(
        nome_completo=payload.nome_completo,
        email=payload.email,
        senha_hash=hash_password(payload.senha),
        papel=papel,
        telefone_emergencia=payload.telefone_emergencia,
        ativo=True,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user
