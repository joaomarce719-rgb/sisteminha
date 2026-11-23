"""Resumo financeiro e zootécnico de um ciclo: base do Financeiro e do histórico do viveiro (seção 5.6)."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.ciclo_produtivo import CicloProdutivo
from src.models.custo_operacional import CustoOperacional
from src.models.enums import CategoriaCusto, StatusCiclo
from src.models.insumo import ConsumoInsumo, Insumo
from src.services import decision_engine as de
from src.services import populacao as pv
from src.services.precos import regra_da_organizacao, tabela_vigente
from src.services.regras_data import hoje_da_fazenda
from src.services.sobrevivencia import ordenar, peso_na_data, sobrevivencia_vigente


@dataclass(frozen=True)
class SituacaoAtual:
    peso_medio_g: float | None
    taxa_sobrevivencia_pct: float
    populacao: int
    biomassa_kg: float | None
    preco_kg: float | None


def situacao_atual(db: Session, ciclo: CicloProdutivo, hoje: date) -> SituacaoAtual:
    """Peso da última biometria, população (descontadas as vendas), biomassa na água e preço de hoje.

    Exige ciclo povoado (pós-larvas preenchidas).
    """
    peso = peso_na_data(ciclo.biometrias, date.max)
    taxa = sobrevivencia_vigente(ciclo.manejos_alimentares)
    populacao = pv.populacao_vigente(ciclo.quantidade_pos_larvas, taxa, ciclo.vendas)
    biomassa = de.calcular_biomassa_kg(populacao, peso) if peso is not None else None
    preco = None
    if peso is not None:
        org = ciclo.viveiro.organizacao_id
        preco = de.buscar_preco_por_gramatura(peso, tabela_vigente(db, org, hoje), regra_da_organizacao(db, org))
    return SituacaoAtual(peso, taxa, populacao, biomassa, preco)


def _r2(valor: float | None) -> float | None:
    return None if valor is None else round(valor, 2)


def _racao_por_semana(
    ciclo: CicloProdutivo, biomassa_inicial: float, preco_racao: float | None
) -> list[dict]:
    """Ração por semana desde o povoamento, com custo e FCA parcial acumulado até o fim de cada semana."""
    manejos = ordenar(ciclo.manejos_alimentares)
    if not manejos:
        return []
    vendas = sorted(ciclo.vendas, key=lambda v: v.data_venda)
    kg_por_semana: dict[int, float] = defaultdict(float)
    for m in manejos:
        kg_por_semana[max(0, (m.data_registro - ciclo.data_povoamento).days // 7)] += m.quantidade_racao_kg
    finalizado = ciclo.status == StatusCiclo.FINALIZADO
    semanas, acumulado = [], 0.0
    taxa, j, k = 100.0, 0, 0  # taxa vigente, manejos e vendas já passados: uma passada só, sem refiltrar a cada semana
    for i in range(max(kg_por_semana) + 1):
        inicio = ciclo.data_povoamento + timedelta(days=7 * i)
        fim = inicio + timedelta(days=6)
        kg = kg_por_semana.get(i, 0.0)
        acumulado += kg
        fca = None
        while j < len(manejos) and manejos[j].data_registro <= fim:
            if manejos[j].taxa_sobrevivencia_estimada_fuzzy is not None:
                taxa = manejos[j].taxa_sobrevivencia_estimada_fuzzy
            j += 1
        while k < len(vendas) and vendas[k].data_venda <= fim:
            k += 1
        peso = peso_na_data(ciclo.biometrias, fim)
        if peso is not None and acumulado > 0:  # sem ração ainda, FCA 0 pareceria perfeito
            vendas_ate = vendas[:k]
            if finalizado and ciclo.data_despesca_real and fim >= ciclo.data_despesca_real:
                biomassa = 0.0  # a água foi esvaziada na despesca final
            else:
                populacao = pv.populacao_vigente(ciclo.quantidade_pos_larvas, taxa, vendas_ate)
                biomassa = de.calcular_biomassa_kg(populacao, peso)
            fca = de.calcular_fca(acumulado, biomassa, biomassa_inicial, pv.biomassa_vendida_kg(vendas_ate))
        semanas.append({
            "inicio": inicio,
            "fim": fim,
            "kg": round(kg, 2),
            "custo_rs": None if preco_racao is None else round(kg * preco_racao, 2),
            "fca_parcial": None if fca is None else round(fca, 3),
        })
    return semanas


def resumo_do_ciclo(db: Session, ciclo: CicloProdutivo, mostrar_valores: bool) -> dict:
    """Campos do Financeiro (`FinanceiroCicloResponse`) e do histórico (`HistoricoCicloResponse`).

    Sem `mostrar_valores` (CAMPO e VIGIA) todo campo em reais vem None.
    """
    vendas = ciclo.vendas
    custos = ciclo.custos_operacionais
    povoado = ciclo.quantidade_pos_larvas is not None
    finalizado = ciclo.status == StatusCiclo.FINALIZADO

    def rs(valor: float | None) -> float | None:
        return _r2(valor) if mostrar_valores else None

    # custos
    por_fase: dict[str, float] = defaultdict(float)
    por_categoria: dict[str, float] = defaultdict(float)
    por_fase_categoria: dict[tuple[str, str], float] = defaultdict(float)
    for c in custos:
        valor = float(c.valor_rs)
        por_fase[c.fase] += valor
        por_categoria[c.categoria.value] += valor
        por_fase_categoria[(c.fase, c.categoria.value)] += valor
    custo_total = sum(por_fase.values())
    custo_racao = por_categoria.get(CategoriaCusto.RACAO.value, 0.0)

    # vendas
    receita = pv.receita_realizada_rs(vendas)
    biomassa_vendida = pv.biomassa_vendida_kg(vendas)
    lucro_realizado = receita - custo_total
    margem = lucro_realizado / receita * 100 if receita > 0 else None
    custo_por_kg = custo_total / biomassa_vendida if biomassa_vendida > 0 else None
    finais = [v for v in vendas if v.tipo == "DESPESCA_FINAL"]
    biomassa_finais = sum(float(v.biomassa_kg) for v in finais)

    # ração: preço médio do kg = custo de ração lançado ÷ kg dos manejos (como em estimar_custo_diario)
    racao_total = sum(m.quantidade_racao_kg for m in ciclo.manejos_alimentares)
    preco_racao = custo_racao / racao_total if custo_racao > 0 and racao_total > 0 else None

    # zootécnicos e lucro estimado
    biomassa_inicial = de.calcular_biomassa_kg(ciclo.quantidade_pos_larvas or 0, ciclo.peso_medio_pl_g or 0.0)
    fca = lucro_estimado = sobrevivencia_final = peso_final = None
    tem_racao = racao_total > 0  # sem ração registrada, FCA 0 pareceria perfeito
    if finalizado:
        if ciclo.quantidade_pos_larvas:
            sobrevivencia_final = pv.animais_vendidos_ate(vendas) / ciclo.quantidade_pos_larvas * 100
        if biomassa_finais > 0:  # a última despesca final pode ter sido excluída por correção
            peso_final = sum(float(v.biomassa_kg) * float(v.peso_medio_g) for v in finais) / biomassa_finais
        if tem_racao:
            fca = de.calcular_fca(racao_total, 0.0, biomassa_inicial, biomassa_vendida)
    elif povoado:
        atual = situacao_atual(db, ciclo, hoje_da_fazenda())
        if atual.biomassa_kg is not None and tem_racao:
            fca = de.calcular_fca(racao_total, atual.biomassa_kg, biomassa_inicial, biomassa_vendida)
        lucro_estimado = de.calcular_metricas_economicas(
            [float(c.valor_rs) for c in custos], atual.biomassa_kg, atual.preco_kg, receita
        ).lucro_operacional

    # insumos usados
    usos = db.execute(
        select(Insumo.id, Insumo.nome, Insumo.unidade_uso, ConsumoInsumo.quantidade,
               ConsumoInsumo.preco_unitario_rs, ConsumoInsumo.recalculado_em, CustoOperacional.valor_rs)
        .join(Insumo, ConsumoInsumo.insumo_id == Insumo.id)
        .outerjoin(CustoOperacional, ConsumoInsumo.custo_id == CustoOperacional.id)
        .where(ConsumoInsumo.ciclo_id == ciclo.id)
        .order_by(Insumo.nome)
    ).all()
    insumos: dict = {}
    for u in usos:
        item = insumos.setdefault(u.id, {"insumo_id": u.id, "nome": u.nome, "unidade_uso": u.unidade_uso,
                                         "quantidade_total": 0.0, "custo_total_rs": None})
        item["quantidade_total"] += float(u.quantidade)
        if u.valor_rs is not None:  # None = nenhum uso com valor (R$ 0,00 pareceria insumo de graça)
            item["custo_total_rs"] = (item["custo_total_rs"] or 0.0) + float(u.valor_rs)
    for item in insumos.values():
        item["quantidade_total"] = round(item["quantidade_total"], 4)
        item["custo_total_rs"] = rs(item["custo_total_rs"])
    recalculos = [u.recalculado_em for u in usos if u.recalculado_em is not None]

    racao_por_semana = _racao_por_semana(ciclo, biomassa_inicial, preco_racao) if povoado else []
    if not mostrar_valores:
        for semana in racao_por_semana:
            semana["custo_rs"] = None

    return {
        # identificação
        "ciclo_id": ciclo.id,
        "status": ciclo.status,
        "data_povoamento": ciclo.data_povoamento,
        "data_despesca_real": ciclo.data_despesca_real,
        "quantidade_pos_larvas": ciclo.quantidade_pos_larvas,
        "etapas": [
            {"tipo": e.tipo, "status": e.status, "data_inicio": e.data_inicio, "data_fim": e.data_fim}
            for e in ciclo.etapas_preparo
        ],
        # financeiro
        "custos_por_fase": {k: rs(v) for k, v in por_fase.items()},
        "custos_por_categoria": {k: rs(v) for k, v in por_categoria.items()},
        "custos_fase_categoria": [
            {"fase": fase, "categoria": categoria, "total_rs": rs(v)}
            for (fase, categoria), v in sorted(por_fase_categoria.items())
        ],
        "vendas_lista": vendas,
        "receita_realizada_rs": rs(receita),
        "custo_total_rs": rs(custo_total),
        "lucro_realizado_rs": rs(lucro_realizado),
        "margem_realizada_pct": rs(margem),
        "margem_pct": rs(margem),
        "lucro_estimado_se_despescar_hoje_rs": rs(lucro_estimado),
        "custo_por_kg_rs": rs(custo_por_kg),
        "definitivo": finalizado,
        "usos_pendentes": sum(1 for u in usos if u.preco_unitario_rs is None),
        "valores_recalculados_em": max(recalculos, default=None),
        # histórico
        "insumos": list(insumos.values()),
        "racao_total_kg": round(racao_total, 2),
        "racao_custo_rs": rs(custo_racao),
        "racao_por_semana": racao_por_semana,
        "vendas": {"quantidade": len(vendas), "biomassa_total_kg": round(biomassa_vendida, 2), "receita_rs": rs(receita)},
        "peso_final_g": _r2(peso_final),
        "sobrevivencia_final_pct": _r2(sobrevivencia_final),
        "fca": None if fca is None else round(fca, 3),
    }
