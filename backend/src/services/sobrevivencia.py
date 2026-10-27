"""Sobrevivência estimada do ciclo: ração real × tabela alimentar e mortos informados.

O viveiro escavado não permite contar os animais, então a população é estimada por três sinais:
- mortos encontrados pelo raçoador: evidência direta, piso da perda;
- consumo: a ração efetiva do dia dividida pela taxa da tabela dá a biomassa que os animais
  comem, e daí a sobrevivência implícita (média dos últimos dias);
- fuzzy (consumo × sobra × crescimento), que continua como terceiro sinal.

A perda do período é a maior das três, para não contar a mesma mortalidade duas vezes, e a
sobrevivência nunca sobe. Os parâmetros abaixo são premissas a calibrar com dados de campo.
"""

from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from src.models.enums import NivelSobraBandeja
from src.services.fuzzy_engine import SOBRA_MAPA, ajuste_no_periodo

JANELA_DIAS = 7                 # dias usados na média da sobrevivência implícita
MIN_DIAS_COM_REGISTRO = 3       # com menos dias a estimativa pelo consumo não é usada
BANDA_PP = 2.0                  # diferença (pontos percentuais) abaixo da qual o consumo é ignorado
FRACAO_CORRECAO = 0.5           # parte da diferença corrigida a cada período
TETO_QUEDA_SEMANAL_PP = 12.0    # maior queda aceita pelo consumo em uma semana
TOLERANCIA_CONFRONTO_PP = 5.0   # diferença aceita entre os vivos pelos mortos e pelo consumo

# Fração da ração lançada que sobra na bandeja, por nível de sobra
FRACAO_SOBRA: dict[NivelSobraBandeja, float] = {
    NivelSobraBandeja.SEM_SOBRA: 0.0,
    NivelSobraBandeja.SOBRA_LEVE: 0.05,
    NivelSobraBandeja.SOBRA_MODERADA: 0.15,
    NivelSobraBandeja.SOBRA_EXCESSIVA: 0.30,
}


@dataclass
class DiaManejo:
    """Tratos de uma mesma data somados."""

    data: date
    racao_kg: float
    racao_efetiva_kg: float   # ração lançada menos a sobra estimada na bandeja
    pior_sobra: NivelSobraBandeja
    mortos: int


def ordenar(manejos: Iterable) -> list:
    """Registros em ordem de data e, no mesmo dia, de criação (os novos, ainda sem data de criação, por último)."""
    return sorted(manejos, key=lambda m: (m.data_registro, m.created_at is None, m.created_at or datetime.min))


def peso_na_data(biometrias: Iterable, data: date) -> float | None:
    """Peso médio (g) da última biometria até a data, ou None se ainda não havia nenhuma."""
    medidas = sorted((b for b in biometrias if b.data_medicao <= data), key=lambda b: b.data_medicao)
    return medidas[-1].peso_medio_g if medidas else None


def sobrevivencia_vigente(manejos: Iterable) -> float:
    """Sobrevivência (%) após o último registro de manejo; 100% enquanto não há nenhum."""
    taxa = 100.0
    for m in ordenar(manejos):
        if m.taxa_sobrevivencia_estimada_fuzzy is not None:
            taxa = m.taxa_sobrevivencia_estimada_fuzzy
    return taxa


def agrupar_por_dia(manejos: Iterable) -> list[DiaManejo]:
    """Soma os tratos de cada data: o confronto com a tabela é diário."""
    por_data: dict[date, list] = defaultdict(list)
    for m in manejos:
        por_data[m.data_registro].append(m)
    dias = []
    for data in sorted(por_data):
        registros = por_data[data]
        dias.append(
            DiaManejo(
                data=data,
                racao_kg=sum(r.quantidade_racao_kg for r in registros),
                racao_efetiva_kg=sum(r.quantidade_racao_kg * (1 - FRACAO_SOBRA[r.sobra_bandeja_nivel]) for r in registros),
                pior_sobra=max((r.sobra_bandeja_nivel for r in registros), key=lambda n: SOBRA_MAPA[n]),
                mortos=sum(r.camaroes_mortos or 0 for r in registros),
            )
        )
    return dias


