/** SAD Carcinicultura — Cliente HTTP para a API FastAPI. */

import type {
  Alerta,
  Biometria,
  CicloProdutivo,
  CompraInsumo,
  CustoOperacional,
  CustoResumo,
  FazendaAdmin,
  GestorAdmin,
  Insumo,
  LogAuditoria,
  ManejoAlimentar,
  MetricasAtuais,
  MetricasGlobaisAdmin,
  Organizacao,
  PainelNoturno,
  PrecoMercado,
  Propriedade,
  RecomendacaoAlimentar,
  RondaNoturna,
  SimulacaoComparativa,
  SimulacaoResponse,
  StatusAlerta,
  TabelaAlimentar,
  TokenResponse,
  UsoInsumo,
  Usuario,
  Viveiro,
} from "./types";

/** Corpo JSON enviado à API. */
type Payload = Record<string, unknown>;

const API_BASE = "/api/v1";

// ── Sessão por aba ────────────────────────────────────
// Cada aba guarda a própria sessão no sessionStorage (mantido ao recarregar a aba);
// o localStorage guarda o último login, herdado pelas abas que ainda não têm sessão
// (aba nova, navegador reaberto). Entrar com outro usuário numa aba não troca o
// usuário das outras, e sair numa aba não desconecta as outras.
const CHAVE_TOKEN = "sad_token";
const CHAVE_USUARIO = "sad_user";
const CHAVE_SAIU = "sad_sessao_encerrada"; // a aba saiu: não herda o último login

// Mesma validade do JWT (JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 480)
const SESSAO_SEGUNDOS = 8 * 60 * 60;

const noNavegador = () => typeof window !== "undefined";

function lerSessao(chave: string): string | null {
  const daAba = sessionStorage.getItem(chave);
  if (daAba !== null) return daAba;
  return sessionStorage.getItem(CHAVE_SAIU) ? null : localStorage.getItem(chave);
}

/** Copia o último login para esta aba, que a partir daí não muda com logins de outras abas. */
function fixarSessaoNaAba(): void {
  if (sessionStorage.getItem(CHAVE_TOKEN) !== null || sessionStorage.getItem(CHAVE_SAIU)) return;
  const token = localStorage.getItem(CHAVE_TOKEN);
  const usuario = localStorage.getItem(CHAVE_USUARIO);
  if (token && usuario) {
    sessionStorage.setItem(CHAVE_TOKEN, token);
    sessionStorage.setItem(CHAVE_USUARIO, usuario);
  }
}

// Lido pelo src/proxy.ts para redirecionar antes de renderizar
function gravarCookiePapel(papel: string | null): void {
  document.cookie = papel
    ? `sad_papel=${encodeURIComponent(papel)}; path=/; max-age=${SESSAO_SEGUNDOS}; samesite=lax`
    : "sad_papel=; path=/; max-age=0; samesite=lax";
}

/** O cookie é um só por navegador: cada aba o regrava com o seu perfil ao ficar ativa. */
function sincronizarCookieDaAba(): void {
  gravarCookiePapel(getStoredUser()?.role ?? null);
}

export function getToken(): string | null {
  if (!noNavegador()) return null;
  const token = lerSessao(CHAVE_TOKEN);
  // A primeira requisição fixa na aba o login que ela herdou
  if (token !== null) fixarSessaoNaAba();
  return token;
}

export function setToken(token: string): void {
  sessionStorage.removeItem(CHAVE_SAIU);
  sessionStorage.setItem(CHAVE_TOKEN, token);
  localStorage.setItem(CHAVE_TOKEN, token);
}

export function clearToken(): void {
  const token = sessionStorage.getItem(CHAVE_TOKEN) ?? lerSessao(CHAVE_TOKEN);
  sessionStorage.removeItem(CHAVE_TOKEN);
  sessionStorage.removeItem(CHAVE_USUARIO);
  sessionStorage.setItem(CHAVE_SAIU, "1");
  // O último login só é apagado se for o desta aba; a aba que continua logada
  // regrava o cookie quando voltar a ficar ativa
  if (localStorage.getItem(CHAVE_TOKEN) === token) {
    localStorage.removeItem(CHAVE_TOKEN);
    localStorage.removeItem(CHAVE_USUARIO);
  }
  gravarCookiePapel(null);
}

export interface StoredUser {
  nome: string;
  role: string;
  email?: string;
  is_superadmin?: boolean;
}

/** Usuário desta aba como texto (estável para o useSyncExternalStore de lib/sessao.ts). */
export function lerUsuarioDaAba(): string | null {
  return noNavegador() ? lerSessao(CHAVE_USUARIO) : null;
}

