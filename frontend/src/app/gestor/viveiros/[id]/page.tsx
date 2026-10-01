"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Shell,
  Activity,
  Scale,
  Utensils,
  Plus,
  X,
  Loader2,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Minus,
  Droplets,
  MapPin,
  Ruler,
  CalendarDays,
  Bug,
  Zap,
  Target,
  DollarSign,
  BarChart3,
  ChevronDown,
  ChevronUp,
  Info,
  Edit3,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import {
  viveirosApi,
  ciclosApi,
  biometriasApi,
  manejosApi,
} from "@/lib/api";
import type {
  Viveiro,
  CicloProdutivo,
  MetricasAtuais,
  Biometria,
  ManejoAlimentar,
  RecomendacaoAlimentar,
} from "@/lib/types";

// ── Tab type ────────────────────────────────────────
type Tab = "metricas" | "biometrias" | "manejos";

// ── Helper: format date ─────────────────────────────
function fmtDate(d: string) {
  return new Date(d).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

// ── Metric Card Component ───────────────────────────
function MetricCard({
  label,
  value,
  unit,
  icon: Icon,
  color = "ocean",
  alert = false,
  subtitle,
}: {
  label: string;
  value: string | number;
  unit?: string;
  icon: any;
  color?: string;
  alert?: boolean;
  subtitle?: string;
}) {
  const colorMap: Record<string, string> = {
    ocean: "#1aa0ff",
    pond: "#28d280",
    shrimp: "#ff7d33",
    red: "#ef4444",
    amber: "#f59e0b",
  };

  return (
    <div
      className={`glass-card p-4 ${alert ? "pulse-alert border-red-500/30" : ""}`}
    >
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-4 h-4" style={{ color: colorMap[color] || colorMap.ocean }} />
        <span className="text-xs text-[var(--text-muted)] font-medium uppercase tracking-wider">
          {label}
        </span>
      </div>
      <p
        className="text-2xl font-bold tabular-nums"
        style={{ color: colorMap[color] || colorMap.ocean }}
      >
        {value}
        {unit && (
          <span className="text-sm font-normal text-[var(--text-muted)] ml-1">
            {unit}
          </span>
        )}
      </p>
      {subtitle && (
        <p className="text-xs text-[var(--text-muted)] mt-1">{subtitle}</p>
      )}
    </div>
  );
}

// ── Modal Iniciar Ciclo ─────────────────────────────
function IniciarCicloModal({
  open,
  onClose,
  onCreated,
  viveiroId,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
  viveiroId: string;
}) {
  const [form, setForm] = useState({
    data_povoamento: new Date().toISOString().split("T")[0],
    quantidade_pos_larvas: "",
    custo_aquisicao_pl: "",
    laboratorio_origem: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await ciclosApi.criar({
        viveiro_id: viveiroId,
        data_povoamento: form.data_povoamento,
        quantidade_pos_larvas: parseInt(form.quantidade_pos_larvas),
        custo_aquisicao_pl: parseFloat(form.custo_aquisicao_pl),
        laboratorio_origem: form.laboratorio_origem || null,
      });
      onCreated();
      onClose();
    } catch (err: any) {
      setError(err.message || "Erro ao iniciar ciclo");
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass-card p-6 w-full max-w-md relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors">
          <X className="w-5 h-5" />
        </button>
        <h2 className="text-xl font-bold text-[var(--text-primary)] mb-1">Iniciar Ciclo Produtivo</h2>
        <p className="text-sm text-[var(--text-muted)] mb-6">Povoamento de pós-larvas</p>

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm mb-4">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Data do Povoamento *</label>
            <input
              required
              type="date"
              value={form.data_povoamento}
              onChange={(e) => setForm({ ...form, data_povoamento: e.target.value })}
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Qtde. Pós-Larvas *</label>
            <input
              required
              type="number"
              min="1"
              inputMode="numeric"
              value={form.quantidade_pos_larvas}
              onChange={(e) => setForm({ ...form, quantidade_pos_larvas: e.target.value })}
              placeholder="300000"
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Custo aquisição PLs (R$) *</label>
            <input
              required
              type="number"
              min="0"
              step="0.01"
              inputMode="decimal"
              value={form.custo_aquisicao_pl}
              onChange={(e) => setForm({ ...form, custo_aquisicao_pl: e.target.value })}
              placeholder="4500.00"
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Laboratório de Origem</label>
            <input
              value={form.laboratorio_origem}
              onChange={(e) => setForm({ ...form, laboratorio_origem: e.target.value })}
              placeholder="Opcional"
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-pond-600 to-pond-500 text-white font-semibold flex items-center justify-center gap-2 hover:from-pond-500 hover:to-pond-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-pond-500/20 active:scale-[0.98]"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><Activity className="w-5 h-5" /> Iniciar Ciclo</>}
          </button>
        </form>
      </div>
    </div>
  );
}

// ── Modal Biometria ─────────────────────────────────
function BiometriaModal({
  open,
  onClose,
  onCreated,
  cicloId,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
  cicloId: string;
}) {
  const [form, setForm] = useState({
    data_medicao: new Date().toISOString().split("T")[0],
    peso_medio_g: "",
    uniformidade_percentual: "",
    observacoes: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await biometriasApi.criar(cicloId, {
        data_medicao: form.data_medicao,
        peso_medio_g: parseFloat(form.peso_medio_g),
        uniformidade_percentual: form.uniformidade_percentual
          ? parseFloat(form.uniformidade_percentual)
          : null,
        observacoes: form.observacoes || null,
      });
      onCreated();
      onClose();
      setForm({ data_medicao: new Date().toISOString().split("T")[0], peso_medio_g: "", uniformidade_percentual: "", observacoes: "" });
    } catch (err: any) {
      setError(err.message || "Erro ao registrar biometria");
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass-card p-6 w-full max-w-md relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors">
          <X className="w-5 h-5" />
        </button>
        <h2 className="text-xl font-bold text-[var(--text-primary)] mb-1">Nova Biometria</h2>
        <p className="text-sm text-[var(--text-muted)] mb-6">Registre a amostragem biométrica</p>

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm mb-4">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Data da Medição *</label>
            <input required type="date" value={form.data_medicao} onChange={(e) => setForm({ ...form, data_medicao: e.target.value })}
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Peso Médio (g) *</label>
              <input required type="number" step="0.01" min="0.01" inputMode="decimal"
                value={form.peso_medio_g} onChange={(e) => setForm({ ...form, peso_medio_g: e.target.value })} placeholder="12.5"
                className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Uniformidade (%)</label>
              <input type="number" step="0.1" min="0" max="100" inputMode="decimal"
                value={form.uniformidade_percentual} onChange={(e) => setForm({ ...form, uniformidade_percentual: e.target.value })} placeholder="85"
                className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Observações</label>
            <textarea value={form.observacoes} onChange={(e) => setForm({ ...form, observacoes: e.target.value })} rows={2} placeholder="Notas da amostragem..."
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all resize-none"
            />
          </div>
          <button type="submit" disabled={loading}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-ocean-600 to-ocean-500 text-white font-semibold flex items-center justify-center gap-2 hover:from-ocean-500 hover:to-ocean-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-ocean-500/20 active:scale-[0.98]"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><Scale className="w-5 h-5" /> Registrar Biometria</>}
          </button>
        </form>
      </div>
    </div>
  );
}

// ── Modal Manejo Alimentar ──────────────────────────
const SOBRA_OPTIONS = [
  { value: "SEM_SOBRA", label: "Sem sobra", color: "text-green-400" },
  { value: "SOBRA_LEVE", label: "Sobra leve", color: "text-yellow-400" },
  { value: "SOBRA_MODERADA", label: "Sobra moderada", color: "text-orange-400" },
  { value: "SOBRA_EXCESSIVA", label: "Sobra excessiva", color: "text-red-400" },
];

function ManejoModal({
  open,
  onClose,
  onCreated,
  cicloId,
  recomendacao,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
  cicloId: string;
  recomendacao: RecomendacaoAlimentar | null;
}) {
  const [form, setForm] = useState({
    data_registro: new Date().toISOString().split("T")[0],
    quantidade_racao_kg: "",
    sobra_bandeja_nivel: "SEM_SOBRA",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Preencher com recomendação
  useEffect(() => {
    if (recomendacao && !form.quantidade_racao_kg) {
      setForm((prev) => ({
        ...prev,
        quantidade_racao_kg: recomendacao.racao_diaria_sugerida_kg.toString(),
      }));
    }
  }, [recomendacao]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await manejosApi.criar(cicloId, {
        data_registro: form.data_registro,
        quantidade_racao_kg: parseFloat(form.quantidade_racao_kg),
        sobra_bandeja_nivel: form.sobra_bandeja_nivel,
      });
      onCreated();
      onClose();
      setForm({ data_registro: new Date().toISOString().split("T")[0], quantidade_racao_kg: "", sobra_bandeja_nivel: "SEM_SOBRA" });
    } catch (err: any) {
      setError(err.message || "Erro ao registrar manejo");
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass-card p-6 w-full max-w-md relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors">
          <X className="w-5 h-5" />
        </button>
        <h2 className="text-xl font-bold text-[var(--text-primary)] mb-1">Registrar Manejo</h2>
        <p className="text-sm text-[var(--text-muted)] mb-4">Lançamento de ração fornecida</p>

        {/* Recomendação */}
        {recomendacao && (
          <div className="glass-card p-3 mb-4 border-ocean-500/20">
            <div className="flex items-center gap-2 mb-1.5">
              <Info className="w-4 h-4 text-ocean-400" />
              <span className="text-xs font-semibold text-ocean-400 uppercase tracking-wider">Recomendação Clifford</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-[var(--text-muted)]">Ração sugerida:</span>
                <span className="text-[var(--text-primary)] font-semibold ml-1">{recomendacao.racao_diaria_sugerida_kg} kg</span>
              </div>
              <div>
                <span className="text-[var(--text-muted)]">Taxa Clifford:</span>
                <span className="text-[var(--text-primary)] font-semibold ml-1">{recomendacao.taxa_clifford_pct}%</span>
              </div>
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-1.5">{recomendacao.ajuste_sugerido}</p>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm mb-4">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Data do Registro *</label>
            <input required type="date" value={form.data_registro} onChange={(e) => setForm({ ...form, data_registro: e.target.value })}
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Ração fornecida (kg) *</label>
            <input required type="number" step="0.01" min="0" inputMode="decimal"
              value={form.quantidade_racao_kg} onChange={(e) => setForm({ ...form, quantidade_racao_kg: e.target.value })} placeholder="25.0"
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Nível de Sobra na Bandeja *</label>
            <div className="grid grid-cols-2 gap-2">
              {SOBRA_OPTIONS.map((opt) => (
                <button key={opt.value} type="button"
                  onClick={() => setForm({ ...form, sobra_bandeja_nivel: opt.value })}
                  className={`px-3 py-2.5 rounded-xl text-sm font-medium transition-all border ${
                    form.sobra_bandeja_nivel === opt.value
                      ? "bg-ocean-500/15 border-ocean-500/30 text-ocean-400"
                      : "bg-white/5 border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-white/8"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          <button type="submit" disabled={loading}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-shrimp-600 to-shrimp-500 text-white font-semibold flex items-center justify-center gap-2 hover:from-shrimp-500 hover:to-shrimp-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-shrimp-500/20 active:scale-[0.98]"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><Utensils className="w-5 h-5" /> Registrar Manejo</>}
          </button>
        </form>
      </div>
    </div>
  );
}

// ── Modal Encerrar Ciclo ────────────────────────────
function EncerrarCicloModal({
  open,
  onClose,
  onDone,
  cicloId,
}: {
  open: boolean;
  onClose: () => void;
  onDone: () => void;
  cicloId: string;
}) {
  const [form, setForm] = useState({
    data_despesca_real: new Date().toISOString().split("T")[0],
    biomassa_colhida_kg: "",
    receita_real_rs: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await ciclosApi.encerrar(cicloId, {
        data_despesca_real: form.data_despesca_real,
        biomassa_colhida_kg: parseFloat(form.biomassa_colhida_kg),
        receita_real_rs: parseFloat(form.receita_real_rs),
      });
      onDone();
      onClose();
    } catch (err: any) {
      setError(err.message || "Erro ao encerrar ciclo");
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass-card p-6 w-full max-w-md relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors">
          <X className="w-5 h-5" />
        </button>
        <h2 className="text-xl font-bold text-red-400 mb-1">Encerrar Ciclo (Despesca)</h2>
        <p className="text-sm text-[var(--text-muted)] mb-6">Registre os dados reais da colheita</p>

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm mb-4">
            <AlertTriangle className="w-4 h-4 shrink-0" /> {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Data da Despesca *</label>
            <input required type="date" value={form.data_despesca_real} onChange={(e) => setForm({ ...form, data_despesca_real: e.target.value })}
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Biomassa Colhida (kg) *</label>
            <input required type="number" step="0.01" min="0.01" inputMode="decimal"
              value={form.biomassa_colhida_kg} onChange={(e) => setForm({ ...form, biomassa_colhida_kg: e.target.value })} placeholder="1500"
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Receita Real (R$) *</label>
            <input required type="number" step="0.01" min="0" inputMode="decimal"
              value={form.receita_real_rs} onChange={(e) => setForm({ ...form, receita_real_rs: e.target.value })} placeholder="45000"
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all"
            />
          </div>
          <button type="submit" disabled={loading}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-red-600 to-red-500 text-white font-semibold flex items-center justify-center gap-2 hover:from-red-500 hover:to-red-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-red-500/20 active:scale-[0.98]"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><XCircle className="w-5 h-5" /> Encerrar Ciclo</>}
          </button>
        </form>
      </div>
    </div>
  );
}

// ── Main Page ───────────────────────────────────────
export default function ViveiroDetalhePage() {
  const params = useParams();
  const router = useRouter();
  const viveiroId = params.id as string;

  const [viveiro, setViveiro] = useState<Viveiro | null>(null);
  const [cicloAtivo, setCicloAtivo] = useState<CicloProdutivo | null>(null);
  const [metricas, setMetricas] = useState<MetricasAtuais | null>(null);
  const [biometrias, setBiometrias] = useState<Biometria[]>([]);
  const [manejos, setManejos] = useState<ManejoAlimentar[]>([]);
  const [recomendacao, setRecomendacao] = useState<RecomendacaoAlimentar | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("metricas");
  const [loading, setLoading] = useState(true);

  // Modal states
  const [showCicloModal, setShowCicloModal] = useState(false);
  const [showBioModal, setShowBioModal] = useState(false);
  const [showManejoModal, setShowManejoModal] = useState(false);
  const [showEncerrarModal, setShowEncerrarModal] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const viv = await viveirosApi.obter(viveiroId);
      setViveiro(viv);

      // Buscar ciclos do viveiro
      const cycs: CicloProdutivo[] = await ciclosApi.listar({
        viveiro_id: viveiroId,
        status_filtro: "ATIVO",
      });

      const ciclo = cycs.length > 0 ? cycs[0] : null;
      setCicloAtivo(ciclo);

      if (ciclo) {
        const [met, bios, mans, rec] = await Promise.all([
          ciclosApi.metricas(ciclo.id).catch(() => null),
          biometriasApi.listar(ciclo.id).catch(() => []),
          manejosApi.listar(ciclo.id).catch(() => []),
          manejosApi.recomendacao(ciclo.id).catch(() => null),
        ]);
        setMetricas(met);
        setBiometrias(bios);
        setManejos(mans);
        setRecomendacao(rec);
      } else {
        setMetricas(null);
        setBiometrias([]);
        setManejos([]);
        setRecomendacao(null);
      }
    } catch {
      // handle
    } finally {
      setLoading(false);
    }
  }, [viveiroId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-8 h-8 text-ocean-400 animate-spin" />
      </div>
    );
  }

  if (!viveiro) {
    return (
      <div className="glass-card p-12 text-center max-w-md mx-auto mt-12">
        <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
        <h3 className="text-lg font-bold text-[var(--text-primary)] mb-2">Viveiro não encontrado</h3>
        <Link href="/gestor/viveiros" className="text-ocean-400 hover:underline text-sm">
          ← Voltar para viveiros
        </Link>
      </div>
    );
  }

  const diasCultivo = cicloAtivo
    ? Math.floor((new Date().getTime() - new Date(cicloAtivo.data_povoamento).getTime()) / (1000 * 60 * 60 * 24))
    : 0;

  return (
    <div className="max-w-7xl mx-auto">
      {/* Breadcrumb */}
      <Link
        href="/gestor/viveiros"
        className="inline-flex items-center gap-2 text-sm text-[var(--text-muted)] hover:text-ocean-400 transition-colors mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Voltar para Viveiros
      </Link>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-8">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-ocean-500/20 to-pond-500/20 border border-ocean-500/30 flex items-center justify-center">
            <Shell className="w-7 h-7 text-ocean-400" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)]">
              {viveiro.identificacao}
            </h1>
            <div className="flex items-center gap-3 mt-1">
              <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${viveiro.status_ativo ? "badge-success" : "badge-danger"}`}>
                {viveiro.status_ativo ? "Ativo" : "Inativo"}
              </span>
              <span className="text-sm text-[var(--text-muted)]">
                {viveiro.area_util_m2.toLocaleString("pt-BR")} m²
              </span>
              {viveiro.localizacao && (
                <span className="text-sm text-[var(--text-muted)] flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5" />
                  {viveiro.localizacao}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          {!cicloAtivo ? (
            <button
              onClick={() => setShowCicloModal(true)}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-pond-600 to-pond-500 text-white font-semibold text-sm hover:from-pond-500 hover:to-pond-400 transition-all shadow-lg shadow-pond-500/20 active:scale-[0.98]"
            >
              <Activity className="w-4 h-4" />
              Iniciar Ciclo
            </button>
          ) : (
            <>
              <button
                onClick={() => setShowBioModal(true)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-ocean-500/15 text-ocean-400 border border-ocean-500/25 font-medium text-sm hover:bg-ocean-500/25 transition-all"
              >
                <Scale className="w-4 h-4" />
                Biometria
              </button>
              <button
                onClick={() => setShowManejoModal(true)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-shrimp-500/15 text-shrimp-400 border border-shrimp-500/25 font-medium text-sm hover:bg-shrimp-500/25 transition-all"
              >
                <Utensils className="w-4 h-4" />
                Manejo
              </button>
              <button
                onClick={() => setShowEncerrarModal(true)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-red-500/10 text-red-400 border border-red-500/25 font-medium text-sm hover:bg-red-500/20 transition-all"
              >
                <XCircle className="w-4 h-4" />
                Encerrar
              </button>
            </>
          )}
        </div>
      </div>

      {/* No active cycle */}
      {!cicloAtivo && (
        <div className="glass-card p-12 text-center">
          <Activity className="w-12 h-12 text-[var(--text-muted)] mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
            Nenhum ciclo ativo
          </h3>
          <p className="text-sm text-[var(--text-muted)] mb-6">
            Inicie um novo ciclo produtivo para começar a registrar biometrias e manejos
          </p>
          <button
            onClick={() => setShowCicloModal(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-pond-600 to-pond-500 text-white font-semibold text-sm hover:from-pond-500 hover:to-pond-400 transition-all"
          >
            <Plus className="w-4 h-4" />
            Iniciar Ciclo
          </button>
        </div>
      )}

      {/* Active cycle content */}
      {cicloAtivo && (
        <>
          {/* Cycle info banner */}
          <div className="glass-card p-4 mb-6 flex flex-wrap items-center gap-x-6 gap-y-2">
            <div className="flex items-center gap-2">
              <CalendarDays className="w-4 h-4 text-pond-400" />
              <span className="text-sm text-[var(--text-secondary)]">
                Povoamento: <span className="text-[var(--text-primary)] font-medium">{fmtDate(cicloAtivo.data_povoamento)}</span>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-pond-400" />
              <span className="text-sm text-[var(--text-secondary)]">
                <span className="text-[var(--text-primary)] font-bold">{diasCultivo}</span> dias de cultivo
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Bug className="w-4 h-4 text-shrimp-400" />
              <span className="text-sm text-[var(--text-secondary)]">
                <span className="text-[var(--text-primary)] font-medium">{cicloAtivo.quantidade_pos_larvas.toLocaleString("pt-BR")}</span> PLs
              </span>
            </div>
            {cicloAtivo.laboratorio_origem && (
              <span className="text-xs badge-info px-2.5 py-0.5 rounded-full font-medium">
                {cicloAtivo.laboratorio_origem}
              </span>
            )}
          </div>

          {/* Tabs */}
          <div className="flex gap-1 mb-6 bg-white/5 p-1 rounded-xl border border-[var(--border-subtle)] w-fit">
            {[
              { key: "metricas" as Tab, label: "Métricas", icon: BarChart3 },
              { key: "biometrias" as Tab, label: "Biometrias", icon: Scale },
              { key: "manejos" as Tab, label: "Manejos", icon: Utensils },
            ].map((t) => (
              <button
                key={t.key}
                onClick={() => setActiveTab(t.key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  activeTab === t.key
                    ? "bg-ocean-500/15 text-ocean-400"
                    : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
                }`}
              >
                <t.icon className="w-4 h-4" />
                {t.label}
              </button>
            ))}
          </div>

          {/* Tab: Métricas */}
          {activeTab === "metricas" && metricas && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              <MetricCard
                label="Dias de Cultivo"
                value={metricas.dias_cultivo}
                icon={CalendarDays}
                color="ocean"
              />
              <MetricCard
                label="Peso Médio"
                value={metricas.peso_medio_atual_g.toFixed(1)}
                unit="g"
                icon={Scale}
                color="shrimp"
              />
              <MetricCard
                label="Biomassa Atual"
                value={metricas.biomassa_atual_kg.toLocaleString("pt-BR")}
                unit="kg"
                icon={TrendingUp}
                color="pond"
              />
              <MetricCard
                label="Densidade"
                value={metricas.densidade_estocagem}
                unit="PLs/m²"
                icon={Target}
                color={metricas.alerta_hiperdensidade ? "red" : "ocean"}
                alert={metricas.alerta_hiperdensidade}
                subtitle={metricas.alerta_hiperdensidade ? "⚠️ Hiperdensidade!" : undefined}
              />
              <MetricCard
                label="Pop. Estimada"
                value={metricas.populacao_estimada.toLocaleString("pt-BR")}
                icon={Bug}
                color="ocean"
              />
              <MetricCard
                label="Sobrevivência"
                value={metricas.taxa_sobrevivencia_fuzzy_pct.toFixed(1)}
                unit="%"
                icon={Activity}
                color={metricas.taxa_sobrevivencia_fuzzy_pct < 70 ? "red" : metricas.taxa_sobrevivencia_fuzzy_pct < 85 ? "amber" : "pond"}
              />
              <MetricCard
                label="Ração Acumulada"
                value={metricas.racao_acumulada_kg.toLocaleString("pt-BR")}
                unit="kg"
                icon={Utensils}
                color="shrimp"
              />
              <MetricCard
                label="FCA"
                value={metricas.fca_atual?.toFixed(3) || "—"}
                icon={BarChart3}
                color={
                  metricas.classificacao_fca === "ALTA_EFICIENCIA" ? "pond"
                    : metricas.classificacao_fca === "DESPERDICIO_INDICADO" ? "red"
                    : "amber"
                }
                subtitle={
                  metricas.classificacao_fca === "ALTA_EFICIENCIA" ? "Alta eficiência"
                    : metricas.classificacao_fca === "DESPERDICIO_INDICADO" ? "Desperdício indicado"
                    : metricas.classificacao_fca === "FAIXA_PADRAO" ? "Faixa padrão"
                    : undefined
                }
              />
              <MetricCard
                label="Ração Diária Sugerida"
                value={metricas.racao_diaria_sugerida_kg}
                unit="kg"
                icon={Zap}
                color="shrimp"
                subtitle={`Taxa Clifford: ${metricas.taxa_alimentar_clifford_pct}%`}
              />
              <MetricCard
                label="Custo Total"
                value={`R$ ${metricas.custo_operacional_total_rs.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`}
                icon={DollarSign}
                color="red"
              />
              <MetricCard
                label="Receita Estimada"
                value={`R$ ${metricas.receita_bruta_estimada_rs.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`}
                icon={DollarSign}
                color="pond"
              />
              <MetricCard
                label="Lucro Operacional"
                value={`R$ ${metricas.lucro_operacional_rs.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`}
                icon={TrendingUp}
                color={metricas.lucro_operacional_rs >= 0 ? "pond" : "red"}
                subtitle={metricas.margem_operacional_pct != null ? `Margem: ${metricas.margem_operacional_pct}%` : undefined}
              />
            </div>
          )}

          {activeTab === "metricas" && !metricas && (
            <div className="glass-card p-8 text-center">
              <BarChart3 className="w-10 h-10 text-[var(--text-muted)] mx-auto mb-3" />
              <p className="text-[var(--text-muted)]">Registre ao menos uma biometria para ver as métricas</p>
            </div>
          )}

          {/* Tab: Biometrias */}
          {activeTab === "biometrias" && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-[var(--text-primary)]">
                  Histórico de Biometrias
                  <span className="text-sm font-normal text-[var(--text-muted)] ml-2">
                    ({biometrias.length} registros)
                  </span>
                </h3>
                <button
                  onClick={() => setShowBioModal(true)}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-ocean-500/15 text-ocean-400 border border-ocean-500/25 text-sm font-medium hover:bg-ocean-500/25 transition-all"
                >
                  <Plus className="w-4 h-4" />
                  Nova
                </button>
              </div>

              {biometrias.length === 0 ? (
                <div className="glass-card p-8 text-center">
                  <Scale className="w-10 h-10 text-[var(--text-muted)] mx-auto mb-3" />
                  <p className="text-[var(--text-muted)]">Nenhuma biometria registrada ainda</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {[...biometrias].reverse().map((bio) => (
                    <div key={bio.id} className="glass-card p-4 flex flex-wrap items-center gap-x-6 gap-y-2">
                      <div className="flex items-center gap-2 min-w-[140px]">
                        <CalendarDays className="w-4 h-4 text-ocean-400" />
                        <span className="text-sm font-medium text-[var(--text-primary)]">{fmtDate(bio.data_medicao)}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Scale className="w-4 h-4 text-shrimp-400" />
                        <span className="text-sm text-[var(--text-primary)] font-bold tabular-nums">{bio.peso_medio_g} g</span>
                      </div>
                      {bio.ganho_medio_semanal_g != null && (
                        <div className="flex items-center gap-1">
                          {bio.ganho_medio_semanal_g > 0 ? (
                            <TrendingUp className="w-4 h-4 text-pond-400" />
                          ) : bio.ganho_medio_semanal_g < 0 ? (
                            <TrendingDown className="w-4 h-4 text-red-400" />
                          ) : (
                            <Minus className="w-4 h-4 text-[var(--text-muted)]" />
                          )}
                          <span className={`text-sm font-medium tabular-nums ${bio.ganho_medio_semanal_g > 0 ? "text-pond-400" : bio.ganho_medio_semanal_g < 0 ? "text-red-400" : "text-[var(--text-muted)]"}`}>
                            {bio.ganho_medio_semanal_g > 0 ? "+" : ""}{bio.ganho_medio_semanal_g} g/sem
                          </span>
                        </div>
                      )}
                      {bio.uniformidade_percentual != null && (
                        <span className="text-xs badge-info px-2 py-0.5 rounded-full font-medium">
                          {bio.uniformidade_percentual}% uniforme
                        </span>
                      )}
                      {bio.observacoes && (
                        <span className="text-xs text-[var(--text-muted)] italic">{bio.observacoes}</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab: Manejos */}
          {activeTab === "manejos" && (
            <div>
              {/* Recomendação atual */}
              {recomendacao && (
                <div className="glass-card p-4 mb-4 border-l-4 border-l-ocean-500">
                  <div className="flex items-center gap-2 mb-2">
                    <Zap className="w-4 h-4 text-ocean-400" />
                    <span className="text-sm font-bold text-ocean-400">Recomendação para próximo trato</span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-2">
                    <div>
                      <p className="text-xs text-[var(--text-muted)]">Ração sugerida</p>
                      <p className="text-lg font-bold text-[var(--text-primary)]">{recomendacao.racao_diaria_sugerida_kg} <span className="text-xs font-normal text-[var(--text-muted)]">kg</span></p>
                    </div>
                    <div>
                      <p className="text-xs text-[var(--text-muted)]">Taxa Clifford</p>
                      <p className="text-lg font-bold text-[var(--text-primary)]">{recomendacao.taxa_clifford_pct} <span className="text-xs font-normal text-[var(--text-muted)]">%</span></p>
                    </div>
                    <div>
                      <p className="text-xs text-[var(--text-muted)]">Biomassa est.</p>
                      <p className="text-lg font-bold text-[var(--text-primary)]">{recomendacao.biomassa_estimada_kg} <span className="text-xs font-normal text-[var(--text-muted)]">kg</span></p>
                    </div>
                  </div>
                  <p className="text-sm text-[var(--text-secondary)]">{recomendacao.ajuste_sugerido}</p>
                </div>
              )}

              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-[var(--text-primary)]">
                  Histórico de Manejos
                  <span className="text-sm font-normal text-[var(--text-muted)] ml-2">
                    ({manejos.length} registros)
                  </span>
                </h3>
                <button
                  onClick={() => setShowManejoModal(true)}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-shrimp-500/15 text-shrimp-400 border border-shrimp-500/25 text-sm font-medium hover:bg-shrimp-500/25 transition-all"
                >
                  <Plus className="w-4 h-4" />
                  Novo
                </button>
              </div>

              {manejos.length === 0 ? (
                <div className="glass-card p-8 text-center">
                  <Utensils className="w-10 h-10 text-[var(--text-muted)] mx-auto mb-3" />
                  <p className="text-[var(--text-muted)]">Nenhum manejo registrado ainda</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {[...manejos].reverse().map((m) => {
                    const sobraLabel = SOBRA_OPTIONS.find((o) => o.value === m.sobra_bandeja_nivel);
                    const statusColor =
                      m.status_alimentar_ajustado === "NORMAL" ? "badge-success"
                        : m.status_alimentar_ajustado === "SUB_ARRAC_SUSPEITO" ? "badge-warning"
                        : m.status_alimentar_ajustado === "SUPER_ARRAC_SUSPEITO" ? "badge-danger"
                        : "badge-info";
                    const statusLabel =
                      m.status_alimentar_ajustado === "NORMAL" ? "Normal"
                        : m.status_alimentar_ajustado === "SUB_ARRAC_SUSPEITO" ? "Sub-arraçoamento"
                        : m.status_alimentar_ajustado === "SUPER_ARRAC_SUSPEITO" ? "Super-arraçoamento"
                        : "—";

                    return (
                      <div key={m.id} className="glass-card p-4 flex flex-wrap items-center gap-x-6 gap-y-2">
                        <div className="flex items-center gap-2 min-w-[140px]">
                          <CalendarDays className="w-4 h-4 text-shrimp-400" />
                          <span className="text-sm font-medium text-[var(--text-primary)]">{fmtDate(m.data_registro)}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Utensils className="w-4 h-4 text-shrimp-400" />
                          <span className="text-sm text-[var(--text-primary)] font-bold tabular-nums">{m.quantidade_racao_kg} kg</span>
                        </div>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          m.sobra_bandeja_nivel === "SEM_SOBRA" ? "badge-success"
                            : m.sobra_bandeja_nivel === "SOBRA_LEVE" ? "badge-warning"
                            : m.sobra_bandeja_nivel === "SOBRA_MODERADA" ? "badge-warning"
                            : "badge-danger"
                        }`}>
                          {sobraLabel?.label || m.sobra_bandeja_nivel}
                        </span>
                        {m.status_alimentar_ajustado && (
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColor}`}>
                            {statusLabel}
                          </span>
                        )}
                        {m.taxa_sobrevivencia_estimada_fuzzy != null && (
                          <span className="text-xs text-[var(--text-muted)]">
                            Sobrev. fuzzy: <span className="font-medium text-[var(--text-secondary)]">{m.taxa_sobrevivencia_estimada_fuzzy.toFixed(1)}%</span>
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Modals */}
      <IniciarCicloModal
        open={showCicloModal}
        onClose={() => setShowCicloModal(false)}
        onCreated={loadData}
        viveiroId={viveiroId}
      />
      {cicloAtivo && (
        <>
          <BiometriaModal
            open={showBioModal}
            onClose={() => setShowBioModal(false)}
            onCreated={loadData}
            cicloId={cicloAtivo.id}
          />
          <ManejoModal
            open={showManejoModal}
            onClose={() => setShowManejoModal(false)}
            onCreated={loadData}
            cicloId={cicloAtivo.id}
            recomendacao={recomendacao}
          />
          <EncerrarCicloModal
            open={showEncerrarModal}
            onClose={() => setShowEncerrarModal(false)}
            onDone={loadData}
            cicloId={cicloAtivo.id}
          />
        </>
      )}
    </div>
  );
}
