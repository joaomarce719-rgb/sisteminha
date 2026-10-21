import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

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