export function getStoredUser(): StoredUser | null {
  const raw = lerUsuarioDaAba();
  return raw ? JSON.parse(raw) : null;
}

export function setStoredUser(user: StoredUser): void {
  const bruto = JSON.stringify(user);
  sessionStorage.removeItem(CHAVE_SAIU);
  sessionStorage.setItem(CHAVE_USUARIO, bruto);
  localStorage.setItem(CHAVE_USUARIO, bruto);
  gravarCookiePapel(user.role);
}

if (noNavegador()) {
  fixarSessaoNaAba();
  sincronizarCookieDaAba();
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") sincronizarCookieDaAba();
  });
  window.addEventListener("focus", sincronizarCookieDaAba);
  window.addEventListener("pageshow", sincronizarCookieDaAba);
}

/** Indicador apenas de navegação; a autorização real é feita pelo backend (403). */
export function isSuperadmin(user: StoredUser | null = getStoredUser()): boolean {
  return Boolean(user?.is_superadmin);
}

// ── Mensagens de erro da API ──────────────────────────
// Erros de validação do FastAPI (422) chegam como lista em `detail`; sem isso a
// tela mostrava "[object Object]".
interface ErroDeValidacao {
  loc?: (string | number)[];
  msg?: string;
  type?: string;
  ctx?: Record<string, unknown>;
}

const NOMES_DOS_CAMPOS: Record<string, string> = {
  nome: "Nome",
  nome_completo: "Nome",
  email: "E-mail",
  senha: "Senha",
  telefone_emergencia: "Telefone",
  identificador: "Código",
  organizacao_nome: "Nome da organização",
  localizacao: "Localização",
  descricao: "Descrição",
  moeda: "Moeda",
  identificacao: "Identificação",
  observacoes: "Observações",
  laboratorio_origem: "Laboratório de origem",
};

function textoDoErro(erro: ErroDeValidacao): string {
  const campo = erro.loc?.[erro.loc.length - 1];
  const nome = typeof campo === "string" ? (NOMES_DOS_CAMPOS[campo] ?? campo) : "Campo";
  const ctx = erro.ctx ?? {};
  switch (erro.type) {
    case "string_too_long":
    case "too_long":
      return `${nome}: no máximo ${ctx.max_length} caracteres`;
    case "string_too_short":
    case "too_short":
      return `${nome}: no mínimo ${ctx.min_length} caracteres`;
    case "missing":
      return `${nome}: campo obrigatório`;
    default:
      return `${nome}: ${erro.msg ?? "valor inválido"}`;
  }
}

/** Texto do `detail` de uma resposta de erro, seja mensagem simples ou lista de validação. */
export function mensagemDaApi(detail: unknown, padrao: string): string {
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((e) => textoDoErro(e as ErroDeValidacao)).join("; ");
  }
  return padrao;
}

// ── Fetch Wrapper ─────────────────────────────────────
async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    clearToken();
    const isLoginEndpoint = path.includes("/auth/login");
    if (typeof window !== "undefined" && !isLoginEndpoint && window.location.pathname !== "/login") {
      // Fora da árvore React não há router: recarrega a página de login
      window.location.assign(new URL("/login", window.location.origin));
    }
    const body = await res.json().catch(() => ({ detail: "Credenciais inválidas" }));
    throw new Error(mensagemDaApi(body.detail, "Sessão expirada"));
  }

  if (!res.ok) {
    // Resposta sem JSON (ex.: erro 500 do servidor): o código ajuda a localizar o problema
    const body = await res.json().catch(() => ({
      detail:
        res.status >= 500
          ? `Erro interno do servidor (código ${res.status}). Tente novamente ou avise o suporte.`
          : `Erro ${res.status}`,
    }));
    throw new Error(mensagemDaApi(body.detail, `Erro ${res.status}`));
  }

  // 204 No Content (ex.: exclusões) não tem corpo JSON
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Auth ──────────────────────────────────────────────
export async function login(email: string, senha: string): Promise<TokenResponse> {
  const data = await apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, senha }),
  });
  setToken(data.access_token);
  setStoredUser({
    nome: data.nome,
    role: data.role,
    email: data.email ?? email,
    is_superadmin: data.is_superadmin,
  });
  return data;
}

