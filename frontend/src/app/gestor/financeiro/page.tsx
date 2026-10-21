"use client";

import { useEffect, useState } from "react";
import {
  DollarSign,
  Plus,
  Loader2,
  Shell,
  CalendarDays,
  BarChart3,
  TrendingUp,
  Tag,
  Receipt,
  PieChart,
  Download,
  Percent,
} from "lucide-react";
import { ciclosApi, custosApi, precosApi, viveirosApi } from "@/lib/api";
import { mensagemErro } from "@/lib/utils";
import type { CicloProdutivo, Viveiro, CustoOperacional, CustoResumo, PrecoMercado } from "@/lib/types";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { toast } from "@/components/ui/toast";

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
  RACAO: "#f97316",
  ENERGIA_ELETRICA: "#f59e0b",
  MAO_DE_OBRA: "#0284c7",
  POS_LARVAS: "#10b981",
  PROBIOTICOS_QUIMICOS: "#8b5cf6",
  MANUTENCAO: "#64748b",
  OUTROS: "#94a3b8",
};

function fmtMoney(v: number) {
  return `R$ ${v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtDate(d: string) {
  return new Date(d).toLocaleDateString("pt-BR");
}

export default function FinanceiroPage() {
  const [tab, setTab] = useState("custos");
  const [viveiros, setViveiros] = useState<Viveiro[]>([]);
  const [ciclos, setCiclos] = useState<CicloProdutivo[]>([]);
  const [selectedCiclo, setSelectedCiclo] = useState("");
  const [custos, setCustos] = useState<CustoOperacional[]>([]);
  const [resumo, setResumo] = useState<CustoResumo[]>([]);
  const [precos, setPrecos] = useState<PrecoMercado[]>([]);
  const [loading, setLoading] = useState(true);

  // Modals state
  const [showCustoModal, setShowCustoModal] = useState(false);
  const [custoForm, setCustoForm] = useState({
    data_lancamento: new Date().toISOString().split("T")[0],
    categoria: "RACAO",
    descricao: "",
    valor_rs: "",
  });
  const [custoSubmitting, setCustoSubmitting] = useState(false);

  const [showPrecoModal, setShowPrecoModal] = useState(false);
  const [precoForm, setPrecoForm] = useState({
    faixa_gramatura_min: "",
    faixa_gramatura_max: "",
    preco_por_kg: "",
    vigencia_inicio: new Date().toISOString().split("T")[0],
    vigencia_fim: "",
  });
  const [precoSubmitting, setPrecoSubmitting] = useState(false);

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

  const handleCustoSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCiclo) return;
    setCustoSubmitting(true);
    try {
      await custosApi.criar(selectedCiclo, {
        data_lancamento: custoForm.data_lancamento,
        categoria: custoForm.categoria,
        descricao: custoForm.descricao,
        valor_rs: parseFloat(custoForm.valor_rs),
      });
      toast.success("Custo lançado com sucesso!", `${custoForm.descricao} — ${fmtMoney(parseFloat(custoForm.valor_rs))}`);
      await refreshCustos();
      setShowCustoModal(false);
      setCustoForm({
        data_lancamento: new Date().toISOString().split("T")[0],
        categoria: "RACAO",
        descricao: "",
        valor_rs: "",
      });
    } catch (err) {
      toast.error("Erro ao lançar custo", mensagemErro(err, "Tente novamente"));
    } finally {
      setCustoSubmitting(false);
    }
  };

  const handlePrecoSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPrecoSubmitting(true);
    try {
      await precosApi.criar({
        faixa_gramatura_min: parseFloat(precoForm.faixa_gramatura_min),
        faixa_gramatura_max: parseFloat(precoForm.faixa_gramatura_max),
        preco_por_kg: parseFloat(precoForm.preco_por_kg),
        vigencia_inicio: precoForm.vigencia_inicio,
        vigencia_fim: precoForm.vigencia_fim || null,
      });
      toast.success("Preço de mercado cadastrado!", `${precoForm.faixa_gramatura_min}g–${precoForm.faixa_gramatura_max}g a ${fmtMoney(parseFloat(precoForm.preco_por_kg))}/kg`);
      const prcs = await precosApi.listar();
      setPrecos(prcs);
      setShowPrecoModal(false);
      setPrecoForm({
        faixa_gramatura_min: "",
        faixa_gramatura_max: "",
        preco_por_kg: "",
        vigencia_inicio: new Date().toISOString().split("T")[0],
        vigencia_fim: "",
      });
    } catch (err) {
      toast.error("Erro ao cadastrar preço", mensagemErro(err, "Tente novamente"));
    } finally {
      setPrecoSubmitting(false);
    }
  };

  const getViveiroName = (vId: string) => viveiros.find((v) => v.id === vId)?.identificacao || "—";
  const totalCustos = resumo.reduce((sum, r) => sum + r.total_rs, 0);
  const maiorCategoria = resumo.length > 0 ? [...resumo].sort((a, b) => b.total_rs - a.total_rs)[0] : null;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* ── Page Header Inspirado na Captura de Gestão Financeira ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Módulo Econômico
            </span>
            <span className="h-1 w-1 rounded-full bg-slate-300" />
            <span className="text-xs font-semibold text-sky-600">
              Controle de Despesas & Insumos
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            Gestão Financeira e Custos
          </h1>
          <p className="text-slate-500 text-xs mt-1">
            Acompanhamento de custos acumulados do ciclo e cotação de venda no frigorífico.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {tab === "custos" && selectedCiclo && (
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                try {
                  await custosApi.exportarCsv(selectedCiclo);
                  toast.success("Download concluído!", "Arquivo CSV de custos baixado com sucesso.");
                } catch (err) {
                  toast.error("Erro na exportação", mensagemErro(err, "Tente novamente"));
                }
              }}
            >
              <Download className="w-4 h-4 mr-1.5 text-slate-600" />
              Exportar CSV
            </Button>
          )}

          {tab === "custos" ? (
            <Button onClick={() => setShowCustoModal(true)} disabled={ciclos.length === 0} size="sm">
              <Plus className="w-4 h-4" /> Lançar Despesa
            </Button>
          ) : (
            <Button onClick={() => setShowPrecoModal(true)} size="sm" variant="emerald">
              <Plus className="w-4 h-4" /> Nova Faixa de Preço
            </Button>
          )}
        </div>
      </div>

      {/* ── KPI Metric Cards (Inspirados em 112858.png + RF-019/RN-014) ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          label="Custo Operacional Total"
          value={fmtMoney(totalCustos)}
          accentColor="coral"
          icon={DollarSign}
          badge={{
            text: `${custos.length} lançamentos`,
            variant: "destructive",
          }}
          subtitle="Acumulado do ciclo selecionado"
        />

        <MetricCard
          label="Principal Centro de Custo"
          value={maiorCategoria ? CATEGORIAS[maiorCategoria.categoria] || maiorCategoria.categoria : "—"}
          accentColor="amber"
          icon={PieChart}
          badge={{
            text: maiorCategoria ? `${((maiorCategoria.total_rs / (totalCustos || 1)) * 100).toFixed(0)}% do total` : "—",
            variant: "warning",
          }}
          subtitle={maiorCategoria ? fmtMoney(maiorCategoria.total_rs) : "Sem dados"}
        />

        <MetricCard
          label="Tabela de Mercado"
          value={`${precos.length} faixas`}
          accentColor="ocean"
          icon={Tag}
          badge={{
            text: "Cotações vigentes",
            variant: "info",
          }}
          subtitle="Atualizado recentemente"
        />

        {/* ROA (RF-019, RN-014, Critério 4: não exibir como zero quando faltar insumo) */}
        <MetricCard
          label="ROA (Retorno s/ Ativo)"
          value="Indisponível"
          accentColor="slate"
          icon={Percent}
          badge={{
            text: "Requer Ativo Total",
            variant: "neutral",
          }}
          subtitle="Lucro Líquido / Ativo Total"
        />

        {/* ROE (RF-019, RN-014, Critério 4: não exibir como zero quando faltar insumo) */}
        <MetricCard
          label="ROE (Retorno s/ Patrimônio)"
          value="Indisponível"
          accentColor="slate"
          icon={TrendingUp}
          badge={{
            text: "Requer Patr. Líquido",
            variant: "neutral",
          }}
          subtitle="Lucro Líquido / Patrimônio Líquido"
        />
      </div>

      {/* ── Navegação por Abas (Tabs) ── */}
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="custos">
            <DollarSign className="w-4 h-4 mr-1.5" /> Custos Operacionais
          </TabsTrigger>
          <TabsTrigger value="precos">
            <Tag className="w-4 h-4 mr-1.5" /> Tabela de Preços do Mercado
          </TabsTrigger>
        </TabsList>

        {/* ── Aba Custos ── */}
        <TabsContent value="custos" className="space-y-6">
          {ciclos.length === 0 ? (
            <Card className="p-10 text-center">
              <Shell className="w-10 h-10 text-slate-300 mx-auto mb-3" />
              <h3 className="font-bold text-slate-800">Nenhum ciclo ativo encontrado</h3>
              <p className="text-xs text-slate-500 mt-1">Inicie um ciclo em um viveiro para lançar despesas.</p>
            </Card>
          ) : (
            <>
              {/* Seletor de Ciclo */}
              <div className="flex flex-col sm:flex-row items-end gap-3 bg-white p-4 rounded-2xl border border-slate-200">
                <div className="flex-1 w-full">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-1.5">
                    Filtrar por Viveiro / Ciclo Ativo
                  </label>
                  <select
                    value={selectedCiclo}
                    onChange={(e) => setSelectedCiclo(e.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-semibold text-slate-800 focus:border-sky-500 focus:outline-none"
                  >
                    {ciclos.map((c) => (
                      <option key={c.id} value={c.id}>
                        {getViveiroName(c.viveiro_id)} — Povoado em {fmtDate(c.data_povoamento)} (Lote #{c.id.substring(0, 6)})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Distribuição por Categoria de Custo */}
              {resumo.length > 0 && (
                <Card>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base flex items-center gap-2">
                        <BarChart3 className="w-4 h-4 text-sky-600" />
                        Distribuição por Categoria
                      </CardTitle>
                      <span className="text-xs font-bold text-slate-500">
                        Total: <strong className="text-slate-900">{fmtMoney(totalCustos)}</strong>
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {resumo.sort((a, b) => b.total_rs - a.total_rs).map((r) => {
                        const pct = totalCustos > 0 ? (r.total_rs / totalCustos) * 100 : 0;
                        return (
                          <div key={r.categoria}>
                            <div className="flex justify-between text-xs mb-1 font-semibold">
                              <span className="text-slate-700">{CATEGORIAS[r.categoria] || r.categoria}</span>
                              <span className="text-slate-900 tabular-nums">
                                {fmtMoney(r.total_rs)} <span className="text-slate-400 font-normal">({pct.toFixed(1)}%)</span>
                              </span>
                            </div>
                            <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                              <div
                                className="h-full rounded-full transition-all duration-500"
                                style={{ width: `${pct}%`, background: CAT_COLORS[r.categoria] || "#94a3b8" }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Tabela de Lançamentos de Despesas */}
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Receipt className="w-4 h-4 text-sky-600" />
                      Histórico de Despesas Lançadas
                    </CardTitle>
                    <Badge variant="secondary">{custos.length} registros</Badge>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  {custos.length === 0 ? (
                    <div className="py-12 text-center text-xs text-slate-400">
                      Nenhuma despesa registrada para este ciclo ainda.
                    </div>
                  ) : (
                    <div className="divide-y divide-slate-100">
                      {[...custos].reverse().map((c) => (
                        <div key={c.id} className="py-3 flex flex-wrap items-center justify-between gap-3 text-xs">
                          <div className="flex items-center gap-3 min-w-[140px]">
                            <CalendarDays className="w-4 h-4 text-slate-400 shrink-0" />
                            <span className="font-semibold text-slate-700">{fmtDate(c.data_lancamento)}</span>
                          </div>

                          <div className="w-36">
                            <span
                              className="inline-block px-2 py-0.5 rounded-md text-[11px] font-bold"
                              style={{
                                background: `${CAT_COLORS[c.categoria] || "#94a3b8"}15`,
                                color: CAT_COLORS[c.categoria] || "#64748b",
                                border: `1px solid ${CAT_COLORS[c.categoria] || "#94a3b8"}30`,
                              }}
                            >
                              {CATEGORIAS[c.categoria] || c.categoria}
                            </span>
                          </div>

                          <span className="flex-1 min-w-[180px] font-medium text-slate-600 truncate">
                            {c.descricao}
                          </span>

                          <span className="font-black text-slate-900 tabular-nums text-sm">
                            {fmtMoney(c.valor_rs)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>

        {/* ── Aba Preços de Mercado ── */}
        <TabsContent value="precos" className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {precos.map((p) => (
              <Card key={p.id} className="border-t-4 border-t-emerald-500">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                      Faixa Zootécnica
                    </span>
                    <Badge variant="success">Vigente</Badge>
                  </div>
                  <CardTitle className="text-xl font-black text-slate-900 mt-1">
                    {p.faixa_gramatura_min}g a {p.faixa_gramatura_max}g
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-black text-emerald-600 tabular-nums">
                    {fmtMoney(p.preco_por_kg)} <span className="text-xs font-semibold text-slate-400">/ kg</span>
                  </p>
                  <p className="text-[11px] text-slate-400 mt-2 border-t border-slate-100 pt-2">
                    Início: {fmtDate(p.vigencia_inicio)}
                    {p.vigencia_fim ? ` • Até: ${fmtDate(p.vigencia_fim)}` : " • Preço atual de tabela"}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* ── Modal Lançar Custo (Shadcn Dialog) ── */}
      <Dialog
        open={showCustoModal}
        onOpenChange={setShowCustoModal}
        title="Lançar Custo Operacional"
        description="Registre uma despesa zootécnica ou operacional deste ciclo"
      >
        <form onSubmit={handleCustoSubmit} className="space-y-4 pt-2">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Data de Lançamento *</Label>
              <Input
                required
                type="date"
                value={custoForm.data_lancamento}
                onChange={(e) => setCustoForm({ ...custoForm, data_lancamento: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>Categoria *</Label>
              <select
                value={custoForm.categoria}
                onChange={(e) => setCustoForm({ ...custoForm, categoria: e.target.value })}
                className="w-full mt-1 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-slate-800 focus:border-sky-500 focus:outline-none h-11"
              >
                {Object.entries(CATEGORIAS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <Label>Descrição da Despesa *</Label>
            <Input
              required
              minLength={3}
              value={custoForm.descricao}
              onChange={(e) => setCustoForm({ ...custoForm, descricao: e.target.value })}
              placeholder="Ex: 50 sacos ração 35% proteína"
              className="mt-1"
            />
          </div>

          <div>
            <Label>Valor Total (R$) *</Label>
            <Input
              required
              type="number"
              step="0.01"
              min="0.01"
              value={custoForm.valor_rs}
              onChange={(e) => setCustoForm({ ...custoForm, valor_rs: e.target.value })}
              placeholder="1500.00"
              className="mt-1 text-lg font-bold"
            />
          </div>

          <div className="pt-2 flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setShowCustoModal(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={custoSubmitting}>
              {custoSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Confirmar Despesa
            </Button>
          </div>
        </form>
      </Dialog>

      {/* ── Modal Novo Preço (Shadcn Dialog) ── */}
      <Dialog
        open={showPrecoModal}
        onOpenChange={setShowPrecoModal}
        title="Cadastrar Preço de Mercado"
        description="Defina uma cotação por gramatura para cálculo da receita bruta"
      >
        <form onSubmit={handlePrecoSubmit} className="space-y-4 pt-2">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Gramatura Mínima (g) *</Label>
              <Input
                required
                type="number"
                step="0.1"
                min="0"
                value={precoForm.faixa_gramatura_min}
                onChange={(e) => setPrecoForm({ ...precoForm, faixa_gramatura_min: e.target.value })}
                placeholder="8.0"
                className="mt-1"
              />
            </div>
            <div>
              <Label>Gramatura Máxima (g) *</Label>
              <Input
                required
                type="number"
                step="0.1"
                min="0"
                value={precoForm.faixa_gramatura_max}
                onChange={(e) => setPrecoForm({ ...precoForm, faixa_gramatura_max: e.target.value })}
                placeholder="12.0"
                className="mt-1"
              />
            </div>
          </div>

          <div>
            <Label>Preço por Quilo (R$/kg) *</Label>
            <Input
              required
              type="number"
              step="0.01"
              min="0.01"
              value={precoForm.preco_por_kg}
              onChange={(e) => setPrecoForm({ ...precoForm, preco_por_kg: e.target.value })}
              placeholder="26.50"
              className="mt-1 text-lg font-bold"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Início da Vigência *</Label>
              <Input
                required
                type="date"
                value={precoForm.vigencia_inicio}
                onChange={(e) => setPrecoForm({ ...precoForm, vigencia_inicio: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label>Fim da Vigência (Opcional)</Label>
              <Input
                type="date"
                value={precoForm.vigencia_fim}
                onChange={(e) => setPrecoForm({ ...precoForm, vigencia_fim: e.target.value })}
                className="mt-1"
              />
            </div>
          </div>

          <div className="pt-2 flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setShowPrecoModal(false)}>
              Cancelar
            </Button>
            <Button type="submit" variant="emerald" disabled={precoSubmitting}>
              {precoSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Salvar Preço
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
