"use client";

import { useEffect, useState } from "react";
import {
  Moon,
  Loader2,
  Droplets,
  Thermometer,
  Wind,
  AlertTriangle,
  Shell,
  Zap,
  Eye,
  CalendarDays,
  Activity,
} from "lucide-react";
import { rondasApi } from "@/lib/api";
import type { RondaNoturna } from "@/lib/types";

const COMP_LABELS: Record<string, { label: string; color: string }> = {
  NORMAL_FUNDO: { label: "Normal (fundo)", color: "#28d280" },
  FLOR_DAGUA_BOQUEANDO: { label: "Flor d'água / Boqueando", color: "#ef4444" },
  NATACAO_AGITADA: { label: "Natação agitada", color: "#f59e0b" },
  ECDISE_MASSIVA: { label: "Ecdise massiva", color: "#a78bfa" },
  PRESENCA_BORDAS: { label: "Presença nas bordas", color: "#f59e0b" },
};

const ENERGIA_LABELS: Record<string, string> = {
  REDE_CONCESSIONARIA: "Rede elétrica",
  GERADOR_DIESEL: "Gerador diesel",
  SEM_ENERGIA_QUEDA: "Sem energia (queda)",
};

interface PainelData {
  viveiro_id: string;
  viveiro_identificacao: string;
  rondas: RondaNoturna[];
  o2_minimo: number | null;
  o2_maximo: number | null;
  alertas_criticos: number;
}

