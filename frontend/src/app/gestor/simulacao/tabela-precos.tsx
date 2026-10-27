"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Check, CheckCircle2, Loader2, Pencil, Plus, Tag, Trash2, X } from "lucide-react";
import { precosApi } from "@/lib/api";
import { mensagemErro } from "@/lib/utils";
import type { PrecoMercado } from "@/lib/types";
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

const formVazio = () => ({ min: "", max: "", preco: "", inicio: hoje(), fim: "" });

function validar(f: ReturnType<typeof formVazio>): string | null {
  const min = parseFloat(f.min);
  const max = parseFloat(f.max);
  const preco = parseFloat(f.preco);
  if (Number.isNaN(min) || Number.isNaN(max) || Number.isNaN(preco)) {
    return "Preencha o peso mínimo, o peso máximo e o preço.";
  }
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

  const recarregar = useCallback(async () => {
    try {
      setPrecos(await precosApi.listar());
    } catch (err) {
      toast.error("Não foi possível carregar a tabela de preços", mensagemErro(err, "Tente novamente"));
    }
  }, []);

  useEffect(() => {
    let ativo = true;
    async function carregar() {
      try {
        const lista = await precosApi.listar();
        if (ativo) setPrecos(lista);
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

  // Mesma regra do servidor: na divisa entre duas faixas vale a de cima
  const faixaDoPeso =
    pesoAtualG == null
      ? undefined
      : precos
          .filter((p) => p.faixa_gramatura_min <= pesoAtualG && pesoAtualG <= p.faixa_gramatura_max)
          .sort((a, b) => b.faixa_gramatura_min - a.faixa_gramatura_min)[0];

  const preencherComPesoAtual = () => {
    if (pesoAtualG == null) return;
    const min = Math.floor(pesoAtualG);
    setForm((f) => ({ ...f, min: String(min), max: String(min + 2) }));
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
    if (Number.isNaN(novo) || novo <= 0) {
      toast.error("Preço inválido", "Informe um valor maior que zero.");
      return;
    }
    setOcupadoId(p.id);
    try {
      await precosApi.atualizar(p.id, { preco_por_kg: novo });
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
          <Badge variant="secondary">{precos.length} {precos.length === 1 ? "faixa vigente" : "faixas vigentes"}</Badge>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Preço do kg pelo peso do camarão. A simulação usa a faixa do peso atual do lote (despescar hoje) e a do peso
          projetado (esperar). Na divisa entre duas faixas vale a de cima.
        </p>
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
            Peso atual do lote: <strong>{fmtPeso(pesoAtualG)} g</strong>. Faixa aplicada:{" "}
            <strong>{fmtMoney(faixaDoPeso.preco_por_kg)}/kg</strong>.
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
            {precos.map((p) => {
              const aplicada = faixaDoPeso?.id === p.id;
              const editando = editandoId === p.id;
              return (
                <div
                  key={p.id}
                  className={`grid grid-cols-2 sm:grid-cols-[1.3fr_1fr_1.3fr_auto] items-center gap-x-3 gap-y-1 px-3 py-2.5 text-sm ${
                    aplicada ? "bg-emerald-50/60" : "bg-white"
                  }`}
                >
                  <div className="font-bold text-slate-900 tabular-nums">
                    {fmtPeso(p.faixa_gramatura_min)} g a {fmtPeso(p.faixa_gramatura_max)} g
                    {aplicada && (
                      <Badge variant="success" className="ml-2 align-middle">
                        peso atual
                      </Badge>
                    )}
                  </div>

                  <div className="tabular-nums">
                    {editando ? (
                      <Input
                        type="number"
                        step="0.5"
                        min="0"
                        value={precoEditado}
                        onChange={(e) => setPrecoEditado(e.target.value)}
                        className="h-8 w-28"
                        aria-label="Novo preço por kg"
                        autoFocus
                      />
                    ) : (
                      <span className="font-extrabold text-sky-700">
                        {fmtMoney(p.preco_por_kg)} <span className="text-xs font-semibold text-slate-400">/ kg</span>
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
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div>
              <Label htmlFor="preco-min">Peso mínimo (g)</Label>
              <Input id="preco-min" type="number" step="0.5" min="0" inputMode="decimal" value={form.min} onChange={campo("min")} placeholder="Ex: 12" className="mt-1.5" />
            </div>
            <div>
              <Label htmlFor="preco-max">Peso máximo (g)</Label>
              <Input id="preco-max" type="number" step="0.5" min="0" inputMode="decimal" value={form.max} onChange={campo("max")} placeholder="Ex: 14" className="mt-1.5" />
            </div>
            <div>
              <Label htmlFor="preco-valor">Preço (R$/kg)</Label>
              <Input id="preco-valor" type="number" step="0.5" min="0" inputMode="decimal" value={form.preco} onChange={campo("preco")} placeholder="Ex: 24.50" className="mt-1.5" />
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
