"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Check, CheckCircle2, Loader2, Pencil, Plus, Tag, Trash2, X } from "lucide-react";
import { organizacoesApi, precosApi } from "@/lib/api";
import { mensagemErro } from "@/lib/utils";
import type { Organizacao, PrecoMercado, RegraArredondamento } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/toast";

// Data local (toISOString usaria UTC e, à noite no Brasil, já seria o dia seguinte)
function hoje() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

const fmtMoney = (v: number) =>
  `R$ ${v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const fmtPeso = (v: number) => v.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
const fmtData = (d: string) => new Date(`${d}T00:00:00`).toLocaleDateString("pt-BR");

const formVazio = () => ({ min: "", max: "", preco: "", incremento: "1", inicio: hoje(), fim: "" });

const REGRAS: { valor: RegraArredondamento; rotulo: string }[] = [
  { valor: "PARA_BAIXO", rotulo: "Para baixo (12,7 g conta 12 g)" },
  { valor: "PARA_CIMA", rotulo: "Para cima (12,1 g conta 13 g)" },
  { valor: "PROPORCIONAL", rotulo: "Exato, sem arredondar" },
];

// Mesma regra do servidor (decision_engine.peso_para_preco): 6 casas antes do floor/ceil
function pesoParaPreco(peso: number, regra: RegraArredondamento): number {
  const p = Math.round(peso * 1e6) / 1e6;
  return regra === "PARA_BAIXO" ? Math.floor(p) : regra === "PARA_CIMA" ? Math.ceil(p) : p;
}

// Preço da tabela: preço de 10 g mais o incremento por grama acima de 10 g
const precoDaFaixa = (p: PrecoMercado, peso: number) =>
  Math.round((p.preco_por_kg + p.incremento_por_g * (peso - 10)) * 100) / 100;

function validar(f: ReturnType<typeof formVazio>): string | null {
  const min = parseFloat(f.min);
  const max = parseFloat(f.max);
  const preco = parseFloat(f.preco);
  const incremento = parseFloat(f.incremento);
  if (Number.isNaN(min) || Number.isNaN(max) || Number.isNaN(preco) || Number.isNaN(incremento)) {
    return "Preencha o peso mínimo, o peso máximo, o preço e o incremento por grama.";
  }
  if (incremento < 0) return "O incremento por grama não pode ser negativo.";
  if (min < 0) return "O peso mínimo não pode ser negativo.";
  if (max <= min) return "O peso máximo deve ser maior que o mínimo.";
  if (preco <= 0) return "O preço deve ser maior que zero.";
  if (f.fim && f.fim < f.inicio) return "O fim da vigência não pode ser anterior ao início.";
  return null;
}

interface Props {
  /** Peso médio atual do lote (g), para mostrar qual faixa se aplica; null se ainda não há biometria. */
  pesoAtualG: number | null;
  /** Chamado depois de cadastrar, editar ou excluir uma faixa (resultados da simulação ficam velhos). */
  onAlterado?: () => void;
}

export default function TabelaPrecosCard({ pesoAtualG, onAlterado }: Props) {
  const [precos, setPrecos] = useState<PrecoMercado[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(formVazio);
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [precoEditado, setPrecoEditado] = useState("");
  const [ocupadoId, setOcupadoId] = useState<string | null>(null);
  const [incrementoEditado, setIncrementoEditado] = useState("");
  const [org, setOrg] = useState<Organizacao | null>(null);
  const regra: RegraArredondamento = org?.regra_arredondamento ?? "PARA_BAIXO";

  const recarregar = useCallback(async () => {
    try {
      setPrecos(await precosApi.listar(false));
    } catch (err) {
      toast.error("Não foi possível carregar a tabela de preços", mensagemErro(err, "Tente novamente"));
    }
  }, []);

  useEffect(() => {
    let ativo = true;
    async function carregar() {
      try {
        const [todas, orgs] = await Promise.all([precosApi.listar(false), organizacoesApi.listar()]);
        if (ativo) {
          setPrecos(todas);
          setOrg(orgs[0] ?? null);
        }
      } catch (err) {
        toast.error("Não foi possível carregar a tabela de preços", mensagemErro(err, "Tente novamente"));
      } finally {
        if (ativo) setLoading(false);
      }
    }
    carregar();
    return () => {
      ativo = false;
    };
  }, []);

  // O servidor só usa faixas vigentes hoje; futuras e encerradas aparecem esmaecidas na lista
  const hojeStr = hoje();
  const situacao = (p: PrecoMercado): "vigente" | "futura" | "encerrada" =>
    p.vigencia_inicio > hojeStr ? "futura" : p.vigencia_fim && p.vigencia_fim < hojeStr ? "encerrada" : "vigente";
  const ordemSituacao = { vigente: 0, futura: 1, encerrada: 2 } as const;
  const lista = [...precos].sort(
    (a, b) =>
      ordemSituacao[situacao(a)] - ordemSituacao[situacao(b)] || a.faixa_gramatura_min - b.faixa_gramatura_min
  );
  const vigentes = precos.filter((p) => situacao(p) === "vigente");

  const pesoPreco = pesoAtualG == null ? null : pesoParaPreco(pesoAtualG, regra);

  // Mesma regra do servidor: peso arredondado pelo acordo; na divisa entre duas faixas vale a de cima
  const faixaDoPeso =
    pesoPreco == null
      ? undefined
      : vigentes
          .filter((p) => p.faixa_gramatura_min <= pesoPreco && pesoPreco <= p.faixa_gramatura_max)
          .sort((a, b) => b.faixa_gramatura_min - a.faixa_gramatura_min)[0];

  const trocarRegra = async (nova: RegraArredondamento) => {
    if (!org) return;
    try {
      setOrg(await organizacoesApi.atualizar(org.id, { regra_arredondamento: nova }));
      toast.success("Regra de arredondamento atualizada", REGRAS.find((r) => r.valor === nova)?.rotulo ?? nova);
      onAlterado?.();
    } catch (err) {
      toast.error("Não foi possível salvar a regra", mensagemErro(err, "Tente novamente"));
    }
  };

  const preencherComPesoAtual = () => {
    if (pesoAtualG == null) return;
    const min = Math.floor(pesoAtualG);
    // Não invade a faixa seguinte (evita o erro de sobreposição)
    const proximas = precos
      .filter((p) => situacao(p) !== "encerrada" && p.faixa_gramatura_min > min)
      .map((p) => p.faixa_gramatura_min);
    const max = Math.min(min + 2, ...proximas);
    setForm((f) => ({ ...f, min: String(min), max: String(max) }));
    document.getElementById("preco-min")?.focus();
  };

  const adicionar = async (e: React.FormEvent) => {
    e.preventDefault();
    const problema = validar(form);
    if (problema) {
      setErro(problema);
      return;
    }
    setErro("");
    setSalvando(true);
    try {
      await precosApi.criar({
        faixa_gramatura_min: parseFloat(form.min),
        faixa_gramatura_max: parseFloat(form.max),
        preco_por_kg: parseFloat(form.preco),
        incremento_por_g: parseFloat(form.incremento),
        vigencia_inicio: form.inicio,
        vigencia_fim: form.fim || null,
      });
      toast.success(
        "Faixa de preço cadastrada!",
        `${fmtPeso(parseFloat(form.min))} g a ${fmtPeso(parseFloat(form.max))} g por ${fmtMoney(parseFloat(form.preco))}/kg`
      );
      setForm(formVazio());
      await recarregar();
      onAlterado?.();
    } catch (err) {
      setErro(mensagemErro(err, "Não foi possível cadastrar a faixa."));
    } finally {
      setSalvando(false);
    }
  };

  const salvarPreco = async (p: PrecoMercado) => {
    const novo = parseFloat(precoEditado);
    const novoIncremento = parseFloat(incrementoEditado);
    if (Number.isNaN(novo) || novo <= 0) {
      toast.error("Preço inválido", "Informe um valor maior que zero.");
      return;
    }
    if (Number.isNaN(novoIncremento) || novoIncremento < 0) {
      toast.error("Incremento inválido", "Informe zero ou um valor positivo.");
      return;
    }
    setOcupadoId(p.id);
    try {
      await precosApi.atualizar(p.id, { preco_por_kg: novo, incremento_por_g: novoIncremento });
      toast.success("Preço atualizado!", `${fmtPeso(p.faixa_gramatura_min)} g a ${fmtPeso(p.faixa_gramatura_max)} g: ${fmtMoney(novo)}/kg`);
      setEditandoId(null);
      await recarregar();
      onAlterado?.();
    } catch (err) {
      toast.error("Erro ao atualizar o preço", mensagemErro(err, "Tente novamente"));
    } finally {
      setOcupadoId(null);
    }
  };

  const excluir = async (p: PrecoMercado) => {
    const faixa = `${fmtPeso(p.faixa_gramatura_min)} g a ${fmtPeso(p.faixa_gramatura_max)} g (${fmtMoney(p.preco_por_kg)}/kg)`;
    if (!window.confirm(`Excluir a faixa ${faixa}? Para mudar só o preço, use o lápis.`)) return;
    setOcupadoId(p.id);
    try {
      await precosApi.excluir(p.id);
      toast.success("Faixa excluída", faixa);
      await recarregar();
      onAlterado?.();
    } catch (err) {
      toast.error("Erro ao excluir a faixa", mensagemErro(err, "Tente novamente"));
    } finally {
      setOcupadoId(null);
    }
  };

  const campo = (chave: keyof ReturnType<typeof formVazio>) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [chave]: e.target.value }));

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Tag className="w-4 h-4 text-sky-600" />
            Tabela de Preços de Mercado
          </CardTitle>
          <Badge variant="secondary">{vigentes.length} {vigentes.length === 1 ? "faixa vigente" : "faixas vigentes"}</Badge>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          O preço informado é o do camarão de 10 g (a tabela); cada grama acima soma o incremento por grama. Use
          incremento 0 para preço fixo na faixa (por exemplo, abaixo de 10 g). A simulação usa a faixa do peso atual do
          lote (despescar hoje) e a do peso projetado (esperar). Na divisa entre duas faixas vale a de cima.
        </p>
        <div className="mt-2">
          <Label htmlFor="regra-arredondamento">Arredondamento do peso (acordo com o comprador)</Label>
          <select
            id="regra-arredondamento"
            value={regra}
            disabled={!org}
            onChange={(e) => trocarRegra(e.target.value as RegraArredondamento)}
            className="w-full sm:w-72 mt-1.5 px-3 py-2 text-sm rounded-xl bg-white border border-slate-200 focus:outline-none focus:ring-1 focus:ring-sky-500"
          >
            {REGRAS.map((r) => (
              <option key={r.valor} value={r.valor}>
                {r.rotulo}
              </option>
            ))}
          </select>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* ── Situação do peso atual ── */}
        {pesoAtualG == null ? (
          <p className="text-xs text-slate-500 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2">
            Este lote ainda não tem biometria: registre uma para o sistema saber qual faixa de preço se aplica.
          </p>
        ) : faixaDoPeso ? (
          <div className="flex items-center gap-2 text-xs text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-xl px-3 py-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            Peso atual do lote: <strong>{fmtPeso(pesoAtualG)} g</strong>
            {pesoPreco !== pesoAtualG && <> (conta como {fmtPeso(pesoPreco ?? pesoAtualG)} g)</>}. Preço aplicado:{" "}
            <strong>{fmtMoney(precoDaFaixa(faixaDoPeso, pesoPreco ?? pesoAtualG))}/kg</strong>.
          </div>
        ) : (
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-amber-900 bg-amber-50 border border-amber-300 rounded-xl px-3 py-2.5">
            <span className="flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>
                Nenhuma faixa cobre o peso atual do lote (<strong>{fmtPeso(pesoAtualG)} g</strong>). Sem preço, a
                simulação não consegue calcular a receita. Cadastre uma faixa abaixo.
              </span>
            </span>
            <Button type="button" variant="outline" size="sm" onClick={preencherComPesoAtual}>
              Preencher para {fmtPeso(pesoAtualG)} g
            </Button>
          </div>
        )}

        {/* ── Faixas cadastradas ── */}
        {loading ? (
          <div className="flex justify-center py-4">
            <Loader2 className="w-5 h-5 text-sky-500 animate-spin" />
          </div>
        ) : precos.length === 0 ? (
          <p className="text-xs text-slate-500 italic">
            Nenhuma faixa cadastrada ainda. Adicione a primeira no formulário abaixo.
          </p>
        ) : (
          <div className="rounded-xl border border-slate-200 divide-y divide-slate-100 overflow-hidden">
            {lista.map((p) => {
              const sit = situacao(p);
              const aplicada = faixaDoPeso?.id === p.id;
              const editando = editandoId === p.id;
              return (
                <div
                  key={p.id}
                  className={`grid grid-cols-2 sm:grid-cols-[1.3fr_1fr_1.3fr_auto] items-center gap-x-3 gap-y-1 px-3 py-2.5 text-sm ${
                    aplicada ? "bg-emerald-50/60" : sit === "vigente" ? "bg-white" : "bg-slate-50 text-slate-500"
                  }`}
                >
                  <div className="font-bold text-slate-900 tabular-nums">
                    {fmtPeso(p.faixa_gramatura_min)} g a {fmtPeso(p.faixa_gramatura_max)} g
                    {aplicada && (
                      <Badge variant="success" className="ml-2 align-middle">
                        peso atual
                      </Badge>
                    )}
                    {sit !== "vigente" && (
                      <Badge variant="secondary" className="ml-2 align-middle">
                        {sit}
                      </Badge>
                    )}
                  </div>

                  <div className="tabular-nums">
                    {editando ? (
                      <>
                      <Input
                        type="number"
                        step="any"
                        min="0"
                        value={precoEditado}
                        onChange={(e) => setPrecoEditado(e.target.value)}
                        className="h-8 w-28"
                        aria-label="Novo preço por kg"
                        autoFocus
                      />
                      <Input
                        type="number"
                        step="any"
                        min="0"
                        value={incrementoEditado}
                        onChange={(e) => setIncrementoEditado(e.target.value)}
                        className="h-8 w-28 mt-1"
                        aria-label="Novo incremento por grama"
                      />
                      </>
                    ) : (
                      <span className="font-extrabold text-sky-700">
                        {fmtMoney(p.preco_por_kg)} <span className="text-xs font-semibold text-slate-400">/ kg (10 g)</span>
                        <span className="block text-xs font-semibold text-slate-500">
                          {p.incremento_por_g > 0 ? `+ ${fmtMoney(p.incremento_por_g)} por grama` : "preço fixo na faixa"}
                        </span>
                      </span>
                    )}
                  </div>

                  <div className="text-xs text-slate-500">
                    desde {fmtData(p.vigencia_inicio)}
                    {p.vigencia_fim ? ` até ${fmtData(p.vigencia_fim)}` : ""}
                  </div>

                  <div className="flex items-center justify-end gap-1">
                    {ocupadoId === p.id ? (
                      <Loader2 className="w-4 h-4 text-sky-500 animate-spin" />
                    ) : editando ? (
                      <>
                        <button type="button" onClick={() => salvarPreco(p)} className="p-1.5 rounded-lg text-emerald-600 hover:bg-emerald-50" aria-label="Salvar preço">
                          <Check className="w-4 h-4" />
                        </button>
                        <button type="button" onClick={() => setEditandoId(null)} className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100" aria-label="Cancelar edição">
                          <X className="w-4 h-4" />
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          type="button"
                          onClick={() => {
                            setEditandoId(p.id);
                            setPrecoEditado(String(p.preco_por_kg));
                            setIncrementoEditado(String(p.incremento_por_g));
                          }}
                          className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100"
                          aria-label="Editar preço"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button type="button" onClick={() => excluir(p)} className="p-1.5 rounded-lg text-red-500 hover:bg-red-50" aria-label="Excluir faixa">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* ── Nova faixa ── */}
        <form onSubmit={adicionar} className="rounded-xl bg-slate-50 border border-slate-200 p-4 space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">Adicionar faixa de preço</h4>
          <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
            <div>
              <Label htmlFor="preco-min">Peso mínimo (g)</Label>
              <Input id="preco-min" type="number" step="any" min="0" inputMode="decimal" value={form.min} onChange={campo("min")} placeholder="Ex: 12" className="mt-1.5" />
            </div>
            <div>
              <Label htmlFor="preco-max">Peso máximo (g)</Label>
              <Input id="preco-max" type="number" step="any" min="0" inputMode="decimal" value={form.max} onChange={campo("max")} placeholder="Ex: 14" className="mt-1.5" />
            </div>
            <div>
              <Label htmlFor="preco-valor">Tabela: preço de 10 g (R$/kg)</Label>
              <Input id="preco-valor" type="number" step="any" min="0" inputMode="decimal" value={form.preco} onChange={campo("preco")} placeholder="Ex: 13" className="mt-1.5" />
            </div>
            <div>
              <Label htmlFor="preco-incremento">Incremento (R$/g)</Label>
              <Input id="preco-incremento" type="number" step="any" min="0" inputMode="decimal" value={form.incremento} onChange={campo("incremento")} placeholder="Ex: 1" className="mt-1.5" />
            </div>
            <div>
              <Label htmlFor="preco-inicio">Vigência desde</Label>
              <Input id="preco-inicio" type="date" value={form.inicio} onChange={campo("inicio")} className="mt-1.5" />
            </div>
            <div>
              <Label htmlFor="preco-fim">Vigência até (opcional)</Label>
              <Input id="preco-fim" type="date" value={form.fim} onChange={campo("fim")} className="mt-1.5" />
            </div>
          </div>

          {erro && (
            <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              {erro}
            </div>
          )}

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <p className="text-[11px] text-slate-500">
              Faixas vizinhas são aceitas (8 a 10 g e 10 a 12 g). Faixas que se sobrepõem no mesmo período, não.
            </p>
            <Button type="submit" disabled={salvando} className="w-full sm:w-auto">
              {salvando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Adicionar faixa
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
