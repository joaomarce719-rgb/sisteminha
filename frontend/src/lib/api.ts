/** SAD Carcinicultura — Cliente HTTP para a API FastAPI. */

import type {
  Alerta,
  RondaNoturna,
  SimulacaoComparativa,
  SimulacaoResponse,
  StatusAlerta,
  TokenResponse,
  Usuario,
} from "./types";

const API_BASE = "/api/v1";

// ── Token Management ──────────────────────────────────
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("sad_token");
}

export function setToken(token: string): void {
  localStorage.setItem("sad_token", token);
}

export function clearToken(): void {
  localStorage.removeItem("sad_token");
  localStorage.removeItem("sad_user");
}

export interface StoredUser {
  nome: string;
  role: string;
  email?: string;
  is_superadmin?: boolean;
}

export function getStoredUser(): StoredUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("sad_user");
  return raw ? JSON.parse(raw) : null;
}

export function setStoredUser(user: StoredUser): void {
  localStorage.setItem("sad_user", JSON.stringify(user));
}

/** Indicador apenas de navegação; a autorização real é feita pelo backend (403). */
export function isSuperadmin(user: StoredUser | null = getStoredUser()): boolean {
  return Boolean(user?.is_superadmin);
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
      window.location.href = "/login";
    }
    const body = await res.json().catch(() => ({ detail: "Credenciais inválidas" }));
    throw new Error(body.detail || "Sessão expirada");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Erro desconhecido" }));
    throw new Error(body.detail || `Erro ${res.status}`);
  }

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
}) {
  return apiFetch<Usuario>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function registrarPrimeiroUsuario(
  nome_completo: string,
  email: string,
  senha: string
) {
  return apiFetch("/auth/registrar", {
    method: "POST",
    body: JSON.stringify({ nome_completo, email, senha }),
  });
}

// ── Viveiros ──────────────────────────────────────────
export const viveirosApi = {
  listar: async () => {
    const res = await apiFetch<any>("/viveiros/");
    return Array.isArray(res) ? res : (res?.items || []);
  },
  obter: (id: string) => apiFetch<any>(`/viveiros/${id}`),
  criar: (data: any) => apiFetch<any>("/viveiros/", { method: "POST", body: JSON.stringify(data) }),
  atualizar: (id: string, data: any) =>
    apiFetch<any>(`/viveiros/${id}`, { method: "PUT", body: JSON.stringify(data) }),
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
    return apiFetch<any[]>(`/ciclos/?${q.toString()}`);
  },
  obter: (id: string) => apiFetch<any>(`/ciclos/${id}`),
  criar: (data: any) => apiFetch<any>("/ciclos/", { method: "POST", body: JSON.stringify(data) }),
  encerrar: (id: string, data: any) =>
    apiFetch<any>(`/ciclos/${id}/encerrar`, { method: "POST", body: JSON.stringify(data) }),
  pausar: (id: string) => apiFetch<any>(`/ciclos/${id}/pausar`, { method: "POST" }),
  retomar: (id: string) => apiFetch<any>(`/ciclos/${id}/retomar`, { method: "POST" }),
  metricas: (id: string) => apiFetch<any>(`/ciclos/${id}/metricas-atuais`),
  exportarCsv: (id: string) =>
    downloadFile(`/ciclos/${id}/exportar-csv`, `relatorio_ciclo_${id.slice(0, 8)}.csv`),
};

// ── Biometrias ────────────────────────────────────────
export const biometriasApi = {
  listar: (cicloId: string) => apiFetch<any[]>(`/ciclos/${cicloId}/biometrias/`),
  criar: (cicloId: string, data: any) =>
    apiFetch<any>(`/ciclos/${cicloId}/biometrias/`, { method: "POST", body: JSON.stringify(data) }),
};

// ── Manejos ───────────────────────────────────────────
export const manejosApi = {
  listar: (cicloId: string) => apiFetch<any[]>(`/ciclos/${cicloId}/manejos-alimentares/`),
  criar: (cicloId: string, data: any) =>
    apiFetch<any>(`/ciclos/${cicloId}/manejos-alimentares/`, { method: "POST", body: JSON.stringify(data) }),
  recomendacao: (cicloId: string) => apiFetch<any>(`/ciclos/${cicloId}/manejos-alimentares/recomendacao`),
};

// ── Custos ─────────────────────────────────────────────
export const custosApi = {
  listar: (cicloId: string) => apiFetch<any[]>(`/ciclos/${cicloId}/custos/`),
  criar: (cicloId: string, data: any) =>
    apiFetch<any>(`/ciclos/${cicloId}/custos/`, { method: "POST", body: JSON.stringify(data) }),
  resumo: (cicloId: string) => apiFetch<any[]>(`/ciclos/${cicloId}/custos/resumo`),
  exportarCsv: (cicloId: string) =>
    downloadFile(`/ciclos/${cicloId}/custos/exportar-csv`, `custos_ciclo_${cicloId.slice(0, 8)}.csv`),
};

