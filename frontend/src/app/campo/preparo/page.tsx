"use client";

import { useEffect, useState } from "react";
import { Loader2, Sprout } from "lucide-react";
import { ciclosApi, viveirosApi } from "@/lib/api";
import { mensagemErro } from "@/lib/utils";
import type { CicloProdutivo, Viveiro } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/toast";
import { fmtData, ListaUsosInsumo, useUsosInsumo } from "@/components/insumos/lista-usos-insumo";
import { UsoInsumoForm } from "@/components/insumos/uso-insumo-form";
import { ChecklistEtapas, useEtapasPreparo } from "@/components/viveiro/preparo-ciclo";

/** Preparo do viveiro para o campo: atualiza as etapas do ciclo planejado e lança os insumos usados nelas. */
export default function PreparoCampoPage() {
  const [viveiros, setViveiros] = useState<Viveiro[]>([]);
  const [ciclos, setCiclos] = useState<CicloProdutivo[]>([]);
  const [cicloId, setCicloId] = useState("");
  const [loading, setLoading] = useState(true);
  const { etapas, falhou, recarregar: recarregarEtapas } = useEtapasPreparo(cicloId);
  const { usos, recarregar: recarregarUsos } = useUsosInsumo(cicloId);

  useEffect(() => {
    async function carregar() {
      try {
        const [vivs, cycs] = await Promise.all([viveirosApi.listar(), ciclosApi.listar({ status_filtro: "PLANEJADO" })]);
        setViveiros(vivs);
        setCiclos(cycs);
        if (cycs.length > 0) setCicloId(cycs[0].id);
      } catch (err) {
        toast.error("Erro ao carregar o preparo", mensagemErro(err, "Tente recarregar a página"));
      } finally {
        setLoading(false);
      }
    }
    carregar();
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto space-y-5 pb-12">
      <div className="rounded-3xl bg-gradient-to-br from-[#0c1527] to-[#152238] p-6 text-white shadow-xl border border-white/10">
        <div className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold border mb-3 bg-emerald-500/20 text-emerald-300 border-emerald-500/30">
          <span className="h-2 w-2 rounded-full animate-pulse bg-emerald-400" />
          Módulo de Campo
        </div>
        <h1 className="text-2xl font-black tracking-tight flex items-center gap-2.5">
          <Sprout className="h-6 w-6 text-emerald-400" />
          Preparo do Viveiro
        </h1>
        <p className="text-xs text-slate-300 mt-1">
          Marque a situação de cada etapa antes do povoamento e registre os insumos aplicados nelas.
        </p>
      </div>

      {ciclos.length === 0 ? (
        <p className="rounded-2xl border border-slate-200/90 bg-white p-5 text-center text-xs text-slate-500 shadow-sm">
          Nenhum viveiro em preparo. O gestor planeja o ciclo para abrir as etapas do preparo.
        </p>
      ) : (
        <>
          <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm">
            <label htmlFor="ciclo-preparo" className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Viveiro em preparo
            </label>
            <select
              id="ciclo-preparo"
              value={cicloId}
              onChange={(e) => setCicloId(e.target.value)}
              className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-800 focus:border-sky-500 focus:outline-none"
            >
              {ciclos.map((c) => (
                <option key={c.id} value={c.id}>
                  {viveiros.find((v) => v.id === c.viveiro_id)?.identificacao || "Viveiro"} — povoamento previsto{" "}
                  {fmtData(c.data_povoamento)}
                </option>
              ))}
            </select>
          </div>

          <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">Etapas do preparo</h2>
            <ChecklistEtapas cicloId={cicloId} etapas={etapas} falhou={falhou} onAlterado={recarregarEtapas} />
          </div>

          <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">Registrar uso de insumo</h2>
            <UsoInsumoForm
              key={cicloId}
              cicloId={cicloId}
              fase="PREPARO"
              etapas={etapas ?? undefined}
              onSalvo={recarregarUsos}
            />
          </div>

          <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">Últimos usos lançados</h2>
              {usos && <Badge variant="secondary">{usos.length}</Badge>}
            </div>
            <ListaUsosInsumo usos={usos && usos.slice(0, 5)} />
          </div>
        </>
      )}
    </div>
  );
}
