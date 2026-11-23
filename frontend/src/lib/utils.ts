import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

import type { CategoriaCusto, StatusCiclo } from "@/lib/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** "AAAA-MM-DDTHH:mm" no fuso local (valor de <input type="datetime-local">). */
export function agoraLocalInput(): string {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}

/** Converte o valor de um datetime-local em ISO 8601 com o offset local (ex.: -03:00). */
export function localInputParaIso(valor: string): string {
  const offsetMin = -new Date(valor).getTimezoneOffset();
  const sinal = offsetMin >= 0 ? "+" : "-";
  const abs = Math.abs(offsetMin);
  const hh = String(Math.floor(abs / 60)).padStart(2, "0");
  const mm = String(abs % 60).padStart(2, "0");
  return `${valor}:00${sinal}${hh}:${mm}`;
}

/** Mensagem de um erro capturado (a API lança Error com o `detail` do backend). */
export function mensagemErro(err: unknown, padrao: string): string {
  return err instanceof Error && err.message ? err.message : padrao;
}

export const fmtQtd = (v: number) => v.toLocaleString("pt-BR", { maximumFractionDigits: 4 });
export const fmtMoney = (v: number) =>
  `R$ ${v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
// O preço unitário tem 4 casas (a API só arredonda o total a centavos)
export const fmtPreco = (v: number) =>
  `R$ ${v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`;
/** Data "AAAA-MM-DD" da API, sem passar por UTC (new Date("AAAA-MM-DD") mostraria o dia anterior no Brasil). */
export const fmtData = (d: string) => new Date(`${d}T00:00:00`).toLocaleDateString("pt-BR");

export const ROTULO_CATEGORIA: Record<CategoriaCusto, string> = {
  RACAO: "Ração",
  ENERGIA_ELETRICA: "Energia Elétrica",
  MAO_DE_OBRA: "Mão de Obra",
  POS_LARVAS: "Pós-Larvas",
  PROBIOTICOS_QUIMICOS: "Probióticos/Químicos",
  MANUTENCAO: "Manutenção",
  OUTROS: "Outros",
};

export const ROTULO_STATUS_CICLO: Record<StatusCiclo, string> = {
  PLANEJADO: "Planejado",
  ATIVO: "Ativo",
  PAUSADO: "Pausado",
  FINALIZADO: "Finalizado",
  CANCELADO: "Cancelado",
};
