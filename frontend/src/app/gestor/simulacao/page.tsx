"use client";

import { useEffect, useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  Loader2,
  AlertTriangle,
  Shell,
  DollarSign,
  Scale,
  CalendarDays,
  Target,
  ChevronDown,
  Info,
  CheckCircle2,
  XCircle,
  BarChart3,
} from "lucide-react";
import { ciclosApi, simulacaoApi, viveirosApi } from "@/lib/api";
import type { CicloProdutivo, Viveiro, SimulacaoResponse, SimulacaoComparativa } from "@/lib/types";

function fmtMoney(v: number) {
  return `R$ ${v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function SimulacaoPage() {
  const [viveiros, setViveiros] = useState<Viveiro[]>([]);
  const [ciclos, setCiclos] = useState<CicloProdutivo[]>([]);
  const [selectedCiclo, setSelectedCiclo] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [result, setResult] = useState<SimulacaoComparativa | null>(null);
  const [error, setError] = useState("");

  // Custom simulation
  const [customDias, setCustomDias] = useState("7");
  const [customPreco, setCustomPreco] = useState("");
  const [customResult, setCustomResult] = useState<SimulacaoResponse | null>(null);
  const [customLoading, setCustomLoading] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [vivs, cycs] = await Promise.all([
          viveirosApi.listar(),
          ciclosApi.listar({ status_filtro: "ATIVO" }),
        ]);
        setViveiros(vivs);
        setCiclos(cycs);
        if (cycs.length > 0) setSelectedCiclo(cycs[0].id);
      } catch {
        // handle
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const getViveiroName = (vId: string) =>
    viveiros.find((v) => v.id === vId)?.identificacao || "—";

  const handleComparativo = async () => {
    if (!selectedCiclo) return;
    setError("");
    setSimulating(true);
    setResult(null);
    setCustomResult(null);
    try {
      const data = await simulacaoApi.comparativo(selectedCiclo);
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Erro ao simular");
    } finally {
      setSimulating(false);
    }
  };

  const handleCustom = async () => {
    if (!selectedCiclo) return;
    setError("");
    setCustomLoading(true);
    try {
      const data = await simulacaoApi.simular(
        selectedCiclo,
        parseInt(customDias),
        customPreco ? parseFloat(customPreco) : undefined
      );
      setCustomResult(data);
    } catch (err: any) {
      setError(err.message || "Erro ao simular");
    } finally {
      setCustomLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-8 h-8 text-ocean-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)]">
          Simulador ΔV — Despesca
        </h1>
        <p className="text-[var(--text-secondary)] text-sm mt-1">
          Compare cenários de horizonte e decida o melhor momento para despescar
        </p>
      </div>

      {ciclos.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <Shell className="w-12 h-12 text-[var(--text-muted)] mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">Nenhum ciclo ativo</h3>
          <p className="text-sm text-[var(--text-muted)]">Inicie um ciclo produtivo para poder usar o simulador</p>
        </div>
      ) : (
        <>
          {/* Selector */}
          <div className="glass-card p-5 mb-6">
            <div className="flex flex-col sm:flex-row gap-4 items-end">
              <div className="flex-1">
                <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
                  Selecione o ciclo
                </label>
                <select
                  value={selectedCiclo}
                  onChange={(e) => { setSelectedCiclo(e.target.value); setResult(null); setCustomResult(null); }}
                  className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-ocean-500 transition-all appearance-none"
                >
                  {ciclos.map((c) => (
                    <option key={c.id} value={c.id} className="bg-[var(--bg-secondary)]">
                      {getViveiroName(c.viveiro_id)} — Povoado em {new Date(c.data_povoamento).toLocaleDateString("pt-BR")}
                    </option>
                  ))}
                </select>
              </div>
              <button
                onClick={handleComparativo}
                disabled={simulating || !selectedCiclo}
                className="px-6 py-3 rounded-xl bg-gradient-to-r from-ocean-600 to-ocean-500 text-white font-semibold flex items-center gap-2 hover:from-ocean-500 hover:to-ocean-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-ocean-500/20 active:scale-[0.98]"
              >
                {simulating ? <Loader2 className="w-5 h-5 animate-spin" /> : <BarChart3 className="w-5 h-5" />}
                Comparativo (7, 10, 15 dias)
              </button>
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm mb-6">
              <AlertTriangle className="w-4 h-4 shrink-0" /> {error}
            </div>
          )}

          {/* Comparativo Results */}
          {result && (
            <div className="mb-8">
              <h2 className="text-lg font-bold text-[var(--text-primary)] mb-4">
                Resultado Comparativo
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {result.simulacoes.map((sim) => {
                  const isBest = result.melhor_cenario?.dias_horizonte === sim.dias_horizonte;
                  const isDespesca = sim.recomendacao === "DESPESCA_IMEDIATA";
                  return (
                    <div
                      key={sim.dias_horizonte}
                      className={`glass-card p-5 relative transition-all ${
                        isBest ? "border-pond-500/40 shadow-lg shadow-pond-500/10" : ""
                      }`}
                    >
                      {isBest && (
                        <div className="absolute -top-3 left-4 px-3 py-0.5 rounded-full bg-pond-500 text-white text-xs font-bold">
                          ✨ Melhor cenário
                        </div>
                      )}

                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-bold text-[var(--text-primary)]">
                          {sim.dias_horizonte} dias
                        </h3>
                        <span
                          className={`text-xs px-2.5 py-1 rounded-full font-bold ${
                            isDespesca ? "badge-danger" : "badge-success"
                          }`}
                        >
                          {isDespesca ? "Despescar Já" : "Manter Cultivo"}
                        </span>
                      </div>

                      <div className="space-y-3">
                        <div className="flex justify-between text-sm">
                          <span className="text-[var(--text-muted)]">Peso projetado</span>
                          <span className="text-[var(--text-primary)] font-semibold tabular-nums">
                            {sim.peso_medio_projetado_g.toFixed(1)} g
                          </span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-[var(--text-muted)]">Biomassa proj.</span>
                          <span className="text-[var(--text-primary)] font-semibold tabular-nums">
                            {sim.biomassa_projetada_kg.toLocaleString("pt-BR")} kg
                          </span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-[var(--text-muted)]">Receita proj.</span>
                          <span className="text-pond-400 font-semibold tabular-nums">
                            {fmtMoney(sim.receita_projetada_rs)}
                          </span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-[var(--text-muted)]">Custo adicional</span>
                          <span className="text-red-400 font-semibold tabular-nums">
                            {fmtMoney(sim.custo_adicional_projetado_rs)}
                          </span>
                        </div>

                        <div className="border-t border-[var(--border-subtle)] pt-3 mt-3">
                          <div className="flex justify-between text-sm">
                            <span className="text-[var(--text-muted)]">Lucro projetado</span>
                            <span
                              className={`font-bold tabular-nums ${
                                sim.lucro_projetado_rs >= 0 ? "text-pond-400" : "text-red-400"
                              }`}
                            >
                              {fmtMoney(sim.lucro_projetado_rs)}
                            </span>
                          </div>
                          <div className="flex justify-between text-sm mt-2">
                            <span className="font-medium text-ocean-400">ΔV</span>
                            <span
                              className={`text-lg font-black tabular-nums ${
                                sim.delta_v_rs > 0 ? "text-pond-400" : "text-red-400"
                              }`}
                            >
                              {sim.delta_v_rs > 0 ? "+" : ""}
                              {fmtMoney(sim.delta_v_rs)}
                            </span>
                          </div>
                        </div>
                      </div>

                      <p className="text-xs text-[var(--text-muted)] mt-3 italic">{sim.justificativa}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Custom simulation */}
          <div className="glass-card p-5">
            <h2 className="text-lg font-bold text-[var(--text-primary)] mb-4">
              Simulação Customizada
            </h2>
            <div className="flex flex-col sm:flex-row gap-4 items-end">
              <div>
                <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Horizonte (dias)</label>
                <select
                  value={customDias}
                  onChange={(e) => setCustomDias(e.target.value)}
                  className="px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-ocean-500 transition-all"
                >
                  <option value="7" className="bg-[var(--bg-secondary)]">7 dias</option>
                  <option value="10" className="bg-[var(--bg-secondary)]">10 dias</option>
                  <option value="15" className="bg-[var(--bg-secondary)]">15 dias</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Preço custom (R$/kg)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  inputMode="decimal"
                  value={customPreco}
                  onChange={(e) => setCustomPreco(e.target.value)}
                  placeholder="Usar tabela"
                  className="px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 transition-all w-40"
                />
              </div>
              <button
                onClick={handleCustom}
                disabled={customLoading || !selectedCiclo}
                className="px-5 py-3 rounded-xl bg-shrimp-500/15 text-shrimp-400 border border-shrimp-500/25 font-semibold flex items-center gap-2 hover:bg-shrimp-500/25 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {customLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Target className="w-5 h-5" />}
                Simular
              </button>
            </div>

            {customResult && (
              <div className="mt-5 p-4 rounded-xl bg-white/5 border border-[var(--border-subtle)]">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-3">
                  <div>
                    <p className="text-xs text-[var(--text-muted)]">Peso projetado</p>
                    <p className="text-lg font-bold text-[var(--text-primary)] tabular-nums">{customResult.peso_medio_projetado_g.toFixed(1)} g</p>
                  </div>
                  <div>
                    <p className="text-xs text-[var(--text-muted)]">Lucro projetado</p>
                    <p className={`text-lg font-bold tabular-nums ${customResult.lucro_projetado_rs >= 0 ? "text-pond-400" : "text-red-400"}`}>{fmtMoney(customResult.lucro_projetado_rs)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[var(--text-muted)]">ΔV</p>
                    <p className={`text-xl font-black tabular-nums ${customResult.delta_v_rs > 0 ? "text-pond-400" : "text-red-400"}`}>
                      {customResult.delta_v_rs > 0 ? "+" : ""}{fmtMoney(customResult.delta_v_rs)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-[var(--text-muted)]">Recomendação</p>
                    <span className={`text-sm px-2.5 py-1 rounded-full font-bold inline-block mt-1 ${customResult.recomendacao === "DESPESCA_IMEDIATA" ? "badge-danger" : "badge-success"}`}>
                      {customResult.recomendacao === "DESPESCA_IMEDIATA" ? "Despescar Já" : "Manter Cultivo"}
                    </span>
                  </div>
                </div>
                <p className="text-sm text-[var(--text-secondary)] italic">{customResult.justificativa}</p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
