"use client";

import { useEffect, useState } from "react";
import {
  Utensils,
  Loader2,
  AlertTriangle,
  Shell,
  CalendarDays,
  Zap,
  Info,
  CheckCircle2,
  Plus,
  Activity,
} from "lucide-react";
import { ciclosApi, viveirosApi, manejosApi } from "@/lib/api";
import type { CicloProdutivo, Viveiro, RecomendacaoAlimentar, ManejoAlimentar } from "@/lib/types";

const SOBRA_OPTIONS = [
  { value: "SEM_SOBRA", label: "🟢 Sem sobra" },
  { value: "SOBRA_LEVE", label: "🟡 Sobra leve" },
  { value: "SOBRA_MODERADA", label: "🟠 Sobra moderada" },
  { value: "SOBRA_EXCESSIVA", label: "🔴 Sobra excessiva" },
];

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

  const [form, setForm] = useState({
    data_registro: new Date().toISOString().split("T")[0],
    quantidade_racao_kg: "",
    sobra_bandeja_nivel: "SEM_SOBRA",
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
        if (rec) {
          setForm((prev) => ({ ...prev, quantidade_racao_kg: rec.racao_diaria_sugerida_kg.toString() }));
        }
      } catch { }
    }
    loadCicloData();
  }, [selectedCiclo]);

  const getViveiroName = (vId: string) =>
    viveiros.find((v) => v.id === vId)?.identificacao || "—";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess(false);
    setSubmitting(true);
    try {
      await manejosApi.criar(selectedCiclo, {
        data_registro: form.data_registro,
        quantidade_racao_kg: parseFloat(form.quantidade_racao_kg),
        sobra_bandeja_nivel: form.sobra_bandeja_nivel,
      });
      setSuccess(true);
      // Refresh
      const [rec, mans] = await Promise.all([
        manejosApi.recomendacao(selectedCiclo).catch(() => null),
        manejosApi.listar(selectedCiclo).catch(() => []),
      ]);
      setRecomendacao(rec);
      setManejos(mans);
      setForm((prev) => ({
        ...prev,
        quantidade_racao_kg: rec ? rec.racao_diaria_sugerida_kg.toString() : "",
        sobra_bandeja_nivel: "SEM_SOBRA",
      }));
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message || "Erro ao registrar");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="w-8 h-8 text-pond-400 animate-spin" /></div>;

  if (ciclos.length === 0) {
    return (
      <div className="glass-card p-10 text-center mt-8">
        <Activity className="w-12 h-12 text-[var(--text-muted)] mx-auto mb-4" />
        <h2 className="text-lg font-bold text-[var(--text-primary)] mb-2">Nenhum ciclo ativo</h2>
        <p className="text-sm text-[var(--text-muted)]">Aguarde o gestor iniciar um ciclo produtivo</p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-xl font-bold text-[var(--text-primary)] mb-4 flex items-center gap-2">
        <Utensils className="w-5 h-5 text-shrimp-400" />
        Registrar Manejo
      </h2>

      {/* Ciclo selector */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Viveiro / Ciclo</label>
        <select
          value={selectedCiclo}
          onChange={(e) => { setSelectedCiclo(e.target.value); setSuccess(false); }}
          className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-pond-500 transition-all appearance-none text-base"
        >
          {ciclos.map((c) => (
            <option key={c.id} value={c.id} className="bg-[var(--bg-secondary)]">
              {getViveiroName(c.viveiro_id)} — {c.quantidade_pos_larvas.toLocaleString("pt-BR")} PLs
            </option>
          ))}
        </select>
      </div>

      {/* Recomendação */}
      {recomendacao && (
        <div className="glass-card p-4 mb-5 border-l-4 border-l-ocean-500">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-ocean-400" />
            <span className="text-xs font-bold text-ocean-400 uppercase tracking-wider">Recomendação</span>
          </div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-2xl font-black text-[var(--text-primary)]">{recomendacao.racao_diaria_sugerida_kg}</span>
            <span className="text-sm text-[var(--text-muted)]">kg de ração sugerida</span>
          </div>
          <p className="text-sm text-[var(--text-secondary)]">{recomendacao.ajuste_sugerido}</p>
        </div>
      )}

      {/* Success message */}
      {success && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-green-500/10 border border-green-500/30 text-green-400 text-sm mb-4 animate-in">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span className="font-medium">Manejo registrado com sucesso!</span>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm mb-4">
          <AlertTriangle className="w-4 h-4 shrink-0" />{error}
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Data do Registro</label>
          <input
            required
            type="date"
            value={form.data_registro}
            onChange={(e) => setForm({ ...form, data_registro: e.target.value })}
            className="w-full px-4 py-3.5 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-pond-500 focus:ring-1 focus:ring-pond-500/50 transition-all text-base"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Ração Fornecida (kg)</label>
          <input
            required
            type="number"
            step="0.01"
            min="0"
            inputMode="decimal"
            value={form.quantidade_racao_kg}
            onChange={(e) => setForm({ ...form, quantidade_racao_kg: e.target.value })}
            placeholder="25.0"
            className="w-full px-4 py-3.5 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-pond-500 focus:ring-1 focus:ring-pond-500/50 transition-all text-lg font-semibold"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">Sobra na Bandeja</label>
          <div className="grid grid-cols-1 gap-2">
            {SOBRA_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setForm({ ...form, sobra_bandeja_nivel: opt.value })}
                className={`px-4 py-3.5 rounded-xl text-left text-base font-medium transition-all border ${
                  form.sobra_bandeja_nivel === opt.value
                    ? "bg-pond-500/15 border-pond-500/30 text-pond-400"
                    : "bg-white/5 border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-white/8"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-4 rounded-xl bg-gradient-to-r from-shrimp-600 to-shrimp-500 text-white font-bold text-lg flex items-center justify-center gap-2 hover:from-shrimp-500 hover:to-shrimp-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-shrimp-500/20 active:scale-[0.98]"
        >
          {submitting ? <Loader2 className="w-6 h-6 animate-spin" /> : <><Utensils className="w-6 h-6" /> Registrar Manejo</>}
        </button>
      </form>

      {/* Últimos registros */}
      {manejos.length > 0 && (
        <div className="mt-8">
          <h3 className="text-sm font-bold text-[var(--text-muted)] uppercase tracking-wider mb-3">Últimos registros</h3>
          <div className="space-y-2">
            {[...manejos].reverse().slice(0, 5).map((m) => (
              <div key={m.id} className="glass-card p-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CalendarDays className="w-4 h-4 text-[var(--text-muted)]" />
                  <span className="text-sm text-[var(--text-primary)]">{fmtDate(m.data_registro)}</span>
                </div>
                <span className="text-sm font-bold text-shrimp-400 tabular-nums">{m.quantidade_racao_kg} kg</span>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  m.sobra_bandeja_nivel === "SEM_SOBRA" ? "badge-success"
                    : m.sobra_bandeja_nivel === "SOBRA_LEVE" ? "badge-warning"
                    : m.sobra_bandeja_nivel === "SOBRA_MODERADA" ? "badge-warning"
                    : "badge-danger"
                }`}>
                  {SOBRA_OPTIONS.find((o) => o.value === m.sobra_bandeja_nivel)?.label.replace(/[🟢🟡🟠🔴]\s?/, "") || m.sobra_bandeja_nivel}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