function fmtDateTime(d: string) {
  return new Date(d).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function O2Badge({ valor, classificacao }: { valor: number; classificacao: string }) {
  const config = classificacao === "EMERGENCIA"
    ? { bg: "bg-red-500/15", text: "text-red-400", border: "border-red-500/30", label: "Emergência" }
    : classificacao === "ALERTA"
    ? { bg: "bg-amber-500/15", text: "text-amber-400", border: "border-amber-500/30", label: "Alerta" }
    : { bg: "bg-green-500/15", text: "text-green-400", border: "border-green-500/30", label: "Normal" };

  return (
    <span className={`${config.bg} ${config.text} ${config.border} border text-xs px-2 py-0.5 rounded-full font-medium`}>
      {valor.toFixed(1)} mg/L — {config.label}
    </span>
  );
}

export default function PainelNoturnoPage() {
  const [painel, setPainel] = useState<PainelData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await rondasApi.painelNoturno();
        setPainel(data);
      } catch { } finally { setLoading(false); }
    }
    load();
  }, []);

  if (loading) return <div className="flex items-center justify-center py-32"><Loader2 className="w-8 h-8 text-ocean-400 animate-spin" /></div>;

  const totalAlertas = painel.reduce((sum, p) => sum + p.alertas_criticos, 0);

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center gap-3 mb-8">
        <Moon className="w-8 h-8 text-ocean-400" />
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)]">Painel Noturno</h1>
          <p className="text-[var(--text-secondary)] text-sm mt-0.5">
            Rondas das últimas 12 horas — monitoramento de O₂ e aeradores
          </p>
        </div>
      </div>

      {/* Alert summary */}
      {totalAlertas > 0 && (
        <div className="glass-card p-4 mb-6 border-l-4 border-l-red-500 flex items-center gap-3 pulse-alert">
          <AlertTriangle className="w-6 h-6 text-red-400 shrink-0" />
          <div>
            <p className="font-bold text-red-400">
              {totalAlertas} alerta{totalAlertas > 1 ? "s" : ""} crítico{totalAlertas > 1 ? "s" : ""} de O₂
            </p>
            <p className="text-sm text-[var(--text-muted)]">
              Oxigênio dissolvido abaixo de 2.5 mg/L detectado
            </p>
          </div>
        </div>
      )}

      {painel.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <Moon className="w-12 h-12 text-[var(--text-muted)] mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">Sem rondas recentes</h3>
          <p className="text-sm text-[var(--text-muted)]">Nenhuma ronda registrada nas últimas 12 horas</p>
        </div>
      ) : (
        <div className="space-y-6">
          {painel.map((p) => (
            <div key={p.viveiro_id} className="glass-card overflow-hidden">
              {/* Viveiro header */}
              <div className={`p-4 flex items-center justify-between border-b border-[var(--border-subtle)] ${p.alertas_criticos > 0 ? "bg-red-500/5" : ""}`}>
                <div className="flex items-center gap-3">
                  <Shell className="w-5 h-5 text-ocean-400" />
                  <h2 className="font-bold text-[var(--text-primary)]">{p.viveiro_identificacao}</h2>
                  <span className="text-xs badge-info px-2 py-0.5 rounded-full font-medium">
                    {p.rondas.length} ronda{p.rondas.length > 1 ? "s" : ""}
                  </span>
                  {p.alertas_criticos > 0 && (
                    <span className="text-xs badge-danger px-2 py-0.5 rounded-full font-bold">
                      {p.alertas_criticos} emergência{p.alertas_criticos > 1 ? "s" : ""}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-4 text-sm text-[var(--text-muted)]">
                  {p.o2_minimo != null && (
                    <span>O₂: <span className="font-semibold text-[var(--text-primary)]">{p.o2_minimo.toFixed(1)}</span> – <span className="font-semibold text-[var(--text-primary)]">{p.o2_maximo?.toFixed(1)}</span> mg/L</span>
                  )}
                </div>
              </div>

              {/* Rondas */}
              <div className="divide-y divide-[var(--border-subtle)]">
                {p.rondas.map((r) => {
                  const comp = COMP_LABELS[r.comportamento] || { label: r.comportamento, color: "#94a3b8" };
                  return (
                    <div key={r.id} className="p-4 flex flex-wrap items-center gap-x-5 gap-y-2">
                      <div className="flex items-center gap-2 min-w-[130px]">
                        <CalendarDays className="w-4 h-4 text-[var(--text-muted)]" />
                        <span className="text-sm font-medium text-[var(--text-primary)] tabular-nums">{fmtDateTime(r.data_hora_ronda)}</span>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <Droplets className="w-4 h-4 text-blue-400" />
                        <O2Badge valor={r.oxigenio_dissolvido_mg_l} classificacao={r.classificacao_oxigenio} />
                      </div>

                      <div className="flex items-center gap-1.5">
                        <Thermometer className="w-4 h-4 text-orange-400" />
                        <span className="text-sm text-[var(--text-primary)] tabular-nums">{r.temperatura_agua_c.toFixed(1)}°C</span>
                      </div>

                      <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={{ background: `${comp.color}20`, color: comp.color, border: `1px solid ${comp.color}40` }}>
                        {comp.label}
                      </span>

                      {r.aeradores_ligados != null && r.aeradores_instalados != null && (
                        <div className="flex items-center gap-1.5">
                          <Wind className="w-4 h-4 text-[var(--text-muted)]" />
                          <span className="text-xs text-[var(--text-secondary)]">
                            {r.aeradores_ligados}/{r.aeradores_instalados} aeradores
                            {r.taxa_aeracao_pct != null && ` (${r.taxa_aeracao_pct}%)`}
                          </span>
                        </div>
                      )}

                      {r.fonte_energia && (
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${r.fonte_energia === "SEM_ENERGIA_QUEDA" ? "badge-danger" : r.fonte_energia === "GERADOR_DIESEL" ? "badge-warning" : "badge-success"}`}>
                          {ENERGIA_LABELS[r.fonte_energia] || r.fonte_energia}
                        </span>
                      )}

                      {r.falha_mecanica_detectada && (
                        <span className="text-xs badge-danger px-2 py-0.5 rounded-full font-bold">⚠ Falha mecânica</span>
                      )}

                      <span className="text-xs text-[var(--text-muted)]">
                        <Eye className="w-3.5 h-3.5 inline mr-1" />{r.vigia_nome}
                      </span>

                      {r.observacoes && <span className="text-xs text-[var(--text-muted)] italic w-full">💬 {r.observacoes}</span>}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
