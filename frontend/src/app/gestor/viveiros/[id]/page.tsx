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
  Info,
  CheckCircle2,
  XCircle,
  Download,
  Pause,
  Play,
} from "lucide-react";
import {
  viveirosApi,
  ciclosApi,
  biometriasApi,
  manejosApi,
  tabelasAlimentaresApi,
} from "@/lib/api";
import type {
  Viveiro,
  CicloProdutivo,
  MetricasAtuais,
  Biometria,
  ManejoAlimentar,
  RecomendacaoAlimentar,
} from "@/lib/types";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { toast } from "@/components/ui/toast";

function fmtDate(d: string) {
  return new Date(d).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

// ── Modal Iniciar Ciclo com Shadcn Dialog ───────────
function IniciarCicloDialog({
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
    tabela_alimentar_id: "",
  });
  const [tabelas, setTabelas] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      tabelasAlimentaresApi
        .listar(true)
        .then((data) => {
          setTabelas(data);
          const padrao = data.find((t: any) => t.is_padrao);
          if (padrao) {
            setForm((prev) => ({ ...prev, tabela_alimentar_id: padrao.id }));
          }
        })
        .catch(() => {});
    }
  }, [open]);

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
        laboratorio_origem: form.laboratorio_origem.trim() || null,
        tabela_alimentar_id: form.tabela_alimentar_id || null,
      });
      toast.success(
        "Ciclo produtivo iniciado!",
        `${parseInt(form.quantidade_pos_larvas).toLocaleString("pt-BR")} pós-larvas povoadas.`
      );
      onCreated();
      onClose();
    } catch (err: any) {
      setError(err.message || "Erro ao iniciar ciclo");
      toast.error("Falha ao iniciar ciclo", err.message || "Verifique os dados");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title="Iniciar Ciclo Produtivo" description="Povoamento de pós-larvas no viveiro">
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm mb-4">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Label htmlFor="data_povoamento">Data do Povoamento *</Label>
          <Input
            id="data_povoamento"
            required
            type="date"
            value={form.data_povoamento}
            onChange={(e) => setForm({ ...form, data_povoamento: e.target.value })}
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor="quantidade_pos_larvas">Quantidade de Pós-Larvas (PLs) *</Label>
          <Input
            id="quantidade_pos_larvas"
            required
            type="number"
            min="1"
            inputMode="numeric"
            value={form.quantidade_pos_larvas}
            onChange={(e) => setForm({ ...form, quantidade_pos_larvas: e.target.value })}
            placeholder="Ex: 250000"
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor="custo_aquisicao_pl">Custo Total de Aquisição das PLs (R$) *</Label>
          <Input
            id="custo_aquisicao_pl"
            required
            type="number"
            min="0"
            step="0.01"
            inputMode="decimal"
            value={form.custo_aquisicao_pl}
            onChange={(e) => setForm({ ...form, custo_aquisicao_pl: e.target.value })}
            placeholder="Ex: 3500.00"
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor="laboratorio_origem">Laboratório de Origem / Fornecedor</Label>
          <Input
            id="laboratorio_origem"
            value={form.laboratorio_origem}
            onChange={(e) => setForm({ ...form, laboratorio_origem: e.target.value })}
            placeholder="Ex: Aquagenetics, Larvicultura Norte"
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor="tabela_alimentar_id">Tabela de Arraçoamento (RF-010)</Label>
          <select
            id="tabela_alimentar_id"
            value={form.tabela_alimentar_id}
            onChange={(e) => setForm({ ...form, tabela_alimentar_id: e.target.value })}
            className="w-full mt-1 text-sm h-10 px-3 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            {tabelas.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nome} (v{t.versao}) {t.is_padrao ? "★ [Padrão]" : ""}
              </option>
            ))}
            {tabelas.length === 0 && (
              <option value="">Clifford (1992) — Padrão do Sistema</option>
            )}
          </select>
          <p className="text-[11px] text-slate-400 mt-1">
            Define os pontos de calibração utilizados no cálculo algorítmico da ração diária
          </p>
        </div>

        <div className="pt-2 flex gap-3">
          <Button type="button" variant="outline" onClick={onClose} className="flex-1">
            Cancelar
          </Button>
          <Button type="submit" disabled={loading} className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white">
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Activity className="w-4 h-4 mr-2" />}
            Iniciar Ciclo
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

