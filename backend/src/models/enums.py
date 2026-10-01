"""SAD Carcinicultura — Enumerações do sistema.

Define todos os tipos enumerados usados pelo banco de dados e lógica de negócio,
espelhando os ENUM do PostgreSQL.
"""

import enum


# ── Perfis de Acesso (RBAC) ─────────────────────────
class RoleUsuario(str, enum.Enum):
    """Papéis operacionais do sistema RBAC."""
    CAMPO = "CAMPO"
    VIGIA = "VIGIA"
    GESTOR = "GESTOR"


# ── Ciclo de Produção ───────────────────────────────
class StatusCiclo(str, enum.Enum):
    """Estados possíveis de um ciclo produtivo."""
    PLANEJADO = "PLANEJADO"
    ATIVO = "ATIVO"
    FINALIZADO = "FINALIZADO"
    CANCELADO = "CANCELADO"


# ── Manejo Alimentar ────────────────────────────────
class NivelSobraBandeja(str, enum.Enum):
    """Grau de resíduos alimentares observados na bandeja."""
    SEM_SOBRA = "SEM_SOBRA"
    SOBRA_LEVE = "SOBRA_LEVE"
    SOBRA_MODERADA = "SOBRA_MODERADA"
    SOBRA_EXCESSIVA = "SOBRA_EXCESSIVA"


class StatusAlimentar(str, enum.Enum):
    """Diagnóstico do padrão alimentar ajustado."""
    NORMAL = "NORMAL"
    SUB_ARRAC_SUSPEITO = "SUB_ARRAC_SUSPEITO"
    SUPER_ARRAC_SUSPEITO = "SUPER_ARRAC_SUSPEITO"


# ── Custos Operacionais ─────────────────────────────
class CategoriaCusto(str, enum.Enum):
    """Categorias de custos operacionais do ciclo."""
    RACAO = "RACAO"
    ENERGIA_ELETRICA = "ENERGIA_ELETRICA"
    MAO_DE_OBRA = "MAO_DE_OBRA"
    POS_LARVAS = "POS_LARVAS"
    PROBIOTICOS_QUIMICOS = "PROBIOTICOS_QUIMICOS"
    MANUTENCAO = "MANUTENCAO"
    OUTROS = "OUTROS"


# ── Simulação de Despesca ───────────────────────────
class RecomendacaoDespesca(str, enum.Enum):
    """Diretriz de decisão emitida pelo simulador Δ V."""
    MANTER_CULTIVO = "MANTER_CULTIVO"
    DESPESCA_IMEDIATA = "DESPESCA_IMEDIATA"


# ── Ronda Noturna (Vigia) ───────────────────────────
class ComportamentoCamarao(str, enum.Enum):
    """Padrão comportamental observado pelo vigia durante a ronda."""
    NORMAL_FUNDO = "NORMAL_FUNDO"
    FLOR_DAGUA_BOQUEANDO = "FLOR_DAGUA_BOQUEANDO"
    NATACAO_AGITADA = "NATACAO_AGITADA"
    ECDISE_MASSIVA = "ECDISE_MASSIVA"
    PRESENCA_BORDAS = "PRESENCA_BORDAS"


class StatusEnergia(str, enum.Enum):
    """Fonte de energia do viveiro no momento da ronda."""
    REDE_CONCESSIONARIA = "REDE_CONCESSIONARIA"
    GERADOR_DIESEL = "GERADOR_DIESEL"
    SEM_ENERGIA_QUEDA = "SEM_ENERGIA_QUEDA"


# ── Classificação de Oxigênio (RN-09) ──────────────
class ClassificacaoOxigenio(str, enum.Enum):
    """Faixas de classificação de O₂ dissolvido conforme RN-09."""
    NORMAL = "NORMAL"      # >= 4.0 mg/L
    ALERTA = "ALERTA"      # 2.5 a 4.0 mg/L
    EMERGENCIA = "EMERGENCIA"  # < 2.5 mg/L


# ── Classificação de FCA (RN-03) ────────────────────
class ClassificacaoFCA(str, enum.Enum):
    """Eficiência zootécnica baseada no FCA."""
    ALTA_EFICIENCIA = "ALTA_EFICIENCIA"          # FCA <= 1.2
    FAIXA_PADRAO = "FAIXA_PADRAO"                # 1.2 < FCA <= 1.6
    DESPERDICIO_INDICADO = "DESPERDICIO_INDICADO"  # FCA > 1.6
