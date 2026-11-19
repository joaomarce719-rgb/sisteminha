"""SAD Carcinicultura — Rotas das etapas do preparo do ciclo (secagem, calagem...)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database import get_db
from src.dependencies import require_gestor
from src.models.ciclo_produtivo import CicloProdutivo
from src.models.enums import RoleUsuario, StatusCiclo
from src.models.etapa_preparo import EtapaPreparo
from src.models.usuario import Usuario
from src.schemas.etapa_preparo import EtapaPreparoCreate, EtapaPreparoResponse, EtapaPreparoUpdate
from src.services.audit import registrar_auditoria, snapshot
from src.services.auth_service import has_role
from src.services.escopo import verificar_ciclo_da_organizacao
from src.services.regras_ciclo import obter_ciclo

router = APIRouter(
    prefix="/api/v1/ciclos/{ciclo_id}/etapas-preparo",
    tags=["Etapas do Preparo"],
    dependencies=[Depends(verificar_ciclo_da_organizacao)],
)

gestor_ou_campo = has_role([RoleUsuario.GESTOR, RoleUsuario.CAMPO])


def _ciclo_alteravel(db: Session, ciclo_id: UUID, user: Usuario) -> CicloProdutivo:
    """CANCELADO recusa mudanças; FINALIZADO só o GESTOR altera (como nos usos de insumo)."""
    ciclo = obter_ciclo(db, ciclo_id)
    if ciclo.status == StatusCiclo.CANCELADO:
        raise HTTPException(status_code=400, detail="Ciclo cancelado não altera etapas do preparo.")
    if ciclo.status == StatusCiclo.FINALIZADO and user.papel != RoleUsuario.GESTOR:
        raise HTTPException(status_code=403, detail="Somente o gestor altera um ciclo finalizado.")
    return ciclo


def etapa_do_ciclo(db: Session, ciclo_id: UUID, etapa_id: UUID) -> EtapaPreparo:
    etapa = db.get(EtapaPreparo, etapa_id)
    if not etapa or etapa.ciclo_id != ciclo_id:
        raise HTTPException(status_code=404, detail="Etapa do preparo não encontrada.")
    return etapa


def _validar_datas(etapa: EtapaPreparo) -> None:
    if etapa.data_inicio and etapa.data_fim and etapa.data_fim < etapa.data_inicio:
        raise HTTPException(status_code=422, detail="O fim da etapa não pode ser anterior ao início.")


@router.get("", response_model=list[EtapaPreparoResponse])
@router.get("/", response_model=list[EtapaPreparoResponse])
def listar_etapas(ciclo_id: UUID, db: Session = Depends(get_db), _user: Usuario = Depends(gestor_ou_campo)):
    """Etapas do preparo do ciclo, na ordem."""
    return db.scalars(
        select(EtapaPreparo)
        .where(EtapaPreparo.ciclo_id == ciclo_id)
        .order_by(EtapaPreparo.ordem, EtapaPreparo.created_at)
    ).all()


@router.post("", response_model=EtapaPreparoResponse, status_code=201)
@router.post("/", response_model=EtapaPreparoResponse, status_code=201)
def criar_etapa(
    ciclo_id: UUID,
    payload: EtapaPreparoCreate,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_gestor),
):
    """Acrescenta uma etapa; sem ordem, ela vai para o fim da lista."""
    _ciclo_alteravel(db, ciclo_id, _user)
    dados = payload.model_dump()
    if dados["ordem"] is None:
        ultima = db.scalar(select(func.max(EtapaPreparo.ordem)).where(EtapaPreparo.ciclo_id == ciclo_id))
        dados["ordem"] = (ultima or 0) + 1
    etapa = EtapaPreparo(ciclo_id=ciclo_id, **dados)
    _validar_datas(etapa)
    db.add(etapa)
    db.flush()
    registrar_auditoria(db, "CRIAR_ETAPA_PREPARO", "EtapaPreparo", etapa.id, _user, dados_novos=snapshot(etapa))
    return etapa


@router.patch("/{etapa_id}", response_model=EtapaPreparoResponse)
def atualizar_etapa(
    ciclo_id: UUID,
    etapa_id: UUID,
    payload: EtapaPreparoUpdate,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(gestor_ou_campo),
):
    """Atualiza status, datas ou observação; só os campos enviados mudam."""
    _ciclo_alteravel(db, ciclo_id, _user)
    etapa = etapa_do_ciclo(db, ciclo_id, etapa_id)
    antes = snapshot(etapa)
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(etapa, campo, valor)
    _validar_datas(etapa)
    db.flush()
    registrar_auditoria(
        db, "ATUALIZAR_ETAPA_PREPARO", "EtapaPreparo", etapa.id, _user,
        dados_anteriores=antes, dados_novos=snapshot(etapa),
    )
    return etapa


@router.delete("/{etapa_id}", status_code=204)
def excluir_etapa(
    ciclo_id: UUID,
    etapa_id: UUID,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_gestor),
):
    """Remove a etapa; os usos de insumo ligados a ela ficam sem etapa."""
    _ciclo_alteravel(db, ciclo_id, _user)
    etapa = etapa_do_ciclo(db, ciclo_id, etapa_id)
    antes = snapshot(etapa)
    db.delete(etapa)
    db.flush()
    registrar_auditoria(db, "EXCLUIR_ETAPA_PREPARO", "EtapaPreparo", etapa_id, _user, dados_anteriores=antes)
