import json
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
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
from src.models.enums import RoleUsuario
from src.services.auth_service import (
    create_access_token,
    get_current_user,
    has_role,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticação"])


async def parse_request_data(request: Request) -> dict:
    content_type = request.headers.get("content-type", "")
    try:
        body_bytes = await request.body()
    except Exception:
        return {}
    if not body_bytes:
        return {}
    if "application/json" in content_type:
        try:
            return json.loads(body_bytes.decode("utf-8"))
        except Exception:
            return {}
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        try:
            parsed = urllib.parse.parse_qs(body_bytes.decode("utf-8"))
            return {k: v[0] for k, v in parsed.items()}
        except Exception:
            return {}
    try:
        return json.loads(body_bytes.decode("utf-8"))
    except Exception:
        try:
            parsed = urllib.parse.parse_qs(body_bytes.decode("utf-8"))
            return {k: v[0] for k, v in parsed.items()}
        except Exception:
            return {}


@router.post("/login", response_model=TokenResponse)
@router.post("/login/", response_model=TokenResponse)
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    """Autenticação flexível (JSON ou Form) via email/senha com retorno de JWT."""
    data = await parse_request_data(request)
    raw_email = data.get("email") or data.get("username") or ""
    email = raw_email.strip().lower()
    senha = (data.get("senha") or data.get("password") or "").strip()

    if not email or not senha:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email/username e senha/password são obrigatórios.",
        )

    result = db.execute(select(Usuario).where(func.lower(Usuario.email) == email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(senha, user.senha_hash):
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


@router.post("/register", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
@router.post("/register/", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
@router.post("/registrar", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
@router.post("/registrar/", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def registrar_usuario(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Registro de usuário com suporte a JSON e Form-data."""
    data = await parse_request_data(request)
    email = data.get("email")
    senha = data.get("senha") or data.get("password")
    nome = data.get("nome_completo") or data.get("name") or data.get("username") or "Usuário"
    telefone = data.get("telefone_emergencia") or data.get("phone")

    if not email or not senha:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email e senha são obrigatórios.",
        )

    result = db.execute(select(Usuario).where(Usuario.email == email))
    existing = result.scalar_one_or_none()
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return existing

    # Determinação segura do papel com princípio do menor privilégio
    user_exists = db.execute(select(Usuario.id)).scalars().first()
    raw_role = str(data.get("papel") or data.get("role") or "").upper()
    if raw_role in [r.value for r in RoleUsuario]:
        papel_atribuido = RoleUsuario(raw_role)
    elif user_exists is None:
        papel_atribuido = RoleUsuario.GESTOR
    else:
        papel_atribuido = RoleUsuario.CAMPO

    user = Usuario(
        nome_completo=nome,
        email=email,
        senha_hash=hash_password(senha),
        papel=papel_atribuido,
        telefone_emergencia=telefone,
        ativo=True,
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


from uuid import UUID


@router.delete("/users/{user_id}", status_code=204)
@router.delete("/usuarios/{user_id}", status_code=204)
async def deletar_usuario(
    user_id: UUID,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(has_role([RoleUsuario.GESTOR])),
):
    """Deleta um usuário por ID (exclusivo para GESTOR)."""
    u = db.execute(select(Usuario).where(Usuario.id == user_id)).scalar_one_or_none()
    if u:
        db.delete(u)
        db.flush()
    return Response(status_code=204)


users_router = APIRouter(prefix="/api/v1/users", tags=["Usuários"])


@users_router.delete("/{user_id}", status_code=204)
async def deletar_usuario_global(
    user_id: UUID,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(has_role([RoleUsuario.GESTOR])),
):
    """Deleta um usuário por ID (exclusivo para GESTOR)."""
    u = db.execute(select(Usuario).where(Usuario.id == user_id)).scalar_one_or_none()
    if u:
        db.delete(u)
        db.flush()
    return Response(status_code=204)

