"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Shell,
  Activity,
  Scale,
  TrendingUp,
  TrendingDown,
  DollarSign,
  AlertTriangle,
  Loader2,
  ChevronRight,
  Plus,
} from "lucide-react";
import { viveirosApi, ciclosApi } from "@/lib/api";
import type { Viveiro, CicloProdutivo, MetricasAtuais } from "@/lib/types";
import { MetricCard } from "@/components/ui/metric-card";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

// ── Viveiro Active Card ─────────────────────────────
function ViveiroActiveCard({
  viveiro,
  metricas,
}: {
  viveiro: Viveiro;
  metricas: MetricasAtuais | null;
}) {
  return (
    <Link href={`/gestor/viveiros/${viveiro.id}`}>
      <Card className="hover:border-sky-500/40 hover:shadow-md transition-all duration-300 cursor-pointer h-full group">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-sky-50 text-sky-600 border border-sky-100 flex items-center justify-center font-bold dark:bg-sky-950/40 dark:text-sky-400 dark:border-sky-800/40">
                <Shell className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-base text-slate-900 group-hover:text-sky-600 transition-colors dark:text-white">
                  {viveiro.identificacao}
                </h3>
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  {(viveiro.area_util_m2 / 10000).toFixed(1)} ha • Setor Produtivo
                </span>
              </div>
            </div>
            <Badge variant="success">Ciclo Ativo</Badge>
          </div>
        </CardHeader>

        <CardContent className="pt-0">
          {metricas ? (
            <div className="grid grid-cols-2 gap-3 pt-3 border-t border-slate-100 dark:border-white/5">
              <div>
                <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Dias de Cultivo
                </p>
                <p className="text-lg font-extrabold text-slate-900 dark:text-white tabular-nums">
                  {metricas.dias_cultivo} <span className="text-xs font-normal text-slate-400">dias</span>
                </p>
              </div>
              <div>
                <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Peso Médio
                </p>
                <p className="text-lg font-extrabold text-sky-600 dark:text-sky-400 tabular-nums">
                  {metricas.peso_medio_atual_g != null ? (
                    <>
                      {metricas.peso_medio_atual_g.toFixed(1)}{" "}
                      <span className="text-xs font-normal text-slate-400">g</span>
                    </>
                  ) : (
                    <span className="text-xs font-semibold text-amber-500">Sem biometria</span>
                  )}
                </p>
              </div>
              <div>
                <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Biomassa Est.
                </p>
                <p className="text-lg font-extrabold text-emerald-600 dark:text-emerald-400 tabular-nums">
                  {metricas.biomassa_atual_kg != null ? (
                    <>
                      {metricas.biomassa_atual_kg.toLocaleString("pt-BR")}{" "}
                      <span className="text-xs font-normal text-slate-400">kg</span>
                    </>
                  ) : (
                    <span className="text-xs font-semibold text-slate-400">—</span>
                  )}
                </p>
              </div>
              <div>
                <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Sobrevivência
                </p>
                <p
                  className={`text-lg font-extrabold tabular-nums ${
                    metricas.taxa_sobrevivencia_fuzzy_pct >= 85
                      ? "text-emerald-600 dark:text-emerald-400"
                      : metricas.taxa_sobrevivencia_fuzzy_pct >= 70
                      ? "text-amber-500"
                      : "text-red-500"
                  }`}
                >
                  {metricas.taxa_sobrevivencia_fuzzy_pct.toFixed(1)}%
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 py-4 text-xs text-slate-400">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Calculando parâmetros zootécnicos...
            </div>
          )}

          {metricas && metricas.alerta_hiperdensidade && (
            <div className="mt-3 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-50 border border-red-200 text-red-600 dark:bg-red-950/40 dark:border-red-800/40 dark:text-red-400 text-xs font-bold">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
              Hiperdensidade &gt; 50 camarões/m²
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}

// ── Main Dashboard ──────────────────────────────────
export default function DashboardPage() {
  const [viveiros, setViveiros] = useState<Viveiro[]>([]);
  const [ciclosAtivos, setCiclosAtivos] = useState<CicloProdutivo[]>([]);
  const [metricas, setMetricas] = useState<Record<string, MetricasAtuais>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [vivs, cycs] = await Promise.all([
          viveirosApi.listar(),
          ciclosApi.listar({ status_filtro: "ATIVO" }),
        ]);
        setViveiros(vivs);
        setCiclosAtivos(cycs);

        const metricasMap: Record<string, MetricasAtuais> = {};
        await Promise.all(
          cycs.map(async (c: CicloProdutivo) => {
            try {
              const m = await ciclosApi.metricas(c.id);
              metricasMap[c.viveiro_id] = m;
            } catch {
              // skip
            }
          })
        );
        setMetricas(metricasMap);
      } catch {
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const viveirosAtivos = viveiros.filter((v) => v.status_ativo);
  const viveirosComCiclo = viveirosAtivos.filter((v) =>
    ciclosAtivos.some((c) => c.viveiro_id === v.id)
  );
  const vivSemCiclo = viveirosAtivos.filter(
    (v) => !ciclosAtivos.some((c) => c.viveiro_id === v.id)
  );

  const allMetricas = Object.values(metricas);
  const totalBiomassa = allMetricas.reduce((sum, m) => sum + (m.biomassa_atual_kg || 0), 0);
  const totalReceita = allMetricas.reduce((sum, m) => sum + (m.receita_bruta_estimada_rs || 0), 0);
  const totalCusto = allMetricas.reduce((sum, m) => sum + (m.custo_operacional_total_rs || 0), 0);
  const totalLucro = totalReceita - totalCusto;
  const alertas = allMetricas.filter((m) => m.alerta_hiperdensidade).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* ── Page Header Inspirado no Layout do Gestor ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-200/80 dark:border-white/10">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Fazenda de Carcinicultura
            </span>
            <span className="h-1 w-1 rounded-full bg-slate-300" />
            <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
              Vale do Jaguaribe
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight dark:text-white">
            Painel Executivo da Fazenda
          </h1>
          <p className="text-slate-500 text-xs mt-1 dark:text-slate-400">
            Monitoramento bioeconômico em tempo real de biomassa, custos e projeção de receita.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link href="/gestor/simulacao">
            <Button variant="outline" size="sm">
              <TrendingUp className="w-4 h-4 text-sky-600" />
              Simulador ΔV
            </Button>
          </Link>
          <Link href="/gestor/viveiros">
            <Button size="sm">
              <Plus className="w-4 h-4" />
              Novo Ciclo / Viveiro
            </Button>
          </Link>
        </div>
      </div>

      {/* ── KPI Cards (Inspirados nas capturas 112821 e 112858) ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Biomassa Estimada"
          value={totalBiomassa.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}
          unit="kg"
          accentColor="emerald"
          icon={Scale}
          badge={{
            text: `${viveirosComCiclo.length} viveiros ativos`,
            variant: "success",
          }}
          subtitle="Modelagem populacional ativa"
        />

        <MetricCard
          label="Receita Bruta Estimada"
          value={`R$ ${(totalReceita / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}k`}
          accentColor="ocean"
          icon={DollarSign}
          badge={{
            text: "Cotação frigorífico",
            variant: "info",
          }}
          subtitle="Tabela de preços vigente"
        />

        <MetricCard
          label="Lucro Operacional Est."
          value={`R$ ${(totalLucro / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}k`}
          accentColor={totalLucro >= 0 ? "emerald" : "coral"}
          icon={totalLucro >= 0 ? TrendingUp : TrendingDown}
          badge={{
            text: totalLucro >= 0 ? "Margem positiva" : "Atenção a custos",
            variant: totalLucro >= 0 ? "success" : "destructive",
          }}
          subtitle={`Custos: R$ ${(totalCusto / 1000).toFixed(1)}k`}
        />

        <MetricCard
          label="Alertas Zootécnicos"
          value={alertas}
          accentColor={alertas > 0 ? "coral" : "slate"}
          icon={AlertTriangle}
          badge={{
            text: alertas > 0 ? "Revisar densidade" : "Condições ideais",
            variant: alertas > 0 ? "destructive" : "neutral",
          }}
          subtitle={alertas > 0 ? "Densidade > 50 cam/m²" : "Sem anomalias"}
        />
      </div>

      {/* ── Viveiros com Ciclo Ativo ── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900 tracking-tight dark:text-white">
              Viveiros em Produção
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Selecione um viveiro para abrir o relatório completo com biometrias e balanço de ração.
            </p>
          </div>
          <Link
            href="/gestor/viveiros"
            className="text-xs font-bold text-sky-600 hover:text-sky-700 flex items-center gap-1 dark:text-sky-400"
          >
            Ver todos ({viveiros.length}) <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {viveirosComCiclo.length === 0 ? (
          <Card className="p-10 text-center">
            <Activity className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="font-bold text-base text-slate-800 dark:text-slate-200">
              Nenhum ciclo produtivo em andamento
            </h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-4 dark:text-slate-400">
              Inicie um novo povoamento para acompanhar biometrias, ração e estimativas econômicas de despesca.
            </p>
            <Link href="/gestor/viveiros">
              <Button size="sm">Cadastrar / Iniciar Ciclo</Button>
            </Link>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {viveirosComCiclo.map((v) => (
              <ViveiroActiveCard
                key={v.id}
                viveiro={v}
                metricas={metricas[v.id] || null}
              />
            ))}
          </div>
        )}
      </div>

      {/* ── Viveiros Disponíveis / Em Preparação ── */}
      {vivSemCiclo.length > 0 && (
        <div className="pt-4 border-t border-slate-200/60 dark:border-white/5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300">
              Viveiros Disponíveis para Povoamento ({vivSemCiclo.length})
            </h3>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {vivSemCiclo.map((v) => (
              <Link key={v.id} href={`/gestor/viveiros/${v.id}`}>
                <div className="rounded-xl border border-slate-200/80 bg-white p-3.5 hover:border-slate-300 hover:shadow-sm transition-all text-center dark:border-white/10 dark:bg-[#151d2e]">
                  <Shell className="w-6 h-6 text-slate-400 mx-auto mb-1.5" />
                  <p className="font-bold text-slate-900 text-sm dark:text-white">
                    {v.identificacao}
                  </p>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    {(v.area_util_m2 / 10000).toFixed(1)} ha ({(v.area_util_m2).toLocaleString("pt-BR")} m²)
                  </p>
                  <Badge variant="secondary" className="mt-2 text-[10px]">
                    Sem ciclo
                  </Badge>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
