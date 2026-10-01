"""SAD Carcinicultura — Schemas Pydantic para Autenticação e Usuários."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from src.models.enums import RoleUsuario


# ── Login ────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(..., min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: RoleUsuario
    nome: str


class TokenPayload(BaseModel):
    sub: str  # user UUID
    email: str
    role: RoleUsuario
    nome: str
    exp: int


# ── Usuário CRUD ─────────────────────────────────────
class UsuarioCreate(BaseModel):
    nome_completo: str = Field(..., min_length=3, max_length=120)
    email: EmailStr
    senha: str = Field(..., min_length=6, max_length=128)
    papel: RoleUsuario = RoleUsuario.CAMPO
    telefone_emergencia: str | None = Field(None, max_length=20)


class UsuarioUpdate(BaseModel):
    nome_completo: str | None = Field(None, min_length=3, max_length=120)
    papel: RoleUsuario | None = None
    telefone_emergencia: str | None = Field(None, max_length=20)
    ativo: bool | None = None


class UsuarioResponse(BaseModel):
    id: UUID
    nome_completo: str
    email: str
    papel: RoleUsuario
    telefone_emergencia: str | None
    ativo: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlterarSenhaRequest(BaseModel):
    senha_atual: str = Field(..., min_length=6)
    nova_senha: str = Field(..., min_length=6, max_length=128)
