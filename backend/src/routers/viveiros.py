"""SAD Carcinicultura — Rotas de Viveiros (RF-01)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.audit import registrar_auditoria, snapshot
from src.models.enums import RoleUsuario, StatusCiclo
from src.models.viveiro import Viveiro
from src.schemas.viveiro import ViveiroCreate, ViveiroListResponse, ViveiroResponse, ViveiroUpdate
from src.services.auth_service import get_current_user, has_role

router = APIRouter(prefix="/api/v1/viveiros", tags=["Viveiros"])


@router.post("", response_model=ViveiroResponse, status_code=201)
@router.post("/", response_model=ViveiroResponse, status_code=201)
async def criar_viveiro(
    payload: ViveiroCreate,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Cadastra um novo viveiro (somente GESTOR)."""
    # Verificar duplicidade
    exists = db.execute(
        select(Viveiro).where(Viveiro.identificacao == payload.identificacao)
    )
    if exists.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Viveiro '{payload.identificacao}' já existe.",
        )

    viveiro = Viveiro(**payload.model_dump())
    db.add(viveiro)
    db.flush()
    db.refresh(viveiro)
    registrar_auditoria(db, "CRIAR", "Viveiro", viveiro.id, _user, dados_novos=snapshot(viveiro))
    return viveiro


@router.get("", response_model=ViveiroListResponse)
@router.get("/", response_model=ViveiroListResponse)
async def listar_viveiros(
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Lista todos os viveiros com paginação e KPIs agregados."""
    result = db.execute(
        select(Viveiro).order_by(Viveiro.identificacao)
    )
    viveiros = result.scalars().all()
    ativos_count = sum(1 for v in viveiros if v.status_ativo)
    area_total = sum(v.area_util_m2 for v in viveiros if v.status_ativo)
    
    return {
        "items": viveiros,
        "total": len(viveiros),
        "kpis": {
            "total_viveiros": len(viveiros),
            "ativos": ativos_count,
            "area_total_m2": area_total,
        },
    }



@router.get("/{viveiro_id}", response_model=ViveiroResponse)
async def obter_viveiro(
    viveiro_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Retorna um viveiro específico por ID."""
    result = db.execute(select(Viveiro).where(Viveiro.id == viveiro_id))
    viveiro = result.scalar_one_or_none()
    if not viveiro:
        raise HTTPException(status_code=404, detail="Viveiro não encontrado.")
    return viveiro


@router.put("/{viveiro_id}", response_model=ViveiroResponse)
async def atualizar_viveiro(
    viveiro_id: UUID,
    payload: ViveiroUpdate,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Atualiza dados de um viveiro (somente GESTOR)."""
    result = db.execute(select(Viveiro).where(Viveiro.id == viveiro_id))
    viveiro = result.scalar_one_or_none()
    if not viveiro:
        raise HTTPException(status_code=404, detail="Viveiro não encontrado.")

    antes = snapshot(viveiro)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(viveiro, field, value)

    db.add(viveiro)
    db.flush()
    db.refresh(viveiro)
    registrar_auditoria(db, "ATUALIZAR", "Viveiro", viveiro.id, _user, antes, snapshot(viveiro))
    return viveiro


@router.delete("/{viveiro_id}", status_code=status.HTTP_200_OK)
async def deletar_viveiro(
    viveiro_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Exclui um viveiro por ID."""
    result = db.execute(select(Viveiro).where(Viveiro.id == viveiro_id))
    viveiro = result.scalar_one_or_none()
    if not viveiro:
        raise HTTPException(status_code=404, detail="Viveiro não encontrado.")
    if viveiro.ciclos:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Viveiro possui ciclos registrados; inative-o para preservar o histórico.",
        )
    registrar_auditoria(db, "EXCLUIR", "Viveiro", viveiro.id, _user, dados_anteriores=snapshot(viveiro))
    db.delete(viveiro)
    db.flush()
    return {"detail": "Viveiro excluído com sucesso.", "id": str(viveiro_id)}

