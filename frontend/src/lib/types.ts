/** SAD Carcinicultura — Tipos TypeScript compartilhados. */

// ── Enums ─────────────────────────────────────────────
export type RoleUsuario = "CAMPO" | "VIGIA" | "GESTOR";
export type StatusCiclo = "PLANEJADO" | "ATIVO" | "FINALIZADO" | "CANCELADO";
export type NivelSobraBandeja = "SEM_SOBRA" | "SOBRA_LEVE" | "SOBRA_MODERADA" | "SOBRA_EXCESSIVA";
export type StatusAlimentar = "NORMAL" | "SUB_ARRAC_SUSPEITO" | "SUPER_ARRAC_SUSPEITO";
export type CategoriaCusto = "RACAO" | "ENERGIA_ELETRICA" | "MAO_DE_OBRA" | "POS_LARVAS" | "PROBIOTICOS_QUIMICOS" | "MANUTENCAO" | "OUTROS";
export type RecomendacaoDespesca = "MANTER_CULTIVO" | "DESPESCA_IMEDIATA";
export type ComportamentoCamarao = "NORMAL_FUNDO" | "FLOR_DAGUA_BOQUEANDO" | "NATACAO_AGITADA" | "ECDISE_MASSIVA" | "PRESENCA_BORDAS";
export type StatusEnergia = "REDE_CONCESSIONARIA" | "GERADOR_DIESEL" | "SEM_ENERGIA_QUEDA";
export type ClassificacaoOxigenio = "NORMAL" | "ALERTA" | "EMERGENCIA";

// ── Auth ──────────────────────────────────────────────
export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: RoleUsuario;
  nome: string;
}

export interface Usuario {
  id: string;
  nome_completo: string;
  email: string;
  papel: RoleUsuario;
  telefone_emergencia: string | null;
  ativo: boolean;
  created_at: string;
}

// ── Viveiro ───────────────────────────────────────────
export interface Viveiro {
  id: string;
  identificacao: string;
  area_util_m2: number;
  profundidade_media_m: number | null;
  localizacao: string | null;
  status_ativo: boolean;
  created_at: string;
  updated_at: string;
}

// ── Ciclo Produtivo ───────────────────────────────────
export interface CicloProdutivo {
  id: string;
  viveiro_id: string;
  data_povoamento: string;
  quantidade_pos_larvas: number;
  custo_aquisicao_pl: number;
  laboratorio_origem: string | null;
  status: StatusCiclo;
  data_despesca_real: string | null;
  biomassa_colhida_kg: number | null;
  receita_real_rs: number | null;
  created_at: string;
}

export interface MetricasAtuais {
  ciclo_id: string;
  viveiro_identificacao: string;
  dias_cultivo: number;
  densidade_estocagem: number;
  alerta_hiperdensidade: boolean;
  populacao_inicial: number;
  taxa_sobrevivencia_fuzzy_pct: number;
  populacao_estimada: number;
  peso_medio_atual_g: number;
  biomassa_atual_kg: number;
  racao_acumulada_kg: number;
  fca_atual: number | null;
  classificacao_fca: string | null;
  taxa_alimentar_clifford_pct: number;
  racao_diaria_sugerida_kg: number;
  custo_operacional_total_rs: number;
  receita_bruta_estimada_rs: number;
  lucro_operacional_rs: number;
  margem_operacional_pct: number | null;
  preco_venda_atual_rs_kg: number | null;
}

// ── Biometria ─────────────────────────────────────────
export interface Biometria {
  id: string;
  ciclo_id: string;
  data_medicao: string;
  peso_medio_g: number;
  ganho_medio_semanal_g: number | null;
  uniformidade_percentual: number | null;
  observacoes: string | null;
  created_at: string;
}

// ── Manejo Alimentar ──────────────────────────────────
export interface ManejoAlimentar {
  id: string;
  ciclo_id: string;
  data_registro: string;
  quantidade_racao_kg: number;
  taxa_alimentar_calculada_pct: number | null;
  sobra_bandeja_nivel: NivelSobraBandeja;
  status_alimentar_ajustado: StatusAlimentar | null;
  taxa_sobrevivencia_estimada_fuzzy: number | null;
  created_at: string;
}

export interface RecomendacaoAlimentar {
  racao_diaria_sugerida_kg: number;
  taxa_clifford_pct: number;
  biomassa_estimada_kg: number;
  ajuste_sugerido: string;
}

// ── Simulação de Despesca ─────────────────────────────
export interface SimulacaoResponse {
  ciclo_id: string;
  data_referencia: string;
  peso_medio_atual_g: number;
  biomassa_atual_kg: number;
  lucro_operacional_atual_rs: number;
  dias_horizonte: number;
  peso_medio_projetado_g: number;
  biomassa_projetada_kg: number;
  receita_projetada_rs: number;
  custo_adicional_projetado_rs: number;
  lucro_projetado_rs: number;
  delta_v_rs: number;
  recomendacao: RecomendacaoDespesca;
  justificativa: string;
}

export interface SimulacaoComparativa {
  simulacoes: SimulacaoResponse[];
  melhor_cenario: SimulacaoResponse | null;
}

// ── Ronda Noturna ─────────────────────────────────────
export interface RondaNoturna {
  id: string;
  ciclo_id: string;
  vigia_id: string;
  vigia_nome: string;
  data_hora_ronda: string;
  oxigenio_dissolvido_mg_l: number;
  temperatura_agua_c: number;
  comportamento: ComportamentoCamarao;
  observacoes: string | null;
  classificacao_oxigenio: ClassificacaoOxigenio;
  created_at: string;
  aeradores_instalados: number | null;
  aeradores_ligados: number | null;
  taxa_aeracao_pct: number | null;
  fonte_energia: StatusEnergia | null;
  falha_mecanica_detectada: boolean | null;
}

// ── Custos ────────────────────────────────────────────
export interface CustoOperacional {
  id: string;
  ciclo_id: string;
  data_lancamento: string;
  categoria: CategoriaCusto;
  descricao: string;
  valor_rs: number;
  created_at: string;
}

export interface CustoResumo {
  categoria: CategoriaCusto;
  total_rs: number;
  qtd_lancamentos: number;
}

// ── Preços ────────────────────────────────────────────
export interface PrecoMercado {
  id: string;
  faixa_gramatura_min: number;
  faixa_gramatura_max: number;
  preco_por_kg: number;
  vigencia_inicio: string;
  vigencia_fim: string | null;
  created_at: string;
}
