"""SAD Carcinicultura — Motor de Decisão Bioeconômica.

Implementa todas as fórmulas zootécnicas e econômicas do SRS:
- RN-01: Densidade de estocagem
- RN-02: Dinâmica da população sobrevivente
- RN-03: Fator de Conversão Alimentar (FCA)
- RN-04: Tabela alimentar de Clifford (1992) com interpolação linear
- RN-06: Métricas econômicas (CO, RB, LO, MO)
- RN-07: Algoritmo preditivo Delta V (ΔV) para decisão de despesca
"""

from dataclasses import dataclass
from datetime import date

import numpy as np

from src.models.enums import ClassificacaoFCA, RecomendacaoDespesca


# ── Tabela de Clifford (1992) — RN-04 ──────────────
# Pontos de referência: peso (g) → taxa alimentar (%)
# Tabela 1 do documento de referência (adaptado de Clifford, 1992), de 2 g a 20 g
_CLIFFORD_POINTS = np.array([
    [2.0, 7.15], [3.0, 6.13], [4.0, 5.50], [5.0, 5.05], [6.0, 4.71],
    [7.0, 4.44], [8.0, 4.22], [9.0, 4.04], [10.0, 3.88], [11.0, 3.74],
    [12.0, 3.62], [13.0, 3.51], [14.0, 3.42], [15.0, 3.33], [16.0, 3.25],
    [17.0, 3.17], [18.0, 3.10], [19.0, 3.04], [20.0, 2.98],
])
_CLIFFORD_PESOS = _CLIFFORD_POINTS[:, 0]
_CLIFFORD_TAXAS = _CLIFFORD_POINTS[:, 1]


def taxa_alimentar(peso_medio_g: float, pontos: list[tuple[float, float]] | None = None) -> float:
    """Retorna a taxa alimentar (%) por interpolação linear de pontos customizados ou da tabela Clifford."""
    if pontos and len(pontos) >= 2:
        pts = sorted(pontos, key=lambda p: p[0])
        pesos = [p[0] for p in pts]
        taxas = [p[1] for p in pts]
        return float(np.interp(peso_medio_g, pesos, taxas))
    return float(np.interp(peso_medio_g, _CLIFFORD_PESOS, _CLIFFORD_TAXAS))


def taxa_alimentar_clifford(peso_medio_g: float) -> float:
    """Retorna a taxa alimentar (%) por interpolação linear da tabela de Clifford (1992)."""
    return taxa_alimentar(peso_medio_g)


# ── RN-01: Densidade de Estocagem ───────────────────
def calcular_densidade(n_pos_larvas: int, area_m2: float) -> float:
    """D = N / A (camarões/m²)."""
    if area_m2 <= 0:
        raise ValueError("Área útil deve ser > 0.")
    return n_pos_larvas / area_m2


def verificar_hiperdensidade(densidade: float, limite: float = 50.0) -> bool:
    """Retorna True se D > limite (semi-intensivo no Vale do Jaguaribe)."""
    return densidade > limite


# ── RN-02: População Sobrevivente ────────────────────
def calcular_populacao_atual(pop_inicial: int, taxa_sobrev_pct: float) -> int:
    """Pop_Atual = Pop_Inicial × (Taxa_Sobrevivência / 100)."""
    return int(pop_inicial * (taxa_sobrev_pct / 100.0))


def calcular_biomassa_kg(populacao: int, peso_medio_g: float) -> float:
    """B (kg) = (Pop × Peso_Médio_g) / 1000."""
    return (populacao * peso_medio_g) / 1000.0


# ── RN-03: Fator de Conversão Alimentar ──────────────
def calcular_fca(racao_total_kg: float, biomassa_atual_kg: float, biomassa_inicial_kg: float) -> float | None:
    """FCA = Ração_Total / (Biomassa_Atual - Biomassa_Inicial).

    Retorna None se o ganho de biomassa for zero ou negativo.
    """
    ganho = biomassa_atual_kg - biomassa_inicial_kg
    if ganho <= 0:
        return None
    return racao_total_kg / ganho


def classificar_fca(fca: float | None) -> ClassificacaoFCA | None:
    """Classifica o FCA conforme RN-03."""
    if fca is None:
        return None
    if fca <= 1.2:
        return ClassificacaoFCA.ALTA_EFICIENCIA
    if fca <= 1.6:
        return ClassificacaoFCA.FAIXA_PADRAO
    return ClassificacaoFCA.DESPERDICIO_INDICADO


# ── RN-04: Ração Diária Sugerida ────────────────────
def calcular_racao_diaria(
    biomassa_kg: float,
    peso_medio_g: float,
    pontos: list[tuple[float, float]] | None = None,
) -> float:
    """Q (kg) = B × (Taxa / 100)."""
    taxa = taxa_alimentar(peso_medio_g, pontos)
    return biomassa_kg * (taxa / 100.0)


