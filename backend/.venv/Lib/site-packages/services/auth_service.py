"""SAD Carcinicultura — Serviço de Autenticação e RBAC.

Implementa hashing de senhas (bcrypt via passlib), geração/validação de JWT
e dependency injection para controle de acesso baseado em papéis.
"""

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import get_settings
from src.database import get_db
from src.models.enums import RoleUsuario
from src.models.usuario import Usuario
from src.schemas.auth import TokenPayload

settings = get_settings()

# ── Hashing ──────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ──────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def create_access_token(user: Usuario) -> str:
    """Gera JWT com claims de RBAC conforme RN-08."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.papel.value,
        "nome": user.nome_completo,
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenPayload:
    """Decodifica e valida o JWT, retornando o payload tipado."""
    try:
        data = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return TokenPayload(
            sub=data["sub"],
            email=data["email"],
            role=RoleUsuario(data["role"]),
            nome=data["nome"],
            exp=data["exp"],
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# ── Dependencies ─────────────────────────────────────
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """Retorna o usuário autenticado a partir do token JWT."""
    payload = decode_token(token)
    result = db.execute(
        select(Usuario).where(Usuario.id == payload.sub)
    )
    user = result.scalar_one_or_none()
    if user is None or not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo.",
        )
    return user


def has_role(allowed_roles: list[RoleUsuario]):
    """Factory de dependency que restringe acesso por papel (RN-11)."""

    async def _check_role(current_user: Usuario = Depends(get_current_user)) -> Usuario:
        if current_user.papel not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso restrito aos perfis: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return _check_role