// ── Modal Biometria com Shadcn Dialog ───────────────
function BiometriaDialog({
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
    quantidade_amostrada: "50",
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
        quantidade_amostrada: parseInt(form.quantidade_amostrada) || 50,
        peso_medio_g: parseFloat(form.peso_medio_g),
        uniformidade_percentual: form.uniformidade_percentual
          ? parseFloat(form.uniformidade_percentual)
          : null,
        observacoes: form.observacoes.trim() || null,
      });
      toast.success(
        "Biometria salva com sucesso!",
        `Peso médio: ${parseFloat(form.peso_medio_g).toFixed(2)} g registrado (${form.quantidade_amostrada} camarões amostrados).`
      );
      onCreated();
      onClose();
      setForm({ data_medicao: new Date().toISOString().split("T")[0], quantidade_amostrada: "50", peso_medio_g: "", uniformidade_percentual: "", observacoes: "" });
    } catch (err: any) {
      setError(err.message || "Erro ao registrar biometria");
      toast.error("Erro na biometria", err.message || "Verifique os valores");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title="Nova Biometria" description="Registre a pesagem amostral do lote">
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm mb-4">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Label htmlFor="data_medicao">Data da Amostragem *</Label>
          <Input
            id="data_medicao"
            required
            type="date"
            value={form.data_medicao}
            onChange={(e) => setForm({ ...form, data_medicao: e.target.value })}
            className="mt-1"
          />
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <Label htmlFor="quantidade_amostrada">Qtd. Amostrada *</Label>
            <Input
              id="quantidade_amostrada"
              required
              type="number"
              min="1"
              value={form.quantidade_amostrada}
              onChange={(e) => setForm({ ...form, quantidade_amostrada: e.target.value })}
              placeholder="Ex: 50"
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="peso_medio_g">Peso Médio (g) *</Label>
            <Input
              id="peso_medio_g"
              required
              type="number"
              step="0.01"
              min="0.01"
              inputMode="decimal"
              value={form.peso_medio_g}
              onChange={(e) => setForm({ ...form, peso_medio_g: e.target.value })}
              placeholder="Ex: 12.5"
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="uniformidade">Uniformidade (%)</Label>
            <Input
              id="uniformidade"
              type="number"
              step="0.1"
              min="0"
              max="100"
              inputMode="decimal"
              value={form.uniformidade_percentual}
              onChange={(e) => setForm({ ...form, uniformidade_percentual: e.target.value })}
              placeholder="Ex: 85.0"
              className="mt-1"
            />
          </div>
        </div>

        <div>
          <Label htmlFor="obs_bio">Observações da Biometria</Label>
          <textarea
            id="obs_bio"
            rows={2}
            value={form.observacoes}
            onChange={(e) => setForm({ ...form, observacoes: e.target.value })}
            placeholder="Ex: Camarões com trato digestivo cheio, carapaça lisa..."
            className="w-full mt-1 px-3 py-2 text-sm rounded-xl border border-slate-200 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-ocean-500/20 focus:border-ocean-500 resize-none"
          />
        </div>

        <div className="pt-2 flex gap-3">
          <Button type="button" variant="outline" onClick={onClose} className="flex-1">
            Cancelar
          </Button>
          <Button type="submit" disabled={loading} className="flex-1 bg-ocean-600 hover:bg-ocean-700 text-white">
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Scale className="w-4 h-4 mr-2" />}
            Salvar Biometria
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

// ── Modal Manejo Alimentar com Shadcn Dialog ─────────
const SOBRA_OPTIONS = [
  { value: "SEM_SOBRA", label: "Sem sobra", desc: "Consumo total" },
  { value: "SOBRA_LEVE", label: "Sobra leve (<5%)", desc: "Ajuste fino" },
  { value: "SOBRA_MODERADA", label: "Sobra moderada (10%)", desc: "Reduzir 10%" },
  { value: "SOBRA_EXCESSIVA", label: "Sobra excessiva (>20%)", desc: "Suspender/cortar" },
];