// ── Preços ─────────────────────────────────────────────
export const precosApi = {
  listar: () => apiFetch<any[]>("/precos-mercado/"),
  criar: (data: any) =>
    apiFetch<any>("/precos-mercado/", { method: "POST", body: JSON.stringify(data) }),
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
  criar: (data: any) =>
    apiFetch<RondaNoturna>("/rondas-noturnas/", { method: "POST", body: JSON.stringify(data) }),
  listarPorCiclo: (cicloId: string) =>
    apiFetch<any[]>(`/rondas-noturnas/ciclo/${cicloId}`),
  painelNoturno: () => apiFetch<any[]>("/rondas-noturnas/painel-noturno"),
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
  obterMetricasGlobais: () => apiFetch<any>("/admin/metricas-globais"),
  listarUsuarios: () => apiFetch<any[]>("/admin/usuarios"),
  criarUsuario: (data: any) =>
    apiFetch<any>("/admin/usuarios", { method: "POST", body: JSON.stringify(data) }),
  atualizarUsuario: (id: string, data: any) =>
    apiFetch<any>(`/admin/usuarios/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  aprovarUsuario: (id: string, data: { papel: string; ativo: boolean }) =>
    apiFetch<any>(`/admin/usuarios/${id}/aprovar`, { method: "PUT", body: JSON.stringify(data) }),
  resetarSenha: (id: string) =>
    apiFetch<{ detail: string; senha_temporaria: string }>(`/admin/usuarios/${id}/resetar-senha`, {
      method: "POST",
    }),
  excluirUsuario: (id: string) =>
    apiFetch<any>(`/admin/usuarios/${id}`, { method: "DELETE" }),
  listarFazendas: () => apiFetch<any[]>("/admin/fazendas"),
  criarFazenda: (data: any) =>
    apiFetch<any>("/admin/fazendas", { method: "POST", body: JSON.stringify(data) }),
  alternarStatusFazenda: (id: string) =>
    apiFetch<any>(`/admin/fazendas/${id}/status`, { method: "PUT" }),
  // Gestores Administrativos (Exclusivo Superadmin)
  listarGestores: () => apiFetch<any[]>("/admin/gestores"),
  criarGestor: (data: any) =>
    apiFetch<any>("/admin/gestores", { method: "POST", body: JSON.stringify(data) }),
  // Operadores Normais de Campo (Método 1 da Fazenda)
  listarOperadores: () => apiFetch<any[]>("/admin/operadores"),
  criarOperador: (data: any) =>
    apiFetch<any>("/admin/operadores", { method: "POST", body: JSON.stringify(data) }),
};

// ── Tabelas Alimentares (RF-010, Critério 5) ─────────────
export const tabelasAlimentaresApi = {
  listar: (apenasAtivas = true) =>
    apiFetch<any[]>(`/tabelas-alimentares/?apenas_ativas=${apenasAtivas}`),
  obter: (id: string) => apiFetch<any>(`/tabelas-alimentares/${id}`),
  criar: (data: any) =>
    apiFetch<any>("/tabelas-alimentares/", { method: "POST", body: JSON.stringify(data) }),
  atualizar: (id: string, data: any) =>
    apiFetch<any>(`/tabelas-alimentares/${id}`, { method: "PUT", body: JSON.stringify(data) }),
};

// ── Trilha de Auditoria (RF-027, Critério 10) ────────────
export const auditoriaApi = {
  listar: (params?: { entidade?: string; acao?: string; limite?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.entidade) q.set("entidade", params.entidade);
    if (params?.acao) q.set("acao", params.acao);
    if (params?.limite) q.set("limite", params.limite.toString());
    if (params?.offset) q.set("offset", params.offset.toString());
    return apiFetch<any[]>(`/auditoria/?${q.toString()}`);
  },
};

// ── Organizações & Propriedades (RF-002, RF-003) ─────────
export const organizacoesApi = {
  listar: () => apiFetch<any[]>("/organizacoes/"),
  obter: (id: string) => apiFetch<any>(`/organizacoes/${id}`),
  criar: (data: any) => apiFetch<any>("/organizacoes/", { method: "POST", body: JSON.stringify(data) }),
  atualizar: (id: string, data: any) =>
    apiFetch<any>(`/organizacoes/${id}`, { method: "PUT", body: JSON.stringify(data) }),
};

export const propriedadesApi = {
  listar: (orgId?: string) => {
    const q = orgId ? `?organizacao_id=${orgId}` : "";
    return apiFetch<any[]>(`/propriedades/${q}`);
  },
  obter: (id: string) => apiFetch<any>(`/propriedades/${id}`),
  criar: (data: any) => apiFetch<any>("/propriedades/", { method: "POST", body: JSON.stringify(data) }),
  atualizar: (id: string, data: any) =>
    apiFetch<any>(`/propriedades/${id}`, { method: "PUT", body: JSON.stringify(data) }),
};


