"""SAD Carcinicultura — Regras de venda compartilhadas: colunas derivadas, preço da tabela e totais do ciclo."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.ciclo_produtivo import CicloProdutivo
from src.models.enums import StatusCiclo
from src.models.venda_ciclo import VendaCiclo
from src.schemas.venda import VendaCreate
from src.services.decision_engine import buscar_preco_por_gramatura
from src.services.populacao import biomassa_vendida_kg, receita_realizada_rs
from src.services.precos import regra_da_organizacao, tabela_vigente
from src.services.regras_ciclo import validar_data_no_ciclo
from src.services.regras_data import exigir_retroativo_para_data_passada, hoje_da_fazenda

# limites das colunas: Integer (32 bits) e Numeric(12,2)
_MAX_ANIMAIS = 2_147_483_647
_MAX_VALOR_RS = 9_999_999_999.99


def sincronizar_totais_do_ciclo(db: Session, ciclo: CicloProdutivo) -> None:
    """Com o ciclo finalizado, biomassa colhida e receita real passam a ser a soma das vendas,
    e a data da despesca, a da última despesca final."""
    if ciclo.status != StatusCiclo.FINALIZADO:
        return
    db.flush()
    vendas = db.scalars(select(VendaCiclo).where(VendaCiclo.ciclo_id == ciclo.id)).all()
    ciclo.biomassa_colhida_kg = round(biomassa_vendida_kg(vendas), 2)
    ciclo.receita_real_rs = round(receita_realizada_rs(vendas), 2)
    datas_finais = [v.data_venda for v in vendas if v.tipo == "DESPESCA_FINAL"]
    if datas_finais:
        ciclo.data_despesca_real = max(datas_finais)


def preco_da_tabela(db: Session, ciclo: CicloProdutivo, peso_medio_g: float) -> float | None:
    """Preço sugerido para a gramatura: tabela vigente hoje e regra de arredondamento da organização."""
    organizacao_id = ciclo.viveiro.organizacao_id
    return buscar_preco_por_gramatura(
        peso_medio_g, tabela_vigente(db, organizacao_id, hoje_da_fazenda()), regra_da_organizacao(db, organizacao_id)
    )


def colunas_da_venda(db: Session, ciclo: CicloProdutivo, payload: VendaCreate) -> dict:
    """Valida datas, resolve o preço e deriva animais e valor total (arredondados como as colunas)."""
    exigir_retroativo_para_data_passada(payload.data_venda, payload.retroativo, "A data da venda")
    validar_data_no_ciclo(ciclo, payload.data_venda, "A data da venda")
    biomassa = round(payload.biomassa_kg, 2)
    peso = round(payload.peso_medio_g, 2)
    preco = payload.preco_kg if payload.preco_kg is not None else preco_da_tabela(db, ciclo, peso)
    if preco is None:
        raise HTTPException(
            status_code=422,
            detail=f"Sem preço na tabela de preços para {peso:g} g: informe o preço por kg.",
        )
    preco = round(preco, 2)
    animais = round(biomassa * 1000 / peso)
    valor = round(biomassa * preco, 2)
    if animais > _MAX_ANIMAIS or valor > _MAX_VALOR_RS:
        raise HTTPException(status_code=422, detail="Biomassa, peso médio e preço resultam em valores grandes demais.")
    return {
        **payload.model_dump(),
        "biomassa_kg": biomassa,
        "peso_medio_g": peso,
        "preco_kg": preco,
        "animais_estimados": animais,
        "valor_total_rs": valor,
    }
