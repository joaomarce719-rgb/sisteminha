"use client";

import { useEffect, useState, type ReactNode } from "react";
import { CheckCircle2, ClipboardList, Loader2, Package, Receipt, Sprout, type LucideIcon } from "lucide-react";
import { viveirosApi } from "@/lib/api";
import { mensagemErro } from "@/lib/utils";
import { ROTULO_STATUS_ETAPA, ROTULO_TIPO_ETAPA } from "@/lib/etapas-preparo";
import type { EtapaHistorico, HistoricoCiclo, StatusCiclo } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { toast } from "@/components/ui/toast";
import { fmtData, fmtMoney, fmtQtd } from "@/components/insumos/lista-usos-insumo";
import { VARIANTE_STATUS } from "@/components/viveiro/preparo-ciclo";
import { VendasCiclo } from "@/components/viveiro/vendas-ciclo";

const STATUS_CICLO: Record<StatusCiclo, { rotulo: string; variante: "secondary" | "success" | "warning" | "info" | "destructive" }> = {
  PLANEJADO: { rotulo: "Planejado", variante: "secondary" },
  ATIVO: { rotulo: "Ativo", variante: "success" },
  PAUSADO: { rotulo: "Pausado", variante: "warning" },
  FINALIZADO: { rotulo: "Finalizado", variante: "info" },
  CANCELADO: { rotulo: "Cancelado", variante: "destructive" },
};

// A API devolve 0 no FCA quando não há ração registrada: vale como "sem dados"
const fmtFca = (v: number | null) => (v ? fmtQtd(v) : "—");

function periodoEtapa(e: EtapaHistorico): string | null {
  if (e.data_inicio && e.data_fim) return `${fmtData(e.data_inicio)} a ${fmtData(e.data_fim)}`;
  if (e.data_inicio) return `desde ${fmtData(e.data_inicio)}`;
  if (e.data_fim) return `até ${fmtData(e.data_fim)}`;
  return null;
}

function Passo({ icone: Icone, titulo, children }: { icone: LucideIcon; titulo: string; children: ReactNode }) {
  return (
    <li className="relative pl-7">
      <span className="absolute -left-[13px] top-0 flex h-6 w-6 items-center justify-center rounded-full border-2 border-slate-200 bg-white text-sky-600">
        <Icone className="w-3 h-3" aria-hidden />
      </span>
      <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500">{titulo}</h5>
      <div className="mt-1.5 space-y-1 text-xs text-slate-600">{children}</div>
    </li>
  );
}

function Dado({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-[11px] font-semibold text-slate-400">{rotulo}</dt>
      <dd className="font-bold text-slate-900 tabular-nums">{children}</dd>
    </div>
  );
}

