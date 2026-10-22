import json
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.audit import registrar_auditoria, snapshot
from src.models.organizacao import Organizacao
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
    is_superadmin,
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


def _registrar_falha_login(
    db: Session, email: str, ip: str | None, user: Usuario | None, motivo: str = "credenciais inválidas"
) -> None:
    """Grava a tentativa recusada e confirma já, pois o erro HTTP desfaz a transação."""
    registrar_auditoria(
        db,
        "LOGIN_FALHA",
        "Usuario",
        user.id if user else email,
        user,
        dados_novos={"email": email, "motivo": motivo},
        ip_origem=ip,
    )
    db.commit()


async def dados_da_requisicao(request: Request) -> dict:
    """Lê o corpo (JSON ou formulário) de forma assíncrona para handlers síncronos."""
    return await parse_request_data(request)


@router.post("/login", response_model=TokenResponse)
@router.post("/login/", response_model=TokenResponse)
def login(
    request: Request,
    data: dict = Depends(dados_da_requisicao),
    db: Session = Depends(get_db),
):
    """Autenticação flexível (JSON ou Form) via email/senha com retorno de JWT."""
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

    ip = request.client.host if request.client else None
    if user is None or not verify_password(senha, user.senha_hash):
        _registrar_falha_login(db, email, ip, user)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas.",
        )

    if not user.ativo:
        _registrar_falha_login(db, email, ip, user, motivo="conta inativa")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta desativada. Contate o gestor.",
        )

    registrar_auditoria(db, "LOGIN", "Usuario", user.id, user, ip_origem=ip)
    token = create_access_token(user)
    return TokenResponse(
        access_token=token,
        role=user.papel,
        nome=user.nome_completo,
        email=user.email,
        is_superadmin=is_superadmin(user),
    )


@router.post("/register", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
@router.post("/register/", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
@router.post("/registrar", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
@router.post("/registrar/", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def registrar_usuario(
    request: Request,
    data: dict = Depends(dados_da_requisicao),
    db: Session = Depends(get_db),
):
    """Auto-cadastro público (JSON ou Form-data).

    O papel enviado pelo cliente é ignorado: a conta nasce como CAMPO e inativa,
    aguardando aprovação de um GESTOR. Apenas o primeiro usuário do sistema
    (banco vazio) é criado como GESTOR ativo.
    """
    email = (data.get("email") or "").strip().lower()
    senha = data.get("senha") or data.get("password")
    nome = data.get("nome_completo") or data.get("name") or data.get("username") or "Usuário"
    telefone = data.get("telefone_emergencia") or data.get("phone")

    if not email or not senha:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email e senha são obrigatórios.",
        )

    if len(senha) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A senha deve ter pelo menos 6 caracteres.",
        )

    existing = db.execute(
        select(Usuario.id).where(func.lower(Usuario.email) == email)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não foi possível concluir o cadastro com este e-mail.",
        )

    primeiro_usuario = db.execute(select(Usuario.id).limit(1)).scalar_one_or_none() is None

    # Código (identificador) da organização: vincula o cadastro para aprovação do gestor dela
    organizacao_id = None
    codigo = (data.get("codigo_organizacao") or "").strip()
    if codigo:
        organizacao_id = db.scalar(
            select(Organizacao.id).where(func.lower(Organizacao.identificador) == codigo.lower())
        )
        if organizacao_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Código de organização inválido.",
            )
    elif primeiro_usuario:
        org = Organizacao(nome="Organização Principal", status_ativo=True)
        db.add(org)
        db.flush()
        organizacao_id = org.id

    user = Usuario(
        nome_completo=nome,
        email=email,
        senha_hash=hash_password(senha),
        papel=RoleUsuario.GESTOR if primeiro_usuario else RoleUsuario.CAMPO,
        telefone_emergencia=telefone,
        organizacao_id=organizacao_id,
        ativo=primeiro_usuario,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    registrar_auditoria(db, "AUTOCADASTRO", "Usuario", user.id, user, dados_novos=snapshot(user))
    return user


@router.get("/me", response_model=UsuarioResponse)
def perfil_atual(current_user: Usuario = Depends(get_current_user)):
    """Retorna os dados do usuário autenticado."""
    resposta = UsuarioResponse.model_validate(current_user)
    resposta.is_superadmin = is_superadmin(current_user)
    return resposta


@router.put("/me/senha")
def alterar_senha(
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
    registrar_auditoria(db, "ALTERAR_SENHA", "Usuario", current_user.id, current_user)
    return {"detail": "Senha alterada com sucesso."}


from uuid import UUID


def verificar_alvo_gerenciavel(alvo: Usuario, atual: Usuario) -> None:
    """GESTOR comum só gerencia contas da própria organização e nunca as de superadmin."""
    if not is_superadmin(atual) and alvo.organizacao_id != atual.organizacao_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
    if is_superadmin(alvo) and not is_superadmin(atual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Somente a Administração Central pode alterar esta conta.",
        )


def _possui_registros_operacionais(db: Session, u: Usuario) -> bool:
    from src.models.biometria import Biometria
    from src.models.ronda_noturna import RondaNoturna

    for modelo, coluna in ((RondaNoturna, RondaNoturna.vigia_id), (Biometria, Biometria.responsavel_id)):
        if db.scalar(select(func.count()).select_from(modelo).where(coluna == u.id)):
            return True
    return False


def excluir_usuario_por_id(db: Session, user_id: UUID, atual: Usuario) -> None:
    if user_id == atual.id:
        raise HTTPException(status_code=400, detail="Não é possível excluir a própria conta.")
    u = db.get(Usuario, user_id)
    if u:
        verificar_alvo_gerenciavel(u, atual)
        if _possui_registros_operacionais(db, u):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Usuário possui registros operacionais; desative a conta em vez de excluí-la.",
            )
        registrar_auditoria(db, "EXCLUIR", "Usuario", u.id, atual, dados_anteriores=snapshot(u))
        db.delete(u)
        db.flush()


@router.delete("/users/{user_id}", status_code=204)
@router.delete("/usuarios/{user_id}", status_code=204)
def deletar_usuario(
    user_id: UUID,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(has_role([RoleUsuario.GESTOR])),
):
    """Deleta um usuário por ID (exclusivo para GESTOR)."""
    excluir_usuario_por_id(db, user_id, _user)
    return Response(status_code=204)


users_router = APIRouter(prefix="/api/v1/users", tags=["Usuários"])


@users_router.delete("/{user_id}", status_code=204)
def deletar_usuario_global(
    user_id: UUID,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(has_role([RoleUsuario.GESTOR])),
):
    """Deleta um usuário por ID (exclusivo para GESTOR)."""
    excluir_usuario_por_id(db, user_id, _user)
    return Response(status_code=204)