# ── RN-06: Métricas Econômicas (RN-015: Indisponível se dados faltarem) ──
@dataclass
class MetricasEconomicas:
    custo_operacional_total: float
    receita_bruta: float | None
    lucro_operacional: float | None
    margem_operacional_pct: float | None


def calcular_metricas_economicas(
    custos: list[float],
    biomassa_kg: float | None,
    preco_venda_kg: float | None,
) -> MetricasEconomicas:
    """Calcula CO, RB, LO e MO conforme RN-06 e RN-015."""
    co_total = sum(custos)
    if biomassa_kg is None or preco_venda_kg is None or preco_venda_kg <= 0:
        return MetricasEconomicas(
            custo_operacional_total=co_total,
            receita_bruta=None,
            lucro_operacional=None,
            margem_operacional_pct=None,
        )
    receita = biomassa_kg * preco_venda_kg
    lucro = receita - co_total
    margem = (lucro / receita * 100.0) if receita > 0 else None
    return MetricasEconomicas(
        custo_operacional_total=co_total,
        receita_bruta=receita,
        lucro_operacional=lucro,
        margem_operacional_pct=margem,
    )


# ── RF-019 / RN-014: Retorno sobre Ativos (ROA) e Patrimônio (ROE) ──
def calcular_roa(lucro_liquido: float | None, ativo_total: float | None) -> float | None:
    """ROA = (Lucro Líquido / Ativo Total) * 100. Retorna None se insumos faltarem (Critério 4)."""
    if lucro_liquido is None or ativo_total is None or ativo_total <= 0:
        return None
    return (lucro_liquido / ativo_total) * 100.0


def calcular_roe(lucro_liquido: float | None, patrimonio_liquido: float | None) -> float | None:
    """ROE = (Lucro Líquido / Patrimônio Líquido) * 100. Retorna None se insumos faltarem (Critério 4)."""
    if lucro_liquido is None or patrimonio_liquido is None or patrimonio_liquido <= 0:
        return None
    return (lucro_liquido / patrimonio_liquido) * 100.0



# ── RN-07: Algoritmo Delta V (ΔV) ──────────────────
@dataclass
class ResultadoDeltaV:
    peso_medio_projetado_g: float
    biomassa_projetada_kg: float
    receita_projetada: float
    custo_adicional: float
    lucro_projetado: float
    delta_v: float
    recomendacao: RecomendacaoDespesca
    justificativa: str


def simular_delta_v(
    *,
    dias_horizonte: int,
    peso_medio_atual_g: float,
    ganho_diario_g: float,
    populacao_atual: int,
    mortalidade_diaria_pct: float,
    custo_operacional_total: float,
    preco_atual_kg: float,
    preco_futuro_kg: float | None,
    custo_diario_racao_energia: float,
    biomassa_atual_kg: float,
) -> ResultadoDeltaV:
    """Executa o algoritmo preditivo ΔV conforme RN-07.

    Args:
        dias_horizonte: H ∈ {7, 10, 15} dias.
        peso_medio_atual_g: Peso médio atual do lote (g).
        ganho_diario_g: Taxa de crescimento diário recente (g/dia).
        populacao_atual: População viva estimada.
        mortalidade_diaria_pct: Mortalidade diária estimada (%).
        custo_operacional_total: CO_t acumulado até o momento.
        preco_atual_kg: Preço de venda na faixa de gramatura atual (R$/kg).
        preco_futuro_kg: Preço na faixa de gramatura futura (se None, usa o atual).
        custo_diario_racao_energia: Custo diário de ração + energia + mão-de-obra.
        biomassa_atual_kg: Biomassa viva atual (kg).

    Returns:
        ResultadoDeltaV com projeção e recomendação.
    """
    # Peso projetado
    peso_proj = peso_medio_atual_g + (ganho_diario_g * dias_horizonte)

    # População projetada (mortalidade composta)
    fator_mortalidade = (1 - mortalidade_diaria_pct / 100.0) ** dias_horizonte
    pop_proj = int(populacao_atual * fator_mortalidade)

    # Biomassa projetada
    bio_proj = (pop_proj * peso_proj) / 1000.0

    # Receita e custo
    preco_futuro = preco_futuro_kg if preco_futuro_kg is not None else preco_atual_kg
    receita_proj = bio_proj * preco_futuro
    custo_add = custo_diario_racao_energia * dias_horizonte

    # Lucros
    lo_atual = (biomassa_atual_kg * preco_atual_kg) - custo_operacional_total
    lucro_proj = receita_proj - (custo_operacional_total + custo_add)

    # Delta V
    delta_v = lucro_proj - lo_atual

    # Decisão
    if delta_v > 0:
        recomendacao = RecomendacaoDespesca.MANTER_CULTIVO
        justificativa = (
            f"O ganho de peso projetado ({peso_proj:.1f}g em {dias_horizonte} dias) "
            f"gera retorno líquido de R$ {delta_v:,.2f}, superior ao custo adicional "
            f"de R$ {custo_add:,.2f} com ração e energia."
        )
        if preco_futuro > preco_atual_kg:
            justificativa += (
                f" Adicionalmente, o lote avança para a faixa de "
                f"R$ {preco_futuro:,.2f}/kg."
            )
    else:
        recomendacao = RecomendacaoDespesca.DESPESCA_IMEDIATA
        justificativa = (
            f"O custo marginal de R$ {custo_add:,.2f} em {dias_horizonte} dias "
            f"supera o ganho de valorização projetado. ΔV = R$ {delta_v:,.2f}. "
            f"Recomenda-se a despesca imediata para preservar o lucro operacional atual."
        )

    return ResultadoDeltaV(
        peso_medio_projetado_g=round(peso_proj, 2),
        biomassa_projetada_kg=round(bio_proj, 2),
        receita_projetada=round(receita_proj, 2),
        custo_adicional=round(custo_add, 2),
        lucro_projetado=round(lucro_proj, 2),
        delta_v=round(delta_v, 2),
        recomendacao=recomendacao,
        justificativa=justificativa,
    )