export async function registrarUsuario(payload: {
  nome_completo: string;
  email: string;
  senha: string;
  telefone_emergencia?: string;
  codigo_organizacao?: string;
}) {
  return apiFetch<Usuario>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ── Viveiros ──────────────────────────────────────────
export const viveirosApi = {
  listar: async () => (await apiFetch<{ items: Viveiro[] }>("/viveiros/")).items,
  obter: (id: string) => apiFetch<Viveiro>(`/viveiros/${id}`),
  criar: (data: Payload) => apiFetch<Viveiro>("/viveiros/", { method: "POST", body: JSON.stringify(data) }),
  atualizar: (id: string, data: Payload) =>
    apiFetch<Viveiro>(`/viveiros/${id}`, { method: "PUT", body: JSON.stringify(data) }),
};

export async function downloadFile(path: string, defaultFilename: string): Promise<void> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}${path}`, { headers });
  if (!res.ok) {
    throw new Error(`Erro ao baixar arquivo: ${res.statusText}`);
  }
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = defaultFilename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

// ── Ciclos ─────────────────────────────────────────────
export const ciclosApi = {
  listar: (params?: { viveiro_id?: string; status_filtro?: string }) => {
    const q = new URLSearchParams();
    if (params?.viveiro_id) q.set("viveiro_id", params.viveiro_id);
    if (params?.status_filtro) q.set("status_filtro", params.status_filtro);
    return apiFetch<CicloProdutivo[]>(`/ciclos/?${q.toString()}`);
  },
  obter: (id: string) => apiFetch<CicloProdutivo>(`/ciclos/${id}`),
  criar: (data: Payload) =>
    apiFetch<CicloProdutivo>("/ciclos/", { method: "POST", body: JSON.stringify(data) }),
  encerrar: (id: string, data: Payload) =>
    apiFetch<CicloProdutivo>(`/ciclos/${id}/encerrar`, { method: "POST", body: JSON.stringify(data) }),
  pausar: (id: string) => apiFetch<CicloProdutivo>(`/ciclos/${id}/pausar`, { method: "POST" }),
  retomar: (id: string) => apiFetch<CicloProdutivo>(`/ciclos/${id}/retomar`, { method: "POST" }),
  metricas: (id: string) => apiFetch<MetricasAtuais>(`/ciclos/${id}/metricas-atuais`),
  exportarCsv: (id: string) =>
    downloadFile(`/ciclos/${id}/exportar-csv`, `relatorio_ciclo_${id.slice(0, 8)}.csv`),
};

// ── Biometrias ────────────────────────────────────────
export const biometriasApi = {
  listar: (cicloId: string) => apiFetch<Biometria[]>(`/ciclos/${cicloId}/biometrias/`),
  criar: (cicloId: string, data: Payload) =>
    apiFetch<Biometria>(`/ciclos/${cicloId}/biometrias/`, { method: "POST", body: JSON.stringify(data) }),
};

// ── Manejos ───────────────────────────────────────────
export const manejosApi = {
  listar: (cicloId: string) => apiFetch<ManejoAlimentar[]>(`/ciclos/${cicloId}/manejos-alimentares/`),
  criar: (cicloId: string, data: Payload) =>
    apiFetch<ManejoAlimentar>(`/ciclos/${cicloId}/manejos-alimentares/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  recomendacao: (cicloId: string) =>
    apiFetch<RecomendacaoAlimentar>(`/ciclos/${cicloId}/manejos-alimentares/recomendacao`),
};

// ── Custos ─────────────────────────────────────────────
export const custosApi = {
  listar: (cicloId: string) => apiFetch<CustoOperacional[]>(`/ciclos/${cicloId}/custos/`),
  criar: (cicloId: string, data: Payload) =>
    apiFetch<CustoOperacional>(`/ciclos/${cicloId}/custos/`, { method: "POST", body: JSON.stringify(data) }),
  resumo: (cicloId: string) => apiFetch<CustoResumo[]>(`/ciclos/${cicloId}/custos/resumo`),
  exportarCsv: (cicloId: string) =>
    downloadFile(`/ciclos/${cicloId}/custos/exportar-csv`, `custos_ciclo_${cicloId.slice(0, 8)}.csv`),
};

