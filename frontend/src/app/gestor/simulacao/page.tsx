"use client";

import { useEffect, useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  Loader2,
  Shell,
  Target,
  Sparkles,
  BarChart3,
  Clock,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import { ciclosApi, simulacaoApi, viveirosApi } from "@/lib/api";
import { mensagemErro } from "@/lib/utils";
import type { CicloProdutivo, Viveiro, SimulacaoResponse, SimulacaoComparativa } from "@/lib/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/toast";

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

  // Custom simulation
  const [customDias, setCustomDias] = useState("7");
  const [customPreco, setCustomPreco] = useState("");
  const [custoDiario, setCustoDiario] = useState("");
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
    setSimulating(true);
    setResult(null);
    setCustomResult(null);
    try {
      const data = await simulacaoApi.comparativo(
        selectedCiclo,
        custoDiario ? parseFloat(custoDiario) : undefined
      );
      setResult(data);
      toast.success("Simulação comparativa executada!", "Cenários de 7, 10 e 15 dias calculados pelo algoritmo ΔV.");
    } catch (err) {
      toast.error("Falha ao executar simulação", mensagemErro(err, "Tente novamente"));
    } finally {
      setSimulating(false);
    }
  };

  const handleCustom = async () => {
    if (!selectedCiclo) return;
    setCustomLoading(true);
    try {
      const data = await simulacaoApi.simular(
        selectedCiclo,
        parseInt(customDias),
        customPreco ? parseFloat(customPreco) : undefined,
        custoDiario ? parseFloat(custoDiario) : undefined
      );
      setCustomResult(data);
      toast.success("Cenário customizado calculado!");
    } catch (err) {
      toast.error("Erro na simulação customizada", mensagemErro(err, "Tente novamente"));
    } finally {
      setCustomLoading(false);
    }
  };

  const chartData = result
    ? result.simulacoes.map((s) => ({
        cenario: `+${s.dias_horizonte} dias`,
        lucro: s.lucro_projetado_rs,
        receita: s.receita_projetada_rs,
        custoAdicional: s.custo_adicional_projetado_rs,
        deltaV: s.delta_v_rs,
      }))
    : [];

  const melhorCenario = result?.melhor_cenario;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* ── Page Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Motor de Decisão Preditivo
            </span>
            <span className="h-1 w-1 rounded-full bg-slate-300" />
            <span className="text-xs font-semibold text-emerald-600">
              Algoritmo Bioeconômico ΔV
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            Simulador de Ponto Ótimo de Despesca
          </h1>
          <p className="text-slate-500 text-xs mt-1">
            Modela ganho de biomassa diária vs. custos incrementais de ração e energia para maximizar o lucro líquido.
          </p>
        </div>
      </div>

      {ciclos.length === 0 ? (
        <Card className="p-10 text-center">
          <Shell className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="font-bold text-slate-800">Nenhum ciclo produtivo ativo</h3>
          <p className="text-xs text-slate-500 mt-1">Inicie um ciclo em um viveiro para simular a despesca.</p>
        </Card>
      ) : (
        <>
          {/* ── Card Seletor e Ação de Simulação ── */}
          <Card>
            <CardContent className="p-5">
              <div className="flex flex-col sm:flex-row gap-4 items-end">
                <div className="flex-1 w-full">
                  <Label>Selecione o Ciclo Ativo para Análise</Label>
                  <select
                    value={selectedCiclo}
                    onChange={(e) => {
                      setSelectedCiclo(e.target.value);
                      setResult(null);
                      setCustomResult(null);
                    }}
                    className="w-full mt-1.5 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-semibold text-slate-800 focus:border-sky-500 focus:outline-none"
                  >
                    {ciclos.map((c) => (
                      <option key={c.id} value={c.id}>
                        {getViveiroName(c.viveiro_id)} — Lote #{c.id.substring(0, 6)} (Povoamento: {new Date(c.data_povoamento).toLocaleDateString("pt-BR")})
                      </option>
                    ))}
                  </select>
                </div>

                <Button
                  onClick={handleComparativo}
                  disabled={simulating || !selectedCiclo}
                  className="w-full sm:w-auto h-11 px-6 font-bold"
                >
                  {simulating ? (
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Calculando Curva...
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4" />
                      Calcular Horizontes (7, 10 e 15 dias)
                    </div>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* ── Card de Decisão Executiva em Destaque ── */}
          {result && melhorCenario && (
            <div className="space-y-6">
              <div
                className={`rounded-2xl p-6 border-2 shadow-lg transition-all ${
                  melhorCenario.recomendacao === "DESPESCA_IMEDIATA"
                    ? "bg-amber-50 border-amber-300 text-amber-950 shadow-amber-500/10"
                    : "bg-emerald-50 border-emerald-300 text-emerald-950 shadow-emerald-500/10"
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex items-start gap-3.5">
                    <div
                      className={`h-12 w-12 rounded-2xl flex items-center justify-center shrink-0 border ${
                        melhorCenario.recomendacao === "DESPESCA_IMEDIATA"
                          ? "bg-amber-100 text-amber-700 border-amber-200"
                          : "bg-emerald-100 text-emerald-700 border-emerald-200"
                      }`}
                    >
                      {melhorCenario.recomendacao === "DESPESCA_IMEDIATA" ? (
                        <TrendingDown className="h-6 w-6" />
                      ) : (
                        <TrendingUp className="h-6 w-6" />
                      )}
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={melhorCenario.recomendacao === "DESPESCA_IMEDIATA" ? "warning" : "success"}
                          className="text-[11px] font-black"
                        >
                          {melhorCenario.recomendacao === "DESPESCA_IMEDIATA" ? "DESPESCA RECOMENDADA" : "MANTER CULTIVO"}
                        </Badge>
                        <span className="text-xs text-slate-500 font-bold">
                          Horizonte ótimo: +{melhorCenario.dias_horizonte} dias
                        </span>
                      </div>

                      <h2 className="text-xl font-black mt-1">
                        {melhorCenario.recomendacao === "DESPESCA_IMEDIATA"
                          ? "Despesca Imediata Recomendada para este Viveiro"
                          : `Manter Cultivo por mais ${melhorCenario.dias_horizonte} dias para Maximizar Lucro`}
                      </h2>

                      <p className="text-xs opacity-90 mt-1 max-w-2xl leading-relaxed">
                        {melhorCenario.justificativa}
                      </p>
                    </div>
                  </div>

                  <div className="bg-white/80 backdrop-blur-sm p-4 rounded-xl border border-black/5 text-right shrink-0">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                      Ganho Financeiro Adicional (ΔV)
                    </span>
                    <span
                      className={`text-2xl font-black tabular-nums block mt-0.5 ${
                        melhorCenario.delta_v_rs > 0 ? "text-emerald-600" : "text-amber-600"
                      }`}
                    >
                      {melhorCenario.delta_v_rs > 0 ? "+" : ""}
                      {fmtMoney(melhorCenario.delta_v_rs)}
                    </span>
                    <span className="text-[11px] text-slate-500 font-semibold">
                      Lucro final projetado: {fmtMoney(melhorCenario.lucro_projetado_rs)}
                    </span>
                  </div>
                </div>
              </div>

              {/* ── Cards dos Cenários Comparativos ── */}
              <div>
                <h3 className="text-base font-bold text-slate-900 mb-3 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-sky-600" />
                  Comparativo de Horizontes Simulados
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {result.simulacoes.map((sim) => {
                    const isBest = result.melhor_cenario?.dias_horizonte === sim.dias_horizonte;
                    const isDespesca = sim.recomendacao === "DESPESCA_IMEDIATA";

                    return (
                      <Card
                        key={sim.dias_horizonte}
                        className={`relative transition-all ${
                          isBest
                            ? "border-2 border-emerald-500 shadow-md ring-2 ring-emerald-500/10"
                            : "hover:border-slate-300"
                        }`}
                      >
                        {isBest && (
                          <div className="absolute -top-3 left-4 px-3 py-0.5 rounded-full bg-emerald-600 text-white text-[11px] font-black shadow-sm">
                            ✨ Ponto Ótimo Econômico
                          </div>
                        )}

                        <CardHeader className="pb-3">
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-lg font-black text-slate-900">
                              +{sim.dias_horizonte} dias de cultivo
                            </CardTitle>
                            <Badge variant={isDespesca ? "destructive" : "success"}>
                              {isDespesca ? "Despescar" : "Manter"}
                            </Badge>
                          </div>
                        </CardHeader>

                        <CardContent className="space-y-3 pt-0 text-xs">
                          <div className="flex justify-between border-b border-slate-100 pb-2">
                            <span className="text-slate-500">Peso médio esperado:</span>
                            <span className="font-extrabold text-slate-900 tabular-nums">
                              {sim.peso_medio_projetado_g.toFixed(1)} g
                            </span>
                          </div>

                          <div className="flex justify-between border-b border-slate-100 pb-2">
                            <span className="text-slate-500">Biomassa projetada:</span>
                            <span className="font-extrabold text-slate-900 tabular-nums">
                              {sim.biomassa_projetada_kg.toLocaleString("pt-BR")} kg
                            </span>
                          </div>

                          <div className="flex justify-between border-b border-slate-100 pb-2">
                            <span className="text-slate-500">Receita bruta esperada:</span>
                            <span className="font-bold text-sky-600 tabular-nums">
                              {fmtMoney(sim.receita_projetada_rs)}
                            </span>
                          </div>

                          <div className="flex justify-between border-b border-slate-100 pb-2">
                            <span className="text-slate-500">Custo adicional de ração/energia:</span>
                            <span className="font-bold text-red-500 tabular-nums">
                              {fmtMoney(sim.custo_adicional_projetado_rs)}
                            </span>
                          </div>

                          <div className="pt-2 bg-slate-50 p-2.5 rounded-xl border border-slate-100 flex items-center justify-between">
                            <div>
                              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                                Variação Líquida (ΔV)
                              </span>
                              <span
                                className={`text-base font-black tabular-nums ${
                                  sim.delta_v_rs > 0 ? "text-emerald-600" : "text-red-500"
                                }`}
                              >
                                {sim.delta_v_rs > 0 ? "+" : ""}
                                {fmtMoney(sim.delta_v_rs)}
                              </span>
                            </div>
                            <div className="text-right">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                                Lucro Total
                              </span>
                              <span className="text-sm font-extrabold text-slate-900 tabular-nums">
                                {fmtMoney(sim.lucro_projetado_rs)}
                              </span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              </div>

              {/* ── Gráfico Comparativo Recharts ── */}
              {chartData.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <BarChart3 className="w-4 h-4 text-sky-600" />
                      Projeção Econômica por Horizonte de Dias
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-64 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                          <XAxis dataKey="cenario" stroke="#64748b" fontSize={12} />
                          <YAxis stroke="#64748b" fontSize={12} tickFormatter={(val) => `R$ ${(val / 1000).toFixed(0)}k`} />
                          <Tooltip
                            formatter={(value) => [fmtMoney(Number(value)), ""]}
                            contentStyle={{ backgroundColor: "#ffffff", borderRadius: "12px", border: "1px solid #e2e8f0" }}
                          />
                          <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                          <Bar dataKey="lucro" name="Lucro Operacional Projetado" fill="#10b981" radius={[6, 6, 0, 0]} />
                          <Bar dataKey="deltaV" name="Ganho Marginal (ΔV)" fill="#0284c7" radius={[6, 6, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* ── Simulação Customizada ── */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Target className="w-4 h-4 text-sky-600" />
                Simulação Customizada de Parâmetros
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col sm:flex-row gap-4 items-end">
                <div className="w-full sm:w-48">
                  <Label>Horizonte Desejado</Label>
                  <select
                    value={customDias}
                    onChange={(e) => setCustomDias(e.target.value)}
                    className="w-full mt-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-slate-800 focus:outline-none"
                  >
                    <option value="7">7 dias</option>
                    <option value="10">10 dias</option>
                    <option value="15">15 dias</option>
                  </select>
                </div>

                <div className="w-full sm:w-48">
                  <Label>Preço Custom (R$/kg)</Label>
                  <Input
                    type="number"
                    step="0.5"
                    min="0"
                    value={customPreco}
                    onChange={(e) => setCustomPreco(e.target.value)}
                    placeholder="Usar tabela padrão"
                    className="mt-1.5"
                  />
                </div>

                <div className="w-full sm:w-56">
                  <Label>Custo Diário (R$)</Label>
                  <Input
                    type="number"
                    step="10"
                    min="0"
                    value={custoDiario}
                    onChange={(e) => setCustoDiario(e.target.value)}
                    placeholder="Média dos custos lançados"
                    className="mt-1.5"
                  />
                </div>

                <Button
                  onClick={handleCustom}
                  disabled={customLoading || !selectedCiclo}
                  variant="outline"
                  className="w-full sm:w-auto h-11"
                >
                  {customLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Target className="w-4 h-4" />}
                  Simular Cenário
                </Button>
              </div>

              {customResult && (
                <div className="mt-5 p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div>
                      <span className="text-slate-400 block font-semibold">Peso Projetado</span>
                      <strong className="text-base text-slate-900 tabular-nums">
                        {customResult.peso_medio_projetado_g.toFixed(1)} g
                      </strong>
                    </div>
                    <div>
                      <span className="text-slate-400 block font-semibold">Lucro Projetado</span>
                      <strong className="text-base text-slate-900 tabular-nums">
                        {fmtMoney(customResult.lucro_projetado_rs)}
                      </strong>
                    </div>
                    <div>
                      <span className="text-slate-400 block font-semibold">Variação ΔV</span>
                      <strong className={`text-base tabular-nums ${customResult.delta_v_rs > 0 ? "text-emerald-600" : "text-red-500"}`}>
                        {customResult.delta_v_rs > 0 ? "+" : ""}{fmtMoney(customResult.delta_v_rs)}
                      </strong>
                    </div>
                    <div>
                      <span className="text-slate-400 block font-semibold">Decisão</span>
                      <Badge variant={customResult.recomendacao === "DESPESCA_IMEDIATA" ? "warning" : "success"} className="mt-1">
                        {customResult.recomendacao === "DESPESCA_IMEDIATA" ? "Despescar" : "Manter"}
                      </Badge>
                    </div>
                  </div>
                  <p className="mt-3 text-slate-600 leading-relaxed">{customResult.justificativa}</p>
                  {customResult.premissas.length > 0 && (
                    <ul className="mt-2 list-disc pl-4 text-slate-500 space-y-0.5">
                      {customResult.premissas.map((p) => (
                        <li key={p}>{p}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