# ── Utilidades de Crescimento ────────────────────────
def calcular_ganho_diario(
    peso_anterior_g: float,
    peso_atual_g: float,
    dias_entre_biometrias: int,
) -> float:
    """Taxa de crescimento diária (g/dia) entre duas biometrias."""
    if dias_entre_biometrias <= 0:
        return 0.0
    return (peso_atual_g - peso_anterior_g) / dias_entre_biometrias


def calcular_ganho_semanal(ganho_diario_g: float) -> float:
    """Ganho semanal extrapolado do diário."""
    return ganho_diario_g * 7.0


def buscar_preco_por_gramatura(
    peso_g: float,
    tabela: list[dict],
) -> float | None:
    """Busca o preço R$/kg na tabela de mercado para uma dada gramatura.

    Na borda entre duas faixas (ex.: 10 g em 8–10 e em 10–12) vale a de cima, pois a faixa
    começa no seu peso mínimo; na mesma faixa, vale a vigência mais recente. O resultado não
    depende da ordem em que as faixas chegam.

    Args:
        peso_g: Peso médio do camarão em gramas.
        tabela: Lista de dicts com keys: faixa_gramatura_min, faixa_gramatura_max, preco_por_kg
            e, opcionalmente, vigencia_inicio.

    Returns:
        Preço R$/kg ou None se não encontrado.
    """
    candidatas = [f for f in tabela if f["faixa_gramatura_min"] <= peso_g <= f["faixa_gramatura_max"]]
    if not candidatas:
        return None
    escolhida = max(candidatas, key=lambda f: (f["faixa_gramatura_min"], f.get("vigencia_inicio") or date.min))
    return float(escolhida["preco_por_kg"])


def estimar_mortalidade_diaria(taxa_sobrev_pct: float, dias_cultivo: int) -> float:
    """Estima mortalidade diária média a partir da sobrevivência acumulada.

    Mortalidade_Diária ≈ (100 - Sobrev%) / dias_cultivo.
    """
    if dias_cultivo <= 0:
        return 0.0
    return (100.0 - taxa_sobrev_pct) / dias_cultivo


@dataclass
class CustoDiarioEstimado:
    total_rs: float
    racao_kg_dia: float | None      # ração de hoje; None quando o custo vem da média do ciclo
    preco_racao_rs_kg: float | None
    fixos_rs_dia: float | None
    marginal: bool                  # True: ração de hoje × preço + fixos; False: média do ciclo


def estimar_custo_diario(
    custo_racao_total: float,
    racao_total_kg: float,
    custos_fixos_total: float,
    dias_cultivo: int,
    racao_diaria_hoje_kg: float | None,
) -> CustoDiarioEstimado | None:
    """Custo diário de manter o viveiro: ração de hoje × preço médio da ração + custos fixos por dia.

    O preço da ração é o custo de ração lançado dividido pelos kg lançados nos manejos. Sem esses
    dados cai na média dos custos do ciclo, que subestima o fim da safra (a ração cresce com o
    peso). Retorna None se não há custo lançado para estimar.
    """
    dias = max(dias_cultivo, 1)
    if custo_racao_total > 0 and racao_total_kg > 0 and racao_diaria_hoje_kg is not None:
        preco = custo_racao_total / racao_total_kg
        fixos = custos_fixos_total / dias
        return CustoDiarioEstimado(racao_diaria_hoje_kg * preco + fixos, racao_diaria_hoje_kg, preco, fixos, True)
    total = (custo_racao_total + custos_fixos_total) / dias
    if total <= 0:
        return None
    return CustoDiarioEstimado(total, None, None, None, False)
