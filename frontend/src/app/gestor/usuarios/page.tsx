"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Users,
  Plus,
  Loader2,
  AlertTriangle,
  Shield,
  Mail,
  Phone,
  RefreshCw,
  UserCheck,
  UserX,
  Lock,
  Search,
  ExternalLink,
  Building2,
} from "lucide-react";
import { adminApi } from "@/lib/api";
import type { Usuario, RoleUsuario } from "@/lib/types";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MetricCard } from "@/components/ui/metric-card";
import { toast } from "@/components/ui/toast";

const ROLE_CONFIG: Record<
  string,
  { label: string; badgeVariant: "success" | "warning"; colorText: string }
> = {
  CAMPO: { label: "Operador Campo", badgeVariant: "success", colorText: "text-emerald-700" },
  VIGIA: { label: "Vigia Noturno", badgeVariant: "warning", colorText: "text-amber-700" },
};

function fmtDate(d: string) {
  try {
    return new Date(d).toLocaleDateString("pt-BR");
  } catch {
    return "-";
  }
}

// ── Modal Criar Usuário Normal (Método 1 da Fazenda) ─
function CriarColaboradorDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState({
    nome_completo: "",
    email: "",
    senha: "",
    papel: "CAMPO" as "CAMPO" | "VIGIA",
    telefone_emergencia: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await adminApi.criarOperador({
        nome_completo: form.nome_completo.trim(),
        email: form.email.trim(),
        senha: form.senha,
        papel: form.papel,
        telefone_emergencia: form.telefone_emergencia.trim() || null,
      });
      toast.success(
        "Colaborador cadastrado com sucesso!",
        `${form.nome_completo} agora tem acesso ao módulo de ${form.papel === "CAMPO" ? "Manejo/Trato" : "Ronda Noturna"}.`
      );
      onCreated();
      onClose();
      setForm({
        nome_completo: "",
        email: "",
        senha: "",
        papel: "CAMPO",
        telefone_emergencia: "",
      });
    } catch (err: any) {
      const msg = err.message || "Erro ao cadastrar operador";
      setError(msg);
      toast.error("Falha no cadastro", msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Cadastrar Novo Colaborador de Campo"
      description="Cadastre operadores de manejo ou vigias noturnos para a operação da fazenda"
    >
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-xs font-medium mb-4">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Label htmlFor="nome_completo">Nome Completo do Colaborador *</Label>
          <Input
            id="nome_completo"
            required
            minLength={3}
            value={form.nome_completo}
            onChange={(e) => setForm({ ...form, nome_completo: e.target.value })}
            placeholder="Ex: José dos Santos"
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor="email_user">E-mail Corporativo *</Label>
          <Input
            id="email_user"
            required
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="Ex: jose.campo@fazenda.com"
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor="senha_user">Senha Provisória *</Label>
          <Input
            id="senha_user"
            required
            type="password"
            minLength={6}
            value={form.senha}
            onChange={(e) => setForm({ ...form, senha: e.target.value })}
            placeholder="Mínimo 6 caracteres"
            className="mt-1"
          />
        </div>

        <div>
          <Label>Função Operacional (RBAC da Fazenda) *</Label>
          <div className="grid grid-cols-2 gap-3 mt-1.5">
            {(["CAMPO", "VIGIA"] as const).map((r) => {
              const cfg = ROLE_CONFIG[r];
              const isSelected = form.papel === r;
              return (
                <button
                  key={r}
                  type="button"
                  onClick={() => setForm({ ...form, papel: r })}
                  className={`p-3 rounded-2xl text-center border text-xs font-bold transition-all flex flex-col items-center gap-1 ${
                    isSelected
                      ? "bg-slate-900 border-slate-900 text-white shadow-sm"
                      : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <span>{cfg.label}</span>
                  <span
                    className={`text-[10px] font-normal ${
                      isSelected ? "text-slate-300" : "text-slate-400"
                    }`}
                  >
                    {r === "CAMPO" ? "Manejo alimentar e biometrias" : "Rondas noturnas e O₂"}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <Label htmlFor="tel_emergencia">Telefone / WhatsApp</Label>
          <Input
            id="tel_emergencia"
            value={form.telefone_emergencia}
            onChange={(e) => setForm({ ...form, telefone_emergencia: e.target.value })}
            placeholder="Ex: (88) 99876-5432"
            className="mt-1"
          />
        </div>

        <div className="pt-2 flex gap-3">
          <Button type="button" variant="outline" onClick={onClose} className="flex-1">
            Cancelar
          </Button>
          <Button
            type="submit"
            disabled={loading}
            className="flex-1 bg-slate-900 hover:bg-slate-800 text-white font-semibold"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <Users className="w-4 h-4 mr-2" />
            )}
            Cadastrar Operador
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

// ── Página Principal: Gestão de Operadores da Fazenda ─
export default function OperadoresPage() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [resetting, setResetting] = useState<string | null>(null);
  const [toggling, setToggling] = useState<string | null>(null);
  const [filtroRole, setFiltroRole] = useState<string>("TODOS");
  const [busca, setBusca] = useState<string>("");

  const loadUsers = async () => {
    setLoading(true);
    try {
      const data = await adminApi.listarOperadores();
      setUsuarios(data || []);
    } catch (err: any) {
      toast.error("Erro ao listar operadores", err.message || "Tente novamente");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleResetSenha = async (id: string, nome: string) => {
    setResetting(id);
    try {
      await adminApi.resetarSenha(id);
      toast.success(
        "Senha redefinida com sucesso!",
        `A nova senha provisória de ${nome} agora é: mudar123`
      );
    } catch (err: any) {
      toast.error("Falha ao resetar senha", err.message || "Tente novamente");
    } finally {
      setResetting(null);
    }
  };

  const handleToggleAtivo = async (user: Usuario) => {
    setToggling(user.id);
    try {
      await adminApi.atualizarUsuario(user.id, { ativo: !user.ativo });
      toast.info(
        `Usuário ${user.ativo ? "bloqueado" : "reativado"}`,
        `${user.nome_completo} agora está ${user.ativo ? "inativo no sistema" : "ativo no sistema"}.`
      );
      loadUsers();
    } catch (err: any) {
      toast.error("Erro ao alterar status", err.message || "Tente novamente");
    } finally {
      setToggling(null);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-32 bg-white rounded-3xl border border-slate-200">
        <Loader2 className="w-8 h-8 text-sky-600 animate-spin mb-2" />
        <p className="text-xs text-slate-400 font-medium">Carregando operadores da fazenda...</p>
      </div>
    );
  }

  const operadoresCampo = usuarios.filter((u) => u.papel === "CAMPO");
  const vigiasNoturnos = usuarios.filter((u) => u.papel === "VIGIA");
  const usuariosAtivos = usuarios.filter((u) => u.ativo);

  const usuariosFiltrados = usuarios.filter((u) => {
    const matchRole =
      filtroRole === "TODOS"
        ? true
        : filtroRole === "BLOQUEADOS"
        ? !u.ativo
        : u.papel === filtroRole;
    const matchBusca =
      busca.trim() === ""
        ? true
        : u.nome_completo.toLowerCase().includes(busca.toLowerCase()) ||
          u.email.toLowerCase().includes(busca.toLowerCase());
    return matchRole && matchBusca;
  });

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header da Tela */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-sky-700 mb-1">
            <Users className="w-4 h-4" />
            Operação de Campo • Gestão de Equipe
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Operadores & Vigias da Fazenda
          </h1>
          <p className="text-slate-500 text-sm mt-0.5">
            Cadastro de colaboradores operacionais para biometrias, alimentação e rondas
          </p>
        </div>

        <Button
          onClick={() => setShowModal(true)}
          className="bg-slate-900 hover:bg-slate-800 text-white font-semibold shadow-md shadow-slate-900/10 text-xs"
        >
          <Plus className="w-4 h-4 mr-1.5" />
          Novo Colaborador
        </Button>
      </div>

      {/* Métricas por Função Operacional */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard
          title="Operadores de Campo"
          value={operadoresCampo.length}
          subtitle="Manejo e biometrias"
          icon={Users}
          accent="emerald"
        />
        <MetricCard
          title="Vigias Noturnos"
          value={vigiasNoturnos.length}
          subtitle="Telemetria e aeração O₂"
          icon={Lock}
          accent="amber"
        />
        <MetricCard
          title="Colaboradores Ativos"
          value={usuariosAtivos.length}
          subtitle={`${usuarios.length} operadores no total`}
          icon={UserCheck}
          accent="ocean"
        />
      </div>

      {/* Tabela de Operadores */}
      <div className="bg-white rounded-3xl border border-slate-200/80 shadow-sm overflow-hidden">
        {/* Barra de Filtros e Busca */}
        <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <Input
              placeholder="Buscar operador por nome ou e-mail..."
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="pl-9 text-xs"
            />
          </div>

          <div className="flex items-center gap-1.5">
            {["TODOS", "CAMPO", "VIGIA", "BLOQUEADOS"].map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFiltroRole(f)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  filtroRole === f
                    ? "bg-slate-900 text-white"
                    : "bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-200"
                }`}
              >
                {f === "TODOS"
                  ? "Todos"
                  : f === "CAMPO"
                  ? "Campo"
                  : f === "VIGIA"
                  ? "Vigias"
                  : "Bloqueados"}
              </button>
            ))}
          </div>
        </div>

        {usuariosFiltrados.length === 0 ? (
          <div className="p-12 text-center">
            <Users className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-bold text-slate-900 mb-1">
              Nenhum colaborador encontrado
            </h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mb-4">
              Cadastre operadores de campo e vigias para liberar o acesso mobile de manejo.
            </p>
            <Button onClick={() => setShowModal(true)} className="bg-slate-900 text-white text-xs">
              <Plus className="w-3.5 h-3.5 mr-1.5" />
              Cadastrar Colaborador
            </Button>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {usuariosFiltrados.map((u) => {
              const cfg = ROLE_CONFIG[u.papel] || ROLE_CONFIG.CAMPO;
              return (
                <div
                  key={u.id}
                  className="p-4 flex flex-wrap items-center justify-between gap-4 hover:bg-slate-50/60 transition-colors"
                >
                  {/* Avatar & Informações */}
                  <div className="flex items-center gap-3.5 min-w-[240px]">
                    <div className="w-10 h-10 rounded-xl bg-slate-900 text-white font-bold text-sm flex items-center justify-center shrink-0 shadow-sm">
                      {u.nome_completo.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <div className="font-bold text-slate-900 text-sm">
                        {u.nome_completo}
                      </div>
                      <div className="text-xs text-slate-500 flex items-center gap-1.5 mt-0.5">
                        <Mail className="w-3 h-3 text-slate-400" />
                        <span>{u.email}</span>
                      </div>
                    </div>
                  </div>

                  {/* Papel Operacional */}
                  <Badge variant={cfg.badgeVariant}>
                    <Users className="w-3 h-3 mr-1" />
                    {cfg.label}
                  </Badge>

                  {/* Status Ativo / Bloqueado */}
                  <button
                    onClick={() => handleToggleAtivo(u)}
                    disabled={toggling === u.id}
                    title="Clique para alternar status do operador"
                    className="transition-transform active:scale-95"
                  >
                    <Badge variant={u.ativo ? "success" : "destructive"}>
                      {toggling === u.id ? (
                        <Loader2 className="w-3 h-3 animate-spin mr-1" />
                      ) : u.ativo ? (
                        <UserCheck className="w-3 h-3 mr-1" />
                      ) : (
                        <UserX className="w-3 h-3 mr-1" />
                      )}
                      {u.ativo ? "Ativo" : "Bloqueado"}
                    </Badge>
                  </button>

                  {/* Telefone */}
                  <div className="text-xs text-slate-500 hidden md:flex items-center gap-1">
                    {u.telefone_emergencia ? (
                      <>
                        <Phone className="w-3 h-3 text-slate-400" />
                        <span>{u.telefone_emergencia}</span>
                      </>
                    ) : (
                      <span className="text-slate-300">Sem telefone</span>
                    )}
                  </div>

                  {/* Data de Registro */}
                  <div className="text-xs text-slate-400 hidden lg:block">
                    Desde {fmtDate(u.created_at)}
                  </div>

                  {/* Resetar Senha Provisória */}
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={resetting === u.id}
                    onClick={() => handleResetSenha(u.id, u.nome_completo)}
                    className="border-slate-200 text-slate-600 hover:text-amber-700 hover:bg-amber-50 hover:border-amber-200 text-xs"
                  >
                    {resetting === u.id ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
                    ) : (
                      <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                    )}
                    Resetar Senha
                  </Button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Modal Diálogo de Criação de Operador (Método 1) */}
      <CriarColaboradorDialog
        open={showModal}
        onClose={() => setShowModal(false)}
        onCreated={loadUsers}
      />
    </div>
  );
}
