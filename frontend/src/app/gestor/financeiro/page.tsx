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
  Receipt,
  PieChart,
  Download,
  Percent,
  AlertTriangle,
  Scale,
  Wallet,
} from "lucide-react";
import { ciclosApi, custosApi, viveirosApi } from "@/lib/api";
import { mensagemErro } from "@/lib/utils";
import type { CicloProdutivo, Viveiro, CustoOperacional, CustoResumo, FinanceiroCiclo } from "@/lib/types";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { toast } from "@/components/ui/toast";
import { FASES, fmtData, fmtMoney, fmtQtd } from "@/components/insumos/lista-usos-insumo";
import { TIPOS_VENDA } from "@/components/viveiro/vendas-ciclo";

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

const ORDEM_FASES = Object.keys(FASES);

const STATUS_CICLO: Record<string, string> = {
  PLANEJADO: "Planejado",
  ATIVO: "Ativo",
  PAUSADO: "Pausado",
  FINALIZADO: "Finalizado",
  CANCELADO: "Cancelado",
};

/** Resultado do ciclo: lucro realizado e lucro estimado (sempre rotulados), margem, custo por kg e avisos. */
function ResultadoCiclo({ dados }: { dados: FinanceiroCiclo }) {
  const { definitivo } = dados;
  const fases = Object.entries(dados.custos_por_fase).sort(([a], [b]) => ORDEM_FASES.indexOf(a) - ORDEM_FASES.indexOf(b));
  const estimado = dados.lucro_estimado_se_despescar_hoje_rs;
  return (
    <div className="space-y-6">
      {dados.usos_pendentes > 0 && (
        <div className="flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            {dados.usos_pendentes === 1 ? "1 uso sem valor" : `${dados.usos_pendentes} usos sem valor`}: o custo ainda
            não entrou no ciclo, então custos e lucros estão incompletos. Registre a compra do insumo ou corrija o
            preço do uso.
          </span>
        </div>
      )}
      {dados.valores_recalculados_em && (
        <p className="text-xs text-slate-500">
          Valores recalculados em {new Date(dados.valores_recalculados_em).toLocaleDateString("pt-BR")} (lançamento
          retroativo de insumo).
        </p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard
          label="Receita realizada"
          value={fmtMoney(dados.receita_realizada_rs)}
          accentColor="emerald"
          icon={Receipt}
          subtitle="Soma das vendas do ciclo"
        />
        <MetricCard
          label="Custo total"
          value={fmtMoney(dados.custo_total_rs)}
          accentColor="coral"
          icon={Wallet}
          subtitle="Todos os custos lançados no ciclo"
        />
        <MetricCard
          label="Lucro realizado"
          value={fmtMoney(dados.lucro_realizado_rs)}
          accentColor={dados.lucro_realizado_rs >= 0 ? "emerald" : "coral"}
          icon={DollarSign}
          badge={{ text: definitivo ? "Definitivo" : "Parcial", variant: definitivo ? "success" : "warning" }}
          subtitle={
            definitivo
              ? "Receita das vendas − custos lançados"
              : "Receita das vendas já feitas − custos lançados até agora"
          }
        />
        <MetricCard
          label="Lucro estimado se despescar hoje"
          value={estimado !== null ? fmtMoney(estimado) : "Indisponível"}
          accentColor={estimado === null ? "slate" : estimado >= 0 ? "emerald" : "coral"}
          icon={TrendingUp}
          badge={{ text: "Estimativa", variant: "info" }}
          subtitle={
            estimado !== null
              ? "Lucro realizado + biomassa na água ao preço de hoje"
              : definitivo
                ? "Ciclo finalizado: vale o lucro realizado"
                : "Falta biometria ou preço de venda para estimar"
          }
        />
        <MetricCard
          label="Margem realizada"
          value={dados.margem_realizada_pct !== null ? `${fmtQtd(dados.margem_realizada_pct)}%` : "—"}
          accentColor="slate"
          icon={Percent}
          subtitle={dados.margem_realizada_pct !== null ? "Lucro realizado ÷ receita realizada" : "Sem receita de vendas"}
        />
        <MetricCard
          label="Custo por kg"
          value={dados.custo_por_kg_rs !== null ? fmtMoney(dados.custo_por_kg_rs) : "—"}
          accentColor="slate"
          icon={Scale}
          subtitle={dados.custo_por_kg_rs !== null ? "Custo total ÷ kg vendidos" : "Sem biomassa vendida"}
        />
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <PieChart className="w-4 h-4 text-sky-600" />
            Custos por fase e categoria
          </CardTitle>
        </CardHeader>
        <CardContent>
          {fases.length === 0 ? (
            <p className="py-6 text-center text-xs text-slate-400">Nenhum custo lançado neste ciclo.</p>
          ) : (
            <div className="space-y-5">
              {fases.map(([fase, total]) => (
                <div key={fase}>
                  <div className="flex justify-between text-sm font-bold text-slate-800 pb-1 border-b border-slate-100">
                    <span>{FASES[fase as keyof typeof FASES] ?? fase}</span>
                    <span className="tabular-nums">{fmtMoney(total)}</span>
                  </div>
                  <ul className="mt-2 space-y-1">
                    {dados.custos_fase_categoria
                      .filter((c) => c.fase === fase)
                      .sort((a, b) => b.total_rs - a.total_rs)
                      .map((c) => (
                        <li key={c.categoria} className="flex justify-between text-xs text-slate-600">
                          <span className="flex items-center gap-2">
                            <span
                              className="inline-block h-2 w-2 rounded-full"
                              style={{ background: CAT_COLORS[c.categoria] || "#94a3b8" }}
                            />
                            {CATEGORIAS[c.categoria] || c.categoria}
                          </span>
                          <span className="tabular-nums">{fmtMoney(c.total_rs)}</span>
                        </li>
                      ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Receipt className="w-4 h-4 text-sky-600" />
              Vendas do ciclo
            </CardTitle>
            <Badge variant="secondary">{dados.vendas.length} registros</Badge>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          {dados.vendas.length === 0 ? (
            <p className="py-6 text-center text-xs text-slate-400">Nenhuma venda registrada neste ciclo.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {dados.vendas.map((v) => (
                <li key={v.id} className="py-3 flex flex-wrap items-center justify-between gap-2 text-xs">
                  <span className="flex items-center gap-2 font-semibold text-slate-700">
                    {fmtData(v.data_venda)}
                    <Badge variant={v.tipo === "DESPESCA_FINAL" ? "success" : "info"}>{TIPOS_VENDA[v.tipo]}</Badge>
                  </span>
                  <span className="text-slate-600 tabular-nums">
                    {fmtQtd(v.biomassa_kg)} kg · {fmtQtd(v.peso_medio_g)} g · {fmtMoney(v.preco_kg)}/kg
                  </span>
                  <strong className="text-sm text-slate-900 tabular-nums">{fmtMoney(v.valor_total_rs)}</strong>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function FinanceiroPage() {
  const [viveiros, setViveiros] = useState<Viveiro[]>([]);
  const [ciclos, setCiclos] = useState<CicloProdutivo[]>([]);
  const [selectedCiclo, setSelectedCiclo] = useState("");
  const [custos, setCustos] = useState<CustoOperacional[]>([]);
  const [resumo, setResumo] = useState<CustoResumo[]>([]);
  const [loading, setLoading] = useState(true);
  const [falhouCiclos, setFalhouCiclos] = useState(false);
  // Guardado com o ciclo a que pertence: trocar de ciclo não mostra o resultado do anterior
  const [financeiro, setFinanceiro] = useState<{ cicloId: string; dados: FinanceiroCiclo | null } | null>(null);
  const [versaoFinanceiro, setVersaoFinanceiro] = useState(0);

  // Modals state
  const [showCustoModal, setShowCustoModal] = useState(false);
  const [custoForm, setCustoForm] = useState({
    data_lancamento: new Date().toISOString().split("T")[0],
    categoria: "RACAO",
    descricao: "",
    valor_rs: "",
  });
  const [custoSubmitting, setCustoSubmitting] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [vivs, cycs] = await Promise.all([
          viveirosApi.listar(),
          ciclosApi.listar(),
        ]);
        setViveiros(vivs);
        setCiclos(cycs);
        // Qualquer ciclo pode ser consultado (o finalizado mostra o lucro definitivo); começa pelo que está em curso
        const emCurso = cycs.find((c) => c.status === "ATIVO" || c.status === "PAUSADO");
        if (cycs.length > 0) setSelectedCiclo((emCurso ?? cycs[0]).id);
      } catch (err) {
        setFalhouCiclos(true);
        toast.error("Não foi possível carregar os ciclos", mensagemErro(err, "Tente novamente"));
      } finally { setLoading(false); }
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
      } catch (err) {
        toast.error("Não foi possível carregar os custos do ciclo", mensagemErro(err, "Tente novamente"));
      }
    }
    loadCustos();
  }, [selectedCiclo]);

  useEffect(() => {
    if (!selectedCiclo) return;
    let ativo = true;
    ciclosApi
      .financeiro(selectedCiclo)
      .then((dados) => {
        if (ativo) setFinanceiro({ cicloId: selectedCiclo, dados });
      })
      .catch((err) => {
        if (ativo) {
          setFinanceiro({ cicloId: selectedCiclo, dados: null });
          toast.error("Não foi possível carregar o resultado do ciclo", mensagemErro(err, "Tente novamente"));
        }
      });
    return () => {
      ativo = false;
    };
  }, [selectedCiclo, versaoFinanceiro]);

  const resultado = financeiro && financeiro.cicloId === selectedCiclo ? financeiro : null;

  const refreshCustos = async () => {
    if (!selectedCiclo) return;
    const [cs, rs] = await Promise.all([
      custosApi.listar(selectedCiclo),
      custosApi.resumo(selectedCiclo),
    ]);
    setCustos(cs);
    setResumo(rs);
    setVersaoFinanceiro((v) => v + 1);
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
            Acompanhamento dos custos acumulados do ciclo. A tabela de preços de venda fica no Simulador ΔV.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {selectedCiclo && (
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

          <Button onClick={() => setShowCustoModal(true)} disabled={ciclos.length === 0} size="sm">
            <Plus className="w-4 h-4" /> Lançar Despesa
          </Button>
        </div>
      </div>

      {/* ── KPI Metric Cards (Inspirados em 112858.png + RF-019/RN-014) ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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

      {/* ── Custos operacionais do ciclo ── */}
      <div className="space-y-6">
        {falhouCiclos ? (
          <Card className="p-10 text-center">
            <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
            <h3 className="font-bold text-slate-800">Não foi possível carregar os ciclos</h3>
            <p className="text-xs text-slate-500 mt-1">Recarregue a página para tentar novamente.</p>
          </Card>
        ) : ciclos.length === 0 ? (
          <Card className="p-10 text-center">
            <Shell className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <h3 className="font-bold text-slate-800">Nenhum ciclo encontrado</h3>
            <p className="text-xs text-slate-500 mt-1">Planeje um ciclo em um viveiro para lançar despesas.</p>
          </Card>
        ) : (
          <>
            {/* Seletor de Ciclo */}
            <div className="flex flex-col sm:flex-row items-end gap-3 bg-white p-4 rounded-2xl border border-slate-200">
              <div className="flex-1 w-full">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-1.5">
                  Viveiro / Ciclo
                </label>
                <select
                  value={selectedCiclo}
                  onChange={(e) => setSelectedCiclo(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-semibold text-slate-800 focus:border-sky-500 focus:outline-none"
                >
                  {ciclos.map((c) => (
                    <option key={c.id} value={c.id}>
                      {getViveiroName(c.viveiro_id)} — {c.quantidade_pos_larvas === null ? "Previsto para" : "Povoado em"} {fmtData(c.data_povoamento)} · {STATUS_CICLO[c.status] ?? c.status} (Lote #{c.id.substring(0, 6)})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Resultado do ciclo: lucros, margem, custo por kg, custos por fase e vendas */}
            {resultado === null && (
              <div className="flex justify-center py-8">
                <Loader2 className="w-6 h-6 text-sky-500 animate-spin" />
              </div>
            )}
            {resultado !== null && resultado.dados === null && (
              <Card className="p-8 text-center">
                <p className="text-xs text-red-500">Não foi possível carregar o resultado do ciclo.</p>
                <Button size="sm" variant="outline" className="mt-3" onClick={() => setVersaoFinanceiro((v) => v + 1)}>
                  Tentar novamente
                </Button>
              </Card>
            )}
            {resultado?.dados && <ResultadoCiclo dados={resultado.dados} />}

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
                          <span className="font-semibold text-slate-700">{fmtData(c.data_lancamento)}</span>
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
      </div>

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
    </div>
  );
}
