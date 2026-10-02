"use client";

import { useEffect, useState } from "react";
import {
  Moon,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Droplets,
  Thermometer,
  Wind,
  Zap,
  Activity,
  CalendarDays,
  Eye,
  Shell,
} from "lucide-react";
import { ciclosApi, viveirosApi, rondasApi } from "@/lib/api";
import type { CicloProdutivo, Viveiro, RondaNoturna } from "@/lib/types";

const COMP_OPTIONS = [
  { value: "NORMAL_FUNDO", label: "🟢 Normal (fundo)", desc: "Camarões nadando normalmente no fundo" },
  { value: "FLOR_DAGUA_BOQUEANDO", label: "🔴 Flor d'água / Boqueando", desc: "Camarões na superfície, falta de O₂" },
  { value: "NATACAO_AGITADA", label: "🟡 Natação agitada", desc: "Movimentação excessiva e desordenada" },
  { value: "ECDISE_MASSIVA", label: "🟣 Ecdise massiva", desc: "Muitas cascas / muda simultânea" },
  { value: "PRESENCA_BORDAS", label: "🟠 Presença nas bordas", desc: "Aglomeração nas bordas do viveiro" },
];

const ENERGIA_OPTIONS = [
  { value: "REDE_CONCESSIONARIA", label: "⚡ Rede elétrica" },
  { value: "GERADOR_DIESEL", label: "🔧 Gerador diesel" },
  { value: "SEM_ENERGIA_QUEDA", label: "❌ Sem energia (queda)" },
];

