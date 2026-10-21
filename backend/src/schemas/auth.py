"""SAD Carcinicultura — Schemas Pydantic para Autenticação e Usuários."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator

from src.models.enums import RoleUsuario


# ── Login ────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(default="", min_length=1, max_length=128)
    password: str | None = None

    @model_validator(mode="before")
    @classmethod
    def harmonize_fields(cls, data):
        if isinstance(data, dict):
            if not data.get("email") and data.get("username"):
                data["email"] = data["username"]
            if not data.get("senha") and data.get("password"):
                data["senha"] = data["password"]
            elif not data.get("password") and data.get("senha"):
                data["password"] = data["senha"]
        return data


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
    nome_completo: str = Field(default="Usuário", min_length=1, max_length=120)
    email: EmailStr
    senha: str = Field(default="", min_length=1, max_length=128)
    password: str | None = None
    papel: RoleUsuario = RoleUsuario.GESTOR
    telefone_emergencia: str | None = Field(None, max_length=20)

    @model_validator(mode="before")
    @classmethod
    def harmonize_create_fields(cls, data):
        if isinstance(data, dict):
            if not data.get("nome_completo"):
                data["nome_completo"] = data.get("name") or data.get("username") or "Usuário"
            if not data.get("senha") and data.get("password"):
                data["senha"] = data["password"]
            elif not data.get("password") and data.get("senha"):
                data["password"] = data["senha"]
        return data


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
