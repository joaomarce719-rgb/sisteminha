"""SAD Carcinicultura — Rotas de vendas do ciclo (desbaste e despesca final), só GESTOR."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database import get_db
from src.dependencies import require_gestor
from src.models.ciclo_produtivo import CicloProdutivo
from src.models.enums import StatusCiclo
from src.models.usuario import Usuario
from src.models.venda_ciclo import VendaCiclo
from src.schemas.venda import PrecoSugeridoResponse, VendaCreate, VendaResponse
from src.services.audit import registrar_auditoria, snapshot
from src.services.escopo import verificar_ciclo_da_organizacao
from src.services.regras_ciclo import obter_ciclo
from src.services.vendas import colunas_da_venda, preco_da_tabela, sincronizar_totais_do_ciclo

router = APIRouter(
    prefix="/api/v1/ciclos/{ciclo_id}/vendas",
    tags=["Vendas do Ciclo"],
    dependencies=[Depends(verificar_ciclo_da_organizacao)],
)

def _validar_status(ciclo: CicloProdutivo, tipo: str, tipo_atual: str | None = None) -> None:
    """DESBASTE só com o ciclo aberto; a despesca final também no finalizado, como correção.

    Corrigir ou excluir uma venda já lançada (`tipo_atual`) vale no ciclo finalizado, mas não
    permite transformá-la em desbaste depois do encerramento.
    """
    permitidos = {StatusCiclo.ATIVO, StatusCiclo.PAUSADO}
    if tipo == "DESPESCA_FINAL" or tipo == tipo_atual:
        permitidos.add(StatusCiclo.FINALIZADO)
    if ciclo.status not in permitidos:
        raise HTTPException(
            status_code=400, detail=f"Ciclo {ciclo.status.value.lower()} não aceita venda do tipo {tipo}."
        )


def _venda_do_ciclo(db: Session, ciclo_id: UUID, venda_id: UUID) -> VendaCiclo:
    venda = db.get(VendaCiclo, venda_id)
    if not venda or venda.ciclo_id != ciclo_id:
        raise HTTPException(status_code=404, detail="Venda não encontrada.")
    return venda


@router.post("", response_model=VendaResponse, status_code=201)
@router.post("/", response_model=VendaResponse, status_code=201)
def lancar_venda(
    ciclo_id: UUID,
    payload: VendaCreate,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_gestor),
):
    """Lança uma venda; os animais vendidos saem da população do ciclo."""
    ciclo = obter_ciclo(db, ciclo_id)
    _validar_status(ciclo, payload.tipo)
    venda = VendaCiclo(ciclo_id=ciclo_id, **colunas_da_venda(db, ciclo, payload))
    db.add(venda)
    db.flush()
    sincronizar_totais_do_ciclo(db, ciclo)
    registrar_auditoria(db, "CRIAR_VENDA", "VendaCiclo", venda.id, _user, dados_novos=snapshot(venda))
    return venda


@router.get("", response_model=list[VendaResponse])
@router.get("/", response_model=list[VendaResponse])
def listar_vendas(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_gestor),
):
    """Vendas do ciclo, da mais recente para a mais antiga."""
    return db.scalars(
        select(VendaCiclo)
        .where(VendaCiclo.ciclo_id == ciclo_id)
        .order_by(VendaCiclo.data_venda.desc(), VendaCiclo.created_at.desc())
    ).all()


@router.get("/preco-sugerido", response_model=PrecoSugeridoResponse)
def preco_sugerido(
    ciclo_id: UUID,
    peso_medio_g: float = Query(..., ge=0.01, le=999_999),
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_gestor),
):
    """Preço por kg da tabela de preços para o peso médio; `None` quando não há faixa."""
    return PrecoSugeridoResponse(preco_kg=preco_da_tabela(db, obter_ciclo(db, ciclo_id), peso_medio_g))


@router.put("/{venda_id}", response_model=VendaResponse)
def corrigir_venda(
    ciclo_id: UUID,
    venda_id: UUID,
    payload: VendaCreate,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_gestor),
):
    """Corrige uma venda (reenvia os campos); animais e valor total são recalculados.

    Com biomassa e preço iguais aos gravados, o valor total fica: a venda do encerramento guarda a
    receita informada, que biomassa × preço arredondado a centavos não reproduz.
    """
    venda = _venda_do_ciclo(db, ciclo_id, venda_id)
    ciclo = obter_ciclo(db, ciclo_id)
    _validar_status(ciclo, payload.tipo, venda.tipo)
    if payload.preco_kg is None and round(payload.peso_medio_g, 2) == float(venda.peso_medio_g):
        # sem preço e com o mesmo peso, vale o preço gravado: a tabela de hoje não reprecifica a venda
        payload = payload.model_copy(update={"preco_kg": float(venda.preco_kg)})
    colunas = colunas_da_venda(db, ciclo, payload)
    if colunas["biomassa_kg"] == float(venda.biomassa_kg) and colunas["preco_kg"] == float(venda.preco_kg):
        colunas["valor_total_rs"] = venda.valor_total_rs
    antes = snapshot(venda)
    for campo, valor in colunas.items():
        setattr(venda, campo, valor)
    db.flush()
    sincronizar_totais_do_ciclo(db, ciclo)
    registrar_auditoria(
        db, "ATUALIZAR_VENDA", "VendaCiclo", venda.id, _user, dados_anteriores=antes, dados_novos=snapshot(venda)
    )
    return venda


@router.delete("/{venda_id}", status_code=204)
def excluir_venda(
    ciclo_id: UUID,
    venda_id: UUID,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_gestor),
):
    """Exclui a venda: os animais voltam à população do ciclo."""
    venda = _venda_do_ciclo(db, ciclo_id, venda_id)
    ciclo = obter_ciclo(db, ciclo_id)
    _validar_status(ciclo, venda.tipo, venda.tipo)
    if ciclo.status == StatusCiclo.FINALIZADO and venda.tipo == "DESPESCA_FINAL":
        outras_finais = db.scalar(select(func.count()).select_from(VendaCiclo).where(
            VendaCiclo.ciclo_id == ciclo_id, VendaCiclo.tipo == "DESPESCA_FINAL", VendaCiclo.id != venda_id
        ))
        if not outras_finais:
            raise HTTPException(
                status_code=409,
                detail="Esta é a única despesca final do ciclo encerrado: corrija a venda em vez de excluí-la, "
                "ou lance outra despesca final antes.",
            )
    antes = snapshot(venda)
    db.delete(venda)
    db.flush()
    sincronizar_totais_do_ciclo(db, ciclo)
    registrar_auditoria(db, "EXCLUIR_VENDA", "VendaCiclo", venda_id, _user, dados_anteriores=antes)
