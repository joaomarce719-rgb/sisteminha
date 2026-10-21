"""SAD Carcinicultura — Rotas de Biometria (RF-03)."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.audit import registrar_auditoria, snapshot
from src.models.biometria import Biometria
from src.models.ciclo_produtivo import CicloProdutivo
from src.models.enums import RoleUsuario, StatusCiclo
from src.schemas.biometria import BiometriaCreate, BiometriaResponse
from src.services.auth_service import has_role
from src.services.decision_engine import calcular_ganho_diario, calcular_ganho_semanal
from src.services.regras_ciclo import validar_data_no_ciclo

router = APIRouter(prefix="/api/v1/ciclos/{ciclo_id}/biometrias", tags=["Biometrias"])


async def _get_ciclo_ativo(ciclo_id: UUID, db: Session) -> CicloProdutivo:
    result = db.execute(select(CicloProdutivo).where(CicloProdutivo.id == ciclo_id))
    ciclo = result.scalar_one_or_none()
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo não encontrado.")
    if ciclo.status != StatusCiclo.ATIVO:
        raise HTTPException(status_code=400, detail="Ciclo não está ativo.")
    return ciclo


def _build_biometria_response(bio: Biometria) -> BiometriaResponse:
    return BiometriaResponse(
        id=bio.id,
        ciclo_id=bio.ciclo_id,
        data_medicao=bio.data_medicao,
        quantidade_amostrada=bio.quantidade_amostrada,
        peso_total_amostra_g=bio.peso_total_amostra_g,
        peso_medio_g=bio.peso_medio_g,
        ganho_medio_semanal_g=bio.ganho_medio_semanal_g,
        uniformidade_percentual=bio.uniformidade_percentual,
        observacoes=bio.observacoes,
        responsavel_id=bio.responsavel_id,
        responsavel_nome=bio.responsavel.nome_completo if bio.responsavel else None,
        created_at=bio.created_at,
    )


@router.post("/", response_model=BiometriaResponse, status_code=201)
async def registrar_biometria(
    ciclo_id: UUID,
    payload: BiometriaCreate,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.CAMPO, RoleUsuario.GESTOR])),
):
    """Registra uma amostragem biométrica com tamanho da amostra (RF-007, RN-004)."""
    ciclo = await _get_ciclo_ativo(ciclo_id, db)
    validar_data_no_ciclo(ciclo, payload.data_medicao, "A data da biometria")

    # Calcular peso médio se fornecido peso total da amostra
    peso_medio = payload.peso_medio_g
    if payload.peso_total_amostra_g and payload.quantidade_amostrada > 0:
        peso_medio = round(payload.peso_total_amostra_g / payload.quantidade_amostrada, 2)

    # Calcular ganho em relação à última biometria
    biometrias = sorted(ciclo.biometrias, key=lambda b: b.data_medicao)
    ganho_semanal = None
    if biometrias:
        ultima = biometrias[-1]
        dias = (payload.data_medicao - ultima.data_medicao).days
        if dias > 0:
            ganho_diario = calcular_ganho_diario(
                ultima.peso_medio_g, peso_medio, dias
            )
            ganho_semanal = round(calcular_ganho_semanal(ganho_diario), 2)

    bio = Biometria(
        ciclo_id=ciclo_id,
        data_medicao=payload.data_medicao,
        quantidade_amostrada=payload.quantidade_amostrada,
        peso_total_amostra_g=payload.peso_total_amostra_g,
        peso_medio_g=peso_medio,
        ganho_medio_semanal_g=ganho_semanal,
        uniformidade_percentual=payload.uniformidade_percentual,
        observacoes=payload.observacoes,
        responsavel_id=getattr(_user, "id", None),
    )
    db.add(bio)
    db.flush()
    db.refresh(bio)
    registrar_auditoria(db, "CRIAR", "Biometria", bio.id, _user, dados_novos=snapshot(bio))
    return _build_biometria_response(bio)


@router.get("/", response_model=list[BiometriaResponse])
async def listar_biometrias(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.CAMPO, RoleUsuario.VIGIA, RoleUsuario.GESTOR])),
):
    """Lista biometrias do ciclo ordenadas por data."""
    result = db.execute(
        select(Biometria)
        .where(Biometria.ciclo_id == ciclo_id)
        .order_by(Biometria.data_medicao)
    )
    return [_build_biometria_response(b) for b in result.scalars().all()]


global_router = APIRouter(prefix="/api/v1/biometrias", tags=["Biometrias"])


@global_router.post("/", response_model=BiometriaResponse, status_code=201)
async def registrar_biometria_global(
    payload: BiometriaCreate,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.CAMPO, RoleUsuario.GESTOR])),
):
    if not payload.ciclo_id:
        raise HTTPException(status_code=422, detail="ciclo_id é obrigatório.")
    return await registrar_biometria(payload.ciclo_id, payload, db, _user)


@global_router.get("/", response_model=list[BiometriaResponse])
async def listar_biometrias_global(
    ciclo_id: UUID | None = None,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.CAMPO, RoleUsuario.VIGIA, RoleUsuario.GESTOR])),
):
    query = select(Biometria).order_by(Biometria.data_medicao.desc())
    if ciclo_id:
        query = query.where(Biometria.ciclo_id == ciclo_id)
    result = db.execute(query)
    return [_build_biometria_response(b) for b in result.scalars().all()]


@global_router.delete("/{biometria_id}", status_code=200)
async def deletar_biometria(
    biometria_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    result = db.execute(select(Biometria).where(Biometria.id == biometria_id))
    bio = result.scalar_one_or_none()
    if not bio:
        raise HTTPException(status_code=404, detail="Biometria não encontrada.")
    registrar_auditoria(db, "EXCLUIR", "Biometria", bio.id, _user, dados_anteriores=snapshot(bio))
    db.delete(bio)
    db.flush()
    return {"detail": "Biometria excluída com sucesso.", "id": str(biometria_id)}


