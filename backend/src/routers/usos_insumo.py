"""SAD Carcinicultura — Rotas de uso de insumo no ciclo: cada uso gera um custo pelo preço médio."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.dependencies import require_gestor
from src.models.ciclo_produtivo import CicloProdutivo
from src.models.custo_operacional import CustoOperacional
from src.models.enums import FaseCusto, RoleUsuario, StatusCiclo
from src.models.insumo import ConsumoInsumo, Insumo
from src.models.usuario import Usuario
from src.schemas.uso_insumo import UsoInsumoCreate, UsoInsumoResponse
from src.services.audit import registrar_auditoria, snapshot
from src.services.auth_service import has_role
from src.services.escopo import insumo_da_organizacao, verificar_ciclo_da_organizacao
from src.services.insumos import reprocessar_insumo
from src.services.regras_ciclo import obter_ciclo, validar_data_no_ciclo
from src.services.regras_data import exigir_retroativo_para_data_passada

router = APIRouter(
    prefix="/api/v1/ciclos/{ciclo_id}/usos-insumo",
    tags=["Usos de Insumo"],
    dependencies=[Depends(verificar_ciclo_da_organizacao)],
)


def _validar_status(ciclo: CicloProdutivo, user: Usuario, fase: FaseCusto | None) -> None:
    """PLANEJADO só aceita PREPARO; FINALIZADO só o GESTOR altera; CANCELADO recusa tudo."""
    if ciclo.status == StatusCiclo.CANCELADO:
        raise HTTPException(status_code=400, detail="Ciclo cancelado não recebe usos de insumo.")
    if ciclo.status == StatusCiclo.FINALIZADO and user.papel != RoleUsuario.GESTOR:
        raise HTTPException(status_code=403, detail="Somente o gestor altera um ciclo finalizado.")
    if ciclo.status == StatusCiclo.PLANEJADO and fase is not None and fase != FaseCusto.PREPARO:
        raise HTTPException(status_code=422, detail="Ciclo planejado só aceita uso de insumo da fase PREPARO.")


def _validar_lancamento(
    db: Session, ciclo: CicloProdutivo, payload: UsoInsumoCreate, user: Usuario, insumo_atual: UUID | None = None
) -> Insumo:
    _validar_status(ciclo, user, payload.fase)
    insumo = insumo_da_organizacao(db, payload.insumo_id, user)
    if not insumo.ativo and insumo.id != insumo_atual:
        raise HTTPException(status_code=422, detail="Insumo inativo não pode ser usado.")
    if payload.preco_corrigido_rs is not None and user.papel != RoleUsuario.GESTOR:
        raise HTTPException(status_code=403, detail="Somente o gestor corrige o preço do uso.")
    exigir_retroativo_para_data_passada(payload.data_uso, payload.retroativo, "A data do uso")
    validar_data_no_ciclo(ciclo, payload.data_uso, "A data do uso", payload.fase)
    return insumo


def _colunas(payload: UsoInsumoCreate) -> dict:
    return {**payload.model_dump(), "fase": payload.fase.value}


def _uso_do_ciclo(db: Session, ciclo_id: UUID, uso_id: UUID) -> ConsumoInsumo:
    uso = db.get(ConsumoInsumo, uso_id)
    if not uso or uso.ciclo_id != ciclo_id:
        raise HTTPException(status_code=404, detail="Uso de insumo não encontrado.")
    return uso


def _resposta(db: Session, uso: ConsumoInsumo, user: Usuario) -> UsoInsumoResponse:
    insumo = db.get(Insumo, uso.insumo_id)
    resposta = UsoInsumoResponse(
        id=uso.id, insumo_id=uso.insumo_id, insumo_nome=insumo.nome, unidade_uso=insumo.unidade_uso,
        data_uso=uso.data_uso, quantidade=uso.quantidade, fase=uso.fase, retroativo=uso.retroativo,
        observacao=uso.observacao, recalculado_em=uso.recalculado_em,
    )
    if user.papel == RoleUsuario.GESTOR:
        custo = db.get(CustoOperacional, uso.custo_id) if uso.custo_id else None
        resposta.preco_unitario_rs = None if uso.preco_unitario_rs is None else float(uso.preco_unitario_rs)
        resposta.valor_rs = None if custo is None else float(custo.valor_rs)
        resposta.pendente_de_valor = uso.preco_unitario_rs is None
        resposta.preco_corrigido_rs = None if uso.preco_corrigido_rs is None else float(uso.preco_corrigido_rs)
    return resposta


@router.post("", response_model=UsoInsumoResponse, status_code=201)
@router.post("/", response_model=UsoInsumoResponse, status_code=201)
def registrar_uso(
    ciclo_id: UUID,
    payload: UsoInsumoCreate,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(has_role([RoleUsuario.GESTOR, RoleUsuario.CAMPO, RoleUsuario.VIGIA])),
):
    """Lança o uso de um insumo; o custo é gerado pelo preço médio vigente na data do uso."""
    ciclo = obter_ciclo(db, ciclo_id)
    _validar_lancamento(db, ciclo, payload, _user)
    uso = ConsumoInsumo(ciclo_id=ciclo_id, registrado_por=_user.id, **_colunas(payload))
    db.add(uso)
    db.flush()
    reprocessar_insumo(db, uso.insumo_id, _user)
    registrar_auditoria(db, "CRIAR_USO_INSUMO", "ConsumoInsumo", uso.id, _user, dados_novos=snapshot(uso))
    return _resposta(db, uso, _user)


@router.get("", response_model=list[UsoInsumoResponse])
@router.get("/", response_model=list[UsoInsumoResponse])
def listar_usos(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(has_role([RoleUsuario.GESTOR, RoleUsuario.CAMPO])),
):
    """Usos de insumo do ciclo, do mais recente para o mais antigo."""
    usos = db.scalars(
        select(ConsumoInsumo)
        .where(ConsumoInsumo.ciclo_id == ciclo_id)
        .order_by(ConsumoInsumo.data_uso.desc(), ConsumoInsumo.created_at.desc())
    ).all()
    return [_resposta(db, u, _user) for u in usos]


@router.put("/{uso_id}", response_model=UsoInsumoResponse)
def atualizar_uso(
    ciclo_id: UUID,
    uso_id: UUID,
    payload: UsoInsumoCreate,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_gestor),
):
    """Corrige um uso (reenvia os campos); o insumo antigo e o novo são reprocessados."""
    uso = _uso_do_ciclo(db, ciclo_id, uso_id)
    _validar_lancamento(db, obter_ciclo(db, ciclo_id), payload, _user, insumo_atual=uso.insumo_id)
    antes = snapshot(uso)
    insumo_anterior = uso.insumo_id
    for campo, valor in _colunas(payload).items():
        setattr(uso, campo, valor)
    db.flush()
    reprocessar_insumo(db, uso.insumo_id, _user)
    if insumo_anterior != uso.insumo_id:
        reprocessar_insumo(db, insumo_anterior, _user)
    registrar_auditoria(
        db, "ATUALIZAR_USO_INSUMO", "ConsumoInsumo", uso.id, _user, dados_anteriores=antes, dados_novos=snapshot(uso)
    )
    return _resposta(db, uso, _user)


@router.delete("/{uso_id}", status_code=204)
def excluir_uso(
    ciclo_id: UUID,
    uso_id: UUID,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_gestor),
):
    """Exclui o uso e o custo gerado por ele; o insumo é reprocessado."""
    uso = _uso_do_ciclo(db, ciclo_id, uso_id)
    _validar_status(obter_ciclo(db, ciclo_id), _user, None)
    antes = snapshot(uso)
    custo = db.get(CustoOperacional, uso.custo_id) if uso.custo_id else None
    db.delete(uso)
    db.flush()
    if custo is not None:
        db.delete(custo)
    reprocessar_insumo(db, uso.insumo_id, _user)
    registrar_auditoria(db, "EXCLUIR_USO_INSUMO", "ConsumoInsumo", uso_id, _user, dados_anteriores=antes)