function CicloHistorico({ ciclo, onCorrigirVendas }: { ciclo: HistoricoCiclo; onCorrigirVendas: () => void }) {
  const povoado = ciclo.quantidade_pos_larvas !== null;
  const finalizado = ciclo.status === "FINALIZADO";
  // CAMPO e VIGIA recebem os campos em reais nulos: nesse caso nada de dinheiro é mostrado
  const comValores = ciclo.custo_total_rs !== null;
  const status = STATUS_CICLO[ciclo.status];
  const semanas = ciclo.racao_por_semana;
  const semanasComCusto = semanas.some((s) => s.custo_rs !== null);

  return (
    <section className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <h4 className="font-bold text-slate-900 text-sm">
            {povoado ? "Ciclo povoado em" : "Ciclo previsto para"} {fmtData(ciclo.data_povoamento)}
          </h4>
          <Badge variant={status.variante}>{status.rotulo}</Badge>
        </div>
        {/* Só o gestor (único com valores) corrige vendas; o ciclo finalizado não aparece em outra tela do viveiro */}
        {comValores && finalizado && (
          <Button size="sm" variant="outline" onClick={onCorrigirVendas}>
            <Receipt className="w-4 h-4 mr-2" />
            Corrigir vendas
          </Button>
        )}
      </header>

      <ol className="relative ml-3 space-y-5 border-l-2 border-slate-200">
        <Passo icone={ClipboardList} titulo="Preparo do viveiro">
          {ciclo.etapas.length === 0 ? (
            <p className="text-slate-400">Sem etapas de preparo registradas.</p>
          ) : (
            <ul className="space-y-1">
              {ciclo.etapas.map((e, i) => (
                <li key={i} className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <span className="font-semibold text-slate-800">{ROTULO_TIPO_ETAPA[e.tipo] ?? e.tipo}</span>
                  <Badge variant={VARIANTE_STATUS[e.status] ?? "secondary"}>{ROTULO_STATUS_ETAPA[e.status] ?? e.status}</Badge>
                  {periodoEtapa(e) && <span className="tabular-nums">{periodoEtapa(e)}</span>}
                </li>
              ))}
            </ul>
          )}
        </Passo>

        <Passo icone={Sprout} titulo={povoado ? "Povoamento" : "Povoamento previsto"}>
          <p>
            <strong className="text-slate-800">{fmtData(ciclo.data_povoamento)}</strong>
            {povoado && (
              <>
                {" "}
                · <strong className="text-slate-800 tabular-nums">{ciclo.quantidade_pos_larvas?.toLocaleString("pt-BR")}</strong>{" "}
                pós-larvas
              </>
            )}
          </p>
        </Passo>

        {(povoado || ciclo.insumos.length > 0) && (
          <Passo icone={Package} titulo="Insumos e ração">
            {ciclo.insumos.length === 0 ? (
              <p className="text-slate-400">Nenhum insumo usado.</p>
            ) : (
              <ul className="space-y-0.5">
                {ciclo.insumos.map((i) => (
                  <li key={i.insumo_id} className="tabular-nums">
                    <span className="font-semibold text-slate-800">{i.nome}</span>: {fmtQtd(i.quantidade_total)} {i.unidade_uso}
                    {i.custo_total_rs !== null && <> · {fmtMoney(i.custo_total_rs)}</>}
                  </li>
                ))}
              </ul>
            )}
            {povoado &&
              (ciclo.racao_total_kg > 0 ? (
                <p className="tabular-nums">
                  <span className="font-semibold text-slate-800">Ração</span>: {fmtQtd(ciclo.racao_total_kg)} kg
                  {ciclo.racao_custo_rs !== null && <> · {fmtMoney(ciclo.racao_custo_rs)}</>}
                </p>
              ) : (
                <p className="text-slate-400">Nenhuma ração registrada.</p>
              ))}
            {semanas.length > 0 && (
              <details className="pt-1">
                <summary className="cursor-pointer font-semibold text-sky-700">Ração por semana ({semanas.length})</summary>
                <div className="mt-2 overflow-x-auto">
                  <table className="w-full text-left tabular-nums">
                    <thead className="text-[11px] text-slate-400">
                      <tr>
                        <th className="pr-3 font-semibold">Semana</th>
                        <th className="pr-3 font-semibold">Ração (kg)</th>
                        {semanasComCusto && <th className="pr-3 font-semibold">Custo</th>}
                        <th className="font-semibold">FCA parcial</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {semanas.map((s) => (
                        <tr key={s.inicio}>
                          <td className="py-1 pr-3">
                            {fmtData(s.inicio)} a {fmtData(s.fim)}
                          </td>
                          <td className="py-1 pr-3">{fmtQtd(s.kg)}</td>
                          {semanasComCusto && <td className="py-1 pr-3">{s.custo_rs !== null ? fmtMoney(s.custo_rs) : "—"}</td>}
                          <td className="py-1">{fmtFca(s.fca_parcial)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            )}
          </Passo>
        )}

        {povoado && (
          <Passo icone={Receipt} titulo="Desbastes e despesca final">
            {ciclo.vendas.quantidade === 0 ? (
              <p className="text-slate-400">Nenhuma venda registrada.</p>
            ) : (
              <p className="tabular-nums">
                {ciclo.vendas.quantidade === 1 ? "1 venda" : `${ciclo.vendas.quantidade} vendas`} ·{" "}
                {fmtQtd(ciclo.vendas.biomassa_total_kg)} kg
                {ciclo.vendas.receita_rs !== null && <> · receita de {fmtMoney(ciclo.vendas.receita_rs)}</>}
              </p>
            )}
            {ciclo.data_despesca_real && (
              <p>
                Despesca final em <strong className="text-slate-800">{fmtData(ciclo.data_despesca_real)}</strong>
              </p>
            )}
          </Passo>
        )}

        {povoado && (
          <Passo icone={CheckCircle2} titulo={finalizado ? "Resultado final" : "Resultado até agora"}>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
              {finalizado && (
                <>
                  <Dado rotulo="Peso final">{ciclo.peso_final_g !== null ? `${fmtQtd(ciclo.peso_final_g)} g` : "—"}</Dado>
                  <Dado rotulo="Sobrevivência final">
                    {ciclo.sobrevivencia_final_pct !== null ? `${fmtQtd(ciclo.sobrevivencia_final_pct)}%` : "—"}
                  </Dado>
                </>
              )}
              <Dado rotulo={finalizado ? "FCA final" : "FCA atual"}>{fmtFca(ciclo.fca)}</Dado>
              {comValores && (
                <>
                  <Dado rotulo="Custo total">{fmtMoney(ciclo.custo_total_rs ?? 0)}</Dado>
                  <Dado rotulo="Custo por kg">{ciclo.custo_por_kg_rs !== null ? fmtMoney(ciclo.custo_por_kg_rs) : "—"}</Dado>
                  <Dado rotulo="Margem realizada">{ciclo.margem_pct !== null ? `${fmtQtd(ciclo.margem_pct)}%` : "—"}</Dado>
                  <Dado rotulo={finalizado ? "Lucro realizado (definitivo)" : "Lucro realizado (parcial)"}>
                    <span className={(ciclo.lucro_realizado_rs ?? 0) >= 0 ? "text-emerald-600" : "text-red-600"}>
                      {fmtMoney(ciclo.lucro_realizado_rs ?? 0)}
                    </span>
                  </Dado>
                </>
              )}
            </dl>
          </Passo>
        )}
      </ol>
    </section>
  );
}

/** Aba "Histórico" do viveiro: um cartão em linha do tempo por ciclo, do mais recente ao mais antigo. */
export function HistoricoViveiro({ viveiroId }: { viveiroId: string }) {
  // Guardado com o viveiro a que pertence: trocar de viveiro não mostra a lista do anterior
  const [carregado, setCarregado] = useState<{ viveiroId: string; lista: HistoricoCiclo[] | null } | null>(null);
  const [versao, setVersao] = useState(0);
  const [corrigindo, setCorrigindo] = useState<HistoricoCiclo | null>(null);

  useEffect(() => {
    let ativo = true;
    viveirosApi
      .historico(viveiroId)
      .then((lista) => {
        if (ativo) setCarregado({ viveiroId, lista });
      })
      .catch((err) => {
        if (ativo) {
          setCarregado({ viveiroId, lista: null });
          toast.error("Não foi possível carregar o histórico do viveiro", mensagemErro(err, "Tente novamente"));
        }
      });
    return () => {
      ativo = false;
    };
  }, [viveiroId, versao]);

  const atual = carregado && carregado.viveiroId === viveiroId ? carregado : null;
  const historico = atual?.lista ?? null;
  const falhou = atual !== null && atual.lista === null;

  return (
    <div className="space-y-4">
      <h3 className="font-bold text-slate-900 text-base">Histórico de ciclos</h3>

      {historico === null && !falhou && (
        <div className="flex justify-center py-8">
          <Loader2 className="w-5 h-5 text-sky-500 animate-spin" />
        </div>
      )}
      {falhou && (
        <div className="bg-white rounded-2xl border border-slate-200/80 p-8 text-center shadow-sm">
          <p className="text-xs text-red-500">Não foi possível carregar o histórico do viveiro.</p>
          <Button size="sm" variant="outline" className="mt-3" onClick={() => setVersao((v) => v + 1)}>
            Tentar novamente
          </Button>
        </div>
      )}
      {historico !== null && historico.length === 0 && (
        <p className="bg-white rounded-2xl border border-slate-200/80 p-8 text-center text-xs text-slate-400 shadow-sm">
          Este viveiro ainda não tem ciclos.
        </p>
      )}
      {historico?.map((c) => (
        <CicloHistorico key={c.ciclo_id} ciclo={c} onCorrigirVendas={() => setCorrigindo(c)} />
      ))}

      <Dialog
        open={corrigindo !== null}
        onOpenChange={(aberto) => !aberto && setCorrigindo(null)}
        title="Corrigir vendas do ciclo"
        description={corrigindo ? `Ciclo povoado em ${fmtData(corrigindo.data_povoamento)}` : undefined}
        className="max-w-2xl max-h-[90vh] overflow-y-auto"
      >
        {corrigindo && <VendasCiclo cicloId={corrigindo.ciclo_id} onAlterado={() => setVersao((v) => v + 1)} />}
      </Dialog>
    </div>
  );
}
