/** SAD Carcinicultura — Cliente HTTP para a API FastAPI. */

import type { TokenResponse } from "./types";

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

export function getStoredUser(): { nome: string; role: string } | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("sad_user");
  return raw ? JSON.parse(raw) : null;
}

export function setStoredUser(nome: string, role: string): void {
  localStorage.setItem("sad_user", JSON.stringify({ nome, role }));
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
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("Sessão expirada");
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
  setStoredUser(data.nome, data.role);
  return data;
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
  listar: () => apiFetch<any[]>("/viveiros/"),
  obter: (id: string) => apiFetch<any>(`/viveiros/${id}`),
  criar: (data: any) => apiFetch<any>("/viveiros/", { method: "POST", body: JSON.stringify(data) }),
  atualizar: (id: string, data: any) =>
    apiFetch<any>(`/viveiros/${id}`, { method: "PUT", body: JSON.stringify(data) }),
};

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
  metricas: (id: string) => apiFetch<any>(`/ciclos/${id}/metricas-atuais`),
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
};

// ── Preços ─────────────────────────────────────────────
export const precosApi = {
  listar: () => apiFetch<any[]>("/precos-mercado/"),
  criar: (data: any) =>
    apiFetch<any>("/precos-mercado/", { method: "POST", body: JSON.stringify(data) }),
};

// ── Simulação ──────────────────────────────────────────
export const simulacaoApi = {
  simular: (cicloId: string, dias: number, precoCustom?: number) =>
    apiFetch<any>(`/ciclos/${cicloId}/simular-despesca/`, {
      method: "POST",
      body: JSON.stringify({
        dias_horizonte: dias,
        preco_kg_customizado: precoCustom || null,
      }),
    }),
  comparativo: (cicloId: string) =>
    apiFetch<any>(`/ciclos/${cicloId}/simular-despesca/comparativo`),
};

// ── Rondas ──────────────────────────────────────────────
export const rondasApi = {
  criar: (data: any) =>
    apiFetch<any>("/rondas-noturnas/", { method: "POST", body: JSON.stringify(data) }),
  listarPorCiclo: (cicloId: string) =>
    apiFetch<any[]>(`/rondas-noturnas/ciclo/${cicloId}`),
  painelNoturno: () => apiFetch<any[]>("/rondas-noturnas/painel-noturno"),
};

// ── Admin ───────────────────────────────────────────────
export const adminApi = {
  listarUsuarios: () => apiFetch<any[]>("/admin/usuarios"),
  criarUsuario: (data: any) =>
    apiFetch<any>("/admin/usuarios", { method: "POST", body: JSON.stringify(data) }),
  atualizarUsuario: (id: string, data: any) =>
    apiFetch<any>(`/admin/usuarios/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  resetarSenha: (id: string) =>
    apiFetch<any>(`/admin/usuarios/${id}/resetar-senha`, { method: "POST" }),
};
