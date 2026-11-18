"use client";

import { useEffect, useState } from "react";
import { Loader2, Package } from "lucide-react";
import { ciclosApi, viveirosApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { CicloProdutivo, Viveiro } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { ListaUsosInsumo, useUsosInsumo } from "@/components/insumos/lista-usos-insumo";
import { UsoInsumoForm } from "@/components/insumos/uso-insumo-form";

const TEMA = {
  CAMPO: {
    etiqueta: "Módulo de Campo",
    pilula: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
    ponto: "bg-emerald-400",
    carregando: "text-emerald-500",
    texto: "Registre o produto aplicado no viveiro. O estoque e o custo do ciclo são atualizados com o seu lançamento.",
  },
  VIGIA: {
    etiqueta: "Vigia Noturno",
    pilula: "bg-amber-500/20 text-amber-300 border-amber-500/30",
    ponto: "bg-amber-400",
    carregando: "text-amber-500",
    texto: "Aplicou algum produto na ronda? Registre aqui para o estoque e o custo do ciclo ficarem corretos.",
  },
} as const;

/**
 * Tela de uso de insumo dos operadores. O campo vê os últimos usos do ciclo (sem valores em reais);
 * o vigia só lança, porque a API não lhe entrega a lista de usos.
 */
export function PaginaInsumosOperador({ perfil }: { perfil: keyof typeof TEMA }) {
  const tema = TEMA[perfil];
  const [viveiros, setViveiros] = useState<Viveiro[]>([]);
  const [ciclos, setCiclos] = useState<CicloProdutivo[]>([]);
  const [cicloId, setCicloId] = useState("");
  const [loading, setLoading] = useState(true);
  // Ciclo vazio: o vigia nunca pede a lista de usos (a rota é proibida para ele)
  const { usos, recarregar } = useUsosInsumo(perfil === "CAMPO" ? cicloId : "");

  useEffect(() => {
    async function carregar() {
      try {
        const [vivs, cycs] = await Promise.all([viveirosApi.listar(), ciclosApi.listar({ status_filtro: "ATIVO" })]);
        setViveiros(vivs);
        setCiclos(cycs);
        if (cycs.length > 0) setCicloId(cycs[0].id);
      } catch {
        // sem ciclos a tela mostra o aviso de ciclo ativo ausente
      } finally {
        setLoading(false);
      }
    }
    carregar();
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className={cn("h-8 w-8 animate-spin", tema.carregando)} />
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto space-y-5 pb-12">
      <div className="rounded-3xl bg-gradient-to-br from-[#0c1527] to-[#152238] p-6 text-white shadow-xl border border-white/10">
        <div className={cn("inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold border mb-3", tema.pilula)}>
          <span className={cn("h-2 w-2 rounded-full animate-pulse", tema.ponto)} />
          {tema.etiqueta}
        </div>
        <h1 className="text-2xl font-black tracking-tight flex items-center gap-2.5">
          <Package className="h-6 w-6 text-sky-400" />
          Uso de Insumos
        </h1>
        <p className="text-xs text-slate-300 mt-1">{tema.texto}</p>
      </div>

      {ciclos.length === 0 ? (
        <p className="rounded-2xl border border-slate-200/90 bg-white p-5 text-center text-xs text-slate-500 shadow-sm">
          Nenhum viveiro com ciclo ativo. O uso de insumo é lançado em um ciclo em andamento.
        </p>
      ) : (
        <>
          <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm">
            <label htmlFor="ciclo-insumo" className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Viveiro selecionado
            </label>
            <select
              id="ciclo-insumo"
              value={cicloId}
              onChange={(e) => setCicloId(e.target.value)}
              className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-800 focus:border-sky-500 focus:outline-none"
            >
              {ciclos.map((c) => (
                <option key={c.id} value={c.id}>
                  {viveiros.find((v) => v.id === c.viveiro_id)?.identificacao || "Viveiro"} — Lote #{c.id.substring(0, 6)}
                </option>
              ))}
            </select>
          </div>

          <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">Registrar uso</h2>
            <UsoInsumoForm cicloId={cicloId} fase="CULTIVO" onSalvo={recarregar} />
          </div>

          {perfil === "CAMPO" && (
            <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between mb-1">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500">Últimos usos lançados</h2>
                {usos && <Badge variant="secondary">{usos.length}</Badge>}
              </div>
              <ListaUsosInsumo usos={usos && usos.slice(0, 5)} />
            </div>
          )}
        </>
      )}
    </div>
  );
}
