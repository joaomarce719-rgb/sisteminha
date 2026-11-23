/** Rótulos e regras compartilhadas das etapas do preparo do ciclo planejado. */

import type { EtapaPreparo, StatusEtapa, TipoEtapa } from "./types";

export const ROTULO_TIPO_ETAPA: Record<TipoEtapa, string> = {
  SECAGEM: "Secagem do fundo",
  CALAGEM: "Calagem",
  ADUBACAO: "Adubação",
  ABASTECIMENTO: "Abastecimento de água",
  TRATAMENTO_AGUA: "Tratamento da água",
  OUTRA: "Outra etapa",
};

export const ROTULO_STATUS_ETAPA: Record<StatusEtapa, string> = {
  PENDENTE: "Pendente",
  EM_ANDAMENTO: "Em andamento",
  CONCLUIDA: "Feita",
  NAO_REALIZADA: "Não realizada",
};

/** Etapa "Outra" não tem nome próprio: a observação descreve o que foi feito. */
export function nomeEtapa(etapa: EtapaPreparo): string {
  return etapa.tipo === "OUTRA" && etapa.observacao ? etapa.observacao : ROTULO_TIPO_ETAPA[etapa.tipo];
}

/** O povoamento espera cada etapa estar feita ou não realizada (mesma regra da API). */
export function etapasEmAberto(etapas: EtapaPreparo[]): number {
  return etapas.filter((e) => e.status === "PENDENTE" || e.status === "EM_ANDAMENTO").length;
}