function ManejoDialog({
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
      toast.success(
        "Manejo registrado com sucesso!",
        `${parseFloat(form.quantidade_racao_kg)} kg de ração lançados.`
      );
      onCreated();
      onClose();
      setForm({
        data_registro: new Date().toISOString().split("T")[0],
        quantidade_racao_kg: "",
        sobra_bandeja_nivel: "SEM_SOBRA",
      });
    } catch (err: any) {
      setError(err.message || "Erro ao registrar manejo");
      toast.error("Erro no manejo", err.message || "Tente novamente");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title="Registrar Manejo Alimentar" description="Lançamento diário de ração e leitura de bandejas">
      {recomendacao && (
        <div className="rounded-xl bg-blue-50/80 border border-blue-200/80 p-3 mb-4">
          <div className="flex items-center gap-1.5 text-xs font-bold text-blue-800 uppercase tracking-wider mb-1">
            <Info className="w-3.5 h-3.5 text-blue-600" />
            Recomendação Algorítmica (Clifford 1992)
          </div>
          <div className="flex justify-between items-center text-xs text-blue-900">
            <span>Sugerido: <strong>{recomendacao.racao_diaria_sugerida_kg} kg/dia</strong></span>
            <span>Taxa: <strong>{recomendacao.taxa_clifford_pct}% da biomassa</strong></span>
          </div>
          <p className="text-[11px] text-blue-700 mt-1">{recomendacao.ajuste_sugerido}</p>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm mb-4">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Label htmlFor="data_registro">Data do Fornecimento *</Label>
          <Input
            id="data_registro"
            required
            type="date"
            value={form.data_registro}
            onChange={(e) => setForm({ ...form, data_registro: e.target.value })}
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor="quantidade_racao_kg">Ração Efetivamente Fornecida (kg) *</Label>
          <Input
            id="quantidade_racao_kg"
            required
            type="number"
            step="0.1"
            min="0"
            inputMode="decimal"
            value={form.quantidade_racao_kg}
            onChange={(e) => setForm({ ...form, quantidade_racao_kg: e.target.value })}
            placeholder="Ex: 45.0"
            className="mt-1"
          />
        </div>

        <div>
          <Label>Leitura da Bandeja de Amostragem *</Label>
          <div className="grid grid-cols-2 gap-2 mt-1.5">
            {SOBRA_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setForm({ ...form, sobra_bandeja_nivel: opt.value })}
                className={`p-2.5 rounded-xl text-left border transition-all text-xs ${
                  form.sobra_bandeja_nivel === opt.value
                    ? "bg-slate-900 border-slate-900 text-white shadow-sm"
                    : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                }`}
              >
                <div className="font-bold">{opt.label}</div>
                <div className={`text-[10px] mt-0.5 ${form.sobra_bandeja_nivel === opt.value ? "text-slate-300" : "text-slate-400"}`}>
                  {opt.desc}
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="pt-2 flex gap-3">
          <Button type="button" variant="outline" onClick={onClose} className="flex-1">
            Cancelar
          </Button>
          <Button type="submit" disabled={loading} className="flex-1 bg-amber-600 hover:bg-amber-700 text-white">
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Utensils className="w-4 h-4 mr-2" />}
            Salvar Manejo
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

// ── Modal Encerrar Ciclo com Shadcn Dialog ──────────
function EncerrarCicloDialog({
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
      toast.success(
        "Ciclo produtivo encerrado com sucesso!",
        `Despesca de ${parseFloat(form.biomassa_colhida_kg).toLocaleString("pt-BR")} kg registrada.`
      );
      onDone();
      onClose();
    } catch (err: any) {
      setError(err.message || "Erro ao encerrar ciclo");
      toast.error("Erro ao encerrar", err.message || "Verifique os dados");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title="Encerrar Ciclo (Despesca)" description="Registre o fechamento e dados finais da safra">
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm mb-4">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Label htmlFor="data_despesca">Data da Despesca Efetiva *</Label>
          <Input
            id="data_despesca"
            required
            type="date"
            value={form.data_despesca_real}
            onChange={(e) => setForm({ ...form, data_despesca_real: e.target.value })}
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor="biomassa_colhida">Biomassa Real Colhida (kg) *</Label>
          <Input
            id="biomassa_colhida"
            required
            type="number"
            step="0.01"
            min="0.01"
            inputMode="decimal"
            value={form.biomassa_colhida_kg}
            onChange={(e) => setForm({ ...form, biomassa_colhida_kg: e.target.value })}
            placeholder="Ex: 3450.00"
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor="receita_real">Receita Total Realizada (R$) *</Label>
          <Input
            id="receita_real"
            required
            type="number"
            step="0.01"
            min="0"
            inputMode="decimal"
            value={form.receita_real_rs}
            onChange={(e) => setForm({ ...form, receita_real_rs: e.target.value })}
            placeholder="Ex: 86250.00"
            className="mt-1"
          />
        </div>

        <div className="pt-2 flex gap-3">
          <Button type="button" variant="outline" onClick={onClose} className="flex-1">
            Cancelar
          </Button>
          <Button type="submit" disabled={loading} className="flex-1 bg-red-600 hover:bg-red-700 text-white">
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <XCircle className="w-4 h-4 mr-2" />}
            Confirmar Despesca
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

// ── Página Principal ────────────────────────────────
export default function ViveiroDetalhePage() {
  const params = useParams();
  const viveiroId = params.id as string;

  const [viveiro, setViveiro] = useState<Viveiro | null>(null);
  const [cicloAtivo, setCicloAtivo] = useState<CicloProdutivo | null>(null);
  const [metricas, setMetricas] = useState<MetricasAtuais | null>(null);
  const [biometrias, setBiometrias] = useState<Biometria[]>([]);
  const [manejos, setManejos] = useState<ManejoAlimentar[]>([]);
  const [recomendacao, setRecomendacao] = useState<RecomendacaoAlimentar | null>(null);
  const [activeTab, setActiveTab] = useState("metricas");
  const [loading, setLoading] = useState(true);

  // Estados dos Diálogos
  const [showCicloModal, setShowCicloModal] = useState(false);
  const [showBioModal, setShowBioModal] = useState(false);
  const [showManejoModal, setShowManejoModal] = useState(false);
  const [showEncerrarModal, setShowEncerrarModal] = useState(false);
  const [exportingCsv, setExportingCsv] = useState(false);

  const handleExportarCsv = async () => {
    if (!cicloAtivo) return;
    setExportingCsv(true);
    try {
      await ciclosApi.exportarCsv(cicloAtivo.id);
      toast.success("Download iniciado", "Relatório CSV do ciclo gerado com sucesso.");
    } catch (err: any) {
      toast.error("Erro ao exportar CSV", err.message || "Tente novamente");
    } finally {
      setExportingCsv(false);
    }
  };

  const handlePausarCiclo = async () => {
    if (!cicloAtivo) return;
    try {
      await ciclosApi.pausar(cicloAtivo.id);
      toast.success("Ciclo pausado", "O ciclo produtivo foi colocado em pausa.");
      loadData();
    } catch (err: any) {
      toast.error("Erro ao pausar ciclo", err.message || "Tente novamente");
    }
  };

  const handleRetomarCiclo = async () => {
    if (!cicloAtivo) return;
    try {
      await ciclosApi.retomar(cicloAtivo.id);
      toast.success("Ciclo retomado", "O ciclo produtivo está ativo novamente.");
      loadData();
    } catch (err: any) {
      toast.error("Erro ao retomar ciclo", err.message || "Tente novamente");
    }
  };

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const viv = await viveirosApi.obter(viveiroId);
      setViveiro(viv);

      const cycs: CicloProdutivo[] = await ciclosApi.listar({
        viveiro_id: viveiroId,
      });

      const ciclo = cycs.find((c) => c.status === "ATIVO" || c.status === "PAUSADO") || null;
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
    } catch (err: any) {
      toast.error("Erro ao carregar viveiro", err.message || "Tente novamente");
    } finally {
      setLoading(false);
    }
  }, [viveiroId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-32 bg-white rounded-2xl border border-slate-200">
        <Loader2 className="w-8 h-8 text-ocean-600 animate-spin mb-2" />
        <p className="text-xs text-slate-400 font-medium">Carregando dados do viveiro...</p>
      </div>
    );
  }

  if (!viveiro) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center max-w-md mx-auto mt-12 shadow-sm">
        <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
        <h3 className="text-lg font-bold text-slate-900 mb-2">Viveiro não encontrado</h3>
        <Link href="/gestor/viveiros">
          <Button variant="outline" size="sm">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Voltar para lista de Viveiros
          </Button>
        </Link>
      </div>
    );
  }

  const diasCultivo = cicloAtivo
    ? Math.floor((new Date().getTime() - new Date(cicloAtivo.data_povoamento).getTime()) / (1000 * 60 * 60 * 24))
    : 0;

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Breadcrumb */}
      <Link
        href="/gestor/viveiros"
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Voltar para Viveiros & Lotes
      </Link>

      {/* Header Principal */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 bg-white rounded-2xl border border-slate-200/80 p-6 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-ocean-50 border border-ocean-200 text-ocean-600 flex items-center justify-center shrink-0">
            <Shell className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
                {viveiro.identificacao}
              </h1>
              <Badge variant={viveiro.status_ativo ? "success" : "secondary"}>
                {viveiro.status_ativo ? "Ativo" : "Inativo"}
              </Badge>
            </div>
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <Ruler className="w-3.5 h-3.5 text-slate-400" />
                <strong className="text-slate-700">{viveiro.area_util_m2.toLocaleString("pt-BR")}</strong> m² de área
              </span>
              {viveiro.profundidade_media_m && (
                <span className="flex items-center gap-1">
                  <Droplets className="w-3.5 h-3.5 text-slate-400" />
                  <strong className="text-slate-700">{viveiro.profundidade_media_m}</strong> m de lâmina
                </span>
              )}
              {viveiro.localizacao && (
                <span className="flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-slate-400" />
                  {viveiro.localizacao}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Botões de Ação */}
        <div className="flex flex-wrap gap-2 pt-2 sm:pt-0">
          {!cicloAtivo ? (
            <Button
              onClick={() => setShowCicloModal(true)}
              className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold shadow-md shadow-emerald-600/20"
            >
              <Activity className="w-4 h-4 mr-2" />
              Iniciar Novo Ciclo
            </Button>
          ) : (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowBioModal(true)}
                className="border-slate-300 text-slate-700 hover:bg-slate-50"
              >
                <Scale className="w-4 h-4 mr-2 text-ocean-600" />
                Nova Biometria
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowManejoModal(true)}
                className="border-slate-300 text-slate-700 hover:bg-slate-50"
              >
                <Utensils className="w-4 h-4 mr-2 text-amber-600" />
                Lançar Manejo
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleExportarCsv}
                disabled={exportingCsv}
                className="border-slate-300 text-slate-700 hover:bg-slate-50"
              >
                {exportingCsv ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin text-emerald-600" />
                ) : (
                  <Download className="w-4 h-4 mr-2 text-emerald-600" />
                )}
                Exportar CSV
              </Button>
              {cicloAtivo.status === "ATIVO" ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handlePausarCiclo}
                  className="border-amber-300 text-amber-700 hover:bg-amber-50"
                >
                  <Pause className="w-4 h-4 mr-2" />
                  Pausar
                </Button>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRetomarCiclo}
                  className="border-emerald-300 text-emerald-700 hover:bg-emerald-50"
                >
                  <Play className="w-4 h-4 mr-2" />
                  Retomar
                </Button>
              )}
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setShowEncerrarModal(true)}
              >
                <XCircle className="w-4 h-4 mr-2" />
                Despesca / Encerrar
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Alerta de Viveiro Sem Ciclo Ativo */}
      {!cicloAtivo && (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-sm">
          <div className="w-14 h-14 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center mx-auto mb-4">
            <Activity className="w-7 h-7" />
          </div>
          <h3 className="text-lg font-bold text-slate-900 mb-1">
            Viveiro pronto para povoamento
          </h3>
          <p className="text-sm text-slate-500 mb-6 max-w-sm mx-auto">
            Não há ciclo em curso neste viveiro. Cadastre um novo lote de pós-larvas para ativar o modelo preditivo.
          </p>
          <Button
            onClick={() => setShowCicloModal(true)}
            className="bg-emerald-600 hover:bg-emerald-700 text-white"
          >
            <Plus className="w-4 h-4 mr-2" />
            Iniciar Ciclo de Cultivo
          </Button>
        </div>
      )}

      {/* Conteúdo do Ciclo Ativo */}
      {cicloAtivo && (
        <>
          {/* Faixa Resumo do Ciclo */}
          <div className="rounded-2xl bg-slate-900 text-white p-4 sm:p-5 flex flex-wrap items-center justify-between gap-4 shadow-sm">
            <div className="flex flex-wrap items-center gap-6">
              <div className="flex items-center gap-2">
                <CalendarDays className="w-4 h-4 text-emerald-400" />
                <span className="text-xs text-slate-300">
                  Povoamento: <strong className="text-white ml-1">{fmtDate(cicloAtivo.data_povoamento)}</strong>
                </span>
              </div>

              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-amber-400" />
                <span className="text-xs text-slate-300">
                  Idade do Lote: <strong className="text-white ml-1">{diasCultivo} dias</strong>
                </span>
              </div>

              <div className="flex items-center gap-2">
                <Bug className="w-4 h-4 text-ocean-400" />
                <span className="text-xs text-slate-300">
                  Estocagem: <strong className="text-white ml-1">{cicloAtivo.quantidade_pos_larvas.toLocaleString("pt-BR")} PLs</strong>
                </span>
              </div>

              {cicloAtivo.laboratorio_origem && (
                <span className="text-xs bg-slate-800 text-slate-300 px-3 py-1 rounded-full border border-slate-700">
                  {cicloAtivo.laboratorio_origem}
                </span>
              )}
            </div>

            <Badge
              variant={cicloAtivo.status === "PAUSADO" ? "secondary" : "success"}
              className={cicloAtivo.status === "PAUSADO" ? "bg-amber-500 text-white font-semibold" : ""}
            >
              {cicloAtivo.status === "PAUSADO" ? "Ciclo Pausado" : "Lote em Produção"}
            </Badge>
          </div>

          {/* Abas de Navegação */}
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="metricas">
                <BarChart3 className="w-4 h-4 mr-2" />
                Painel de Indicadores
              </TabsTrigger>
              <TabsTrigger value="biometrias">
                <Scale className="w-4 h-4 mr-2" />
                Biometrias ({biometrias.length})
              </TabsTrigger>
              <TabsTrigger value="manejos">
                <Utensils className="w-4 h-4 mr-2" />
                Manejo & Ração ({manejos.length})
              </TabsTrigger>
            </TabsList>

            {/* ABA 1: MÉTRICAS */}
            <TabsContent value="metricas">
              {metricas ? (
                <div className="space-y-6">
                  {/* Alerta de Hiperdensidade se houver */}
                  {metricas.alerta_hiperdensidade && (
                    <div className="rounded-2xl bg-amber-50 border border-amber-200 p-4 flex items-center gap-3 text-amber-900">
                      <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
                      <div className="text-sm">
                        <strong>Alerta de Hiperdensidade:</strong> A densidade atual calculada ({metricas.densidade_estocagem} camarões/m²) está acima do limite recomendado para este tipo de aeração.
                      </div>
                    </div>
                  )}

                  {/* Grid de KPIs */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <MetricCard
                      title="Peso Médio Amostrado"
                      value={metricas.peso_medio_atual_g != null ? `${metricas.peso_medio_atual_g.toFixed(1)} g` : "Aguardando biometria"}
                      subtitle="Base da última biometria"
                      icon={Scale}
                      accent="ocean"
                    />
                    <MetricCard
                      title="Biomassa Projetada"
                      value={metricas.biomassa_atual_kg != null ? `${metricas.biomassa_atual_kg.toLocaleString("pt-BR")} kg` : "—"}
                      subtitle="Volume vivo em cultivo"
                      icon={TrendingUp}
                      accent="emerald"
                    />
                    <MetricCard
                      title="Sobrevivência Fuzzy"
                      value={`${metricas.taxa_sobrevivencia_fuzzy_pct.toFixed(1)}%`}
                      subtitle="Ajustada por manejo e dias"
                      icon={Activity}
                      accent={metricas.taxa_sobrevivencia_fuzzy_pct < 75 ? "red" : "emerald"}
                    />
                    <MetricCard
                      title="FCA Acumulado"
                      value={metricas.fca_atual ? metricas.fca_atual.toFixed(2) : "—"}
                      subtitle={
                        metricas.classificacao_fca === "ALTA_EFICIENCIA"
                          ? "Alta eficiência alimentar"
                          : metricas.classificacao_fca === "DESPERDICIO_INDICADO"
                          ? "Alerta de desperdício"
                          : "Faixa operacional padrão"
                      }
                      icon={BarChart3}
                      accent={metricas.classificacao_fca === "ALTA_EFICIENCIA" ? "emerald" : "amber"}
                    />
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <MetricCard
                      title="Ração Acumulada"
                      value={`${metricas.racao_acumulada_kg.toLocaleString("pt-BR")} kg`}
                      subtitle="Total consumido na safra"
                      icon={Utensils}
                      accent="amber"
                    />
                    <MetricCard
                      title="População Estimada"
                      value={metricas.populacao_estimada.toLocaleString("pt-BR")}
                      subtitle="Indivíduos vivos no viveiro"
                      icon={Bug}
                      accent="ocean"
                    />
                    <MetricCard
                      title="Custo Total Acumulado"
                      value={`R$ ${metricas.custo_operacional_total_rs.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`}
                      subtitle="Ração + insumos + PLs"
                      icon={DollarSign}
                      accent="purple"
                    />
                    <MetricCard
                      title="Lucro Operacional Est."
                      value={metricas.lucro_operacional_rs != null ? `R$ ${metricas.lucro_operacional_rs.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}` : "Indisponível"}
                      subtitle={metricas.margem_operacional_pct != null ? `Margem estimada: ${metricas.margem_operacional_pct}%` : (metricas.entradas_faltantes && metricas.entradas_faltantes.length > 0 ? `Requer: ${metricas.entradas_faltantes.join(", ")}` : "Receita menos custos")}
                      icon={DollarSign}
                      accent={metricas.lucro_operacional_rs == null ? "neutral" : metricas.lucro_operacional_rs >= 0 ? "emerald" : "red"}
                    />
                  </div>
                </div>
              ) : (
                <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-sm">
                  <BarChart3 className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                  <h4 className="font-bold text-slate-800 mb-1">Aguardando Primeira Biometria</h4>
                  <p className="text-sm text-slate-500 max-w-sm mx-auto mb-6">
                    Registre a primeira amostragem de peso das pós-larvas para liberar os cálculos do modelo Clifford e FCA.
                  </p>
                  <Button onClick={() => setShowBioModal(true)} className="bg-ocean-600 hover:bg-ocean-700 text-white">
                    <Scale className="w-4 h-4 mr-2" />
                    Lançar Primeira Biometria
                  </Button>
                </div>
              )}
            </TabsContent>

            {/* ABA 2: BIOMETRIAS */}
            <TabsContent value="biometrias">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-900 text-base">
                    Curva de Crescimento e Amostragens
                  </h3>
                  <Button size="sm" onClick={() => setShowBioModal(true)} className="bg-ocean-600 hover:bg-ocean-700 text-white">
                    <Plus className="w-4 h-4 mr-2" />
                    Nova Biometria
                  </Button>
                </div>

                {biometrias.length === 0 ? (
                  <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center shadow-sm">
                    <Scale className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                    <p className="text-sm text-slate-500">Nenhuma biometria cadastrada neste ciclo.</p>
                  </div>
                ) : (
                  <div className="grid gap-3">
                    {[...biometrias].reverse().map((bio) => (
                      <div
                        key={bio.id}
                        className="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-sm flex flex-wrap items-center justify-between gap-4"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-xl bg-ocean-50 text-ocean-600 flex items-center justify-center font-bold">
                            <Scale className="w-5 h-5" />
                          </div>
                          <div>
                            <div className="font-bold text-slate-900 text-sm">
                              {fmtDate(bio.data_medicao)}
                            </div>
                            <div className="text-xs text-slate-500">
                              {bio.observacoes || "Amostragem de rotina"}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-6">
                          <div className="text-right">
                            <div className="text-xs text-slate-400">Peso Médio</div>
                            <div className="text-base font-extrabold text-slate-900">
                              {bio.peso_medio_g.toFixed(2)} g
                            </div>
                          </div>

                          {bio.ganho_medio_semanal_g != null && (
                            <div className="text-right">
                              <div className="text-xs text-slate-400">Ganho Semanal</div>
                              <div className={`text-sm font-bold flex items-center gap-1 ${
                                bio.ganho_medio_semanal_g >= 0 ? "text-emerald-600" : "text-red-500"
                              }`}>
                                {bio.ganho_medio_semanal_g >= 0 ? "+" : ""}
                                {bio.ganho_medio_semanal_g.toFixed(2)} g/sem
                              </div>
                            </div>
                          )}

                          {bio.uniformidade_percentual != null && (
                            <Badge variant="outline" className="border-slate-200">
                              {bio.uniformidade_percentual}% Uniforme
                            </Badge>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </TabsContent>

            {/* ABA 3: MANEJOS */}
            <TabsContent value="manejos">
              <div className="space-y-4">
                {/* Banner de Recomendação Clifford */}
                {recomendacao && (
                  <div className="rounded-2xl bg-gradient-to-r from-blue-900 to-indigo-950 p-5 text-white shadow-md">
                    <div className="flex items-center gap-2 text-xs font-bold text-blue-300 uppercase tracking-wider mb-2">
                      <Zap className="w-4 h-4 text-amber-400" />
                      Prescrição de Trato Sugerida (Modelo Clifford)
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-2">
                      <div>
                        <div className="text-xs text-blue-200">Ração Recomendada</div>
                        <div className="text-xl font-black text-white">{recomendacao.racao_diaria_sugerida_kg} kg/dia</div>
                      </div>
                      <div>
                        <div className="text-xs text-blue-200">Taxa de Arraçoamento</div>
                        <div className="text-xl font-black text-white">{recomendacao.taxa_clifford_pct}%</div>
                      </div>
                      <div>
                        <div className="text-xs text-blue-200">Biomassa Estimada</div>
                        <div className="text-xl font-black text-white">{recomendacao.biomassa_estimada_kg} kg</div>
                      </div>
                      <div>
                        <div className="text-xs text-blue-200">Frequência</div>
                        <div className="text-xl font-black text-white">4 tratos/dia</div>
                      </div>
                    </div>
                    <p className="text-xs text-blue-100/90 pt-1 border-t border-white/10">
                      {recomendacao.ajuste_sugerido}
                    </p>
                  </div>
                )}

                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-900 text-base">
                    Histórico de Arraçoamento e Leituras de Bandeja
                  </h3>
                  <Button size="sm" onClick={() => setShowManejoModal(true)} className="bg-amber-600 hover:bg-amber-700 text-white">
                    <Plus className="w-4 h-4 mr-2" />
                    Novo Manejo
                  </Button>
                </div>

                {manejos.length === 0 ? (
                  <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center shadow-sm">
                    <Utensils className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                    <p className="text-sm text-slate-500">Nenhum manejo alimentar registrado neste lote.</p>
                  </div>
                ) : (
                  <div className="grid gap-3">
                    {[...manejos].reverse().map((m) => {
                      const sobraObj = SOBRA_OPTIONS.find((s) => s.value === m.sobra_bandeja_nivel);
                      return (
                        <div
                          key={m.id}
                          className="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-sm flex flex-wrap items-center justify-between gap-4"
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
                              <Utensils className="w-5 h-5" />
                            </div>
                            <div>
                              <div className="font-bold text-slate-900 text-sm">
                                {fmtDate(m.data_registro)}
                              </div>
                              <div className="text-xs text-slate-500">
                                {sobraObj?.desc || m.sobra_bandeja_nivel}
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-4">
                            <div className="text-right">
                              <div className="text-xs text-slate-400">Ração Lançada</div>
                              <div className="text-base font-extrabold text-slate-900">
                                {m.quantidade_racao_kg.toFixed(1)} kg
                              </div>
                            </div>

                            <Badge
                              variant={
                                m.sobra_bandeja_nivel === "SEM_SOBRA"
                                  ? "success"
                                  : m.sobra_bandeja_nivel === "SOBRA_LEVE"
                                  ? "warning"
                                  : "destructive"
                              }
                            >
                              {sobraObj?.label || m.sobra_bandeja_nivel}
                            </Badge>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </>
      )}

      {/* Diálogos Integrados */}
      <IniciarCicloDialog
        open={showCicloModal}
        onClose={() => setShowCicloModal(false)}
        onCreated={loadData}
        viveiroId={viveiroId}
      />

      {cicloAtivo && (
        <>
          <BiometriaDialog
            open={showBioModal}
            onClose={() => setShowBioModal(false)}
            onCreated={loadData}
            cicloId={cicloAtivo.id}
          />
          <ManejoDialog
            open={showManejoModal}
            onClose={() => setShowManejoModal(false)}
            onCreated={loadData}
            cicloId={cicloAtivo.id}
            recomendacao={recomendacao}
          />
          <EncerrarCicloDialog
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
