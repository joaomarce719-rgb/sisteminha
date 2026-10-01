"""SAD Carcinicultura — Rotas Administrativas (RF-14)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.enums import RoleUsuario
from src.models.usuario import Usuario
from src.schemas.auth import UsuarioCreate, UsuarioResponse, UsuarioUpdate
from src.services.auth_service import has_role, hash_password

router = APIRouter(prefix="/api/v1/admin", tags=["Administração"])


@router.post("/usuarios", response_model=UsuarioResponse, status_code=201)
async def criar_usuario(
    payload: UsuarioCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Cria novo usuário com perfil definido (RF-14, somente GESTOR)."""
    # Verificar email duplicado
    exists = await db.execute(
        select(Usuario).where(Usuario.email == payload.email)
    )
    if exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email já cadastrado.",
        )

    user = Usuario(
        nome_completo=payload.nome_completo,
        email=payload.email,
        senha_hash=hash_password(payload.senha),
        papel=payload.papel,
        telefone_emergencia=payload.telefone_emergencia,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.get("/usuarios", response_model=list[UsuarioResponse])
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Lista todos os usuários do sistema (somente GESTOR)."""
    result = await db.execute(
        select(Usuario).order_by(Usuario.nome_completo)
    )
    return result.scalars().all()


@router.put("/usuarios/{user_id}", response_model=UsuarioResponse)
async def atualizar_usuario(
    user_id: UUID,
    payload: UsuarioUpdate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Atualiza dados/perfil de um usuário (somente GESTOR)."""
    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@router.post("/usuarios/{user_id}/resetar-senha")
async def resetar_senha(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Reseta a senha de um usuário para 'mudar123' (somente GESTOR)."""
    result = await db.execute(select(Usuario).where(Usuario.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    user.senha_hash = hash_password("mudar123")
    db.add(user)
    await db.flush()
    return {"detail": f"Senha de {user.nome_completo} resetada. Nova senha: mudar123"}
