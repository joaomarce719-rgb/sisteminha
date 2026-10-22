"use client";

import { useEffect, useState } from "react";
import {
  Building2,
  Shield,
  Plus,
  Loader2,
  AlertTriangle,
  Mail,
  Phone,
  RefreshCw,
  UserCheck,
  UserX,
  MapPin,
  CheckCircle2,
  XCircle,
  TrendingUp,
  Search,
  Users,
} from "lucide-react";
import { adminApi } from "@/lib/api";
import { mensagemErro } from "@/lib/utils";
import type { FazendaAdmin, MetricasGlobaisAdmin } from "@/lib/types";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MetricCard } from "@/components/ui/metric-card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "@/components/ui/toast";

interface GestorAdminItem {
  id: string;
  nome_completo: string;
  email: string;
  papel: string;
  telefone_emergencia: string | null;
  ativo: boolean;
  organizacao_nome: string | null;
  created_at: string;
}

function fmtDate(d: string) {
  try {
    return new Date(d).toLocaleDateString("pt-BR");
  } catch {
    return "-";
  }
}

// ── Modal Criar Fazenda (Superadmin) ─────────────────
function CriarFazendaDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState({
    nome: "",
    localizacao: "Russas, Vale do Jaguaribe - CE",
    area_total_ha: "",
    organizacao_nome: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await adminApi.criarFazenda({
        nome: form.nome.trim(),
        localizacao: form.localizacao.trim() || null,
        area_total_ha: form.area_total_ha ? parseFloat(form.area_total_ha) : null,
        organizacao_nome: form.organizacao_nome.trim() || undefined,
      });
      toast.success(
        "Fazenda adicionada com sucesso!",
        `${form.nome} está aprovada e ativa para cultivo.`
      );
      onCreated();
      onClose();
      setForm({
        nome: "",
        localizacao: "Russas, Vale do Jaguaribe - CE",
        area_total_ha: "",
        organizacao_nome: "",
      });
    } catch (err) {
      const msg = mensagemErro(err, "Erro ao adicionar fazenda");
      setError(msg);
      toast.error("Falha no cadastro da fazenda", msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Adicionar Nova Fazenda"
      description="Cadastre uma propriedade produtora rural para ser gerenciada na plataforma"
    >
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-medium mb-4">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4 text-slate-200">
        <div>
          <Label htmlFor="nome_fazenda" className="text-xs font-semibold text-slate-300">
            Nome da Fazenda / Propriedade *
          </Label>
          <Input
            id="nome_fazenda"
            required
            minLength={3}
            value={form.nome}
            onChange={(e) => setForm({ ...form, nome: e.target.value })}
            placeholder="Ex: Fazenda Boa Esperança"
            className="mt-1 bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
          />
        </div>

        <div>
          <Label htmlFor="localizacao_fazenda" className="text-xs font-semibold text-slate-300">
            Localização / Bacia Hidrográfica
          </Label>
          <Input
            id="localizacao_fazenda"
            value={form.localizacao}
            onChange={(e) => setForm({ ...form, localizacao: e.target.value })}
            placeholder="Ex: Russas, Vale do Jaguaribe - CE"
            className="mt-1 bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
          />
        </div>

        <div>
          <Label htmlFor="area_fazenda" className="text-xs font-semibold text-slate-300">
            Área Total de Cultivo (Hectares)
          </Label>
          <Input
            id="area_fazenda"
            type="number"
            step="0.1"
            min="0"
            value={form.area_total_ha}
            onChange={(e) => setForm({ ...form, area_total_ha: e.target.value })}
            placeholder="Ex: 45.0"
            className="mt-1 bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
          />
        </div>

        <div>
          <Label htmlFor="org_fazenda" className="text-xs font-semibold text-slate-300">
            Grupo Produtor / Empresa Responsável
          </Label>
          <Input
            id="org_fazenda"
            value={form.organizacao_nome}
            onChange={(e) => setForm({ ...form, organizacao_nome: e.target.value })}
            placeholder="Ex: Grupo Aquacultura do Ceará"
            className="mt-1 bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
          />
        </div>

        <div className="pt-2 flex gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            className="flex-1 border-slate-700 text-slate-300 hover:bg-slate-800"
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            disabled={loading}
            className="flex-1 bg-sky-600 hover:bg-sky-500 text-white font-semibold shadow-md shadow-sky-600/20"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <Building2 className="w-4 h-4 mr-2" />
            )}
            Cadastrar Fazenda
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

// ── Modal Criar Gestor de Fazenda (Superadmin) ───────
function CriarGestorDialog({
  open,
  onClose,
  onCreated,
  fazendas,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
  fazendas: FazendaAdmin[];
}) {
  const [form, setForm] = useState({
    nome_completo: "",
    email: "",
    senha: "",
    telefone_emergencia: "",
    nome_fazenda: fazendas[0]?.nome || "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await adminApi.criarGestor({
        nome_completo: form.nome_completo.trim(),
        email: form.email.trim(),
        senha: form.senha,
        telefone_emergencia: form.telefone_emergencia.trim() || null,
        nome_fazenda: form.nome_fazenda || undefined,
      });
      toast.success(
        "Gestor cadastrado com sucesso!",
        `${form.nome_completo} agora é Gestor Administrativo da fazenda ${form.nome_fazenda || "padrão"}.`
      );
      onCreated();
      onClose();
      setForm({
        nome_completo: "",
        email: "",
        senha: "",
        telefone_emergencia: "",
        nome_fazenda: fazendas[0]?.nome || "",
      });
    } catch (err) {
      const msg = mensagemErro(err, "Erro ao cadastrar gestor administrativo");
      setError(msg);
      toast.error("Falha no cadastro do gestor", msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Cadastrar Novo Gestor de Fazenda"
      description="Conceda permissão executiva e administrativa (GESTOR) para gerenciar uma fazenda"
    >
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-medium mb-4">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4 text-slate-200">
        <div>
          <Label htmlFor="nome_gestor" className="text-xs font-semibold text-slate-300">
            Nome Completo do Gestor *
          </Label>
          <Input
            id="nome_gestor"
            required
            minLength={3}
            value={form.nome_completo}
            onChange={(e) => setForm({ ...form, nome_completo: e.target.value })}
            placeholder="Ex: Dr. Roberto Sampaio"
            className="mt-1 bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
          />
        </div>

        <div>
          <Label htmlFor="email_gestor" className="text-xs font-semibold text-slate-300">
            E-mail Corporativo *
          </Label>
          <Input
            id="email_gestor"
            required
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            placeholder="Ex: roberto.gestor@fazenda.com"
            className="mt-1 bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
          />
        </div>

        <div>
          <Label htmlFor="senha_gestor" className="text-xs font-semibold text-slate-300">
            Senha Provisória de Acesso *
          </Label>
          <Input
            id="senha_gestor"
            required
            type="password"
            minLength={6}
            value={form.senha}
            onChange={(e) => setForm({ ...form, senha: e.target.value })}
            placeholder="Mínimo 6 caracteres"
            className="mt-1 bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
          />
        </div>

        <div>
          <Label htmlFor="fazenda_select" className="text-xs font-semibold text-slate-300">
            Fazenda / Propriedade Responsável *
          </Label>
          <select
            id="fazenda_select"
            value={form.nome_fazenda}
            onChange={(e) => setForm({ ...form, nome_fazenda: e.target.value })}
            className="w-full mt-1 px-3 py-2 text-xs rounded-xl bg-slate-900 border border-slate-700 text-white focus:outline-none focus:ring-1 focus:ring-sky-500"
          >
            {fazendas.length === 0 ? (
              <option value="">Nenhuma fazenda cadastrada</option>
            ) : (
              fazendas.map((f) => (
                <option key={f.id} value={f.nome}>
                  {f.nome} — {f.localizacao || "Vale do Jaguaribe"}
                </option>
              ))
            )}
          </select>
        </div>

        <div>
          <Label htmlFor="tel_gestor" className="text-xs font-semibold text-slate-300">
            Telefone / WhatsApp
          </Label>
          <Input
            id="tel_gestor"
            value={form.telefone_emergencia}
            onChange={(e) => setForm({ ...form, telefone_emergencia: e.target.value })}
            placeholder="Ex: (88) 99876-5432"
            className="mt-1 bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
          />
        </div>

        <div className="pt-2 flex gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            className="flex-1 border-slate-700 text-slate-300 hover:bg-slate-800"
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            disabled={loading}
            className="flex-1 bg-sky-600 hover:bg-sky-500 text-white font-semibold shadow-md shadow-sky-600/20"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <Shield className="w-4 h-4 mr-2" />
            )}
            Homologar Gestor
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

// ── Página Principal do Administrador Geral ───────────
export default function AdminPage() {
  const [tab, setTab] = useState<string>("fazendas");
  const [fazendas, setFazendas] = useState<FazendaAdmin[]>([]);
  const [gestores, setGestores] = useState<GestorAdminItem[]>([]);
  const [metricas, setMetricas] = useState<MetricasGlobaisAdmin | null>(null);
  const [loading, setLoading] = useState(true);

  // Modais
  const [showFazendaModal, setShowFazendaModal] = useState(false);
  const [showGestorModal, setShowGestorModal] = useState(false);

  // Ações
  const [togglingFazenda, setTogglingFazenda] = useState<string | null>(null);
  const [togglingGestor, setTogglingGestor] = useState<string | null>(null);
  const [resetting, setResetting] = useState<string | null>(null);
  const [busca, setBusca] = useState<string>("");

  const carregarDados = async () => {
    try {
      const [fazendasData, gestoresData, metricasData] = await Promise.all([
        adminApi.listarFazendas(),
        adminApi.listarGestores(),
        adminApi.obterMetricasGlobais(),
      ]);
      setFazendas(fazendasData || []);
      setGestores(gestoresData || []);
      setMetricas(metricasData || null);
    } catch (err) {
      toast.error("Erro ao carregar dados do admin", mensagemErro(err, "Tente novamente"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Os setState do carregamento só ocorrem após o await (não são síncronos no efeito)
    (async () => {
      await carregarDados();
    })();
  }, []);

  const handleToggleStatusFazenda = async (fazenda: FazendaAdmin) => {
    setTogglingFazenda(fazenda.id);
    try {
      await adminApi.alternarStatusFazenda(fazenda.id);
      toast.info(
        `Status da fazenda alterado`,
        `${fazenda.nome} agora está ${fazenda.status_ativo ? "suspensa" : "ativa e homologada"}.`
      );
      carregarDados();
    } catch (err) {
      toast.error("Erro ao alterar status da fazenda", mensagemErro(err, "Tente novamente"));
    } finally {
      setTogglingFazenda(null);
    }
  };

  const handleToggleStatusGestor = async (gestor: GestorAdminItem) => {
    setTogglingGestor(gestor.id);
    try {
      await adminApi.atualizarUsuario(gestor.id, { ativo: !gestor.ativo });
      toast.info(
        `Acesso do gestor alterado`,
        `${gestor.nome_completo} agora está ${gestor.ativo ? "bloqueado" : "ativo no sistema"}.`
      );
      carregarDados();
    } catch (err) {
      toast.error("Erro ao alterar status", mensagemErro(err, "Tente novamente"));
    } finally {
      setTogglingGestor(null);
    }
  };

  const handleResetSenhaGestor = async (id: string, nome: string) => {
    setResetting(id);
    try {
      const res = await adminApi.resetarSenha(id);
      toast.success(
        "Senha redefinida com sucesso!",
        `Senha temporária de ${nome}: ${res.senha_temporaria}`,
        60000
      );
    } catch (err) {
      toast.error("Falha ao resetar senha", mensagemErro(err, "Tente novamente"));
    } finally {
      setResetting(null);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-32 bg-slate-900/60 rounded-3xl border border-slate-800">
        <Loader2 className="w-8 h-8 text-sky-400 animate-spin mb-2" />
        <p className="text-xs text-slate-400 font-medium">Carregando governança da plataforma...</p>
      </div>
    );
  }

  const fazendasFiltradas = fazendas.filter((f) =>
    busca.trim() === ""
      ? true
      : f.nome.toLowerCase().includes(busca.toLowerCase()) ||
        (f.localizacao || "").toLowerCase().includes(busca.toLowerCase())
  );

  const gestoresFiltrados = gestores.filter((g) =>
    busca.trim() === ""
      ? true
      : g.nome_completo.toLowerCase().includes(busca.toLowerCase()) ||
        g.email.toLowerCase().includes(busca.toLowerCase()) ||
        (g.organizacao_nome || "").toLowerCase().includes(busca.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header do Painel */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-sky-400 mb-1">
            <Shield className="w-4 h-4" />
            Governança da Plataforma • Visão Superadmin
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Painel do Administrador Geral
          </h1>
          <p className="text-slate-400 text-xs sm:text-sm mt-0.5">
            Adição e homologação de fazendas e cadastro de gestores administrativos
          </p>
        </div>

        <div className="flex items-center gap-2">
          {tab === "fazendas" ? (
            <Button
              onClick={() => setShowFazendaModal(true)}
              className="bg-sky-600 hover:bg-sky-500 text-white font-semibold shadow-lg shadow-sky-600/20 text-xs"
            >
              <Plus className="w-4 h-4 mr-1.5" />
              Adicionar Fazenda
            </Button>
          ) : (
            <Button
              onClick={() => setShowGestorModal(true)}
              className="bg-sky-600 hover:bg-sky-500 text-white font-semibold shadow-lg shadow-sky-600/20 text-xs"
            >
              <Plus className="w-4 h-4 mr-1.5" />
              Novo Gestor de Fazenda
            </Button>
          )}
        </div>
      </div>

      {/* Métricas no Topo com Shadcn MetricCard */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Fazendas Homologadas"
          value={metricas?.fazendas_ativas ?? fazendas.length}
          subtitle={`${fazendas.length} propriedades registradas`}
          icon={Building2}
          accent="ocean"
        />
        <MetricCard
          title="Área Monitorada Total"
          value={`${metricas?.area_total_ha ?? 0} ha`}
          subtitle={`${metricas?.total_viveiros ?? 0} viveiros escavados`}
          icon={TrendingUp}
          accent="emerald"
        />
        <MetricCard
          title="Gestores de Fazenda"
          value={metricas?.gestores ?? gestores.length}
          subtitle="Usuários administrativos"
          icon={Shield}
          accent="amber"
        />
        <MetricCard
          title="Equipe de Campo & Vigias"
          value={metricas ? metricas.operadores_campo + metricas.vigias : 0}
          subtitle="Manejo e rondas noturnas"
          icon={Users}
          accent="ocean"
        />
      </div>

      {/* Tabs Shadcn UI */}
      <Tabs value={tab} onValueChange={setTab} className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <TabsList className="bg-slate-900 border border-slate-800">
            <TabsTrigger value="fazendas" className="text-xs">
              <Building2 className="w-4 h-4 mr-1.5 text-sky-400" />
              Fazendas & Propriedades ({fazendas.length})
            </TabsTrigger>
            <TabsTrigger value="gestores" className="text-xs">
              <Shield className="w-4 h-4 mr-1.5 text-amber-400" />
              Gestores Administrativos ({gestores.length})
            </TabsTrigger>
          </TabsList>

          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <Input
              placeholder="Filtrar nesta lista..."
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="pl-9 text-xs bg-slate-900 border-slate-800 text-white placeholder:text-slate-500"
            />
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════ */}
        {/* ABA 1: ADICIONAR E APROVAR FAZENDAS                    */}
        {/* ══════════════════════════════════════════════════════ */}
        {tab === "fazendas" && (
          <div className="space-y-4">
            {fazendasFiltradas.length === 0 ? (
              <div className="bg-slate-900/60 rounded-3xl border border-slate-800 p-12 text-center">
                <Building2 className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <h3 className="text-base font-bold text-white mb-1">
                  Nenhuma fazenda encontrada
                </h3>
                <p className="text-xs text-slate-400 max-w-sm mx-auto mb-4">
                  Cadastre as propriedades de carcinicultura para liberar o gerenciamento de viveiros.
                </p>
                <Button
                  onClick={() => setShowFazendaModal(true)}
                  className="bg-sky-600 hover:bg-sky-500 text-white text-xs"
                >
                  <Plus className="w-3.5 h-3.5 mr-1.5" />
                  Cadastrar Primeira Fazenda
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {fazendasFiltradas.map((f) => (
                  <div
                    key={f.id}
                    className="bg-slate-900/90 rounded-3xl border border-slate-800 p-5 hover:border-slate-700 transition-all flex flex-col justify-between shadow-sm"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-3 mb-3">
                        <div>
                          <h3 className="font-extrabold text-white text-base">
                            {f.nome}
                          </h3>
                          <div className="text-xs text-slate-400 flex items-center gap-1.5 mt-1">
                            <MapPin className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                            <span>{f.localizacao || "Vale do Jaguaribe, CE"}</span>
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={() => handleToggleStatusFazenda(f)}
                          disabled={togglingFazenda === f.id}
                          title="Clique para aprovar ou suspender a fazenda"
                          className="transition-transform active:scale-95"
                        >
                          <Badge
                            className={
                              f.status_ativo
                                ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                                : "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                            }
                          >
                            {togglingFazenda === f.id ? (
                              <Loader2 className="w-3 h-3 animate-spin mr-1" />
                            ) : f.status_ativo ? (
                              <CheckCircle2 className="w-3 h-3 mr-1" />
                            ) : (
                              <XCircle className="w-3 h-3 mr-1" />
                            )}
                            {f.status_ativo ? "Aprovada & Ativa" : "Pendente / Suspensa"}
                          </Badge>
                        </button>
                      </div>

                      <div className="grid grid-cols-2 gap-3 py-3 border-y border-slate-800 my-3">
                        <div>
                          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                            Área Útil de Cultivo
                          </div>
                          <div className="text-sm font-extrabold text-sky-400 mt-0.5">
                            {f.area_total_ha ? `${f.area_total_ha} hectares` : "Não informada"}
                          </div>
                        </div>

                        <div>
                          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                            Viveiros Associados
                          </div>
                          <div className="text-sm font-extrabold text-white mt-0.5">
                            {f.total_viveiros} viveiro(s) escavado(s)
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-xs text-slate-500 pt-2">
                      <span>Organização: {f.organizacao_nome || "Fazenda Principal"}</span>
                      <span>Homologada em {fmtDate(f.created_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════ */}
        {/* ABA 2: GESTORES & USUÁRIOS ADMINISTRATIVOS             */}
        {/* ══════════════════════════════════════════════════════ */}
        {tab === "gestores" && (
          <div className="bg-slate-900/90 rounded-3xl border border-slate-800 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="font-extrabold text-white text-sm">
                  Gestores de Fazenda ({gestoresFiltrados.length})
                </h3>
                <p className="text-xs text-slate-400">
                  Usuários com perfil de Gestor autorizados a administrar fazendas no SAD
                </p>
              </div>

              <Button
                onClick={() => setShowGestorModal(true)}
                className="bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold"
              >
                <Plus className="w-3.5 h-3.5 mr-1.5" />
                Novo Gestor
              </Button>
            </div>

            {gestoresFiltrados.length === 0 ? (
              <div className="p-12 text-center">
                <Shield className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <h4 className="text-base font-bold text-white mb-1">
                  Nenhum gestor encontrado
                </h4>
                <p className="text-xs text-slate-400 max-w-sm mx-auto mb-4">
                  Cadastre gestores para delegar a administração das fazendas.
                </p>
                <Button
                  onClick={() => setShowGestorModal(true)}
                  className="bg-sky-600 text-white text-xs"
                >
                  <Plus className="w-3.5 h-3.5 mr-1.5" />
                  Homologar Primeiro Gestor
                </Button>
              </div>
            ) : (
              <div className="divide-y divide-slate-800">
                {gestoresFiltrados.map((g) => (
                  <div
                    key={g.id}
                    className="p-4 flex flex-wrap items-center justify-between gap-4 hover:bg-slate-800/40 transition-colors"
                  >
                    {/* Avatar & Nome */}
                    <div className="flex items-center gap-3.5 min-w-[240px]">
                      <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/25 text-sky-400 font-bold text-sm flex items-center justify-center shrink-0">
                        {g.nome_completo.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div className="font-bold text-white text-sm">
                          {g.nome_completo}
                        </div>
                        <div className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
                          <Mail className="w-3 h-3 text-slate-500" />
                          <span>{g.email}</span>
                        </div>
                      </div>
                    </div>

                    {/* Fazenda Responsável */}
                    <div className="text-xs text-slate-300 flex items-center gap-1.5 bg-slate-800/60 border border-slate-700/60 px-3 py-1.5 rounded-xl">
                      <Building2 className="w-3.5 h-3.5 text-sky-400" />
                      <span>{g.organizacao_nome || "Fazenda Vinculada"}</span>
                    </div>

                    {/* Badge de Gestor */}
                    <Badge className="bg-sky-500/15 text-sky-400 border border-sky-500/30 text-xs">
                      <Shield className="w-3 h-3 mr-1" />
                      Gestor Geral
                    </Badge>

                    {/* Status Ativo / Bloqueado */}
                    <button
                      type="button"
                      onClick={() => handleToggleStatusGestor(g)}
                      disabled={togglingGestor === g.id}
                      title="Clique para alternar status do gestor"
                      className="transition-transform active:scale-95"
                    >
                      <Badge
                        className={
                          g.ativo
                            ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                            : "bg-red-500/15 text-red-400 border border-red-500/30"
                        }
                      >
                        {togglingGestor === g.id ? (
                          <Loader2 className="w-3 h-3 animate-spin mr-1" />
                        ) : g.ativo ? (
                          <UserCheck className="w-3 h-3 mr-1" />
                        ) : (
                          <UserX className="w-3 h-3 mr-1" />
                        )}
                        {g.ativo ? "Ativo" : "Bloqueado"}
                      </Badge>
                    </button>

                    {/* Telefone */}
                    <div className="text-xs text-slate-400 hidden lg:flex items-center gap-1">
                      {g.telefone_emergencia ? (
                        <>
                          <Phone className="w-3 h-3 text-slate-500" />
                          <span>{g.telefone_emergencia}</span>
                        </>
                      ) : (
                        <span className="text-slate-600">Sem telefone</span>
                      )}
                    </div>

                    {/* Ação Reset de Senha */}
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={resetting === g.id}
                      onClick={() => handleResetSenhaGestor(g.id, g.nome_completo)}
                      className="border-slate-800 text-slate-300 hover:text-amber-400 hover:bg-amber-500/10 hover:border-amber-500/20 text-xs"
                    >
                      {resetting === g.id ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
                      ) : (
                        <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                      )}
                      Resetar Senha
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Tabs>

      {/* Modais */}
      <CriarFazendaDialog
        open={showFazendaModal}
        onClose={() => setShowFazendaModal(false)}
        onCreated={carregarDados}
      />

      <CriarGestorDialog
        open={showGestorModal}
        onClose={() => setShowGestorModal(false)}
        onCreated={carregarDados}
        fazendas={fazendas}
      />
    </div>
  );
}
