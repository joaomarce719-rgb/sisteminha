"""SAD Carcinicultura — Motor de Inferência Fuzzy (RN-05).

Implementa o sistema de lógica nebulosa para estimar ajuste de sobrevivência
com base no consumo alimentar, sobras em bandeja e tendência de crescimento.

Antecedentes:
  - delta_consumo: Consumo_Efetivo / Consumo_Clifford (0.0 a 2.0)
  - frequencia_sobras: Grau de sobras (0 a 10, mapeado do enum)
  - tendencia_crescimento: Desvio da curva esperada (-2.0 a +2.0 g/semana)

Consequente:
  - ajuste_sobrevivencia: ΔS ∈ [-3.0%, +0.5%] (ajuste semanal)
"""

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

from src.models.enums import NivelSobraBandeja


# ── Mapeamento de NivelSobraBandeja → valor numérico ──
SOBRA_MAPA: dict[NivelSobraBandeja, float] = {
    NivelSobraBandeja.SEM_SOBRA: 0.0,
    NivelSobraBandeja.SOBRA_LEVE: 3.0,
    NivelSobraBandeja.SOBRA_MODERADA: 6.0,
    NivelSobraBandeja.SOBRA_EXCESSIVA: 9.0,
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

    # ── Antecedente 3: Tendência de Crescimento ───────
    tend_cresc = ctrl.Antecedent(np.arange(-2.0, 2.01, 0.01), "tend_crescimento")
    tend_cresc["negativo"] = fuzz.trapmf(tend_cresc.universe, [-2.0, -2.0, -1.0, -0.3])
    tend_cresc["estagnado"] = fuzz.trimf(tend_cresc.universe, [-0.5, 0.0, 0.5])
    tend_cresc["normal"] = fuzz.trimf(tend_cresc.universe, [0.3, 0.8, 1.2])
    tend_cresc["acelerado"] = fuzz.trapmf(tend_cresc.universe, [1.0, 1.3, 2.0, 2.0])

    # ── Consequente: Ajuste de Sobrevivência ──────────
    ajuste_sobrev = ctrl.Consequent(np.arange(-3.0, 0.51, 0.01), "ajuste_sobrevivencia")
    ajuste_sobrev["queda_severa"] = fuzz.trapmf(ajuste_sobrev.universe, [-3.0, -3.0, -2.5, -1.5])
    ajuste_sobrev["queda_moderada"] = fuzz.trimf(ajuste_sobrev.universe, [-2.0, -1.2, -0.5])
    ajuste_sobrev["queda_leve"] = fuzz.trimf(ajuste_sobrev.universe, [-0.8, -0.3, 0.0])
    ajuste_sobrev["estavel"] = fuzz.trimf(ajuste_sobrev.universe, [-0.2, 0.0, 0.3])
    ajuste_sobrev["positivo"] = fuzz.trapmf(ajuste_sobrev.universe, [0.1, 0.3, 0.5, 0.5])

    # ── Regras de Inferência ──────────────────────────
    rules = [
        # Mortalidade silenciosa: muita sobra, pouco consumo, sem crescimento
        ctrl.Rule(
            delta_consumo["muito_baixo"] & freq_sobras["alta"] & tend_cresc["negativo"],
            ajuste_sobrev["queda_severa"],
        ),
        ctrl.Rule(
            delta_consumo["muito_baixo"] & freq_sobras["alta"] & tend_cresc["estagnado"],
            ajuste_sobrev["queda_severa"],
        ),
        ctrl.Rule(
            delta_consumo["baixo"] & freq_sobras["moderada"] & tend_cresc["negativo"],
            ajuste_sobrev["queda_moderada"],
        ),
        ctrl.Rule(
            delta_consumo["baixo"] & freq_sobras["moderada"] & tend_cresc["estagnado"],
            ajuste_sobrev["queda_moderada"],
        ),
        ctrl.Rule(
            delta_consumo["baixo"] & freq_sobras["alta"],
            ajuste_sobrev["queda_moderada"],
        ),
        # Queda leve: consumo OK mas alguma sobra
        ctrl.Rule(
            delta_consumo["ideal"] & freq_sobras["moderada"],
            ajuste_sobrev["queda_leve"],
        ),
        ctrl.Rule(
            delta_consumo["baixo"] & freq_sobras["baixa"],
            ajuste_sobrev["queda_leve"],
        ),
        # Estável: tudo dentro do esperado
        ctrl.Rule(
            delta_consumo["ideal"] & freq_sobras["nula"] & tend_cresc["normal"],
            ajuste_sobrev["estavel"],
        ),
        ctrl.Rule(
            delta_consumo["ideal"] & freq_sobras["baixa"] & tend_cresc["normal"],
            ajuste_sobrev["estavel"],
        ),
        ctrl.Rule(
            delta_consumo["ideal"] & freq_sobras["nula"] & tend_cresc["estagnado"],
            ajuste_sobrev["queda_leve"],
        ),
        # Positivo: alto consumo sem sobra e bom crescimento
        ctrl.Rule(
            delta_consumo["alto"] & freq_sobras["nula"] & tend_cresc["acelerado"],
            ajuste_sobrev["positivo"],
        ),
        ctrl.Rule(
            delta_consumo["ideal"] & freq_sobras["nula"] & tend_cresc["acelerado"],
            ajuste_sobrev["positivo"],
        ),
        ctrl.Rule(
            delta_consumo["alto"] & freq_sobras["nula"] & tend_cresc["normal"],
            ajuste_sobrev["estavel"],
        ),
        # Anomalia: alto consumo mas muita sobra (desperdício mecânico)
        ctrl.Rule(
            delta_consumo["alto"] & freq_sobras["alta"],
            ajuste_sobrev["queda_leve"],
        ),
    ]

    return ctrl.ControlSystem(rules)


# Singleton do sistema fuzzy (construído uma vez, reutilizado)
_FUZZY_SYSTEM: ctrl.ControlSystem | None = None


def _get_system() -> ctrl.ControlSystem:
    global _FUZZY_SYSTEM
    if _FUZZY_SYSTEM is None:
        _FUZZY_SYSTEM = _build_fuzzy_system()
    return _FUZZY_SYSTEM


def inferir_ajuste_sobrevivencia(
    delta_consumo: float,
    nivel_sobra: NivelSobraBandeja,
    ganho_semanal_g: float,
    crescimento_esperado_min: float = 1.0,
    crescimento_esperado_max: float = 1.5,
) -> float:
    """Executa a inferência fuzzy e retorna o ΔS (ajuste semanal de sobrevivência).

    Args:
        delta_consumo: Consumo_Efetivo / Consumo_Clifford (tipicamente 0.0 a 2.0).
        nivel_sobra: Enum do nível de sobra na bandeja.
        ganho_semanal_g: Ganho de peso semanal real (g/semana).
        crescimento_esperado_min: Limite inferior esperado (g/semana).
        crescimento_esperado_max: Limite superior esperado (g/semana).

    Returns:
        ΔS: Fator de ajuste da sobrevivência (tipicamente -3.0 a +0.5 %).
    """
    # Converter sobra para escala numérica
    sobra_val = SOBRA_MAPA.get(nivel_sobra, 5.0)

    # Tendência de crescimento: desvio do centro da faixa esperada
    centro_esperado = (crescimento_esperado_min + crescimento_esperado_max) / 2.0
    tendencia = ganho_semanal_g - centro_esperado

    # Limitar entradas ao universo de discurso
    dc = float(np.clip(delta_consumo, 0.0, 2.0))
    fs = float(np.clip(sobra_val, 0.0, 10.0))
    tc = float(np.clip(tendencia, -2.0, 2.0))

    try:
        sim = ctrl.ControlSystemSimulation(_get_system())
        sim.input["delta_consumo"] = dc
        sim.input["freq_sobras"] = fs
        sim.input["tend_crescimento"] = tc
        sim.compute()
        return round(float(sim.output["ajuste_sobrevivencia"]), 2)
    except Exception:
        # Fallback conservador: se o motor fuzzy falhar, assume queda leve
        return -0.5


def atualizar_taxa_sobrevivencia(
    taxa_atual_pct: float,
    ajuste_semanal: float,
) -> float:
    """Aplica o ΔS à taxa de sobrevivência, limitando entre 0% e 100%.

    Nova_Taxa = Taxa_Atual + ΔS
    """
    nova = taxa_atual_pct + ajuste_semanal
    return round(max(0.0, min(100.0, nova)), 2)