// ── Insumos e compras ──────────────────────────────────
export const insumosApi = {
  listar: () => apiFetch<Insumo[]>("/insumos/"),
  criar: (data: Payload) => apiFetch<Insumo>("/insumos/", { method: "POST", body: JSON.stringify(data) }),
  atualizar: (id: string, data: Payload) =>
    apiFetch<Insumo>(`/insumos/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  compras: {
    listar: (insumoId: string) => apiFetch<CompraInsumo[]>(`/insumos/${insumoId}/compras`),
    criar: (insumoId: string, data: Payload) =>
      apiFetch<CompraInsumo>(`/insumos/${insumoId}/compras`, { method: "POST", body: JSON.stringify(data) }),
    // O PUT reenvia a compra inteira
    atualizar: (insumoId: string, compraId: string, data: Payload) =>
      apiFetch<CompraInsumo>(`/insumos/${insumoId}/compras/${compraId}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    excluir: (insumoId: string, compraId: string) =>
      apiFetch<void>(`/insumos/${insumoId}/compras/${compraId}`, { method: "DELETE" }),
  },
};

// ── Uso de insumo no ciclo ─────────────────────────────
export const usosInsumoApi = {
  listar: (cicloId: string) => apiFetch<UsoInsumo[]>(`/ciclos/${cicloId}/usos-insumo/`),
  criar: (cicloId: string, data: Payload) =>
    apiFetch<UsoInsumo>(`/ciclos/${cicloId}/usos-insumo/`, { method: "POST", body: JSON.stringify(data) }),
  // O PUT reenvia o uso inteiro
  atualizar: (cicloId: string, usoId: string, data: Payload) =>
    apiFetch<UsoInsumo>(`/ciclos/${cicloId}/usos-insumo/${usoId}`, { method: "PUT", body: JSON.stringify(data) }),
  excluir: (cicloId: string, usoId: string) =>
    apiFetch<void>(`/ciclos/${cicloId}/usos-insumo/${usoId}`, { method: "DELETE" }),
};

