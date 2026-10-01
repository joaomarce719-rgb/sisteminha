"use client";

import { useEffect, useState } from "react";
import {
  DollarSign,
  Plus,
  X,
  Loader2,
  AlertTriangle,
  Shell,
  CalendarDays,
  BarChart3,
  TrendingUp,
  Tag,
} from "lucide-react";
import { ciclosApi, custosApi, precosApi, viveirosApi } from "@/lib/api";
import type { CicloProdutivo, Viveiro, CustoOperacional, CustoResumo, PrecoMercado } from "@/lib/types";

type Tab = "custos" | "precos";

const CATEGORIAS: Record<string, string> = {
  RACAO: "Ração",
  ENERGIA_ELETRICA: "Energia Elétrica",
  MAO_DE_OBRA: "Mão de Obra",
  POS_LARVAS: "Pós-Larvas",
  PROBIOTICOS_QUIMICOS: "Probióticos/Químicos",
  MANUTENCAO: "Manutenção",
  OUTROS: "Outros",
};

const CAT_COLORS: Record<string, string> = {
  RACAO: "#ff7d33",
  ENERGIA_ELETRICA: "#f59e0b",
  MAO_DE_OBRA: "#1aa0ff",
  POS_LARVAS: "#28d280",
  PROBIOTICOS_QUIMICOS: "#a78bfa",
  MANUTENCAO: "#64748b",
  OUTROS: "#94a3b8",
};