def sobrevivencia_implicita_pct(
    dias: list[DiaManejo],
    pos_larvas: int,
    peso_na_data: Callable[[date], float | None],
    taxa_pct: Callable[[float], float],
    ate: date,
) -> float | None:
    """Sobrevivência que o consumo dos últimos dias indica, ou None se há poucos dias para estimar.

    Biomassa implícita = ração efetiva do dia ÷ taxa da tabela; dividida pela biomassa de
    povoamento sem perdas (PLs × peso médio da biometria) dá a sobrevivência do dia.
    """
    inicio = ate - timedelta(days=JANELA_DIAS - 1)
    valores = []
    for d in dias:
        if not inicio <= d.data <= ate:
            continue
        peso = peso_na_data(d.data)
        if peso is None or peso <= 0:
            continue
        biomassa_implicita_kg = d.racao_efetiva_kg / (taxa_pct(peso) / 100.0)
        valores.append(min(100.0, biomassa_implicita_kg / (pos_larvas * peso / 1000.0) * 100.0))
    if len(valores) < MIN_DIAS_COM_REGISTRO:
        return None
    return sum(valores) / len(valores)


def nova_sobrevivencia(
    anterior: float,
    dias_periodo: int,
    mortos_pct: float,
    ajuste_fuzzy_semanal: float,
    implicita: float | None,
) -> float:
    """Sobrevivência (%) após o período: a maior perda entre mortos contados, consumo e fuzzy."""
    perda_fuzzy = max(0.0, -ajuste_no_periodo(ajuste_fuzzy_semanal, dias_periodo))
    perda_consumo = 0.0
    if implicita is not None and anterior - implicita > BANDA_PP:
        teto = TETO_QUEDA_SEMANAL_PP * max(0, min(dias_periodo, 7)) / 7.0
        perda_consumo = min((anterior - implicita) * FRACAO_CORRECAO, teto)
    perda = max(mortos_pct, perda_fuzzy, perda_consumo)
    return round(max(0.0, anterior - perda), 2)


@dataclass
class ConfrontoVivos:
    """Vivos pela contagem de mortos x vivos pela alimentação."""

    mortos_acumulados: int
    sobrevivencia_por_mortos_pct: float       # (PLs − mortos contados) ÷ PLs
    sobrevivencia_por_consumo_pct: float | None
    sobrevivencia_estimada_pct: float
    situacao: str


def confrontar_vivos(
    manejos: Iterable,
    pos_larvas: int,
    peso_na_data_fn: Callable[[date], float | None],
    taxa_pct: Callable[[float], float],
    ate: date,
) -> ConfrontoVivos:
    """Confere se os vivos que a contagem de mortos permite batem com os que a ração indica.

    - DE_ACORDO: as duas leituras diferem em até TOLERANCIA_CONFRONTO_PP;
    - PERDA_NAO_CONTADA: o consumo indica mais perda que os mortos contados (mortos que
      ninguém viu, ou ração abaixo da tabela);
    - MORTOS_ACIMA_DO_CONSUMO: os mortos contados indicam mais perda que o consumo (conferir a
      contagem ou o lançamento da ração);
    - SEM_DADOS: poucos dias de ração com biometria para estimar pelo consumo.
    """
    registros = ordenar(manejos)
    mortos = sum(m.camaroes_mortos or 0 for m in registros)
    por_mortos = max(0.0, (pos_larvas - mortos) / pos_larvas * 100.0)
    por_consumo = sobrevivencia_implicita_pct(agrupar_por_dia(registros), pos_larvas, peso_na_data_fn, taxa_pct, ate)
    if por_consumo is None:
        situacao = "SEM_DADOS"
    elif abs(por_consumo - por_mortos) <= TOLERANCIA_CONFRONTO_PP:
        situacao = "DE_ACORDO"
    elif por_consumo < por_mortos:
        situacao = "PERDA_NAO_CONTADA"
    else:
        situacao = "MORTOS_ACIMA_DO_CONSUMO"
    return ConfrontoVivos(
        mortos_acumulados=mortos,
        sobrevivencia_por_mortos_pct=round(por_mortos, 2),
        sobrevivencia_por_consumo_pct=round(por_consumo, 2) if por_consumo is not None else None,
        sobrevivencia_estimada_pct=sobrevivencia_vigente(registros),
        situacao=situacao,
    )