// ── Preços ─────────────────────────────────────────────
export const precosApi = {
  listar: (apenasVigentes = true) =>
    apiFetch<PrecoMercado[]>(`/precos-mercado/?vigentes=${apenasVigentes}`),
  criar: (data: Payload) =>
    apiFetch<PrecoMercado>("/precos-mercado/", { method: "POST", body: JSON.stringify(data) }),
  atualizar: (id: string, data: Payload) =>
    apiFetch<PrecoMercado>(`/precos-mercado/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  excluir: (id: string) => apiFetch<void>(`/precos-mercado/${id}`, { method: "DELETE" }),
};

// ── Simulação ──────────────────────────────────────────
export const simulacaoApi = {
  simular: (cicloId: string, dias: number, precoCustom?: number, custoDiario?: number) =>
    apiFetch<SimulacaoResponse>(`/ciclos/${cicloId}/simular-despesca/`, {
      method: "POST",
      body: JSON.stringify({
        dias_horizonte: dias,
        preco_kg_customizado: precoCustom || null,
        custo_diario_rs: custoDiario || null,
      }),
    }),
  comparativo: (cicloId: string, custoDiario?: number) =>
    apiFetch<SimulacaoComparativa>(
      `/ciclos/${cicloId}/simular-despesca/comparativo${custoDiario ? `?custo_diario_rs=${custoDiario}` : ""}`
    ),
};

// ── Rondas ──────────────────────────────────────────────
export const rondasApi = {
  criar: (data: Payload) =>
    apiFetch<RondaNoturna>("/rondas-noturnas/", { method: "POST", body: JSON.stringify(data) }),
  listarPorCiclo: (cicloId: string) => apiFetch<RondaNoturna[]>(`/rondas-noturnas/ciclo/${cicloId}`),
  painelNoturno: () => apiFetch<PainelNoturno[]>("/rondas-noturnas/painel-noturno"),
};

// ── Alertas (RF-021) ───────────────────────────────────
export const alertasApi = {
  listar: (params?: { status_alerta?: StatusAlerta; ciclo_id?: string }) => {
    const q = new URLSearchParams();
    if (params?.status_alerta) q.set("status_alerta", params.status_alerta);
    if (params?.ciclo_id) q.set("ciclo_id", params.ciclo_id);
    return apiFetch<Alerta[]>(`/alertas/?${q.toString()}`);
  },
  resolver: (id: string, observacao?: string) =>
    apiFetch<Alerta>(`/alertas/${id}/resolver`, {
      method: "PUT",
      body: JSON.stringify({ observacao: observacao || null }),
    }),
};

// ── Admin & Governança (RF-002, RF-003, RF-014) ────────
export const adminApi = {
  obterMetricasGlobais: () => apiFetch<MetricasGlobaisAdmin>("/admin/metricas-globais"),
  listarUsuarios: () => apiFetch<Usuario[]>("/admin/usuarios"),
  criarUsuario: (data: Payload) =>
    apiFetch<Usuario>("/admin/usuarios", { method: "POST", body: JSON.stringify(data) }),
  atualizarUsuario: (id: string, data: Payload) =>
    apiFetch<Usuario>(`/admin/usuarios/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  aprovarUsuario: (id: string, data: { papel: string; ativo: boolean }) =>
    apiFetch<Usuario>(`/admin/usuarios/${id}/aprovar`, { method: "PUT", body: JSON.stringify(data) }),
  resetarSenha: (id: string) =>
    apiFetch<{ detail: string; senha_temporaria: string }>(`/admin/usuarios/${id}/resetar-senha`, {
      method: "POST",
    }),
  excluirUsuario: (id: string) => apiFetch<void>(`/admin/usuarios/${id}`, { method: "DELETE" }),
  listarFazendas: () => apiFetch<FazendaAdmin[]>("/admin/fazendas"),
  criarFazenda: (data: Payload) =>
    apiFetch<FazendaAdmin>("/admin/fazendas", { method: "POST", body: JSON.stringify(data) }),
  alternarStatusFazenda: (id: string) =>
    apiFetch<FazendaAdmin>(`/admin/fazendas/${id}/status`, { method: "PUT" }),
  gerarNovoCodigo: (organizacaoId: string) =>
    apiFetch<{ organizacao_id: string; codigo_organizacao: string }>(
      `/admin/organizacoes/${organizacaoId}/novo-codigo`,
      { method: "POST" }
    ),
  // Gestores Administrativos (Exclusivo Superadmin)
  listarGestores: () => apiFetch<GestorAdmin[]>("/admin/gestores"),
  criarGestor: (data: Payload) =>
    apiFetch<GestorAdmin>("/admin/gestores", { method: "POST", body: JSON.stringify(data) }),
  // Operadores Normais de Campo (Método 1 da Fazenda)
  listarOperadores: () => apiFetch<Usuario[]>("/admin/operadores"),
  criarOperador: (data: Payload) =>
    apiFetch<Usuario>("/admin/operadores", { method: "POST", body: JSON.stringify(data) }),
};

// ── Tabelas Alimentares (RF-010, Critério 5) ─────────────
export const tabelasAlimentaresApi = {
  listar: (apenasAtivas = true) =>
    apiFetch<TabelaAlimentar[]>(`/tabelas-alimentares/?apenas_ativas=${apenasAtivas}`),
  obter: (id: string) => apiFetch<TabelaAlimentar>(`/tabelas-alimentares/${id}`),
  criar: (data: Payload) =>
    apiFetch<TabelaAlimentar>("/tabelas-alimentares/", { method: "POST", body: JSON.stringify(data) }),
  atualizar: (id: string, data: Payload) =>
    apiFetch<TabelaAlimentar>(`/tabelas-alimentares/${id}`, { method: "PUT", body: JSON.stringify(data) }),
};

// ── Trilha de Auditoria (RF-027, Critério 10) ────────────
export const auditoriaApi = {
  listar: (params?: { entidade?: string; acao?: string; limite?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.entidade) q.set("entidade", params.entidade);
    if (params?.acao) q.set("acao", params.acao);
    if (params?.limite) q.set("limite", params.limite.toString());
    if (params?.offset) q.set("offset", params.offset.toString());
    return apiFetch<{ items: LogAuditoria[]; total: number }>(`/auditoria/?${q.toString()}`);
  },
};

// ── Organizações & Propriedades (RF-002, RF-003) ─────────
export const organizacoesApi = {
  listar: () => apiFetch<Organizacao[]>("/organizacoes/"),
  obter: (id: string) => apiFetch<Organizacao>(`/organizacoes/${id}`),
  criar: (data: Payload) =>
    apiFetch<Organizacao>("/organizacoes/", { method: "POST", body: JSON.stringify(data) }),
  atualizar: (id: string, data: Payload) =>
    apiFetch<Organizacao>(`/organizacoes/${id}`, { method: "PUT", body: JSON.stringify(data) }),
};

export const propriedadesApi = {
  listar: (orgId?: string) => {
    const q = orgId ? `?organizacao_id=${orgId}` : "";
    return apiFetch<Propriedade[]>(`/propriedades/${q}`);
  },
  obter: (id: string) => apiFetch<Propriedade>(`/propriedades/${id}`),
  criar: (data: Payload) =>
    apiFetch<Propriedade>("/propriedades/", { method: "POST", body: JSON.stringify(data) }),
  atualizar: (id: string, data: Payload) =>
    apiFetch<Propriedade>(`/propriedades/${id}`, { method: "PUT", body: JSON.stringify(data) }),
};
