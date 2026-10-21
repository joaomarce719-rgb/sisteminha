"use client";

import { useEffect, useState } from "react";
import {
  Scale,
  Loader2,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { ciclosApi, viveirosApi, biometriasApi } from "@/lib/api";
import { mensagemErro } from "@/lib/utils";
import type { CicloProdutivo, Viveiro, Biometria } from "@/lib/types";
import { StepperCounter } from "@/components/ui/stepper-counter";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

function fmtDate(d: string) {
  return new Date(d).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

export default function BiometriaPage() {
  const [viveiros, setViveiros] = useState<Viveiro[]>([]);
  const [ciclos, setCiclos] = useState<CicloProdutivo[]>([]);
  const [selectedCiclo, setSelectedCiclo] = useState("");
  const [biometrias, setBiometrias] = useState<Biometria[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const [pesoMedioG, setPesoMedioG] = useState<number>(12.4);
  const [quantidadeAmostrada, setQuantidadeAmostrada] = useState<number>(50);
  const [uniformidadeNivel, setUniformidadeNivel] = useState<"alta" | "media" | "baixa">("alta");
  const [dataMedicao, setDataMedicao] = useState(new Date().toISOString().split("T")[0]);
  const [observacoes, setObservacoes] = useState("");

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
      } catch {} finally { setLoading(false); }
    }
    load();
  }, []);

  useEffect(() => {
    if (!selectedCiclo) return;
    async function loadBio() {
      try {
        const bios = await biometriasApi.listar(selectedCiclo);
        setBiometrias(bios);
        if (bios.length > 0 && bios[0].peso_medio_g) {
          setPesoMedioG(bios[0].peso_medio_g);
        }
      } catch {}
    }
    loadBio();
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

    const uniformidadePct = uniformidadeNivel === "alta" ? 90 : uniformidadeNivel === "media" ? 75 : 55;

    try {
      await biometriasApi.criar(selectedCiclo, {
        data_medicao: dataMedicao,
        quantidade_amostrada: quantidadeAmostrada,
        peso_medio_g: pesoMedioG,
        uniformidade_percentual: uniformidadePct,
        observacoes: observacoes || null,
      });
      setSuccess(true);
      const bios = await biometriasApi.listar(selectedCiclo);
      setBiometrias(bios);
      setObservacoes("");
      setTimeout(() => setSuccess(false), 4000);
    } catch (err) {
      setError(mensagemErro(err, "Erro ao registrar biometria."));
    } finally {
      setSubmitting(false);
    }
  };

  const addTagObs = (tag: string) => {
    setObservacoes((prev) => (prev ? `${prev}, ${tag}` : tag));
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
      {/* ── Top Header Card (Inspirado no Operador Mobile) ── */}
      <div className="rounded-3xl bg-gradient-to-br from-[#0c1527] to-[#152238] p-6 text-white shadow-xl border border-white/10">
        <div className="flex items-center justify-between mb-3">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-sky-500/20 px-3 py-1 text-xs font-bold text-sky-300 border border-sky-500/30">
            <span className="h-2 w-2 rounded-full bg-sky-400 animate-pulse" />
            Zootecnia de Campo
          </div>
          <span className="text-xs text-slate-400 font-medium">
            Amostragem Semanal
          </span>
        </div>

        <h1 className="text-2xl font-black tracking-tight flex items-center gap-2.5">
          <Scale className="h-6 w-6 text-sky-400" />
          Biometria Amostral
        </h1>
        <p className="text-xs text-slate-300 mt-1">
          Aferição de peso médio, ganho de peso e uniformidade do lote.
        </p>
      </div>

      {/* ── Seletor de Viveiro ── */}
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
      </div>

      {/* ── Formulário Principal de Biometria ── */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Stepper para Peso Médio Amostrado */}
        <StepperCounter
          label="Peso Médio Amostrado"
          unit="g"
          value={pesoMedioG}
          step={0.5}
          min={0.1}
          max={50.0}
          onChange={(val) => setPesoMedioG(val)}
          icon={Scale}
          badge="Gramatura"
          helperText="Ganho estimado de crescimento ativo"
          quickAddOptions={[8.5, 10.0, 12.0, 14.5, 18.0]}
        />

        {/* Stepper para Quantidade Amostrada (RF-007, RN-004 - Inspiração 113527.png) */}
        <StepperCounter
          label="Qtd. Amostrada"
          unit="unid"
          value={quantidadeAmostrada}
          step={10}
          min={1}
          max={500}
          onChange={(val) => setQuantidadeAmostrada(Math.max(1, Math.round(val)))}
          badge="Amostragem"
          helperText="Camarões pesados para aferição da média"
          quickAddOptions={[30, 50, 80, 100]}
        />

        {/* Uniformidade do Lote (Pills Selecionáveis) */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151d2e]">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-bold text-slate-800 dark:text-slate-100">
              Uniformidade do Lote
            </span>
            <span className="text-xs text-slate-400">Classificação Visual</span>
          </div>

          <div className="grid grid-cols-3 gap-2.5">
            <button
              type="button"
              onClick={() => setUniformidadeNivel("alta")}
              className={`rounded-xl border-2 p-3 text-center transition-all ${
                uniformidadeNivel === "alta"
                  ? "border-emerald-500 bg-emerald-50 text-emerald-900 font-bold dark:bg-emerald-950/40 dark:text-emerald-300"
                  : "border-slate-200 bg-slate-50/50 text-slate-600 hover:border-slate-300 dark:border-white/10 dark:bg-white/5 dark:text-slate-400"
              }`}
            >
              <div className="text-sm font-bold">Uniforme</div>
              <div className="text-[10px] opacity-80 mt-0.5">&gt; 85%</div>
            </button>

            <button
              type="button"
              onClick={() => setUniformidadeNivel("media")}
              className={`rounded-xl border-2 p-3 text-center transition-all ${
                uniformidadeNivel === "media"
                  ? "border-amber-500 bg-amber-50 text-amber-900 font-bold dark:bg-amber-950/40 dark:text-amber-300"
                  : "border-slate-200 bg-slate-50/50 text-slate-600 hover:border-slate-300 dark:border-white/10 dark:bg-white/5 dark:text-slate-400"
              }`}
            >
              <div className="text-sm font-bold">Média</div>
              <div className="text-[10px] opacity-80 mt-0.5">65 - 85%</div>
            </button>

            <button
              type="button"
              onClick={() => setUniformidadeNivel("baixa")}
              className={`rounded-xl border-2 p-3 text-center transition-all ${
                uniformidadeNivel === "baixa"
                  ? "border-red-500 bg-red-50 text-red-900 font-bold dark:bg-red-950/40 dark:text-red-300"
                  : "border-slate-200 bg-slate-50/50 text-slate-600 hover:border-slate-300 dark:border-white/10 dark:bg-white/5 dark:text-slate-400"
              }`}
            >
              <div className="text-sm font-bold">Desuniforme</div>
              <div className="text-[10px] opacity-80 mt-0.5">&lt; 65%</div>
            </button>
          </div>
        </div>

        {/* Observações & Tags Rápidas */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151d2e]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-bold text-slate-800 dark:text-slate-100">
              Observações Zootécnicas
            </span>
            <span className="text-[11px] text-slate-400">Opcional</span>
          </div>

          <textarea
            rows={2}
            value={observacoes}
            onChange={(e) => setObservacoes(e.target.value)}
            placeholder="Ex: Camarões ativos na amostragem, tubo digestivo 100% cheio..."
            className="w-full rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-800 placeholder:text-slate-400 focus:border-sky-500 focus:outline-none dark:border-white/10 dark:bg-white/5 dark:text-white"
          />

          <div className="mt-3 flex flex-wrap items-center gap-1.5 pt-2 border-t border-slate-100 dark:border-white/5">
            <span className="text-[11px] font-semibold text-slate-400 mr-1">Adicionar rápido:</span>
            {["+ Trato OK", "+ Casca dura", "+ Ecdise detectada", "+ Trato rápido"].map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => addTagObs(tag.replace("+ ", ""))}
                className="rounded-lg bg-slate-100 px-2 py-1 text-[11px] font-medium text-slate-600 hover:bg-slate-200 dark:bg-white/5 dark:text-slate-300 dark:hover:bg-white/10"
              >
                {tag}
              </button>
            ))}
          </div>
        </div>

        {/* Feedback */}
        {success && (
          <div className="flex items-center gap-2.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-xs font-bold text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 className="h-5 w-5 shrink-0" />
            Biometria registrada com sucesso! Curva de crescimento recalculada.
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2.5 rounded-xl border border-red-500/30 bg-red-500/10 p-3.5 text-xs font-bold text-red-600 dark:text-red-400">
            <AlertTriangle className="h-5 w-5 shrink-0" />
            {error}
          </div>
        )}

        {/* Botão de Envio */}
        <Button
          type="submit"
          disabled={submitting}
          size="lg"
          className="w-full text-base font-bold shadow-lg shadow-sky-500/25 h-13"
        >
          {submitting ? (
            <div className="flex items-center gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              Gravando Dados...
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5" />
              Salvar Biometria Semanal
            </div>
          )}
        </Button>
      </form>

      {/* ── Histórico de Biometrias ── */}
      <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151d2e]">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
          Histórico Recente de Gramatura
        </h3>

        {biometrias.length === 0 ? (
          <p className="text-xs text-slate-400 italic">Nenhuma biometria cadastrada neste ciclo.</p>
        ) : (
          <div className="space-y-2.5">
            {biometrias.slice(0, 5).map((b) => (
              <div
                key={b.id}
                className="flex items-center justify-between rounded-xl bg-slate-50 p-3 text-xs dark:bg-white/5"
              >
                <div>
                  <span className="font-extrabold text-slate-900 dark:text-white text-sm">
                    {b.peso_medio_g.toFixed(1)} g
                  </span>
                  <p className="text-[11px] text-slate-400">{fmtDate(b.data_medicao)}</p>
                </div>

                <div className="text-right">
                  {b.ganho_medio_semanal_g !== null && (
                    <Badge variant="success">
                      +{b.ganho_medio_semanal_g.toFixed(2)} g/sem
                    </Badge>
                  )}
                  {b.uniformidade_percentual && (
                    <span className="text-[11px] text-slate-400 block mt-0.5">
                      {b.uniformidade_percentual}% unif.
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
