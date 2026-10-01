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
  Bug,
  Droplets,
  Moon,
  BarChart3,
  Utensils,
  Target,
  Zap,
  CalendarDays,
  ChevronRight,
  Waves,
} from "lucide-react";
import { viveirosApi, ciclosApi, rondasApi } from "@/lib/api";
import type { Viveiro, CicloProdutivo, MetricasAtuais } from "@/lib/types";

// ── Summary Card ────────────────────────────────────
function SummaryCard({
  label,
  value,
  icon: Icon,
  color,
  subtitle,
}: {
  label: string;
  value: string | number;
  icon: any;
  color: string;
  subtitle?: string;
}) {
  return (
    <div className="glass-card p-5 flex items-start gap-4">
      <div
        className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
        style={{ background: `${color}15`, border: `1px solid ${color}30` }}
      >
        <Icon className="w-6 h-6" style={{ color }} />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-[var(--text-muted)] font-medium uppercase tracking-wider">
          {label}
        </p>
        <p className="text-2xl font-bold mt-0.5" style={{ color }}>
          {value}
        </p>
        {subtitle && (
          <p className="text-xs text-[var(--text-muted)] mt-0.5">{subtitle}</p>
        )}
      </div>
    </div>
  );
}

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
      <div className="glass-card glass-card-hover p-5 transition-all duration-300 cursor-pointer h-full">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-ocean-500/20 to-pond-500/20 border border-ocean-500/30 flex items-center justify-center">
              <Shell className="w-5 h-5 text-ocean-400" />
            </div>
            <div>
              <h3 className="font-bold text-[var(--text-primary)]">
                {viveiro.identificacao}
              </h3>
              <span className="text-xs text-pond-400 font-medium">Ciclo ativo</span>
            </div>
          </div>
          <ChevronRight className="w-4 h-4 text-[var(--text-muted)]" />
        </div>

        {metricas ? (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-xs text-[var(--text-muted)]">Dias cultivo</p>
              <p className="text-lg font-bold text-ocean-400 tabular-nums">
                {metricas.dias_cultivo}
              </p>
            </div>
            <div>
              <p className="text-xs text-[var(--text-muted)]">Peso médio</p>
              <p className="text-lg font-bold text-shrimp-400 tabular-nums">
                {metricas.peso_medio_atual_g.toFixed(1)}
                <span className="text-xs font-normal text-[var(--text-muted)] ml-0.5">g</span>
              </p>
            </div>
            <div>
              <p className="text-xs text-[var(--text-muted)]">Biomassa</p>
              <p className="text-lg font-bold text-pond-400 tabular-nums">
                {metricas.biomassa_atual_kg.toLocaleString("pt-BR")}
                <span className="text-xs font-normal text-[var(--text-muted)] ml-0.5">kg</span>
              </p>
            </div>
            <div>
              <p className="text-xs text-[var(--text-muted)]">Sobrevivência</p>
              <p
                className={`text-lg font-bold tabular-nums ${
                  metricas.taxa_sobrevivencia_fuzzy_pct >= 85
                    ? "text-pond-400"
                    : metricas.taxa_sobrevivencia_fuzzy_pct >= 70
                    ? "text-amber-400"
                    : "text-red-400"
                }`}
              >
                {metricas.taxa_sobrevivencia_fuzzy_pct.toFixed(1)}%
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
            <Loader2 className="w-4 h-4 animate-spin" />
            Carregando métricas...
          </div>
        )}

        {metricas && metricas.alerta_hiperdensidade && (
          <div className="mt-3 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-500/10 border border-red-500/30">
            <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
            <span className="text-xs text-red-400 font-medium">Hiperdensidade detectada</span>
          </div>
        )}
      </div>
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

        // Fetch metrics for all active cycles in parallel
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
        // handle
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

  // Aggregate metrics
  const allMetricas = Object.values(metricas);
  const totalBiomassa = allMetricas.reduce((sum, m) => sum + m.biomassa_atual_kg, 0);
  const totalReceita = allMetricas.reduce((sum, m) => sum + m.receita_bruta_estimada_rs, 0);
  const totalCusto = allMetricas.reduce((sum, m) => sum + m.custo_operacional_total_rs, 0);
  const totalLucro = totalReceita - totalCusto;
  const alertas = allMetricas.filter((m) => m.alerta_hiperdensidade).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-8 h-8 text-ocean-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)]">
          Dashboard
        </h1>
        <p className="text-[var(--text-secondary)] text-sm mt-1">
          Visão geral do sistema — {new Date().toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
        <SummaryCard
          label="Viveiros Ativos"
          value={viveirosAtivos.length}
          icon={Shell}
          color="#1aa0ff"
          subtitle={`${viveirosComCiclo.length} com ciclo ativo`}
        />
        <SummaryCard
          label="Biomassa Total"
          value={`${totalBiomassa.toLocaleString("pt-BR", { maximumFractionDigits: 0 })} kg`}
          icon={Scale}
          color="#28d280"
        />
        <SummaryCard
          label="Lucro Estimado"
          value={`R$ ${totalLucro.toLocaleString("pt-BR", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`}
          icon={totalLucro >= 0 ? TrendingUp : TrendingDown}
          color={totalLucro >= 0 ? "#28d280" : "#ef4444"}
        />
        <SummaryCard
          label="Alertas"
          value={alertas}
          icon={AlertTriangle}
          color={alertas > 0 ? "#ef4444" : "#28d280"}
          subtitle={alertas > 0 ? "Hiperdensidade detectada" : "Sem alertas"}
        />
      </div>

      {/* Viveiros com ciclo ativo */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-[var(--text-primary)]">
            Ciclos Ativos
            <span className="text-sm font-normal text-[var(--text-muted)] ml-2">
              ({viveirosComCiclo.length})
            </span>
          </h2>
          <Link
            href="/gestor/viveiros"
            className="text-sm text-ocean-400 hover:underline flex items-center gap-1"
          >
            Ver todos <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {viveirosComCiclo.length === 0 ? (
          <div className="glass-card p-8 text-center">
            <Activity className="w-10 h-10 text-[var(--text-muted)] mx-auto mb-3" />
            <p className="text-[var(--text-muted)]">Nenhum ciclo ativo no momento</p>
            <Link
              href="/gestor/viveiros"
              className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-xl bg-ocean-500/15 text-ocean-400 text-sm font-medium hover:bg-ocean-500/25 transition-all"
            >
              Gerenciar Viveiros
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
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

      {/* Viveiros sem ciclo */}
      {vivSemCiclo.length > 0 && (
        <div>
          <h2 className="text-lg font-bold text-[var(--text-primary)] mb-4">
            Viveiros Disponíveis
            <span className="text-sm font-normal text-[var(--text-muted)] ml-2">
              ({vivSemCiclo.length} sem ciclo)
            </span>
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {vivSemCiclo.map((v) => (
              <Link key={v.id} href={`/gestor/viveiros/${v.id}`}>
                <div className="glass-card glass-card-hover p-4 transition-all duration-300 cursor-pointer text-center">
                  <Shell className="w-8 h-8 text-[var(--text-muted)] mx-auto mb-2" />
                  <p className="font-semibold text-[var(--text-primary)] text-sm">
                    {v.identificacao}
                  </p>
                  <p className="text-xs text-[var(--text-muted)] mt-1">
                    {v.area_util_m2.toLocaleString("pt-BR")} m²
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
