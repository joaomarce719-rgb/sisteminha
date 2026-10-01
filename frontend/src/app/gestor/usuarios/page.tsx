"use client";

import { useEffect, useState } from "react";
import {
  Users,
  Plus,
  X,
  Loader2,
  AlertTriangle,
  Shield,
  Mail,
  Phone,
  CalendarDays,
  RefreshCw,
  Edit3,
  CheckCircle2,
  XCircle,
  UserCheck,
  UserX,
} from "lucide-react";
import { adminApi } from "@/lib/api";
import type { Usuario, RoleUsuario } from "@/lib/types";

const ROLE_CONFIG: Record<string, { label: string; color: string; bg: string; border: string }> = {
  GESTOR: { label: "Gestor", color: "#1aa0ff", bg: "rgba(0,136,230,0.15)", border: "rgba(0,136,230,0.3)" },
  CAMPO: { label: "Campo", color: "#28d280", bg: "rgba(16,185,129,0.15)", border: "rgba(16,185,129,0.3)" },
  VIGIA: { label: "Vigia", color: "#a78bfa", bg: "rgba(167,139,250,0.15)", border: "rgba(167,139,250,0.3)" },
};

function fmtDate(d: string) { return new Date(d).toLocaleDateString("pt-BR"); }

// ── Modal Criar Usuário ─────────────────────────────
function CriarUsuarioModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({ nome_completo: "", email: "", senha: "", papel: "CAMPO" as RoleUsuario, telefone_emergencia: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await adminApi.criarUsuario({
        nome_completo: form.nome_completo,
        email: form.email,
        senha: form.senha,
        papel: form.papel,
        telefone_emergencia: form.telefone_emergencia || null,
      });
      onCreated();
      onClose();
      setForm({ nome_completo: "", email: "", senha: "", papel: "CAMPO", telefone_emergencia: "" });
    } catch (err: any) { setError(err.message || "Erro"); } finally { setLoading(false); }
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass-card p-6 w-full max-w-md relative animate-in">
        <button onClick={onClose} className="absolute top-4 right-4 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"><X className="w-5 h-5" /></button>
        <h2 className="text-xl font-bold text-[var(--text-primary)] mb-1">Novo Usuário</h2>
        <p className="text-sm text-[var(--text-muted)] mb-6">Cadastrar operador no sistema</p>
        {error && <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm mb-4"><AlertTriangle className="w-4 h-4 shrink-0" />{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div><label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Nome Completo *</label><input required minLength={3} value={form.nome_completo} onChange={(e) => setForm({ ...form, nome_completo: e.target.value })} placeholder="João Silva" className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all" /></div>
          <div><label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Email *</label><input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="joao@fazenda.com" className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all" /></div>
          <div><label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Senha *</label><input required type="password" minLength={6} value={form.senha} onChange={(e) => setForm({ ...form, senha: e.target.value })} placeholder="Mínimo 6 caracteres" className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all" /></div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Perfil *</label>
            <div className="grid grid-cols-3 gap-2">
              {(["CAMPO", "VIGIA", "GESTOR"] as RoleUsuario[]).map((r) => {
                const cfg = ROLE_CONFIG[r];
                return (
                  <button key={r} type="button" onClick={() => setForm({ ...form, papel: r })}
                    className={`px-3 py-2.5 rounded-xl text-sm font-medium transition-all border ${form.papel === r ? "bg-ocean-500/15 border-ocean-500/30 text-ocean-400" : "bg-white/5 border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-white/8"}`}>
                    {cfg.label}
                  </button>
                );
              })}
            </div>
          </div>
          <div><label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">Telefone Emergência</label><input value={form.telefone_emergencia} onChange={(e) => setForm({ ...form, telefone_emergencia: e.target.value })} placeholder="(88) 99999-0000" className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all" /></div>
          <button type="submit" disabled={loading} className="w-full py-3 rounded-xl bg-gradient-to-r from-ocean-600 to-ocean-500 text-white font-semibold flex items-center justify-center gap-2 hover:from-ocean-500 hover:to-ocean-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-ocean-500/20 active:scale-[0.98]">
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <><Users className="w-5 h-5" /> Cadastrar</>}
          </button>
        </form>
      </div>
    </div>
  );
}

