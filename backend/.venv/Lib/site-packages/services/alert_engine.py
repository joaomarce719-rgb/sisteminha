"""SAD Carcinicultura — Motor de Alertas de Manejo (RF-11, RN-09, RN-10).

Centraliza a lógica de detecção de condições críticas que geram
alertas visuais, sonoros ou notificações push para operadores e gestores.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum

from src.models.enums import ClassificacaoOxigenio, ComportamentoCamarao


class NivelAlerta(str, Enum):
    INFO = "INFO"
    AVISO = "AVISO"
    CRITICO = "CRITICO"


@dataclass
class Alerta:
    nivel: NivelAlerta
    codigo: str
    titulo: str
    mensagem: str
    viveiro_id: str | None = None
    timestamp: datetime | None = None


# ── RN-09: Classificação de Oxigênio Dissolvido ─────
def classificar_oxigenio(o2_mg_l: float) -> ClassificacaoOxigenio:
    """Classifica O₂ conforme RN-09.

    >= 4.0 mg/L → NORMAL (Verde)
    2.5 a 4.0 mg/L → ALERTA (Amarelo)
    < 2.5 mg/L → EMERGÊNCIA (Vermelho)
    """
    if o2_mg_l >= 4.0:
        return ClassificacaoOxigenio.NORMAL
    if o2_mg_l >= 2.5:
        return ClassificacaoOxigenio.ALERTA
    return ClassificacaoOxigenio.EMERGENCIA


def gerar_alerta_oxigenio(
    o2_mg_l: float,
    comportamento: ComportamentoCamarao,
    viveiro_id: str,
) -> Alerta | None:
    """Gera alerta se O₂ estiver em faixa crítica ou comportamento anormal."""
    classificacao = classificar_oxigenio(o2_mg_l)

    if comportamento == ComportamentoCamarao.FLOR_DAGUA_BOQUEANDO:
        return Alerta(
            nivel=NivelAlerta.CRITICO,
            codigo="ANOXIA_EMERGENCIA",
            titulo="🚨 EMERGÊNCIA — Camarão na superfície",
            mensagem=(
                f"Oxigênio: {o2_mg_l:.1f} mg/L. Camarões boqueando na superfície. "
                f"LIGAR 100% DA AERAÇÃO E ACIONAR GERADOR IMEDIATAMENTE."
            ),
            viveiro_id=viveiro_id,
            timestamp=datetime.now(),
        )

    if classificacao == ClassificacaoOxigenio.EMERGENCIA:
        return Alerta(
            nivel=NivelAlerta.CRITICO,
            codigo="ANOXIA_EMERGENCIA",
            titulo="🚨 EMERGÊNCIA — O₂ crítico",
            mensagem=(
                f"Oxigênio: {o2_mg_l:.1f} mg/L (abaixo de 2.5). "
                f"AÇÃO IMEDIATA: Ligar aeração total e acionar gerador."
            ),
            viveiro_id=viveiro_id,
            timestamp=datetime.now(),
        )

    if classificacao == ClassificacaoOxigenio.ALERTA:
        return Alerta(
            nivel=NivelAlerta.AVISO,
            codigo="ANOXIA_ALERTA",
            titulo="⚠️ ALERTA — O₂ baixo",
            mensagem=(
                f"Oxigênio: {o2_mg_l:.1f} mg/L (entre 2.5 e 4.0). "
                f"Ligar aeradores adicionais e reavaliar em 30 minutos."
            ),
            viveiro_id=viveiro_id,
            timestamp=datetime.now(),
        )

    return None


# ── RN-10: Cobertura de Aeradores ────────────────────
def calcular_taxa_aeracao(ligados: int, instalados: int) -> float:
    """Taxa_Aeração = (Ligados / Instalados) × 100."""
    if instalados <= 0:
        return 0.0
    return (ligados / instalados) * 100.0


def verificar_aeracao_noturna(
    taxa_aeracao_pct: float,
    biomassa_estimada_kg_ha: float,
    hora_atual: int,
) -> Alerta | None:
    """Gera advertência se aeração < 75% entre 00h e 05h30 com alta biomassa."""
    if 0 <= hora_atual <= 5 and taxa_aeracao_pct < 75.0 and biomassa_estimada_kg_ha > 2500:
        return Alerta(
            nivel=NivelAlerta.AVISO,
            codigo="AERACAO_INSUFICIENTE",
            titulo="⚠️ Aeração abaixo de 75%",
            mensagem=(
                f"Taxa de aeração: {taxa_aeracao_pct:.0f}%. "
                f"Biomassa estimada: {biomassa_estimada_kg_ha:.0f} kg/ha. "
                f"Recomenda-se ligar aeradores adicionais no período noturno."
            ),
            timestamp=datetime.now(),
        )
    return None


# ── RF-11: Alertas de Manejo de Campo ────────────────
def verificar_intervalo_biometria(
    ultima_biometria: date | None,
    hoje: date | None = None,
) -> Alerta | None:
    """Alerta se intervalo sem biometria > 15 dias."""
    if ultima_biometria is None:
        return Alerta(
            nivel=NivelAlerta.AVISO,
            codigo="SEM_BIOMETRIA",
            titulo="📏 Nenhuma biometria registrada",
            mensagem="O ciclo não possui registro de biometria. Realize a primeira amostragem.",
            timestamp=datetime.now(),
        )

    ref = hoje or date.today()
    dias_sem = (ref - ultima_biometria).days
    if dias_sem > 15:
        return Alerta(
            nivel=NivelAlerta.AVISO,
            codigo="BIOMETRIA_ATRASADA",
            titulo="📏 Biometria atrasada",
            mensagem=(
                f"Última biometria há {dias_sem} dias (limite: 15 dias). "
                f"Realize nova amostragem para manter a precisão do modelo."
            ),
            timestamp=datetime.now(),
        )
    return None


def verificar_sobras_consecutivas(
    sobras_recentes: list[str],
    limite_consecutivas: int = 3,
) -> Alerta | None:
    """Alerta se houver N sobras EXCESSIVAS consecutivas."""
    contagem = 0
    for s in reversed(sobras_recentes):
        if s == "SOBRA_EXCESSIVA":
            contagem += 1
        else:
            break

    if contagem >= limite_consecutivas:
        return Alerta(
            nivel=NivelAlerta.CRITICO,
            codigo="SOBRAS_EXCESSIVAS_CONSECUTIVAS",
            titulo="🍽️ Sobras excessivas consecutivas",
            mensagem=(
                f"{contagem} registros consecutivos de sobra excessiva. "
                f"Risco de anoxia por poluição alimentar e/ou mortalidade silenciosa. "
                f"Reduzir imediatamente o arraçoamento e investigar."
            ),
            timestamp=datetime.now(),
        )
    return None


def verificar_delta_v_negativo(
    delta_v: float,
    dias_horizonte: int = 7,
) -> Alerta | None:
    """Alerta se ΔV ≤ 0 no horizonte de 7 dias."""
    if delta_v <= 0 and dias_horizonte == 7:
        return Alerta(
            nivel=NivelAlerta.CRITICO,
            codigo="DESPESCA_IMINENTE",
            titulo="🎯 Colheita iminente — ΔV negativo",
            mensagem=(
                f"ΔV = R$ {delta_v:,.2f} para horizonte de {dias_horizonte} dias. "
                f"O custo marginal supera a valorização. Considere despesca imediata."
            ),
            timestamp=datetime.now(),
        )
    return None
