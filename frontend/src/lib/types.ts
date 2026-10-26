/** SAD Carcinicultura — Tipos TypeScript compartilhados. */

// ── Enums ─────────────────────────────────────────────
export type RoleUsuario = "CAMPO" | "VIGIA" | "GESTOR";
export type StatusCiclo = "PLANEJADO" | "ATIVO" | "PAUSADO" | "FINALIZADO" | "CANCELADO";
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
  email?: string | null;
  is_superadmin?: boolean;
}

export interface Usuario {
  id: string;
  nome_completo: string;
  email: string;
  papel: RoleUsuario;
  telefone_emergencia: string | null;
  ativo: boolean;
  created_at: string;
  is_superadmin?: boolean;
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
  peso_medio_pl_g?: number | null;
  laboratorio_origem: string | null;
  status: StatusCiclo;
  tabela_alimentar_id?: string | null;
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
  peso_medio_atual_g: number | null;
  biomassa_atual_kg: number | null;
  racao_acumulada_kg: number;
  fca_atual: number | null;
  classificacao_fca: string | null;
  taxa_alimentar_clifford_pct: number | null;
  racao_diaria_sugerida_kg: number | null;
  custo_operacional_total_rs: number | null;
  receita_bruta_estimada_rs: number | null;
  lucro_operacional_rs: number | null;
  margem_operacional_pct: number | null;
  preco_venda_atual_rs_kg: number | null;
  entradas_faltantes?: string[];
}

// ── Biometria ─────────────────────────────────────────
export interface Biometria {
  id: string;
  ciclo_id: string;
  data_medicao: string;
  quantidade_amostrada: number;
  peso_total_amostra_g: number | null;
  peso_medio_g: number;
  ganho_medio_semanal_g: number | null;
  uniformidade_percentual: number | null;
  observacoes: string | null;
  responsavel_id?: string | null;
  responsavel_nome?: string | null;
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
  simulacao_id?: string | null;
  preco_atual_rs_kg: number;
  preco_futuro_rs_kg: number;
  custo_diario_rs: number;
  premissas: string[];
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
  alertas?: Alerta[];
}

// ── Alertas ───────────────────────────────────────────
export type NivelAlerta = "INFO" | "AVISO" | "CRITICO";
export type StatusAlerta = "ABERTO" | "RESOLVIDO";

export interface Alerta {
  id: string;
  ciclo_id: string;
  viveiro_id: string;
  viveiro_identificacao: string | null;
  ronda_id: string | null;
  nivel: NivelAlerta;
  codigo: string;
  titulo: string;
  mensagem: string;
  status: StatusAlerta;
  resolvido_em: string | null;
  observacao_resolucao: string | null;
  created_at: string;
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

// ── Tabela Alimentar (RF-010, Critério 5) ─────────────
export interface FaixaAlimentarItem {
  peso_g: number;
  taxa_pct: number;
}

export interface TabelaAlimentar {
  id: string;
  nome: string;
  versao: number;
  descricao: string | null;
  is_padrao: boolean;
  ativo: boolean;
  faixas: FaixaAlimentarItem[];
  created_at: string;
  updated_at: string;
}

// ── Trilha de Auditoria (RF-027, Critério 10) ──────────
export interface LogAuditoria {
  id: string;
  usuario_id: string | null;
  usuario_nome: string | null;
  acao: string;
  entidade: string;
  registro_id: string;
  dados_anteriores: Record<string, unknown> | null;
  dados_novos: Record<string, unknown> | null;
  ip_origem: string | null;
  created_at: string;
}

// ── Governança e Administração de Fazendas (RF-002, RF-003) ──
export interface FazendaAdmin {
  id: string;
  nome: string;
  localizacao: string | null;
  area_total_ha: number | null;
  status_ativo: boolean;
  total_viveiros: number;
  organizacao_nome: string | null;
  created_at: string;
}

export interface MetricasGlobaisAdmin {
  total_usuarios: number;
  gestores: number;
  operadores_campo: number;
  vigias: number;
  usuarios_ativos: number;
  usuarios_bloqueados: number;
  total_fazendas: number;
  fazendas_ativas: number;
  area_total_ha: number;
  total_viveiros: number;
}

export interface GestorAdmin {
  id: string;
  nome_completo: string;
  email: string;
  papel: RoleUsuario;
  telefone_emergencia: string | null;
  ativo: boolean;
  organizacao_id: string | null;
  organizacao_nome: string | null;
  created_at: string;
}

export interface Organizacao {
  id: string;
  nome: string;
  identificador: string | null;
  moeda: string;
  status_ativo: boolean;
  created_at: string;
}

export interface Propriedade {
  id: string;
  organizacao_id: string;
  nome: string;
  localizacao: string | null;
  area_total_ha: number | null;
  status_ativo: boolean;
  created_at: string;
}

export interface PainelNoturno {
  viveiro_id: string;
  viveiro_identificacao: string;
  rondas: RondaNoturna[];
  o2_minimo: number | null;
  o2_maximo: number | null;
  alertas_criticos: number;
}
