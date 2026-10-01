"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Shell,
  Plus,
  MapPin,
  Ruler,
  Droplets,
  Activity,
  AlertTriangle,
  X,
  Loader2,
  Search,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";
import { viveirosApi, ciclosApi } from "@/lib/api";
import type { Viveiro, CicloProdutivo } from "@/lib/types";

// ── Modal de Criar Viveiro ──────────────────────────
function CriarViveiroModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState({
    identificacao: "",
    area_util_m2: "",
    profundidade_media_m: "",
    localizacao: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await viveirosApi.criar({
        identificacao: form.identificacao,
        area_util_m2: parseFloat(form.area_util_m2),
        profundidade_media_m: form.profundidade_media_m
          ? parseFloat(form.profundidade_media_m)
          : null,
        localizacao: form.localizacao || null,
      });
      onCreated();
      onClose();
      setForm({ identificacao: "", area_util_m2: "", profundidade_media_m: "", localizacao: "" });
    } catch (err: any) {
      setError(err.message || "Erro ao criar viveiro");
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass-card p-6 w-full max-w-md relative animate-in">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <h2 className="text-xl font-bold text-[var(--text-primary)] mb-1">
          Novo Viveiro
        </h2>
        <p className="text-sm text-[var(--text-muted)] mb-6">
          Cadastre um novo viveiro na fazenda
        </p>

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm mb-4">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
              Identificação *
            </label>
            <input
              required
              value={form.identificacao}
              onChange={(e) => setForm({ ...form, identificacao: e.target.value })}
              placeholder="Ex: V-01, Viveiro Norte..."
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
                Área útil (m²) *
              </label>
              <input
                required
                type="number"
                step="0.01"
                min="0.01"
                inputMode="decimal"
                value={form.area_util_m2}
                onChange={(e) => setForm({ ...form, area_util_m2: e.target.value })}
                placeholder="10000"
                className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
                Profundidade (m)
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                inputMode="decimal"
                value={form.profundidade_media_m}
                onChange={(e) =>
                  setForm({ ...form, profundidade_media_m: e.target.value })
                }
                placeholder="1.2"
                className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
              Localização
            </label>
            <input
              value={form.localizacao}
              onChange={(e) => setForm({ ...form, localizacao: e.target.value })}
              placeholder="Setor leste, coordenadas..."
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-ocean-600 to-ocean-500 text-white font-semibold flex items-center justify-center gap-2 hover:from-ocean-500 hover:to-ocean-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-ocean-500/20 active:scale-[0.98]"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <Plus className="w-5 h-5" />
                Cadastrar Viveiro
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

// ── Componente de Card de Viveiro ────────────────────
function ViveiroCard({
  viveiro,
  cicloAtivo,
}: {
  viveiro: Viveiro;
  cicloAtivo?: CicloProdutivo | null;
}) {
  const diasCultivo = cicloAtivo
    ? Math.floor(
        (new Date().getTime() - new Date(cicloAtivo.data_povoamento).getTime()) /
          (1000 * 60 * 60 * 24)
      )
    : null;

  return (
    <Link href={`/gestor/viveiros/${viveiro.id}`}>
      <div className="glass-card glass-card-hover p-5 cursor-pointer transition-all duration-300 h-full flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div
              className={`w-11 h-11 rounded-xl flex items-center justify-center ${
                viveiro.status_ativo
                  ? "bg-gradient-to-br from-ocean-500/20 to-pond-500/20 border border-ocean-500/30"
                  : "bg-white/5 border border-[var(--border-subtle)]"
              }`}
            >
              <Shell
                className={`w-5 h-5 ${
                  viveiro.status_ativo ? "text-ocean-400" : "text-[var(--text-muted)]"
                }`}
              />
            </div>
            <div>
              <h3 className="font-bold text-[var(--text-primary)] text-base">
                {viveiro.identificacao}
              </h3>
              <span
                className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  viveiro.status_ativo ? "badge-success" : "badge-danger"
                }`}
              >
                {viveiro.status_ativo ? "Ativo" : "Inativo"}
              </span>
            </div>
          </div>
        </div>

        {/* Info */}
        <div className="space-y-2.5 flex-1">
          <div className="flex items-center gap-2 text-sm">
            <Ruler className="w-4 h-4 text-[var(--text-muted)]" />
            <span className="text-[var(--text-secondary)]">
              {viveiro.area_util_m2.toLocaleString("pt-BR")} m²
            </span>
          </div>

          {viveiro.profundidade_media_m && (
            <div className="flex items-center gap-2 text-sm">
              <Droplets className="w-4 h-4 text-[var(--text-muted)]" />
              <span className="text-[var(--text-secondary)]">
                {viveiro.profundidade_media_m} m de profundidade
              </span>
            </div>
          )}

          {viveiro.localizacao && (
            <div className="flex items-center gap-2 text-sm">
              <MapPin className="w-4 h-4 text-[var(--text-muted)]" />
              <span className="text-[var(--text-secondary)] truncate">
                {viveiro.localizacao}
              </span>
            </div>
          )}
        </div>

        {/* Ciclo ativo badge */}
        <div className="mt-4 pt-3 border-t border-[var(--border-subtle)]">
          {cicloAtivo ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-pond-400" />
                <span className="text-sm font-medium text-pond-400">Ciclo ativo</span>
              </div>
              <span className="text-xs text-[var(--text-muted)] font-medium tabular-nums">
                {diasCultivo} dias
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[var(--text-muted)]" />
              <span className="text-sm text-[var(--text-muted)]">Sem ciclo ativo</span>
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}

// ── Página Principal ────────────────────────────────
export default function ViveirosPage() {
  const [viveiros, setViveiros] = useState<Viveiro[]>([]);
  const [ciclos, setCiclos] = useState<CicloProdutivo[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [filterAtivo, setFilterAtivo] = useState<boolean | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [vivs, cycs] = await Promise.all([
        viveirosApi.listar(),
        ciclosApi.listar({ status_filtro: "ATIVO" }),
      ]);
      setViveiros(vivs);
      setCiclos(cycs);
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const getCicloAtivo = (viveiroId: string) =>
    ciclos.find((c) => c.viveiro_id === viveiroId) || null;

  const filteredViveiros = viveiros.filter((v) => {
    const matchSearch =
      !search ||
      v.identificacao.toLowerCase().includes(search.toLowerCase()) ||
      (v.localizacao && v.localizacao.toLowerCase().includes(search.toLowerCase()));
    const matchFilter =
      filterAtivo === null || v.status_ativo === filterAtivo;
    return matchSearch && matchFilter;
  });

  const totalAtivos = viveiros.filter((v) => v.status_ativo).length;
  const totalComCiclo = viveiros.filter((v) => getCicloAtivo(v.id)).length;

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)]">
            Viveiros & Ciclos
          </h1>
          <p className="text-[var(--text-secondary)] text-sm mt-1">
            Gerencie seus viveiros e acompanhe os ciclos produtivos
          </p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-ocean-600 to-ocean-500 text-white font-semibold text-sm hover:from-ocean-500 hover:to-ocean-400 transition-all shadow-lg shadow-ocean-500/20 active:scale-[0.98]"
        >
          <Plus className="w-4 h-4" />
          Novo Viveiro
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {[
          { label: "Total Viveiros", value: viveiros.length, color: "ocean" },
          { label: "Ativos", value: totalAtivos, color: "pond" },
          { label: "Com Ciclo", value: totalComCiclo, color: "shrimp" },
          { label: "Sem Ciclo", value: totalAtivos - totalComCiclo, color: "ocean" },
        ].map((s) => (
          <div key={s.label} className="glass-card p-4">
            <p className="text-xs text-[var(--text-muted)] font-medium uppercase tracking-wider">
              {s.label}
            </p>
            <p
              className={`text-2xl font-bold mt-1 text-${s.color}-400`}
              style={{
                color:
                  s.color === "ocean"
                    ? "#1aa0ff"
                    : s.color === "pond"
                    ? "#28d280"
                    : "#ff7d33",
              }}
            >
              {s.value}
            </p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar viveiro..."
            className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all text-sm"
          />
        </div>
        <div className="flex gap-2">
          {[
            { label: "Todos", value: null },
            { label: "Ativos", value: true },
            { label: "Inativos", value: false },
          ].map((f) => (
            <button
              key={String(f.value)}
              onClick={() => setFilterAtivo(f.value)}
              className={`px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                filterAtivo === f.value
                  ? "bg-ocean-500/15 text-ocean-400 border border-ocean-500/25"
                  : "bg-white/5 text-[var(--text-secondary)] border border-[var(--border-subtle)] hover:bg-white/8"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-ocean-400 animate-spin" />
        </div>
      ) : filteredViveiros.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <Shell className="w-12 h-12 text-[var(--text-muted)] mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
            {viveiros.length === 0
              ? "Nenhum viveiro cadastrado"
              : "Nenhum viveiro encontrado"}
          </h3>
          <p className="text-sm text-[var(--text-muted)] mb-6">
            {viveiros.length === 0
              ? "Cadastre seu primeiro viveiro para começar"
              : "Tente ajustar os filtros de busca"}
          </p>
          {viveiros.length === 0 && (
            <button
              onClick={() => setModalOpen(true)}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-ocean-600 to-ocean-500 text-white font-semibold text-sm hover:from-ocean-500 hover:to-ocean-400 transition-all"
            >
              <Plus className="w-4 h-4" />
              Novo Viveiro
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredViveiros.map((v) => (
            <ViveiroCard
              key={v.id}
              viveiro={v}
              cicloAtivo={getCicloAtivo(v.id)}
            />
          ))}
        </div>
      )}

      <CriarViveiroModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreated={loadData}
      />
    </div>
  );
}
