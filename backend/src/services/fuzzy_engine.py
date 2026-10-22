"""SAD Carcinicultura — Motor de Inferência Fuzzy (RN-05).

Implementa o sistema de lógica nebulosa para estimar ajuste de sobrevivência
com base no consumo alimentar, sobras em bandeja e crescimento do lote.

Antecedentes:
  - delta_consumo: Consumo_Efetivo / Consumo_Tabela (0.0 a 2.0)
  - freq_sobras: Grau de sobras (0 a 10, mapeado do enum)
  - crescimento: Ganho de peso semanal (-1.0 a +3.0 g/semana; esperado 1.0 a 1.5)

Consequente:
  - ajuste_sobrevivencia: ΔS ∈ [-3.0%, +0.5%] por SEMANA

A base de regras é completa: toda combinação de consumo × sobra dispara uma
regra, e todo valor de crescimento dispara outra. Assim a inferência sempre
produz um resultado (não depende do fallback).
"""

import logging

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

from src.models.enums import NivelSobraBandeja

logger = logging.getLogger("uvicorn.error")

# ── Mapeamento de NivelSobraBandeja → valor numérico ──
SOBRA_MAPA: dict[NivelSobraBandeja, float] = {
    NivelSobraBandeja.SEM_SOBRA: 0.0,
    NivelSobraBandeja.SOBRA_LEVE: 3.0,
    NivelSobraBandeja.SOBRA_MODERADA: 6.0,
    NivelSobraBandeja.SOBRA_EXCESSIVA: 9.0,
}

# Crescimento semanal esperado (g/semana); usado quando não há duas biometrias
CRESCIMENTO_ESPERADO_G_SEMANA = 1.25

# Regras de consumo × sobra: (conjunto de consumo, conjunto de sobra) → consequente
_REGRAS_CONSUMO_SOBRA = {
    ("ideal", "nula"): "estavel",
    ("ideal", "baixa"): "estavel",
    ("ideal", "moderada"): "queda_leve",
    ("ideal", "alta"): "queda_moderada",
    ("alto", "nula"): "estavel",
    ("alto", "baixa"): "estavel",
    ("alto", "moderada"): "queda_leve",
    ("alto", "alta"): "queda_leve",  # desperdício mecânico, não necessariamente mortalidade
    ("baixo", "nula"): "estavel",  # oferta reduzida e totalmente consumida
    ("baixo", "baixa"): "queda_leve",
    ("baixo", "moderada"): "queda_moderada",
    ("baixo", "alta"): "queda_moderada",
    ("muito_baixo", "nula"): "estavel",
    ("muito_baixo", "baixa"): "queda_leve",
    ("muito_baixo", "moderada"): "queda_moderada",
    ("muito_baixo", "alta"): "queda_severa",  # mortalidade silenciosa
}

# Regras de crescimento (combinadas às de consumo × sobra na agregação)
_REGRAS_CRESCIMENTO = {
    "negativo": "queda_moderada",
    "estagnado": "queda_leve",
    "normal": "estavel",
    "acelerado": "positivo",
}


