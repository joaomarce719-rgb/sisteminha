"""SAD Carcinicultura — Rotas de Tabela de Preços de Mercado (RF-07)."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.escopo import org_do_usuario
from src.services.audit import registrar_auditoria, snapshot
from src.models.enums import RoleUsuario
from src.models.tabela_preco import TabelaPrecoMercado
from src.schemas.preco import PrecoCreate, PrecoResponse, PrecoUpdate
from src.services.auth_service import has_role

router = APIRouter(prefix="/api/v1/precos-mercado", tags=["Preços de Mercado"])


def _exigir_sem_sobreposicao(
    db: Session,
    organizacao_id: UUID,
    peso_min: float,
    peso_max: float,
    inicio: date,
    fim: date | None,
    ignorar_id: UUID | None = None,
) -> None:
    """Recusa faixa que dispute o mesmo peso e o mesmo período com outra da organização.

    Faixas vizinhas (8–10 e 10–12) são válidas: o peso de divisa pertence à faixa de cima.
    Preços de períodos diferentes para a mesma faixa também são válidos (histórico).
    """
    existentes = db.execute(
        select(TabelaPrecoMercado).where(TabelaPrecoMercado.organizacao_id == organizacao_id)
    ).scalars().all()
    for f in existentes:
        if f.id == ignorar_id:
            continue
        pesos_se_cruzam = peso_min < f.faixa_gramatura_max and f.faixa_gramatura_min < peso_max
        periodos_se_cruzam = (fim is None or f.vigencia_inicio <= fim) and (
            f.vigencia_fim is None or inicio <= f.vigencia_fim
        )
        if pesos_se_cruzam and periodos_se_cruzam:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"A faixa {peso_min:g}–{peso_max:g} g se sobrepõe à faixa "
                    f"{f.faixa_gramatura_min:g}–{f.faixa_gramatura_max:g} g (R$ {float(f.preco_por_kg):,.2f}/kg) "
                    "no mesmo período. Ajuste os pesos ou encerre a vigência da faixa anterior."
                ),
            )


@router.post("", response_model=PrecoResponse, status_code=201)
@router.post("/", response_model=PrecoResponse, status_code=201)
def criar_faixa_preco(
    payload: PrecoCreate,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Cria nova faixa de preço por gramatura (RF-07, somente GESTOR)."""
    if payload.faixa_gramatura_min >= payload.faixa_gramatura_max:
        raise HTTPException(
            status_code=400,
            detail="faixa_gramatura_min deve ser menor que faixa_gramatura_max.",
        )

    org_id = org_do_usuario(_user)
    _exigir_sem_sobreposicao(
        db, org_id, payload.faixa_gramatura_min, payload.faixa_gramatura_max,
        payload.vigencia_inicio, payload.vigencia_fim,
    )
    preco = TabelaPrecoMercado(**payload.model_dump(), organizacao_id=org_id)
    db.add(preco)
    db.flush()
    db.refresh(preco)
    registrar_auditoria(db, "CRIAR", "TabelaPrecoMercado", preco.id, _user, dados_novos=snapshot(preco))
    return preco


@router.get("", response_model=list[PrecoResponse])
@router.get("/", response_model=list[PrecoResponse])
def listar_precos(
    vigentes: bool = True,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Lista faixas de preço (somente GESTOR — RN-11)."""
    query = (
        select(TabelaPrecoMercado)
        .where(TabelaPrecoMercado.organizacao_id == org_do_usuario(_user))
        .order_by(TabelaPrecoMercado.faixa_gramatura_min)
    )
    if vigentes:
        hoje = date.today()
        query = query.where(
            TabelaPrecoMercado.vigencia_inicio <= hoje,
            (TabelaPrecoMercado.vigencia_fim.is_(None))
            | (TabelaPrecoMercado.vigencia_fim >= hoje),
        )
    result = db.execute(query)
    return result.scalars().all()


@router.put("/{preco_id}", response_model=PrecoResponse)
def atualizar_preco(
    preco_id: UUID,
    payload: PrecoUpdate,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Atualiza preço ou vigência de uma faixa."""
    result = db.execute(
        select(TabelaPrecoMercado).where(TabelaPrecoMercado.id == preco_id)
    )
    preco = result.scalar_one_or_none()
    if not preco or preco.organizacao_id != org_do_usuario(_user):
        raise HTTPException(status_code=404, detail="Faixa de preço não encontrada.")

    antes = snapshot(preco)
    update_data = payload.model_dump(exclude_unset=True)
    if "vigencia_fim" in update_data:
        _exigir_sem_sobreposicao(
            db, preco.organizacao_id, preco.faixa_gramatura_min, preco.faixa_gramatura_max,
            preco.vigencia_inicio, update_data["vigencia_fim"], ignorar_id=preco.id,
        )
    for field, value in update_data.items():
        setattr(preco, field, value)

    db.add(preco)
    db.flush()
    db.refresh(preco)
    registrar_auditoria(db, "ATUALIZAR", "TabelaPrecoMercado", preco.id, _user, antes, snapshot(preco))
    return preco
