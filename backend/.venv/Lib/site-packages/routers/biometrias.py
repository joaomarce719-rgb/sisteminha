"""SAD Carcinicultura — Rotas de Biometria (RF-03)."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.biometria import Biometria
from src.models.ciclo_produtivo import CicloProdutivo
from src.models.enums import RoleUsuario, StatusCiclo
from src.schemas.biometria import BiometriaCreate, BiometriaResponse
from src.services.auth_service import has_role
from src.services.decision_engine import calcular_ganho_diario, calcular_ganho_semanal

router = APIRouter(prefix="/api/v1/ciclos/{ciclo_id}/biometrias", tags=["Biometrias"])


async def _get_ciclo_ativo(ciclo_id: UUID, db: Session) -> CicloProdutivo:
    result = db.execute(select(CicloProdutivo).where(CicloProdutivo.id == ciclo_id))
    ciclo = result.scalar_one_or_none()
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo não encontrado.")
    if ciclo.status != StatusCiclo.ATIVO:
        raise HTTPException(status_code=400, detail="Ciclo não está ativo.")
    return ciclo


@router.post("/", response_model=BiometriaResponse, status_code=201)
async def registrar_biometria(
    ciclo_id: UUID,
    payload: BiometriaCreate,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.CAMPO, RoleUsuario.GESTOR])),
):
    """Registra uma amostragem biométrica (RF-03)."""
    ciclo = await _get_ciclo_ativo(ciclo_id, db)

    # Calcular ganho em relação à última biometria
    biometrias = sorted(ciclo.biometrias, key=lambda b: b.data_medicao)
    ganho_semanal = None
    if biometrias:
        ultima = biometrias[-1]
        dias = (payload.data_medicao - ultima.data_medicao).days
        if dias > 0:
            ganho_diario = calcular_ganho_diario(
                ultima.peso_medio_g, payload.peso_medio_g, dias
            )
            ganho_semanal = round(calcular_ganho_semanal(ganho_diario), 2)

    bio = Biometria(
        ciclo_id=ciclo_id,
        data_medicao=payload.data_medicao,
        peso_medio_g=payload.peso_medio_g,
        ganho_medio_semanal_g=ganho_semanal,
        uniformidade_percentual=payload.uniformidade_percentual,
        observacoes=payload.observacoes,
    )
    db.add(bio)
    db.flush()
    db.refresh(bio)
    return bio


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
    return result.scalars().all()
