"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Shell,
  Plus,
  Ruler,
  Droplets,
  Activity,
  AlertTriangle,
  Loader2,
  Search,
  CalendarDays,
} from "lucide-react";
import { viveirosApi, ciclosApi } from "@/lib/api";
import { mensagemErro } from "@/lib/utils";
import type { Viveiro, CicloProdutivo } from "@/lib/types";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MetricCard } from "@/components/ui/metric-card";
import { toast } from "@/components/ui/toast";

// ── Modal de Criar Viveiro com Dialog Shadcn ──────────────
function CriarViveiroDialog({
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
        identificacao: form.identificacao.trim(),
        area_util_m2: parseFloat(form.area_util_m2),
        profundidade_media_m: form.profundidade_media_m
          ? parseFloat(form.profundidade_media_m)
          : null,
        localizacao: form.localizacao.trim() || null,
      });
      toast.success("Viveiro criado com sucesso!", `Identificação: ${form.identificacao}`);
      onCreated();
      onClose();
      setForm({ identificacao: "", area_util_m2: "", profundidade_media_m: "", localizacao: "" });
    } catch (err) {
      setError(mensagemErro(err, "Erro ao cadastrar viveiro"));
      toast.error("Falha ao criar viveiro", mensagemErro(err, "Verifique os dados informados"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title="Novo Viveiro" description="Cadastre um novo viveiro na fazenda">
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm mb-4">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Label htmlFor="identificacao">Identificação do Viveiro *</Label>
          <Input
            id="identificacao"
            required
            value={form.identificacao}
            onChange={(e) => setForm({ ...form, identificacao: e.target.value })}
            placeholder="Ex: V-01, Viveiro Norte..."
            className="mt-1"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="area_util_m2">Área útil (m²) *</Label>
            <Input
              id="area_util_m2"
              required
              type="number"
              step="0.01"
              min="0.01"
              inputMode="decimal"
              value={form.area_util_m2}
              onChange={(e) => setForm({ ...form, area_util_m2: e.target.value })}
              placeholder="10000"
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="profundidade_media_m">Profundidade (m)</Label>
            <Input
              id="profundidade_media_m"
              type="number"
              step="0.01"
              min="0.01"
              inputMode="decimal"
              value={form.profundidade_media_m}
              onChange={(e) => setForm({ ...form, profundidade_media_m: e.target.value })}
              placeholder="1.20"
              className="mt-1"
            />
          </div>
        </div>

        <div>
          <Label htmlFor="localizacao">Localização / Setor</Label>
          <Input
            id="localizacao"
            value={form.localizacao}
            onChange={(e) => setForm({ ...form, localizacao: e.target.value })}
            placeholder="Ex: Setor Leste, Próximo à Casa de Bombas"
            className="mt-1"
          />
        </div>

        <div className="pt-2 flex gap-3">
          <Button type="button" variant="outline" onClick={onClose} className="flex-1">
            Cancelar
          </Button>
          <Button type="submit" disabled={loading} className="flex-1 bg-ocean-600 hover:bg-ocean-700 text-white">
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
            Cadastrar Viveiro
          </Button>
        </div>
      </form>
    </Dialog>
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
    <Link href={`/gestor/viveiros/${viveiro.id}`} className="group block h-full">
      <div className="h-full rounded-2xl bg-white border border-slate-200/80 p-5 shadow-sm transition-all duration-200 hover:shadow-md hover:border-slate-300 flex flex-col justify-between">
        <div>
          {/* Header */}
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <div
                className={`w-11 h-11 rounded-xl flex items-center justify-center transition-colors ${
                  viveiro.status_ativo
                    ? "bg-ocean-50 text-ocean-600 border border-ocean-200 group-hover:bg-ocean-100"
                    : "bg-slate-100 text-slate-400 border border-slate-200"
                }`}
              >
                <Shell className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-base tracking-tight group-hover:text-ocean-600 transition-colors">
                  {viveiro.identificacao}
                </h3>
                <span className="text-xs text-slate-500">
                  {viveiro.localizacao || "Sem localização cadastrada"}
                </span>
              </div>
            </div>

            <Badge variant={viveiro.status_ativo ? "success" : "secondary"}>
              {viveiro.status_ativo ? "Ativo" : "Inativo"}
            </Badge>
          </div>

          {/* Dados Técnicos */}
          <div className="grid grid-cols-2 gap-2 py-3 border-y border-slate-100 mb-4">
            <div className="flex items-center gap-2 text-xs text-slate-600">
              <Ruler className="w-4 h-4 text-slate-400 shrink-0" />
              <span>
                <strong className="text-slate-800">{viveiro.area_util_m2.toLocaleString("pt-BR")}</strong> m²
              </span>
            </div>

            <div className="flex items-center gap-2 text-xs text-slate-600">
              <Droplets className="w-4 h-4 text-slate-400 shrink-0" />
              <span>
                <strong className="text-slate-800">
                  {viveiro.profundidade_media_m ? `${viveiro.profundidade_media_m} m` : "—"}
                </strong> prof.
              </span>
            </div>
          </div>
        </div>

        {/* Rodapé / Status do Ciclo */}
        <div className="pt-2">
          {cicloAtivo ? (
            <div className="flex items-center justify-between rounded-xl bg-emerald-50/70 border border-emerald-200/60 px-3 py-2 text-xs">
              <div className="flex items-center gap-1.5 font-semibold text-emerald-800">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                Ciclo em Andamento
              </div>
              <span className="font-bold text-emerald-700 bg-emerald-100/80 px-2 py-0.5 rounded-md">
                Dia {diasCultivo}
              </span>
            </div>
          ) : (
            <div className="flex items-center justify-between rounded-xl bg-slate-50 border border-slate-200/60 px-3 py-2 text-xs text-slate-500">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-slate-400" />
                Disponível para povoamento
              </span>
              <span className="font-medium text-slate-400">Vazio</span>
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
    try {
      const [vivs, cycs] = await Promise.all([
        viveirosApi.listar(),
        ciclosApi.listar({ status_filtro: "ATIVO" }),
      ]);
      setViveiros(vivs);
      setCiclos(cycs);
    } catch (err) {
      toast.error("Erro ao carregar viveiros", mensagemErro(err, "Tente recarregar a página"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Os setState do carregamento só ocorrem após o await (não são síncronos no efeito)
    (async () => {
      await loadData();
    })();
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
  const areaTotalM2 = viveiros.reduce((acc, v) => acc + (v.status_ativo ? v.area_util_m2 : 0), 0);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-ocean-600 mb-1">
            <Shell className="w-4 h-4" />
            Infraestrutura de Fazenda
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Viveiros & Lotes Produtivos
          </h1>
          <p className="text-slate-500 text-sm mt-0.5">
            Gerenciamento de lâminas d&apos;água, ciclo ativo de cultivo e status operacional
          </p>
        </div>

        <Button
          onClick={() => setModalOpen(true)}
          className="bg-ocean-600 hover:bg-ocean-700 text-white font-semibold shadow-md shadow-ocean-600/20"
        >
          <Plus className="w-4 h-4 mr-2" />
          Novo Viveiro
        </Button>
      </div>

      {/* Stats Cards (Inspirado no Padrão de Métricas da Pasta de Inspiração) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total de Viveiros"
          value={viveiros.length}
          subtitle="Capacidade instalada"
          icon={Shell}
          accent="ocean"
        />
        <MetricCard
          title="Viveiros Ativos"
          value={totalAtivos}
          subtitle="Operacionais para safra"
          icon={Activity}
          accent="emerald"
        />
        <MetricCard
          title="Com Ciclo em Curso"
          value={totalComCiclo}
          subtitle={`${Math.round((totalComCiclo / (totalAtivos || 1)) * 100)}% de ocupação`}
          icon={CalendarDays}
          accent="amber"
        />
        <MetricCard
          title="Área Útil Ativa"
          value={`${(areaTotalM2 / 10000).toFixed(1)} ha`}
          subtitle={`${areaTotalM2.toLocaleString("pt-BR")} m² em lâmina`}
          icon={Ruler}
          accent="purple"
        />
      </div>

      {/* Filtros e Busca */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por identificação ou setor..."
            className="pl-10"
          />
        </div>

        <div className="flex gap-2">
          {[
            { label: "Todos", value: null },
            { label: "Ativos", value: true },
            { label: "Inativos", value: false },
          ].map((f) => (
            <Button
              key={String(f.value)}
              variant={filterAtivo === f.value ? "default" : "outline"}
              size="sm"
              onClick={() => setFilterAtivo(f.value)}
              className={filterAtivo === f.value ? "bg-slate-900 text-white" : ""}
            >
              {f.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Grid de Viveiros */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-24 bg-white rounded-2xl border border-slate-200">
          <Loader2 className="w-8 h-8 text-ocean-600 animate-spin mb-2" />
          <p className="text-xs text-slate-400 font-medium">Carregando dados dos viveiros...</p>
        </div>
      ) : filteredViveiros.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-sm">
          <div className="w-14 h-14 rounded-2xl bg-slate-50 border border-slate-200 flex items-center justify-center mx-auto mb-4 text-slate-400">
            <Shell className="w-7 h-7" />
          </div>
          <h3 className="text-lg font-bold text-slate-800 mb-1">
            {viveiros.length === 0 ? "Nenhum viveiro cadastrado" : "Nenhum viveiro encontrado"}
          </h3>
          <p className="text-sm text-slate-500 mb-6 max-w-sm mx-auto">
            {viveiros.length === 0
              ? "Cadastre seu primeiro viveiro para iniciar o controle operacional e biometrias."
              : "Tente ajustar o termo de pesquisa ou os filtros ativos acima."}
          </p>
          {viveiros.length === 0 && (
            <Button onClick={() => setModalOpen(true)} className="bg-ocean-600 hover:bg-ocean-700 text-white">
              <Plus className="w-4 h-4 mr-2" />
              Cadastrar Primeiro Viveiro
            </Button>
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

      {/* Diálogo de Criação */}
      <CriarViveiroDialog
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreated={loadData}
      />
    </div>
  );
}