// ── Main Page ───────────────────────────────────────
export default function UsuariosPage() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [resetting, setResetting] = useState<string | null>(null);
  const [toggling, setToggling] = useState<string | null>(null);

  const loadUsers = async () => {
    setLoading(true);
    try { const data = await adminApi.listarUsuarios(); setUsuarios(data); } catch { } finally { setLoading(false); }
  };

  useEffect(() => { loadUsers(); }, []);

  const handleResetSenha = async (id: string) => {
    setResetting(id);
    try { await adminApi.resetarSenha(id); alert("Senha resetada para: mudar123"); } catch (err: any) { alert(err.message || "Erro"); } finally { setResetting(null); }
  };

  const handleToggleAtivo = async (user: Usuario) => {
    setToggling(user.id);
    try {
      await adminApi.atualizarUsuario(user.id, { ativo: !user.ativo });
      loadUsers();
    } catch (err: any) { alert(err.message || "Erro"); } finally { setToggling(null); }
  };

  if (loading) return <div className="flex items-center justify-center py-32"><Loader2 className="w-8 h-8 text-ocean-400 animate-spin" /></div>;

  const byRole = (role: string) => usuarios.filter((u) => u.papel === role);

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)]">Usuários</h1>
          <p className="text-[var(--text-secondary)] text-sm mt-1">Gestão de operadores (RBAC)</p>
        </div>
        <button onClick={() => setShowModal(true)} className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-ocean-600 to-ocean-500 text-white font-semibold text-sm hover:from-ocean-500 hover:to-ocean-400 transition-all shadow-lg shadow-ocean-500/20 active:scale-[0.98]">
          <Plus className="w-4 h-4" /> Novo Usuário
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        {(["GESTOR", "CAMPO", "VIGIA"] as const).map((role) => {
          const cfg = ROLE_CONFIG[role];
          const count = byRole(role).length;
          return (
            <div key={role} className="glass-card p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: cfg.bg, border: `1px solid ${cfg.border}` }}>
                <Shield className="w-5 h-5" style={{ color: cfg.color }} />
              </div>
              <div>
                <p className="text-2xl font-bold" style={{ color: cfg.color }}>{count}</p>
                <p className="text-xs text-[var(--text-muted)]">{cfg.label}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* User list */}
      {usuarios.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <Users className="w-12 h-12 text-[var(--text-muted)] mx-auto mb-4" />
          <p className="text-[var(--text-muted)]">Nenhum usuário cadastrado</p>
        </div>
      ) : (
        <div className="space-y-2">
          {usuarios.map((u) => {
            const cfg = ROLE_CONFIG[u.papel] || ROLE_CONFIG.CAMPO;
            return (
              <div key={u.id} className="glass-card p-4 flex flex-wrap items-center gap-x-5 gap-y-2">
                {/* Avatar */}
                <div className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm shrink-0" style={{ background: `linear-gradient(135deg, ${cfg.color}, ${cfg.color}99)` }}>
                  {u.nome_completo.charAt(0).toUpperCase()}
                </div>

                {/* Name & email */}
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-[var(--text-primary)] text-sm truncate">
                    {u.nome_completo}
                  </p>
                  <p className="text-xs text-[var(--text-muted)] flex items-center gap-1 truncate">
                    <Mail className="w-3 h-3" /> {u.email}
                  </p>
                </div>

                {/* Role badge */}
                <span className="text-xs px-2.5 py-1 rounded-full font-bold" style={{ background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}` }}>
                  <Shield className="w-3 h-3 inline mr-1" />{cfg.label}
                </span>

                {/* Status */}
                <button
                  onClick={() => handleToggleAtivo(u)}
                  disabled={toggling === u.id}
                  className={`text-xs px-2.5 py-1 rounded-full font-medium transition-all ${u.ativo ? "badge-success hover:bg-green-500/25" : "badge-danger hover:bg-red-500/25"}`}
                >
                  {toggling === u.id ? <Loader2 className="w-3 h-3 animate-spin inline" /> : u.ativo ? <><UserCheck className="w-3 h-3 inline mr-1" />Ativo</> : <><UserX className="w-3 h-3 inline mr-1" />Inativo</>}
                </button>

                {/* Phone */}
                {u.telefone_emergencia && (
                  <span className="text-xs text-[var(--text-muted)] flex items-center gap-1">
                    <Phone className="w-3 h-3" /> {u.telefone_emergencia}
                  </span>
                )}

                {/* Created at */}
                <span className="text-xs text-[var(--text-muted)]">{fmtDate(u.created_at)}</span>

                {/* Reset password */}
                <button
                  onClick={() => handleResetSenha(u.id)}
                  disabled={resetting === u.id}
                  className="text-xs px-2.5 py-1 rounded-lg bg-white/5 border border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-amber-400 hover:border-amber-500/30 hover:bg-amber-500/10 transition-all"
                >
                  {resetting === u.id ? <Loader2 className="w-3 h-3 animate-spin inline" /> : <><RefreshCw className="w-3 h-3 inline mr-1" />Reset senha</>}
                </button>
              </div>
            );
          })}
        </div>
      )}

      <CriarUsuarioModal open={showModal} onClose={() => setShowModal(false)} onCreated={loadUsers} />
    </div>
  );
}
