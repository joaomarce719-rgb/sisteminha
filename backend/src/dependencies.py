"""SAD Carcinicultura — Injeção de dependências compartilhadas."""

from src.models.enums import RoleUsuario
from src.services.auth_service import get_current_user, has_role

get_current_usuario = get_current_user
require_gestor = has_role([RoleUsuario.GESTOR])
require_campo = has_role([RoleUsuario.CAMPO, RoleUsuario.GESTOR])
require_vigia = has_role([RoleUsuario.VIGIA, RoleUsuario.GESTOR])
