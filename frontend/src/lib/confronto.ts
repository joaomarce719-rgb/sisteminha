import type { ConfrontoVivos, SituacaoConfronto, StatusAlimentar } from "@/lib/types";

type VarianteBadge = "success" | "warning" | "destructive" | "secondary";

export const ROTULO_CONFRONTO: Record<SituacaoConfronto, string> = {
  DE_ACORDO: "De acordo",
  PERDA_NAO_CONTADA: "Perda não contada",
  MORTOS_ACIMA_DO_CONSUMO: "Conferir contagem",
  SEM_DADOS: "Sem dados",
};

export const VARIANTE_CONFRONTO: Record<SituacaoConfronto, VarianteBadge> = {
  DE_ACORDO: "success",
  PERDA_NAO_CONTADA: "warning",
  MORTOS_ACIMA_DO_CONSUMO: "destructive",
  SEM_DADOS: "secondary",
};

const EXPLICACAO_CONFRONTO: Record<SituacaoConfronto, string> = {
  DE_ACORDO: "Os vivos pela contagem de mortos batem com os que a alimentação indica.",
  PERDA_NAO_CONTADA:
    "A alimentação indica menos vivos que a contagem de mortos: pode haver mortos que ninguém viu ou ração abaixo da tabela.",
  MORTOS_ACIMA_DO_CONSUMO:
    "Os mortos contados superam o que a alimentação indica: confira a contagem ou o lançamento da ração.",
  SEM_DADOS: "Poucos dias de ração com biometria para confrontar com a contagem de mortos.",
};

export function explicacaoConfronto(cv: ConfrontoVivos): string {
  return EXPLICACAO_CONFRONTO[cv.situacao];
}

/** Uma linha para cartões de métrica, ex.: "Contagem 93,3% · Alimentação 81,1% — perda não contada". */
export function resumoConfronto(cv: ConfrontoVivos): string {
  const pct = (v: number) => `${v.toFixed(1).replace(".", ",")}%`;
  const consumo = cv.sobrevivencia_por_consumo_pct != null ? pct(cv.sobrevivencia_por_consumo_pct) : "—";
  return `Contagem ${pct(cv.sobrevivencia_por_mortos_pct)} · Alimentação ${consumo} — ${ROTULO_CONFRONTO[cv.situacao].toLowerCase()}`;
}

export const ROTULO_STATUS_ALIMENTAR: Record<StatusAlimentar, string> = {
  NORMAL: "Dentro do padrão",
  SUB_ARRAC_SUSPEITO: "Abaixo do padrão",
  SUPER_ARRAC_SUSPEITO: "Acima do padrão",
};

export const VARIANTE_STATUS_ALIMENTAR: Record<StatusAlimentar, VarianteBadge> = {
  NORMAL: "success",
  SUB_ARRAC_SUSPEITO: "warning",
  SUPER_ARRAC_SUSPEITO: "warning",
};
