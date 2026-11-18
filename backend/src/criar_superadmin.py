"""SAD Carcinicultura — Cria o primeiro superadmin (GESTOR ativo) sem passar pelo cadastro público.

Uso: python -m src.criar_superadmin voce@empresa.com ["Nome Completo"]
O e-mail precisa estar em SUPERADMIN_EMAILS para valer como superadmin.
"""

import sys
from getpass import getpass

from sqlalchemy import func, select

from src.config import get_settings
from src.database import SessionLocal
from src.models.enums import RoleUsuario
from src.models.usuario import Usuario
from src.services.auth_service import hash_password


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    email = sys.argv[1].strip().lower()
    nome = sys.argv[2] if len(sys.argv) > 2 else "Administrador Central"
    if email not in get_settings().superadmin_emails_set:
        print(f"Aviso: {email} não está em SUPERADMIN_EMAILS; a conta será GESTOR comum.")
    senha = getpass("Senha (mín. 6 caracteres): ")
    if len(senha) < 6 or senha != getpass("Repita a senha: "):
        print("Senha curta demais ou diferente da repetição.")
        return 1
    with SessionLocal() as db:
        if db.scalar(select(Usuario.id).where(func.lower(Usuario.email) == email)):
            print("Já existe usuário com este e-mail.")
            return 1
        db.add(Usuario(nome_completo=nome, email=email, senha_hash=hash_password(senha),
                       papel=RoleUsuario.GESTOR, ativo=True))
        db.commit()
    print(f"Superadmin {email} criado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
