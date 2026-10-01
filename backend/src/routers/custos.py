"""SAD Carcinicultura — Rotas de Custos Operacionais (RF-08)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.custo_operacional import CustoOperacional
from src.models.enums import RoleUsuario
from src.schemas.custo import CustoCreate, CustoResumoResponse, CustoResponse
from src.services.auth_service import has_role

router = APIRouter(prefix="/api/v1/ciclos/{ciclo_id}/custos", tags=["Custos Operacionais"])


@router.post("/", response_model=CustoResponse, status_code=201)
async def lancar_custo(
    ciclo_id: UUID,
    payload: CustoCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Registra uma despesa operacional vinculada ao ciclo (RF-08)."""
    custo = CustoOperacional(
        ciclo_id=ciclo_id,
        **payload.model_dump(),
    )
    db.add(custo)
    await db.flush()
    await db.refresh(custo)
    return custo


@router.get("/", response_model=list[CustoResponse])
async def listar_custos(
    ciclo_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Lista todos os custos do ciclo (somente GESTOR — RN-11)."""
    result = await db.execute(
        select(CustoOperacional)
        .where(CustoOperacional.ciclo_id == ciclo_id)
        .order_by(CustoOperacional.data_lancamento)
    )
    return result.scalars().all()


@router.get("/resumo", response_model=list[CustoResumoResponse])
async def resumo_custos(
    ciclo_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Resumo de custos agrupados por categoria (somente GESTOR)."""
    result = await db.execute(
        select(
            CustoOperacional.categoria,
            func.sum(CustoOperacional.valor_rs).label("total_rs"),
            func.count().label("qtd_lancamentos"),
        )
        .where(CustoOperacional.ciclo_id == ciclo_id)
        .group_by(CustoOperacional.categoria)
    )
    rows = result.all()
    return [
        CustoResumoResponse(
            categoria=row.categoria,
            total_rs=float(row.total_rs),
            qtd_lancamentos=row.qtd_lancamentos,
        )
        for row in rows
    ]
