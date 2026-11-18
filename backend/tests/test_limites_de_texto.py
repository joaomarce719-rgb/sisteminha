"""Todo texto que a API aceita cabe na coluna onde ele é gravado.

O Postgres recusa texto maior que o VARCHAR da coluna (a API respondia 500); o SQLite dos
testes aceita e esconde o problema. Por isso o limite é conferido aqui, schema por schema.
"""

import importlib
import inspect
import pkgutil

from annotated_types import MaxLen
from pydantic import BaseModel

import src.models  # noqa: F401  (registra os modelos)
import src.routers
import src.schemas
from src.database import Base

MODELOS = {m.class_.__name__: m.class_ for m in Base.registry.mappers}

# Schemas cujo nome não segue XxxCreate/XxxUpdate/XxxRequest -> modelo Xxx
ALVOS = {
    "CicloCreate": ["CicloProdutivo"],
    "CustoCreate": ["CustoOperacional"],
    "CompraCreate": ["CompraInsumo"],
    "UsoInsumoCreate": ["ConsumoInsumo"],
    "VendaCreate": ["VendaCiclo"],
    "PrecoCreate": ["TabelaPrecoMercado"],
    "PrecoUpdate": ["TabelaPrecoMercado"],
    "FazendaAdminCreate": ["Propriedade"],
    "GestorAdminCreate": ["Usuario"],
    "OperadorCreate": ["Usuario"],
}
# Campos gravados em coluna de outro nome ou de outro modelo
CAMPOS_RENOMEADOS = {
    ("FazendaAdminCreate", "organizacao_nome"): ("Organizacao", "nome"),
    ("FazendaAdminCreate", "identificador"): ("Organizacao", "identificador"),
}
# Entradas que não gravam texto em coluna (senhas viram hash; descrição só volta na resposta)
SEM_GRAVACAO = {"AlterarSenhaRequest", "LoginRequest", "AprovarUsuarioRequest", "SimulacaoRequest", "SimulacaoGenericRequest"}


def _schemas_de_entrada():
    for pacote in (src.schemas, src.routers):
        for mod in pkgutil.iter_modules(pacote.__path__):
            modulo = importlib.import_module(f"{pacote.__name__}.{mod.name}")
            for nome, cls in inspect.getmembers(modulo, inspect.isclass):
                if issubclass(cls, BaseModel) and cls.__module__ == modulo.__name__ and nome.endswith(("Create", "Update", "Request")):
                    yield nome, cls


def _alvos(nome):
    if nome in ALVOS:
        return ALVOS[nome]
    base = nome.removesuffix("Create").removesuffix("Update").removesuffix("Request")
    return [base] if base in MODELOS else None


def _limite_da_coluna(modelo, coluna):
    col = MODELOS[modelo].__table__.columns.get(coluna)
    return getattr(col.type, "length", None) if col is not None else None


def test_todo_schema_de_entrada_tem_alvo_conhecido():
    sem_alvo = [n for n, _ in _schemas_de_entrada() if n not in SEM_GRAVACAO and _alvos(n) is None]
    assert not sem_alvo, f"Diga em ALVOS ou SEM_GRAVACAO onde estes schemas gravam: {sem_alvo}"


def test_texto_aceito_cabe_na_coluna():
    lacunas = []
    for nome, cls in _schemas_de_entrada():
        if nome in SEM_GRAVACAO:
            continue
        for campo, info in cls.model_fields.items():
            anotacao = str(info.annotation)
            if "str" not in anotacao.lower() or "list" in anotacao or "dict" in anotacao:
                continue
            destinos = [CAMPOS_RENOMEADOS[(nome, campo)]] if (nome, campo) in CAMPOS_RENOMEADOS else [
                (modelo, campo) for modelo in _alvos(nome)
            ]
            limite_api = next((m.max_length for m in info.metadata if isinstance(m, MaxLen)), None)
            for modelo, coluna in destinos:
                limite = _limite_da_coluna(modelo, coluna)
                if limite is not None and (limite_api is None or limite_api > limite):
                    lacunas.append(f"{nome}.{campo}: API aceita {limite_api or 'qualquer tamanho'}, coluna {modelo}.{coluna} tem {limite}")
    assert not lacunas, "\n".join(lacunas)


def test_cadastro_publico_recusa_telefone_longo_com_mensagem(client):
    r = client.post("/api/v1/auth/register", json={
        "nome_completo": "Teste Limite", "email": "limite.telefone@x.com", "senha": "senha123",
        "telefone_emergencia": "(88) 99301-9759 - whatsapp",
    })
    assert r.status_code == 422
    assert r.json()["detail"] == "O telefone deve ter no máximo 20 caracteres."


def test_cadastro_publico_recusa_nome_e_email_longos(client):
    nome_longo = client.post("/api/v1/auth/register", json={"nome_completo": "N" * 121, "email": "limite.nome@x.com", "senha": "senha123"})
    assert nome_longo.status_code == 422 and "nome" in nome_longo.json()["detail"]
    email_longo = client.post("/api/v1/auth/register", json={"nome_completo": "Teste", "email": "e" * 115 + "@x.com.br", "senha": "senha123"})
    assert email_longo.status_code == 422 and "e-mail" in email_longo.json()["detail"]


def test_admin_recusa_codigo_de_organizacao_longo(client, admin):
    r = client.post("/api/v1/admin/fazendas", json={"nome": "Fazenda Limite", "organizacao_nome": "Grupo Limite",
                                                     "identificador": "C" * 31}, headers=admin)
    assert r.status_code == 422