function fmtMoney(v: number) {
  return `R$ ${v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function fmtDate(d: string) {
  return new Date(d).toLocaleDateString("pt-BR");
}

// ── Modal Lançar Custo ──────────────────────────────
function CustoModal({ open, onClose, onCreated, cicloId }: { open: boolean; onClose: () => void; onCreated: () => void; cicloId: string }) {
  const [form, setForm] = useState({ data_lancamento: new Date().toISOString().split("T")[0], categoria: "RACAO", descricao: "", valor_rs: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await custosApi.criar(cicloId, {
        data_lancamento: form.data_lancamento,
        categoria: form.categoria,
        descricao: form.descricao,
        valor_rs: parseFloat(form.valor_rs),
      });
      onCreated();
      onClose();
      setForm({ data_lancamento: new Date().toISOString().split("T")[0], categoria: "RACAO", descricao: "", valor_rs: "" });
    } catch (err: any) { setError(err.message || "Erro"); } finally { setLoading(false); }
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass-card p-6 w-full max-w-md relative animate-in">
        <button onClick={onClose} className="absolute top-4 right-4 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"><X className="w-5 h-5" /></button>
        <h2 className="text-xl font-bold text-[var(--text-primary)] mb-1">Lançar Custo</h2>
        <p className="text-sm text-[var(--text-muted)] mb-6">Registre uma despesa operacional</p>
        {error && <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm mb-4"><AlertTriangle className="w-4 h-4 shrink-0" />{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div><label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Data *</label><input required type="date" value={form.data_lancamento} onChange={(e) => setForm({ ...form, data_lancamento: e.target.value })} className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all" /></div>
          <div><label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Categoria *</label>
            <select value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })} className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-ocean-500 transition-all appearance-none">
              {Object.entries(CATEGORIAS).map(([k, v]) => <option key={k} value={k} className="bg-[var(--bg-secondary)]">{v}</option>)}
            </select>
          </div>
          <div><label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Descrição *</label><input required minLength={3} value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} placeholder="Ex: Compra de ração mês 2" className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all" /></div>
          <div><label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Valor (R$) *</label><input required type="number" step="0.01" min="0.01" inputMode="decimal" value={form.valor_rs} onChange={(e) => setForm({ ...form, valor_rs: e.target.value })} placeholder="1500.00" className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all" /></div>
          <button type="submit" disabled={loading} className="w-full py-3 rounded-xl bg-gradient-to-r from-ocean-600 to-ocean-500 text-white font-semibold flex items-center justify-center gap-2 hover:from-ocean-500 hover:to-ocean-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-ocean-500/20 active:scale-[0.98]">
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><DollarSign className="w-5 h-5" /> Lançar Custo</>}
          </button>
        </form>
      </div>
    </div>
  );
}

// ── Modal Preço de Mercado ──────────────────────────
function PrecoModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({ faixa_gramatura_min: "", faixa_gramatura_max: "", preco_por_kg: "", vigencia_inicio: new Date().toISOString().split("T")[0], vigencia_fim: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await precosApi.criar({
        faixa_gramatura_min: parseFloat(form.faixa_gramatura_min),
        faixa_gramatura_max: parseFloat(form.faixa_gramatura_max),
        preco_por_kg: parseFloat(form.preco_por_kg),
        vigencia_inicio: form.vigencia_inicio,
        vigencia_fim: form.vigencia_fim || null,
      });
      onCreated();
      onClose();
      setForm({ faixa_gramatura_min: "", faixa_gramatura_max: "", preco_por_kg: "", vigencia_inicio: new Date().toISOString().split("T")[0], vigencia_fim: "" });
    } catch (err: any) { setError(err.message || "Erro"); } finally { setLoading(false); }
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass-card p-6 w-full max-w-md relative animate-in">
        <button onClick={onClose} className="absolute top-4 right-4 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"><X className="w-5 h-5" /></button>
        <h2 className="text-xl font-bold text-[var(--text-primary)] mb-1">Novo Preço de Mercado</h2>
        <p className="text-sm text-[var(--text-muted)] mb-6">Cadastre uma faixa de preço por gramatura</p>
        {error && <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm mb-4"><AlertTriangle className="w-4 h-4 shrink-0" />{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div><label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Gramatura mín (g) *</label><input required type="number" step="0.1" min="0" inputMode="decimal" value={form.faixa_gramatura_min} onChange={(e) => setForm({ ...form, faixa_gramatura_min: e.target.value })} placeholder="8" className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all" /></div>
            <div><label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Gramatura máx (g) *</label><input required type="number" step="0.1" min="0" inputMode="decimal" value={form.faixa_gramatura_max} onChange={(e) => setForm({ ...form, faixa_gramatura_max: e.target.value })} placeholder="12" className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all" /></div>
          </div>
          <div><label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Preço por kg (R$) *</label><input required type="number" step="0.01" min="0.01" inputMode="decimal" value={form.preco_por_kg} onChange={(e) => setForm({ ...form, preco_por_kg: e.target.value })} placeholder="28.00" className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all" /></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Vigência início *</label><input required type="date" value={form.vigencia_inicio} onChange={(e) => setForm({ ...form, vigencia_inicio: e.target.value })} className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-ocean-500 transition-all" /></div>
            <div><label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Vigência fim</label><input type="date" value={form.vigencia_fim} onChange={(e) => setForm({ ...form, vigencia_fim: e.target.value })} className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-ocean-500 transition-all" /></div>
          </div>
          <button type="submit" disabled={loading} className="w-full py-3 rounded-xl bg-gradient-to-r from-pond-600 to-pond-500 text-white font-semibold flex items-center justify-center gap-2 hover:from-pond-500 hover:to-pond-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-pond-500/20 active:scale-[0.98]">
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><Tag className="w-5 h-5" /> Cadastrar Preço</>}
          </button>
        </form>
      </div>
    </div>
  );
}

// ── Main Page ───────────────────────────────────────
export default function FinanceiroPage() {
  const [tab, setTab] = useState<Tab>("custos");
  const [viveiros, setViveiros] = useState<Viveiro[]>([]);
  const [ciclos, setCiclos] = useState<CicloProdutivo[]>([]);
  const [selectedCiclo, setSelectedCiclo] = useState("");
  const [custos, setCustos] = useState<CustoOperacional[]>([]);
  const [resumo, setResumo] = useState<CustoResumo[]>([]);
  const [precos, setPrecos] = useState<PrecoMercado[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCustoModal, setShowCustoModal] = useState(false);
  const [showPrecoModal, setShowPrecoModal] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [vivs, cycs, prcs] = await Promise.all([
          viveirosApi.listar(),
          ciclosApi.listar({ status_filtro: "ATIVO" }),
          precosApi.listar(),
        ]);
        setViveiros(vivs);
        setCiclos(cycs);
        setPrecos(prcs);
        if (cycs.length > 0) setSelectedCiclo(cycs[0].id);
      } catch { } finally { setLoading(false); }
    }
    load();
  }, []);

  useEffect(() => {
    if (!selectedCiclo) return;
    async function loadCustos() {
      try {
        const [cs, rs] = await Promise.all([
          custosApi.listar(selectedCiclo),
          custosApi.resumo(selectedCiclo),
        ]);
        setCustos(cs);
        setResumo(rs);
      } catch { }
    }
    loadCustos();
  }, [selectedCiclo]);

  const refreshCustos = async () => {
    if (!selectedCiclo) return;
    const [cs, rs] = await Promise.all([
      custosApi.listar(selectedCiclo),
      custosApi.resumo(selectedCiclo),
    ]);
    setCustos(cs);
    setResumo(rs);
  };

  const refreshPrecos = async () => {
    const prcs = await precosApi.listar();
    setPrecos(prcs);
  };

  const getViveiroName = (vId: string) => viveiros.find((v) => v.id === vId)?.identificacao || "—";
  const totalCustos = resumo.reduce((sum, r) => sum + r.total_rs, 0);

  if (loading) return <div className="flex items-center justify-center py-32"><Loader2 className="w-8 h-8 text-ocean-400 animate-spin" /></div>;

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)]">Financeiro</h1>
        <p className="text-[var(--text-secondary)] text-sm mt-1">Custos operacionais e tabela de preços de mercado</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-white/5 p-1 rounded-xl border border-[var(--border-subtle)] w-fit">
        {[
          { key: "custos" as Tab, label: "Custos", icon: DollarSign },
          { key: "precos" as Tab, label: "Preços de Mercado", icon: Tag },
        ].map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${tab === t.key ? "bg-ocean-500/15 text-ocean-400" : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]"}`}>
            <t.icon className="w-4 h-4" /> {t.label}
          </button>
        ))}
      </div>

      {/* Custos Tab */}
      {tab === "custos" && (
        <>
          {ciclos.length === 0 ? (
            <div className="glass-card p-12 text-center">
              <Shell className="w-12 h-12 text-[var(--text-muted)] mx-auto mb-4" />
              <p className="text-[var(--text-muted)]">Nenhum ciclo ativo para lançar custos</p>
            </div>
          ) : (
            <>
              <div className="flex flex-col sm:flex-row gap-4 items-end mb-6">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Ciclo</label>
                  <select value={selectedCiclo} onChange={(e) => setSelectedCiclo(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-ocean-500 transition-all appearance-none">
                    {ciclos.map((c) => <option key={c.id} value={c.id} className="bg-[var(--bg-secondary)]">{getViveiroName(c.viveiro_id)} — {fmtDate(c.data_povoamento)}</option>)}
                  </select>
                </div>
                <button onClick={() => setShowCustoModal(true)} className="flex items-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-ocean-600 to-ocean-500 text-white font-semibold text-sm hover:from-ocean-500 hover:to-ocean-400 transition-all shadow-lg shadow-ocean-500/20 active:scale-[0.98]">
                  <Plus className="w-4 h-4" /> Lançar Custo
                </button>
              </div>

              {/* Resumo por categoria */}
              {resumo.length > 0 && (
                <div className="glass-card p-5 mb-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-base font-bold text-[var(--text-primary)]">Resumo por Categoria</h3>
                    <p className="text-lg font-bold text-red-400">{fmtMoney(totalCustos)}</p>
                  </div>
                  <div className="space-y-2">
                    {resumo.sort((a, b) => b.total_rs - a.total_rs).map((r) => {
                      const pct = totalCustos > 0 ? (r.total_rs / totalCustos) * 100 : 0;
                      return (
                        <div key={r.categoria}>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="text-[var(--text-secondary)]">{CATEGORIAS[r.categoria] || r.categoria}</span>
                            <span className="text-[var(--text-primary)] font-semibold tabular-nums">{fmtMoney(r.total_rs)} <span className="text-[var(--text-muted)] text-xs">({r.qtd_lancamentos}x)</span></span>
                          </div>
                          <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                            <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: CAT_COLORS[r.categoria] || "#94a3b8" }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Lista de custos */}
              {custos.length === 0 ? (
                <div className="glass-card p-8 text-center">
                  <DollarSign className="w-10 h-10 text-[var(--text-muted)] mx-auto mb-3" />
                  <p className="text-[var(--text-muted)]">Nenhum custo lançado neste ciclo</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {[...custos].reverse().map((c) => (
                    <div key={c.id} className="glass-card p-4 flex flex-wrap items-center gap-x-6 gap-y-2">
                      <div className="flex items-center gap-2 min-w-[120px]">
                        <CalendarDays className="w-4 h-4 text-[var(--text-muted)]" />
                        <span className="text-sm text-[var(--text-primary)]">{fmtDate(c.data_lancamento)}</span>
                      </div>
                      <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={{ background: `${CAT_COLORS[c.categoria] || "#94a3b8"}20`, color: CAT_COLORS[c.categoria] || "#94a3b8", border: `1px solid ${CAT_COLORS[c.categoria] || "#94a3b8"}40` }}>
                        {CATEGORIAS[c.categoria] || c.categoria}
                      </span>
                      <span className="text-sm text-[var(--text-secondary)] flex-1 min-w-0 truncate">{c.descricao}</span>
                      <span className="text-sm font-bold text-red-400 tabular-nums">{fmtMoney(c.valor_rs)}</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </>
      )}

      {/* Preços Tab */}
      {tab === "precos" && (
        <>
          <div className="flex justify-end mb-4">
            <button onClick={() => setShowPrecoModal(true)} className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-pond-600 to-pond-500 text-white font-semibold text-sm hover:from-pond-500 hover:to-pond-400 transition-all shadow-lg shadow-pond-500/20 active:scale-[0.98]">
              <Plus className="w-4 h-4" /> Novo Preço
            </button>
          </div>

          {precos.length === 0 ? (
            <div className="glass-card p-8 text-center">
              <Tag className="w-10 h-10 text-[var(--text-muted)] mx-auto mb-3" />
              <p className="text-[var(--text-muted)]">Nenhum preço cadastrado</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {precos.map((p) => (
                <div key={p.id} className="glass-card p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <Tag className="w-5 h-5 text-pond-400" />
                    <span className="text-sm font-bold text-[var(--text-primary)]">
                      {p.faixa_gramatura_min}g – {p.faixa_gramatura_max}g
                    </span>
                  </div>
                  <p className="text-2xl font-bold text-pond-400 tabular-nums mb-2">
                    {fmtMoney(p.preco_por_kg)} <span className="text-sm font-normal text-[var(--text-muted)]">/kg</span>
                  </p>
                  <div className="text-xs text-[var(--text-muted)]">
                    Vigência: {fmtDate(p.vigencia_inicio)}
                    {p.vigencia_fim ? ` — ${fmtDate(p.vigencia_fim)}` : " — Indeterminado"}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {selectedCiclo && <CustoModal open={showCustoModal} onClose={() => setShowCustoModal(false)} onCreated={refreshCustos} cicloId={selectedCiclo} />}
      <PrecoModal open={showPrecoModal} onClose={() => setShowPrecoModal(false)} onCreated={refreshPrecos} />
    </div>
  );
}
