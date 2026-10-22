"use client";

import { useEffect, useState } from "react";
import {
  Utensils,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
} from "lucide-react";
import { ciclosApi, viveirosApi, manejosApi } from "@/lib/api";
import { mensagemErro } from "@/lib/utils";
import type { CicloProdutivo, Viveiro, RecomendacaoAlimentar, ManejoAlimentar } from "@/lib/types";
import { StepperCounter } from "@/components/ui/stepper-counter";
import { TrayRemnantSelector, type NivelSobra } from "@/components/ui/tray-remnant-selector";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

function fmtDate(d: string) {
  return new Date(d).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

export default function ManejoPage() {
  const [viveiros, setViveiros] = useState<Viveiro[]>([]);
  const [ciclos, setCiclos] = useState<CicloProdutivo[]>([]);
  const [selectedCiclo, setSelectedCiclo] = useState("");
  const [recomendacao, setRecomendacao] = useState<RecomendacaoAlimentar | null>(null);
  const [manejos, setManejos] = useState<ManejoAlimentar[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const [racaoKg, setRacaoKg] = useState<number>(45);
  const [sobraNivel, setSobraNivel] = useState<NivelSobra>("SEM_SOBRA");
  const [dataRegistro, setDataRegistro] = useState(new Date().toISOString().split("T")[0]);

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
      } catch { } finally { setLoading(false); }
    }
    load();
  }, []);

  // Load recomendacao + last manejos when ciclo changes
  useEffect(() => {
    if (!selectedCiclo) return;
    async function loadCicloData() {
      try {
        const [rec, mans] = await Promise.all([
          manejosApi.recomendacao(selectedCiclo).catch(() => null),
          manejosApi.listar(selectedCiclo).catch(() => []),
        ]);
        setRecomendacao(rec);
        setManejos(mans);
        if (rec && rec.racao_diaria_sugerida_kg > 0) {
          setRacaoKg(Math.round(rec.racao_diaria_sugerida_kg));
        }
      } catch { }
    }
    loadCicloData();
  }, [selectedCiclo]);

  const cicloAtual = ciclos.find((c) => c.id === selectedCiclo);
  const viveiroAtual = viveiros.find((v) => v.id === cicloAtual?.viveiro_id);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCiclo) {
      setError("Selecione um viveiro com ciclo ativo.");
      return;
    }
    setError("");
    setSuccess(false);
    setSubmitting(true);
    try {
      await manejosApi.criar(selectedCiclo, {
        data_registro: dataRegistro,
        quantidade_racao_kg: racaoKg,
        sobra_bandeja_nivel: sobraNivel,
      });
      setSuccess(true);
      // Refresh
      const [rec, mans] = await Promise.all([
        manejosApi.recomendacao(selectedCiclo).catch(() => null),
        manejosApi.listar(selectedCiclo).catch(() => []),
      ]);
      setRecomendacao(rec);
      setManejos(mans);
    } catch (err) {
      setError(mensagemErro(err, "Falha ao registrar manejo."));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-sky-500" />
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto space-y-5 pb-12">
      {/* ── Top Header Card (Inspirado nas imagens do Operador) ── */}
      <div className="rounded-3xl bg-gradient-to-br from-[#0c1527] to-[#152238] p-6 text-white shadow-xl border border-white/10">
        <div className="flex items-center justify-between mb-3">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-bold text-emerald-300 border border-emerald-500/30">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            Módulo de Campo
          </div>
          <span className="text-xs text-slate-400 font-medium">
            {new Date().toLocaleDateString("pt-BR", { weekday: "short", day: "2-digit", month: "short" })}
          </span>
        </div>

        <h1 className="text-2xl font-black tracking-tight flex items-center gap-2.5">
          <Utensils className="h-6 w-6 text-sky-400" />
          Registro de Manejo
        </h1>
        <p className="text-xs text-slate-300 mt-1">
          Controle de arraçoamento diário e calibração das bandejas de alimentação.
        </p>
      </div>

      {/* ── Seletor de Viveiro Ativo ── */}
      <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151d2e]">
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Viveiro Selecionado
          </label>
          {cicloAtual && (
            <Badge variant="success">Lote #{cicloAtual.id.substring(0, 6)}</Badge>
          )}
        </div>

        <select
          value={selectedCiclo}
          onChange={(e) => setSelectedCiclo(e.target.value)}
          className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-800 focus:border-sky-500 focus:outline-none dark:border-white/10 dark:bg-white/5 dark:text-white"
        >
          {ciclos.map((c) => {
            const v = viveiros.find((viv) => viv.id === c.viveiro_id);
            return (
              <option key={c.id} value={c.id} className="text-slate-900 bg-white dark:bg-slate-900 dark:text-white">
                {v?.identificacao || "Viveiro"} — Lote #{c.id.substring(0, 6)}
              </option>
            );
          })}
        </select>

        {viveiroAtual && cicloAtual && (
          <div className="mt-3 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 border-t border-slate-100 dark:border-white/5 pt-2.5">
            <span>Área: <strong className="text-slate-700 dark:text-slate-200">{(viveiroAtual.area_util_m2 / 10000).toFixed(1)} ha</strong></span>
            <span>População: <strong className="text-slate-700 dark:text-slate-200">{(cicloAtual.quantidade_pos_larvas / 1000).toFixed(0)}k PL</strong></span>
            <span>Status: <strong className="text-emerald-600 dark:text-emerald-400 font-bold">Ativo</strong></span>
          </div>
        )}
      </div>

      {/* ── Recomendação Clifford (1992) ── */}
      {recomendacao && (
        <div className="rounded-2xl border border-sky-200 bg-sky-50/70 p-4 text-sky-950 dark:border-sky-800/40 dark:bg-sky-950/20 dark:text-sky-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-sky-600 dark:text-sky-400" />
              <span className="text-xs font-bold uppercase tracking-wider text-sky-800 dark:text-sky-300">
                Prescrição Clifford (1992)
              </span>
            </div>
            <button
              type="button"
              onClick={() => setRacaoKg(Math.round(recomendacao.racao_diaria_sugerida_kg))}
              className="text-[11px] font-bold text-sky-700 underline hover:text-sky-900 dark:text-sky-300"
            >
              Aplicar sugerido
            </button>
          </div>

          <div className="mt-2.5 flex items-baseline justify-between">
            <div>
              <span className="text-2xl font-black text-sky-900 dark:text-white tabular-nums">
                {recomendacao.racao_diaria_sugerida_kg.toFixed(1)}
              </span>
              <span className="text-sm font-semibold text-sky-700 dark:text-sky-300 ml-1">kg/dia</span>
            </div>
            <span className="text-xs font-medium text-sky-700 dark:text-sky-400">
              Taxa alimentar: <strong>{recomendacao.taxa_clifford_pct.toFixed(2)}%</strong>
            </span>
          </div>
        </div>
      )}

      {/* ── Formulário Principal de Arraçoamento ── */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Stepper para Quantidade de Ração */}
        <StepperCounter
          label="Ração a Distribuir no Trato"
          unit="kg"
          value={racaoKg}
          step={5}
          min={1}
          max={500}
          onChange={(val) => setRacaoKg(val)}
          icon={Utensils}
          badge="Por Trato"
          helperText="Ajuste fino de acordo com o clima e comportamento"
          quickAddOptions={[20, 35, 45, 60, 80]}
        />

        {/* Seletor de Sobras em Bandeja */}
        <TrayRemnantSelector
          value={sobraNivel}
          onChange={(val) => setSobraNivel(val)}
        />

        {/* Feedback de sucesso ou erro */}
        {success && (
          <div className="flex items-center gap-2.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-xs font-bold text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="h-5 w-5 shrink-0" />
            Manejo alimentar registrado com sucesso! Motor Fuzzy atualizado.
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2.5 rounded-xl border border-red-500/30 bg-red-500/10 p-3.5 text-xs font-bold text-red-600 dark:text-red-400">
            <AlertTriangle className="h-5 w-5 shrink-0" />
            {error}
          </div>
        )}

        {/* Botão de Envio de Alta Visibilidade */}
        <Button
          type="submit"
          disabled={submitting}
          size="lg"
          className="w-full text-base font-bold shadow-lg shadow-sky-500/25 h-13"
        >
          {submitting ? (
            <div className="flex items-center gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              Gravando Manejo...
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5" />
              Confirmar Registro de Manejo
            </div>
          )}
        </Button>
      </form>

      {/* ── Histórico Recente de Tratos ── */}
      <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151d2e]">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
          Últimos Lançamentos de Manejo
        </h3>

        {manejos.length === 0 ? (
          <p className="text-xs text-slate-400 italic">Nenhum manejo registrado para este ciclo ainda.</p>
        ) : (
          <div className="space-y-2.5">
            {manejos.slice(0, 4).map((m) => (
              <div
                key={m.id}
                className="flex items-center justify-between rounded-xl bg-slate-50 p-3 text-xs dark:bg-white/5"
              >
                <div className="flex items-center gap-3">
                  <div className="h-2 w-2 rounded-full bg-sky-500" />
                  <div>
                    <span className="font-bold text-slate-800 dark:text-slate-200">
                      {m.quantidade_racao_kg} kg
                    </span>
                    <p className="text-[11px] text-slate-400">{fmtDate(m.data_registro)}</p>
                  </div>
                </div>

                <Badge
                  variant={
                    m.sobra_bandeja_nivel === "SEM_SOBRA"
                      ? "success"
                      : m.sobra_bandeja_nivel === "SOBRA_LEVE"
                      ? "warning"
                      : "destructive"
                  }
                >
                  {m.sobra_bandeja_nivel === "SEM_SOBRA"
                    ? "Sem Sobra"
                    : m.sobra_bandeja_nivel === "SOBRA_LEVE"
                    ? "Pouca Sobra"
                    : "Muita Sobra"}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
