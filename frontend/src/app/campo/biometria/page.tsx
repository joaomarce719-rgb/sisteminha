"use client";

import { useEffect, useState } from "react";
import {
  Scale,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  CalendarDays,
  Activity,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react";
import { ciclosApi, viveirosApi, biometriasApi } from "@/lib/api";
import type { CicloProdutivo, Viveiro, Biometria } from "@/lib/types";

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

  const [form, setForm] = useState({
    data_medicao: new Date().toISOString().split("T")[0],
    peso_medio_g: "",
    uniformidade_percentual: "",
    observacoes: "",
  });

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
      } catch {}
    }
    loadBio();
  }, [selectedCiclo]);

  const getViveiroName = (vId: string) =>
    viveiros.find((v) => v.id === vId)?.identificacao || "—";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess(false);
    setSubmitting(true);
    try {
      await biometriasApi.criar(selectedCiclo, {
        data_medicao: form.data_medicao,
        peso_medio_g: parseFloat(form.peso_medio_g),
        uniformidade_percentual: form.uniformidade_percentual
          ? parseFloat(form.uniformidade_percentual)
          : null,
        observacoes: form.observacoes || null,
      });
      setSuccess(true);
      const bios = await biometriasApi.listar(selectedCiclo);
      setBiometrias(bios);
      setForm({
        data_medicao: new Date().toISOString().split("T")[0],
        peso_medio_g: "",
        uniformidade_percentual: "",
        observacoes: "",
      });
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message || "Erro ao registrar");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading)
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-pond-400 animate-spin" />
      </div>
    );

  if (ciclos.length === 0) {
    return (
      <div className="glass-card p-10 text-center mt-8">
        <Activity className="w-12 h-12 text-[var(--text-muted)] mx-auto mb-4" />
        <h2 className="text-lg font-bold text-[var(--text-primary)] mb-2">
          Nenhum ciclo ativo
        </h2>
        <p className="text-sm text-[var(--text-muted)]">
          Aguarde o gestor iniciar um ciclo produtivo
        </p>
      </div>
    );
  }

  const lastBio = biometrias.length > 0 ? biometrias[biometrias.length - 1] : null;

  return (
    <div>
      <h2 className="text-xl font-bold text-[var(--text-primary)] mb-4 flex items-center gap-2">
        <Scale className="w-5 h-5 text-ocean-400" />
        Registrar Biometria
      </h2>

      {/* Ciclo selector */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
          Viveiro / Ciclo
        </label>
        <select
          value={selectedCiclo}
          onChange={(e) => {
            setSelectedCiclo(e.target.value);
            setSuccess(false);
          }}
          className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-ocean-500 transition-all appearance-none text-base"
        >
          {ciclos.map((c) => (
            <option key={c.id} value={c.id} className="bg-[var(--bg-secondary)]">
              {getViveiroName(c.viveiro_id)} — {c.quantidade_pos_larvas.toLocaleString("pt-BR")} PLs
            </option>
          ))}
        </select>
      </div>

      {/* Last biometry info */}
      {lastBio && (
        <div className="glass-card p-4 mb-5 border-l-4 border-l-ocean-500">
          <div className="flex items-center gap-2 mb-1">
            <Scale className="w-4 h-4 text-ocean-400" />
            <span className="text-xs font-bold text-ocean-400 uppercase tracking-wider">
              Última biometria
            </span>
          </div>
          <div className="flex items-baseline gap-3">
            <span className="text-2xl font-black text-[var(--text-primary)]">
              {lastBio.peso_medio_g.toFixed(1)} g
            </span>
            <span className="text-sm text-[var(--text-muted)]">
              em {fmtDate(lastBio.data_medicao)}
            </span>
            {lastBio.ganho_medio_semanal_g != null && (
              <span
                className={`text-sm font-semibold flex items-center gap-0.5 ${
                  lastBio.ganho_medio_semanal_g > 0
                    ? "text-pond-400"
                    : lastBio.ganho_medio_semanal_g < 0
                    ? "text-red-400"
                    : "text-[var(--text-muted)]"
                }`}
              >
                {lastBio.ganho_medio_semanal_g > 0 ? (
                  <TrendingUp className="w-4 h-4" />
                ) : lastBio.ganho_medio_semanal_g < 0 ? (
                  <TrendingDown className="w-4 h-4" />
                ) : (
                  <Minus className="w-4 h-4" />
                )}
                {lastBio.ganho_medio_semanal_g > 0 ? "+" : ""}
                {lastBio.ganho_medio_semanal_g.toFixed(2)} g/sem
              </span>
            )}
          </div>
        </div>
      )}

      {/* Success */}
      {success && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-green-500/10 border border-green-500/30 text-green-400 text-sm mb-4 animate-in">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span className="font-medium">Biometria registrada com sucesso!</span>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm mb-4">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
            Data da Medição
          </label>
          <input
            required
            type="date"
            value={form.data_medicao}
            onChange={(e) => setForm({ ...form, data_medicao: e.target.value })}
            className="w-full px-4 py-3.5 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all text-base"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
            Peso Médio (g) *
          </label>
          <input
            required
            type="number"
            step="0.01"
            min="0.01"
            inputMode="decimal"
            value={form.peso_medio_g}
            onChange={(e) => setForm({ ...form, peso_medio_g: e.target.value })}
            placeholder="12.50"
            className="w-full px-4 py-3.5 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all text-lg font-semibold"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
            Uniformidade (%)
          </label>
          <input
            type="number"
            step="0.1"
            min="0"
            max="100"
            inputMode="decimal"
            value={form.uniformidade_percentual}
            onChange={(e) => setForm({ ...form, uniformidade_percentual: e.target.value })}
            placeholder="85.0 (opcional)"
            className="w-full px-4 py-3.5 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all text-base"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
            Observações
          </label>
          <textarea
            value={form.observacoes}
            onChange={(e) => setForm({ ...form, observacoes: e.target.value })}
            placeholder="Ex: camarões com bom aspecto visual..."
            rows={3}
            className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all resize-none text-base"
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-4 rounded-xl bg-gradient-to-r from-ocean-600 to-ocean-500 text-white font-bold text-lg flex items-center justify-center gap-2 hover:from-ocean-500 hover:to-ocean-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-ocean-500/20 active:scale-[0.98]"
        >
          {submitting ? (
            <Loader2 className="w-6 h-6 animate-spin" />
          ) : (
            <>
              <Scale className="w-6 h-6" /> Registrar Biometria
            </>
          )}
        </button>
      </form>

      {/* Histórico */}
      {biometrias.length > 0 && (
        <div className="mt-8">
          <h3 className="text-sm font-bold text-[var(--text-muted)] uppercase tracking-wider mb-3">
            Histórico de Biometrias
          </h3>
          <div className="space-y-2">
            {[...biometrias]
              .reverse()
              .slice(0, 8)
              .map((b) => (
                <div
                  key={b.id}
                  className="glass-card p-3 flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <CalendarDays className="w-4 h-4 text-[var(--text-muted)]" />
                    <span className="text-sm text-[var(--text-primary)]">
                      {fmtDate(b.data_medicao)}
                    </span>
                  </div>
                  <span className="text-sm font-bold text-ocean-400 tabular-nums">
                    {b.peso_medio_g.toFixed(2)} g
                  </span>
                  {b.ganho_medio_semanal_g != null && (
                    <span
                      className={`text-xs font-medium flex items-center gap-0.5 ${
                        b.ganho_medio_semanal_g > 0
                          ? "text-pond-400"
                          : b.ganho_medio_semanal_g < 0
                          ? "text-red-400"
                          : "text-[var(--text-muted)]"
                      }`}
                    >
                      {b.ganho_medio_semanal_g > 0 ? "+" : ""}
                      {b.ganho_medio_semanal_g.toFixed(2)} g/sem
                    </span>
                  )}
                  {b.uniformidade_percentual != null && (
                    <span className="text-xs text-[var(--text-muted)]">
                      {b.uniformidade_percentual.toFixed(0)}% uni
                    </span>
                  )}
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
