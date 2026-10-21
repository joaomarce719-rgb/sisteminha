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
  CheckCircle2,
} from "lucide-react";
import { alertasApi, rondasApi } from "@/lib/api";
import type { Alerta, RondaNoturna } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/toast";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { Badge } from "@/components/ui/badge";

const COMP_LABELS: Record<string, { label: string; bg: string; text: string; border: string }> = {
  NORMAL_FUNDO: { label: "Normal (fundo)", bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  FLOR_DAGUA_BOQUEANDO: { label: "Boqueando (superfície)", bg: "bg-red-50", text: "text-red-700", border: "border-red-200" },
  NATACAO_AGITADA: { label: "Natação agitada", bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200" },
  ECDISE_MASSIVA: { label: "Ecdise massiva", bg: "bg-purple-50", text: "text-purple-700", border: "border-purple-200" },
  PRESENCA_BORDAS: { label: "Presença nas bordas", bg: "bg-orange-50", text: "text-orange-700", border: "border-orange-200" },
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
  return new Date(d).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function O2Badge({ valor, classificacao }: { valor: number; classificacao: string }) {
  if (classificacao === "EMERGENCIA") {
    return (
      <span className="inline-flex items-center gap-1 bg-red-100 text-red-800 border border-red-300 text-xs px-2.5 py-0.5 rounded-full font-bold animate-pulse">
        <span className="w-1.5 h-1.5 rounded-full bg-red-600" />
        {valor.toFixed(1)} mg/L (Crítico)
      </span>
    );
  }
  if (classificacao === "ALERTA") {
    return (
      <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-800 border border-amber-300 text-xs px-2.5 py-0.5 rounded-full font-semibold">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-600" />
        {valor.toFixed(1)} mg/L (Atenção)
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 bg-emerald-100 text-emerald-800 border border-emerald-300 text-xs px-2.5 py-0.5 rounded-full font-semibold">
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
      {valor.toFixed(1)} mg/L (Ideal)
    </span>
  );
}

export default function PainelNoturnoPage() {
  const [painel, setPainel] = useState<PainelData[]>([]);
  const [alertas, setAlertas] = useState<Alerta[]>([]);
  const [resolvendo, setResolvendo] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const resolverAlerta = async (alerta: Alerta) => {
    setResolvendo(alerta.id);
    try {
      await alertasApi.resolver(alerta.id);
      setAlertas((prev) => prev.filter((a) => a.id !== alerta.id));
      toast.success("Alerta resolvido", alerta.titulo);
    } catch (err: any) {
      toast.error("Erro ao resolver alerta", err.message || "Tente novamente");
    } finally {
      setResolvendo(null);
    }
  };

  useEffect(() => {
    async function load() {
      try {
        const [data, abertos] = await Promise.all([
          rondasApi.painelNoturno(),
          alertasApi.listar({ status_alerta: "ABERTO" }),
        ]);
        setPainel(data);
        setAlertas(abertos);
      } catch {
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-32 bg-white rounded-2xl border border-slate-200">
        <Loader2 className="w-8 h-8 text-ocean-600 animate-spin mb-2" />
        <p className="text-xs text-slate-400 font-medium">Carregando telemetria noturna...</p>
      </div>
    );
  }

  const totalAlertas = painel.reduce((sum, p) => sum + p.alertas_criticos, 0);
  const totalRondas = painel.reduce((sum, p) => sum + p.rondas.length, 0);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Cabeçalho */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-ocean-600 mb-1">
            <Moon className="w-4 h-4" />
            Vigia Noturno & Telemetria
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Painel Noturno de Monitoramento
          </h1>
          <p className="text-slate-500 text-sm mt-0.5">
            Registro de rondas das últimas 12 horas — supervisão de oxigênio e aeração
          </p>
        </div>

        <Badge variant={totalAlertas > 0 ? "destructive" : "success"} className="text-xs px-3 py-1">
          {totalAlertas > 0 ? `${totalAlertas} Ocorrências Críticas` : "Parâmetros Estáveis"}
        </Badge>
      </div>

      {/* Cards de Métricas Rápidas */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <MetricCard
          title="Rondas Registradas"
          value={totalRondas}
          subtitle="Últimas 12 horas"
          icon={Activity}
          accent="ocean"
        />
        <MetricCard
          title="Viveiros Monitorados"
          value={painel.length}
          subtitle="Lotes ativos vistoriados"
          icon={Shell}
          accent="emerald"
        />
        <MetricCard
          title="Alertas Críticos de O₂"
          value={totalAlertas}
          subtitle="O₂ abaixo de 2.5 mg/L"
          icon={AlertTriangle}
          accent={totalAlertas > 0 ? "red" : "emerald"}
        />
      </div>

      {/* Alerta Destacado se houver emergências */}
      {totalAlertas > 0 && (
        <div className="rounded-2xl bg-red-50 border border-red-200 p-4 flex items-center gap-3 text-red-900 shadow-sm animate-pulse">
          <AlertTriangle className="w-6 h-6 text-red-600 shrink-0" />
          <div>
            <div className="font-bold text-sm">
              Atenção: {totalAlertas} registro(s) de hipóxia detectado(s) durante a ronda!
            </div>
            <div className="text-xs text-red-700 mt-0.5">
              Oxigênio dissolvido em nível de emergência (&lt; 2.5 mg/L). Verifique os aeradores imediatamente.
            </div>
          </div>
        </div>
      )}

      {/* Alertas em aberto (RF-021) */}
      {alertas.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-600" />
              Alertas em aberto ({alertas.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {alertas.map((a) => (
              <div
                key={a.id}
                className={`flex flex-col sm:flex-row sm:items-center gap-3 p-3 rounded-xl border ${
                  a.nivel === "CRITICO" ? "bg-red-50 border-red-200" : "bg-amber-50 border-amber-200"
                }`}
              >
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-bold text-slate-900">
                    {a.titulo}
                    {a.viveiro_identificacao && (
                      <span className="ml-2 text-xs font-semibold text-slate-500">{a.viveiro_identificacao}</span>
                    )}
                  </div>
                  <div className="text-xs text-slate-600 mt-0.5">{a.mensagem}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">{fmtDateTime(a.created_at)}</div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={resolvendo === a.id}
                  onClick={() => resolverAlerta(a)}
                >
                  {resolvendo === a.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                  Marcar como resolvido
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Lista de Viveiros e Rondas */}
      {painel.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-sm">
          <Moon className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-lg font-bold text-slate-900 mb-1">Nenhuma ronda recente</h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto">
            Não foram registradas rondas de vigia nas últimas 12 horas.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {painel.map((p) => (
            <div
              key={p.viveiro_id}
              className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-sm"
            >
              {/* Header do Viveiro */}
              <div
                className={`p-4 flex items-center justify-between border-b border-slate-100 ${
                  p.alertas_criticos > 0 ? "bg-red-50/40" : "bg-slate-50/50"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-ocean-50 text-ocean-600 flex items-center justify-center font-bold">
                    <Shell className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="font-extrabold text-slate-900 text-base">{p.viveiro_identificacao}</h2>
                    <span className="text-xs text-slate-500">
                      {p.rondas.length} amostragem(ns) realizada(s)
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {p.o2_minimo != null && (
                    <div className="text-xs text-slate-600 hidden sm:block">
                      Faixa O₂: <strong className="text-slate-900">{p.o2_minimo.toFixed(1)}</strong> a{" "}
                      <strong className="text-slate-900">{p.o2_maximo?.toFixed(1)} mg/L</strong>
                    </div>
                  )}

                  {p.alertas_criticos > 0 ? (
                    <Badge variant="destructive">
                      {p.alertas_criticos} Crítico{p.alertas_criticos > 1 ? "s" : ""}
                    </Badge>
                  ) : (
                    <Badge variant="success">Estável</Badge>
                  )}
                </div>
              </div>

              {/* Tabela / Lista de Rondas */}
              <div className="divide-y divide-slate-100">
                {p.rondas.map((r) => {
                  const comp = COMP_LABELS[r.comportamento] || {
                    label: r.comportamento,
                    bg: "bg-slate-50",
                    text: "text-slate-700",
                    border: "border-slate-200",
                  };

                  return (
                    <div
                      key={r.id}
                      className="p-4 flex flex-wrap items-center justify-between gap-4 hover:bg-slate-50/50 transition-colors"
                    >
                      <div className="flex items-center gap-6 flex-wrap">
                        <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 min-w-[120px]">
                          <CalendarDays className="w-4 h-4 text-slate-400" />
                          {fmtDateTime(r.data_hora_ronda)}
                        </div>

                        <div className="flex items-center gap-2">
                          <Droplets className="w-4 h-4 text-blue-500" />
                          <O2Badge valor={r.oxigenio_dissolvido_mg_l} classificacao={r.classificacao_oxigenio} />
                        </div>

                        <div className="flex items-center gap-1.5 text-xs text-slate-700 font-medium">
                          <Thermometer className="w-4 h-4 text-orange-500" />
                          {r.temperatura_agua_c.toFixed(1)}°C
                        </div>

                        <span
                          className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${comp.bg} ${comp.text} ${comp.border}`}
                        >
                          {comp.label}
                        </span>

                        {r.aeradores_ligados != null && r.aeradores_instalados != null && (
                          <div className="flex items-center gap-1.5 text-xs text-slate-600">
                            <Wind className="w-4 h-4 text-slate-400" />
                            <span>
                              {r.aeradores_ligados}/{r.aeradores_instalados} aeradores (
                              {r.taxa_aeracao_pct}%)
                            </span>
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-3 text-xs text-slate-400">
                        {r.falha_mecanica_detectada && (
                          <span className="text-xs bg-red-100 text-red-700 border border-red-200 px-2 py-0.5 rounded-md font-bold">
                            Falha mecânica
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <Eye className="w-3.5 h-3.5" />
                          {r.vigia_nome}
                        </span>
                      </div>

                      {r.observacoes && (
                        <div className="w-full text-xs text-slate-500 italic bg-slate-50 p-2 rounded-lg border border-slate-100">
                          Obs: {r.observacoes}
                        </div>
                      )}
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
