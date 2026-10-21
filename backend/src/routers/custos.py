"""SAD Carcinicultura — Rotas de Custos Operacionais (RF-08)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.custo_operacional import CustoOperacional
from src.models.enums import RoleUsuario
from src.schemas.custo import CustoCreate, CustoListResponse, CustoResumoResponse, CustoResponse
from src.services.auth_service import has_role
from src.services.audit import registrar_auditoria

router = APIRouter(prefix="/api/v1/ciclos/{ciclo_id}/custos", tags=["Custos Operacionais"])



@router.post("", response_model=CustoResponse, status_code=201)
@router.post("/", response_model=CustoResponse, status_code=201)
async def lancar_custo(
    ciclo_id: UUID,
    payload: CustoCreate,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Registra uma despesa operacional vinculada ao ciclo (RF-08)."""
    custo = CustoOperacional(
        ciclo_id=ciclo_id,
        **payload.model_dump(exclude={"ciclo_id"}),
    )
    db.add(custo)
    db.flush()

    registrar_auditoria(
        db=db,
        acao="CRIAR_CUSTO",
        entidade="CustoOperacional",
        registro_id=custo.id,
        usuario=_user,
        dados_novos={
            "ciclo_id": str(ciclo_id),
            "data_lancamento": str(custo.data_lancamento),
            "categoria": custo.categoria.value,
            "descricao": custo.descricao,
            "valor_rs": float(custo.valor_rs),
        },
    )

    db.refresh(custo)
    return custo


@router.get("", response_model=list[CustoResponse])
@router.get("/", response_model=list[CustoResponse])
async def listar_custos(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Lista todos os custos do ciclo (somente GESTOR — RN-11)."""
    result = db.execute(
        select(CustoOperacional)
        .where(CustoOperacional.ciclo_id == ciclo_id)
        .order_by(CustoOperacional.data_lancamento)
    )
    return result.scalars().all()


@router.get("/resumo", response_model=list[CustoResumoResponse])
async def resumo_custos(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Resumo de custos agrupados por categoria (somente GESTOR)."""
    result = db.execute(
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


@router.get("/exportar-csv")
async def exportar_custos_csv(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Exporta custos do ciclo em formato CSV delimitado para Excel (RF-025, UC-012)."""
    import csv
    import io
    from fastapi.responses import Response

    result = db.execute(
        select(CustoOperacional)
        .where(CustoOperacional.ciclo_id == ciclo_id)
        .order_by(CustoOperacional.data_lancamento)
    )
    custos = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["ID", "Data_Lancamento", "Categoria", "Descricao", "Valor_RS"])
    for c in custos:
        writer.writerow([
            str(c.id),
            c.data_lancamento.isoformat(),
            c.categoria.value,
            c.descricao,
            f"{float(c.valor_rs):.2f}".replace(".", ","),
        ])

    content = output.getvalue().encode("utf-8-sig")
    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="custos_ciclo_{str(ciclo_id)[:8]}.csv"'
        },
    )


global_router = APIRouter(prefix="/api/v1/custos", tags=["Custos Operacionais"])


@global_router.post("/", response_model=CustoResponse, status_code=201)
async def lancar_custo_global(
    payload: CustoCreate,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    if not payload.ciclo_id:
        raise HTTPException(status_code=422, detail="ciclo_id é obrigatório.")
    return await lancar_custo(payload.ciclo_id, payload, db, _user)


@global_router.get("/", response_model=CustoListResponse)
async def listar_custos_global(
    ciclo_id: UUID | None = None,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    query = select(CustoOperacional).order_by(CustoOperacional.data_lancamento.desc())
    if ciclo_id:
        query = query.where(CustoOperacional.ciclo_id == ciclo_id)
    custos = db.scalars(query).all()
    total_rs = sum(float(c.valor_rs) for c in custos)
    return {
        "items": custos,
        "total": len(custos),
        "summary": {
            "total_custos_rs": total_rs,
            "total_valor": total_rs,
            "quantidade": len(custos),
            "roa": 0.0,
            "roe": 0.0,
        },
    }


@global_router.delete("/{custo_id}", status_code=200)
async def deletar_custo(
    custo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    result = db.execute(select(CustoOperacional).where(CustoOperacional.id == custo_id))
    custo = result.scalar_one_or_none()
    if not custo:
        raise HTTPException(status_code=404, detail="Custo não encontrado.")
    db.delete(custo)
    db.flush()
    return {"detail": "Custo excluído com sucesso.", "id": str(custo_id)}