def _build_fuzzy_system() -> ctrl.ControlSystem:
    """Constrói o sistema de inferência fuzzy uma única vez."""

    # ── Antecedente 1: Delta Consumo ──────────────────
    delta_consumo = ctrl.Antecedent(np.arange(0.0, 2.01, 0.01), "delta_consumo")
    delta_consumo["muito_baixo"] = fuzz.trapmf(delta_consumo.universe, [0.0, 0.0, 0.3, 0.5])
    delta_consumo["baixo"] = fuzz.trimf(delta_consumo.universe, [0.3, 0.6, 0.8])
    delta_consumo["ideal"] = fuzz.trimf(delta_consumo.universe, [0.7, 1.0, 1.2])
    delta_consumo["alto"] = fuzz.trapmf(delta_consumo.universe, [1.1, 1.4, 2.0, 2.0])

    # ── Antecedente 2: Frequência de Sobras ───────────
    freq_sobras = ctrl.Antecedent(np.arange(0, 10.1, 0.1), "freq_sobras")
    freq_sobras["nula"] = fuzz.trapmf(freq_sobras.universe, [0, 0, 1, 2])
    freq_sobras["baixa"] = fuzz.trimf(freq_sobras.universe, [1, 3, 5])
    freq_sobras["moderada"] = fuzz.trimf(freq_sobras.universe, [4, 6, 8])
    freq_sobras["alta"] = fuzz.trapmf(freq_sobras.universe, [7, 8, 10, 10])

    # ── Antecedente 3: Crescimento semanal (g/semana) ─
    crescimento = ctrl.Antecedent(np.arange(-1.0, 3.01, 0.01), "crescimento")
    crescimento["negativo"] = fuzz.trapmf(crescimento.universe, [-1.0, -1.0, -0.3, 0.0])
    crescimento["estagnado"] = fuzz.trimf(crescimento.universe, [-0.2, 0.2, 0.6])
    crescimento["normal"] = fuzz.trapmf(crescimento.universe, [0.5, 0.9, 1.6, 2.0])
    crescimento["acelerado"] = fuzz.trapmf(crescimento.universe, [1.7, 2.2, 3.0, 3.0])

    # ── Consequente: Ajuste de Sobrevivência (%/semana) ─
    ajuste_sobrev = ctrl.Consequent(np.arange(-3.0, 0.51, 0.01), "ajuste_sobrevivencia")
    ajuste_sobrev["queda_severa"] = fuzz.trapmf(ajuste_sobrev.universe, [-3.0, -3.0, -2.5, -1.5])
    ajuste_sobrev["queda_moderada"] = fuzz.trimf(ajuste_sobrev.universe, [-2.0, -1.2, -0.5])
    ajuste_sobrev["queda_leve"] = fuzz.trimf(ajuste_sobrev.universe, [-0.8, -0.3, 0.0])
    ajuste_sobrev["estavel"] = fuzz.trimf(ajuste_sobrev.universe, [-0.2, 0.0, 0.2])
    ajuste_sobrev["positivo"] = fuzz.trapmf(ajuste_sobrev.universe, [0.1, 0.3, 0.5, 0.5])

    rules = [
        ctrl.Rule(delta_consumo[consumo] & freq_sobras[sobra], ajuste_sobrev[saida])
        for (consumo, sobra), saida in _REGRAS_CONSUMO_SOBRA.items()
    ]
    rules += [
        ctrl.Rule(crescimento[termo], ajuste_sobrev[saida])
        for termo, saida in _REGRAS_CRESCIMENTO.items()
    ]
    return ctrl.ControlSystem(rules)


# Singleton do sistema fuzzy (construído uma vez, reutilizado)
_FUZZY_SYSTEM: ctrl.ControlSystem | None = None


def _get_system() -> ctrl.ControlSystem:
    global _FUZZY_SYSTEM
    if _FUZZY_SYSTEM is None:
        _FUZZY_SYSTEM = _build_fuzzy_system()
    return _FUZZY_SYSTEM


def _inferir(delta_consumo: float, sobra_val: float, ganho_semanal_g: float) -> float:
    sim = ctrl.ControlSystemSimulation(_get_system())
    sim.input["delta_consumo"] = float(np.clip(delta_consumo, 0.0, 2.0))
    sim.input["freq_sobras"] = float(np.clip(sobra_val, 0.0, 10.0))
    sim.input["crescimento"] = float(np.clip(ganho_semanal_g, -1.0, 3.0))
    sim.compute()
    return round(float(sim.output["ajuste_sobrevivencia"]), 2)


def inferir_ajuste_sobrevivencia(
    delta_consumo: float,
    nivel_sobra: NivelSobraBandeja,
    ganho_semanal_g: float | None,
) -> float:
    """Executa a inferência fuzzy e retorna o ΔS semanal de sobrevivência (%).

    Args:
        delta_consumo: Consumo_Efetivo / Consumo_Tabela (tipicamente 0.0 a 2.0).
        nivel_sobra: Enum do nível de sobra na bandeja.
        ganho_semanal_g: Ganho de peso semanal real (g/semana). None quando ainda
            não há duas biometrias — assume-se o crescimento esperado, de modo que
            a falta de dado não seja tratada como estagnação.
    """
    crescimento = CRESCIMENTO_ESPERADO_G_SEMANA if ganho_semanal_g is None else ganho_semanal_g
    try:
        return _inferir(delta_consumo, SOBRA_MAPA.get(nivel_sobra, 5.0), crescimento)
    except Exception:
        # Não deve ocorrer com a base de regras completa; mantém o registro do manejo
        logger.exception("Falha na inferência fuzzy; assumindo sobrevivência estável.")
        return 0.0


def ajuste_no_periodo(ajuste_semanal: float, dias: int) -> float:
    """Converte o ΔS semanal para o intervalo entre registros (limitado a 7 dias)."""
    dias_validos = max(0, min(dias, 7))
    return ajuste_semanal * dias_validos / 7.0


def atualizar_taxa_sobrevivencia(
    taxa_atual_pct: float,
    ajuste: float,
) -> float:
    """Aplica o ΔS à taxa de sobrevivência, limitando entre 0% e 100%.

    Nova_Taxa = Taxa_Atual + ΔS
    """
    nova = taxa_atual_pct + ajuste
    return round(max(0.0, min(100.0, nova)), 2)