function fmtDateTime(d: string) {
  return new Date(d).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export default function RondaPage() {
  const [viveiros, setViveiros] = useState<Viveiro[]>([]);
  const [ciclos, setCiclos] = useState<CicloProdutivo[]>([]);
  const [selectedCiclo, setSelectedCiclo] = useState("");
  const [rondas, setRondas] = useState<RondaNoturna[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    data_hora_ronda: new Date().toISOString().slice(0, 16),
    oxigenio_dissolvido_mg_l: "",
    temperatura_agua_c: "",
    comportamento: "NORMAL_FUNDO",
    aeradores_instalados: "",
    aeradores_ligados: "",
    fonte_energia: "REDE_CONCESSIONARIA",
    falha_mecanica_detectada: false,
    detalhes_falha: "",
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
    async function loadRondas() {
      try {
        const data = await rondasApi.listarPorCiclo(selectedCiclo);
        setRondas(data);
      } catch {}
    }
    loadRondas();
  }, [selectedCiclo]);

  const getViveiroName = (vId: string) =>
    viveiros.find((v) => v.id === vId)?.identificacao || "—";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess(false);
    setSubmitting(true);
    try {
      await rondasApi.criar({
        ciclo_id: selectedCiclo,
        data_hora_ronda: new Date(form.data_hora_ronda).toISOString(),
        oxigenio_dissolvido_mg_l: parseFloat(form.oxigenio_dissolvido_mg_l),
        temperatura_agua_c: parseFloat(form.temperatura_agua_c),
        comportamento: form.comportamento,
        observacoes: form.observacoes || null,
        aeradores_instalados: parseInt(form.aeradores_instalados),
        aeradores_ligados: parseInt(form.aeradores_ligados),
        fonte_energia: form.fonte_energia,
        falha_mecanica_detectada: form.falha_mecanica_detectada,
        detalhes_falha: form.falha_mecanica_detectada ? form.detalhes_falha || null : null,
      });
      setSuccess(true);
      const data = await rondasApi.listarPorCiclo(selectedCiclo);
      setRondas(data);
      // Reset form with updated time
      setForm({
        data_hora_ronda: new Date().toISOString().slice(0, 16),
        oxigenio_dissolvido_mg_l: "",
        temperatura_agua_c: "",
        comportamento: "NORMAL_FUNDO",
        aeradores_instalados: form.aeradores_instalados,
        aeradores_ligados: form.aeradores_ligados,
        fonte_energia: form.fonte_energia,
        falha_mecanica_detectada: false,
        detalhes_falha: "",
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
        <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />
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

  return (
    <div>
      <h2 className="text-xl font-bold text-[var(--text-primary)] mb-4 flex items-center gap-2">
        <Moon className="w-5 h-5 text-amber-400" />
        Registrar Ronda Noturna
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
          className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-amber-500 transition-all appearance-none text-base"
        >
          {ciclos.map((c) => (
            <option key={c.id} value={c.id} className="bg-[var(--bg-secondary)]">
              {getViveiroName(c.viveiro_id)} — {c.quantidade_pos_larvas.toLocaleString("pt-BR")} PLs
            </option>
          ))}
        </select>
      </div>

      {success && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-green-500/10 border border-green-500/30 text-green-400 text-sm mb-4 animate-in">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span className="font-medium">Ronda registrada com sucesso!</span>
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
        {/* Data/hora */}
        <div>
          <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
            <CalendarDays className="w-4 h-4 inline mr-1" />
            Data e Hora
          </label>
          <input
            required
            type="datetime-local"
            value={form.data_hora_ronda}
            onChange={(e) => setForm({ ...form, data_hora_ronda: e.target.value })}
            className="w-full px-4 py-3.5 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500/50 transition-all text-base"
          />
        </div>

        {/* O2 + Temperatura */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
              <Droplets className="w-4 h-4 inline mr-1 text-blue-400" />
              O₂ (mg/L) *
            </label>
            <input
              required
              type="number"
              step="0.1"
              min="0"
              max="20"
              inputMode="decimal"
              value={form.oxigenio_dissolvido_mg_l}
              onChange={(e) => setForm({ ...form, oxigenio_dissolvido_mg_l: e.target.value })}
              placeholder="5.0"
              className="w-full px-4 py-3.5 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 transition-all text-lg font-semibold"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
              <Thermometer className="w-4 h-4 inline mr-1 text-orange-400" />
              Temp (°C) *
            </label>
            <input
              required
              type="number"
              step="0.1"
              min="15"
              max="40"
              inputMode="decimal"
              value={form.temperatura_agua_c}
              onChange={(e) => setForm({ ...form, temperatura_agua_c: e.target.value })}
              placeholder="28.0"
              className="w-full px-4 py-3.5 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500/50 transition-all text-lg font-semibold"
            />
          </div>
        </div>

        {/* Comportamento */}
        <div>
          <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
            <Eye className="w-4 h-4 inline mr-1" />
            Comportamento dos Camarões *
          </label>
          <div className="space-y-2">
            {COMP_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setForm({ ...form, comportamento: opt.value })}
                className={`w-full px-4 py-3 rounded-xl text-left transition-all border ${
                  form.comportamento === opt.value
                    ? "bg-amber-500/15 border-amber-500/30 text-amber-400"
                    : "bg-white/5 border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-white/8"
                }`}
              >
                <span className="text-base font-medium block">{opt.label}</span>
                <span className="text-xs text-[var(--text-muted)]">{opt.desc}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Aeradores */}
        <div className="glass-card p-4">
          <h3 className="text-sm font-bold text-[var(--text-primary)] mb-3 flex items-center gap-2">
            <Wind className="w-4 h-4 text-[var(--text-muted)]" />
            Aeradores
          </h3>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">
                Instalados *
              </label>
              <input
                required
                type="number"
                min="1"
                max="30"
                inputMode="numeric"
                value={form.aeradores_instalados}
                onChange={(e) => setForm({ ...form, aeradores_instalados: e.target.value })}
                placeholder="4"
                className="w-full px-3 py-2.5 rounded-lg bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-amber-500 transition-all text-base"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--text-muted)] mb-1">
                Ligados *
              </label>
              <input
                required
                type="number"
                min="0"
                max="30"
                inputMode="numeric"
                value={form.aeradores_ligados}
                onChange={(e) => setForm({ ...form, aeradores_ligados: e.target.value })}
                placeholder="4"
                className="w-full px-3 py-2.5 rounded-lg bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-amber-500 transition-all text-base"
              />
            </div>
          </div>

          {/* Energia */}
          <div className="mb-3">
            <label className="block text-xs font-medium text-[var(--text-muted)] mb-1.5">
              Fonte de Energia
            </label>
            <div className="grid grid-cols-3 gap-2">
              {ENERGIA_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setForm({ ...form, fonte_energia: opt.value })}
                  className={`px-2 py-2 rounded-lg text-xs font-medium text-center transition-all border ${
                    form.fonte_energia === opt.value
                      ? opt.value === "SEM_ENERGIA_QUEDA"
                        ? "bg-red-500/15 border-red-500/30 text-red-400"
                        : "bg-amber-500/15 border-amber-500/30 text-amber-400"
                      : "bg-white/5 border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-white/8"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Falha mecânica */}
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={form.falha_mecanica_detectada}
              onChange={(e) => setForm({ ...form, falha_mecanica_detectada: e.target.checked })}
              className="w-5 h-5 rounded border-[var(--border-subtle)] text-red-500 focus:ring-red-500/50"
            />
            <span className="text-sm text-[var(--text-secondary)]">
              <AlertTriangle className="w-4 h-4 inline mr-1 text-red-400" />
              Falha mecânica detectada
            </span>
          </label>

          {form.falha_mecanica_detectada && (
            <input
              type="text"
              value={form.detalhes_falha}
              onChange={(e) => setForm({ ...form, detalhes_falha: e.target.value })}
              placeholder="Descreva a falha..."
              className="w-full mt-2 px-3 py-2.5 rounded-lg bg-white/5 border border-red-500/30 text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-red-500 transition-all text-sm"
            />
          )}
        </div>

        {/* Observações */}
        <div>
          <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
            Observações
          </label>
          <textarea
            value={form.observacoes}
            onChange={(e) => setForm({ ...form, observacoes: e.target.value })}
            placeholder="Observações da ronda..."
            rows={2}
            className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500/50 transition-all resize-none text-base"
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-4 rounded-xl bg-gradient-to-r from-amber-600 to-amber-500 text-white font-bold text-lg flex items-center justify-center gap-2 hover:from-amber-500 hover:to-amber-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-amber-500/20 active:scale-[0.98]"
        >
          {submitting ? (
            <Loader2 className="w-6 h-6 animate-spin" />
          ) : (
            <>
              <Moon className="w-6 h-6" /> Registrar Ronda
            </>
          )}
        </button>
      </form>

      {/* Últimas rondas */}
      {rondas.length > 0 && (
        <div className="mt-8">
          <h3 className="text-sm font-bold text-[var(--text-muted)] uppercase tracking-wider mb-3">
            Últimas Rondas
          </h3>
          <div className="space-y-2">
            {rondas.slice(0, 5).map((r) => {
              const o2Color =
                r.classificacao_oxigenio === "EMERGENCIA"
                  ? "text-red-400"
                  : r.classificacao_oxigenio === "ALERTA"
                  ? "text-amber-400"
                  : "text-green-400";
              return (
                <div key={r.id} className="glass-card p-3 flex flex-wrap items-center gap-x-4 gap-y-1">
                  <span className="text-sm text-[var(--text-primary)] tabular-nums">
                    {fmtDateTime(r.data_hora_ronda)}
                  </span>
                  <span className={`text-sm font-bold tabular-nums ${o2Color}`}>
                    O₂ {r.oxigenio_dissolvido_mg_l.toFixed(1)}
                  </span>
                  <span className="text-sm text-[var(--text-secondary)] tabular-nums">
                    {r.temperatura_agua_c.toFixed(1)}°C
                  </span>
                  {r.aeradores_ligados != null && (
                    <span className="text-xs text-[var(--text-muted)]">
                      {r.aeradores_ligados}/{r.aeradores_instalados} aer.
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
