"""SAD Carcinicultura — Rotas de Viveiros (RF-01)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.enums import RoleUsuario, StatusCiclo
from src.models.viveiro import Viveiro
from src.schemas.viveiro import ViveiroCreate, ViveiroResponse, ViveiroUpdate
from src.services.auth_service import get_current_user, has_role

router = APIRouter(prefix="/api/v1/viveiros", tags=["Viveiros"])


@router.post("/", response_model=ViveiroResponse, status_code=201)
async def criar_viveiro(
    payload: ViveiroCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Cadastra um novo viveiro (somente GESTOR)."""
    # Verificar duplicidade
    exists = await db.execute(
        select(Viveiro).where(Viveiro.identificacao == payload.identificacao)
    )
    if exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Viveiro '{payload.identificacao}' já existe.",
        )

    viveiro = Viveiro(**payload.model_dump())
    db.add(viveiro)
    await db.flush()
    await db.refresh(viveiro)
    return viveiro


@router.get("/", response_model=list[ViveiroResponse])
async def listar_viveiros(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Lista todos os viveiros com status e ciclos atuais."""
    result = await db.execute(
        select(Viveiro).order_by(Viveiro.identificacao)
    )
    return result.scalars().all()


@router.get("/{viveiro_id}", response_model=ViveiroResponse)
async def obter_viveiro(
    viveiro_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Retorna um viveiro específico por ID."""
    result = await db.execute(select(Viveiro).where(Viveiro.id == viveiro_id))
    viveiro = result.scalar_one_or_none()
    if not viveiro:
        raise HTTPException(status_code=404, detail="Viveiro não encontrado.")
    return viveiro


@router.put("/{viveiro_id}", response_model=ViveiroResponse)
async def atualizar_viveiro(
    viveiro_id: UUID,
    payload: ViveiroUpdate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Atualiza dados de um viveiro (somente GESTOR)."""
    result = await db.execute(select(Viveiro).where(Viveiro.id == viveiro_id))
    viveiro = result.scalar_one_or_none()
    if not viveiro:
        raise HTTPException(status_code=404, detail="Viveiro não encontrado.")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(viveiro, field, value)

    db.add(viveiro)
    await db.flush()
    await db.refresh(viveiro)
    return viveiro
