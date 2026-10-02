"""SAD Carcinicultura — Rotas de Autenticação."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.usuario import Usuario
from src.schemas.auth import (
    AlterarSenhaRequest,
    LoginRequest,
    TokenResponse,
    UsuarioCreate,
    UsuarioResponse,
)
from src.services.auth_service import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticação"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Autenticação via email/senha com retorno de JWT."""
    result = db.execute(
        select(Usuario).where(Usuario.email == payload.email)
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.senha, user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas.",
        )

    if not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta desativada. Contate o gestor.",
        )

    token = create_access_token(user)
    return TokenResponse(
        access_token=token,
        role=user.papel,
        nome=user.nome_completo,
    )


@router.post("/registrar", response_model=UsuarioResponse, status_code=201)
async def registrar_primeiro_usuario(
    payload: UsuarioCreate,
    db: Session = Depends(get_db),
):
    """Registro do primeiro usuário (GESTOR). Bloqueado se já houver usuários."""
    result = db.execute(select(Usuario).limit(1))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registro público desabilitado. Peça ao gestor para criar sua conta.",
        )

    from src.models.enums import RoleUsuario
    user = Usuario(
        nome_completo=payload.nome_completo,
        email=payload.email,
        senha_hash=hash_password(payload.senha),
        papel=RoleUsuario.GESTOR,
        telefone_emergencia=payload.telefone_emergencia,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


@router.get("/me", response_model=UsuarioResponse)
async def perfil_atual(current_user: Usuario = Depends(get_current_user)):
    """Retorna os dados do usuário autenticado."""
    return current_user


@router.put("/me/senha")
async def alterar_senha(
    payload: AlterarSenhaRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Altera a senha do usuário autenticado."""
    if not verify_password(payload.senha_atual, current_user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta.",
        )

    current_user.senha_hash = hash_password(payload.nova_senha)
    db.add(current_user)
    db.flush()
    return {"detail": "Senha alterada com sucesso."}
