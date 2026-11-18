"use client";

import { useEffect, useState } from "react";
import { Loader2, Package, Pencil, Plus, Receipt, Trash2 } from "lucide-react";
import { insumosApi } from "@/lib/api";
import { cn, mensagemErro } from "@/lib/utils";
import type { CategoriaCusto, CompraInsumo, Insumo } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataLancamento, hojeLocal } from "@/components/ui/data-lancamento";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/toast";

const CATEGORIAS: Record<CategoriaCusto, string> = {
  RACAO: "Ração",
  ENERGIA_ELETRICA: "Energia Elétrica",
  MAO_DE_OBRA: "Mão de Obra",
  POS_LARVAS: "Pós-Larvas",
  PROBIOTICOS_QUIMICOS: "Probióticos/Químicos",
  MANUTENCAO: "Manutenção",
  OUTROS: "Outros",
};

// Ração e pós-larvas têm custo próprio (manejo alimentar e povoamento): a API não as aceita como insumo
const CATEGORIAS_INSUMO = (Object.keys(CATEGORIAS) as CategoriaCusto[]).filter(
  (c) => c !== "RACAO" && c !== "POS_LARVAS"
);

const fmtQtd = (v: number) => v.toLocaleString("pt-BR", { maximumFractionDigits: 4 });
const fmtMoney = (v: number) =>
  `R$ ${v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
// O preço unitário tem 4 casas (a API só arredonda o total a centavos)
const fmtPreco = (v: number) =>
  `R$ ${v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`;
const fmtData = (d: string) => new Date(`${d}T00:00:00`).toLocaleDateString("pt-BR");

const insumoVazio = () => ({ nome: "", unidade: "", categoria: "OUTROS" as CategoriaCusto });
const compraVazia = () => ({ data: hojeLocal(), retroativo: false, quantidade: "", valor: "", fornecedor: "", observacao: "" });

export default function InsumosPage() {
  const [insumos, setInsumos] = useState<Insumo[]>([]);
  const [loading, setLoading] = useState(true);
  const [selId, setSelId] = useState<string | null>(null);
  // Compras guardadas com o insumo a que pertencem: trocar de insumo não mostra a lista do anterior
  const [compras, setCompras] = useState<{ insumoId: string; lista: CompraInsumo[] } | null>(null);
  // Cada alteração incrementa a versão, e os efeitos recarregam lista e compras (saldo e preço médio mudam)
  const [versao, setVersao] = useState(0);
  const recarregar = () => setVersao((v) => v + 1);

  const [insumoAberto, setInsumoAberto] = useState(false);
  const [insumoForm, setInsumoForm] = useState(insumoVazio);
  const [compraAberta, setCompraAberta] = useState(false);
  const [compraEditando, setCompraEditando] = useState<CompraInsumo | null>(null);
  const [compraForm, setCompraForm] = useState(compraVazia);
  const [salvando, setSalvando] = useState(false);
  const [excluindoId, setExcluindoId] = useState<string | null>(null);

  useEffect(() => {
    let ativo = true;
    async function carregar() {
      try {
        const lista = await insumosApi.listar();
        if (!ativo) return;
        setInsumos(lista);
        setSelId((atual) => atual ?? lista[0]?.id ?? null);
      } catch (err) {
        toast.error("Não foi possível carregar os insumos", mensagemErro(err, "Tente novamente"));
      } finally {
        if (ativo) setLoading(false);
      }
    }
    carregar();
    return () => {
      ativo = false;
    };
  }, [versao]);

  useEffect(() => {
    if (!selId) return;
    let ativo = true;
    async function carregar(insumoId: string) {
      try {
        const lista = await insumosApi.compras.listar(insumoId);
        if (ativo) setCompras({ insumoId, lista });
      } catch (err) {
        toast.error("Não foi possível carregar as compras", mensagemErro(err, "Tente novamente"));
      }
    }
    carregar(selId);
    return () => {
      ativo = false;
    };
  }, [selId, versao]);

  const selecionado = insumos.find((i) => i.id === selId) ?? null;
  const comprasDoSelecionado = compras && compras.insumoId === selId ? compras.lista : null;

  const abrirNovoInsumo = () => {
    setInsumoForm(insumoVazio());
    setInsumoAberto(true);
  };

  const salvarInsumo = async (e: React.FormEvent) => {
    e.preventDefault();
    setSalvando(true);
    try {
      const novo = await insumosApi.criar({
        nome: insumoForm.nome.trim(),
        unidade_uso: insumoForm.unidade.trim(),
        categoria: insumoForm.categoria,
      });
      toast.success("Insumo cadastrado!", `${novo.nome} (${novo.unidade_uso})`);
      setInsumoAberto(false);
      setSelId(novo.id);
      recarregar();
    } catch (err) {
      toast.error("Erro ao cadastrar o insumo", mensagemErro(err, "Tente novamente"));
    } finally {
      setSalvando(false);
    }
  };

  const abrirCompra = (compra: CompraInsumo | null) => {
    setCompraEditando(compra);
    setCompraForm(
      compra
        ? {
            data: compra.data_compra,
            // Compra de dias atrás editada hoje já é retroativa, mesmo que na época não fosse
            retroativo: compra.retroativo || compra.data_compra < hojeLocal(),
            quantidade: String(compra.quantidade),
            valor: String(compra.valor_total_rs),
            fornecedor: compra.fornecedor ?? "",
            observacao: compra.observacao ?? "",
          }
        : compraVazia()
    );
    setCompraAberta(true);
  };

  const salvarCompra = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selecionado) return;
    setSalvando(true);
    const payload = {
      data_compra: compraForm.data,
      quantidade: parseFloat(compraForm.quantidade),
      valor_total_rs: parseFloat(compraForm.valor),
      fornecedor: compraForm.fornecedor.trim() || null,
      observacao: compraForm.observacao.trim() || null,
      // A caixa marcada com a data de hoje não é retroativa de fato
      retroativo: compraForm.retroativo && compraForm.data < hojeLocal(),
    };
    try {
      if (compraEditando) {
        await insumosApi.compras.atualizar(selecionado.id, compraEditando.id, payload);
        toast.success("Compra atualizada!", `${selecionado.nome}: saldo e preço médio recalculados`);
      } else {
        await insumosApi.compras.criar(selecionado.id, payload);
        toast.success("Compra registrada!", `${fmtQtd(payload.quantidade)} ${selecionado.unidade_uso} de ${selecionado.nome}`);
      }
      setCompraAberta(false);
      recarregar();
    } catch (err) {
      toast.error("Erro ao salvar a compra", mensagemErro(err, "Tente novamente"));
    } finally {
      setSalvando(false);
    }
  };

  const excluirCompra = async (compra: CompraInsumo) => {
    if (!selecionado) return;
    const resumo = `${fmtData(compra.data_compra)}, ${fmtQtd(compra.quantidade)} ${selecionado.unidade_uso}, ${fmtMoney(compra.valor_total_rs)}`;
    if (!window.confirm(`Excluir a compra de ${resumo}? O preço médio e os usos já lançados serão recalculados.`)) return;
    setExcluindoId(compra.id);
    try {
      await insumosApi.compras.excluir(selecionado.id, compra.id);
      toast.success("Compra excluída", resumo);
      recarregar();
    } catch (err) {
      toast.error("Erro ao excluir a compra", mensagemErro(err, "Tente novamente"));
    } finally {
      setExcluindoId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Módulo Econômico</span>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">Insumos e Compras</h1>
          <p className="text-slate-500 text-xs mt-1">
            O preço médio de cada insumo é ponderado pelas compras: cada uso no ciclo vira custo por esse preço.
          </p>
        </div>
        <Button onClick={abrirNovoInsumo} size="sm">
          <Plus className="w-4 h-4" /> Novo insumo
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)] gap-6 items-start">
        {/* ── Lista de insumos ── */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Package className="w-4 h-4 text-sky-600" />
                Insumos cadastrados
              </CardTitle>
              <Badge variant="secondary">{insumos.length}</Badge>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            {insumos.length === 0 ? (
              <p className="py-10 text-center text-xs text-slate-400">
                Nenhum insumo cadastrado ainda. Use &quot;Novo insumo&quot; para começar.
              </p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {insumos.map((i) => {
                  const ativo = i.id === selId;
                  return (
                    <li key={i.id}>
                      <button
                        type="button"
                        onClick={() => setSelId(i.id)}
                        aria-pressed={ativo}
                        className={cn(
                          "w-full text-left px-3 py-3 rounded-xl transition-colors",
                          ativo ? "bg-sky-50 ring-1 ring-sky-200" : "hover:bg-slate-50"
                        )}
                      >
                        <span className="flex items-center justify-between gap-2">
                          <span className="font-bold text-sm text-slate-900 truncate">{i.nome}</span>
                          <span className="flex gap-1 shrink-0">
                            {i.saldo_negativo && <Badge variant="destructive">saldo negativo</Badge>}
                            {!i.ativo && <Badge variant="secondary">inativo</Badge>}
                          </span>
                        </span>
                        <span className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-slate-500">
                          <span>{CATEGORIAS[i.categoria]}</span>
                          <span>
                            Saldo:{" "}
                            <strong className={cn("tabular-nums", i.saldo_negativo ? "text-red-600" : "text-slate-800")}>
                              {fmtQtd(i.saldo ?? 0)} {i.unidade_uso}
                            </strong>
                          </span>
                          <span>
                            Preço médio:{" "}
                            <strong className="tabular-nums text-slate-800">
                              {i.preco_medio_rs == null ? "sem compras" : `${fmtPreco(i.preco_medio_rs)}/${i.unidade_uso}`}
                            </strong>
                          </span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* ── Compras do insumo selecionado ── */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between gap-2">
              <CardTitle className="text-base flex items-center gap-2 min-w-0">
                <Receipt className="w-4 h-4 text-sky-600 shrink-0" />
                <span className="truncate">{selecionado ? `Compras de ${selecionado.nome}` : "Compras"}</span>
              </CardTitle>
              {selecionado && (
                <Button size="sm" onClick={() => abrirCompra(null)}>
                  <Plus className="w-4 h-4" /> Registrar compra
                </Button>
              )}
            </div>
            {selecionado && (
              <p className="text-xs text-slate-500 mt-1">
                Estoque que já existe entra como uma compra, com o preço pago.
              </p>
            )}
          </CardHeader>
          <CardContent className="pt-0">
            {!selecionado ? (
              <p className="py-10 text-center text-xs text-slate-400">Selecione um insumo para ver as compras.</p>
            ) : comprasDoSelecionado === null ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-5 h-5 text-sky-500 animate-spin" />
              </div>
            ) : comprasDoSelecionado.length === 0 ? (
              <p className="py-10 text-center text-xs text-slate-400">Nenhuma compra registrada para este insumo.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {comprasDoSelecionado.map((c) => (
                  <li key={c.id} className="py-3 flex items-start justify-between gap-3 text-xs">
                    <div className="min-w-0 space-y-0.5">
                      <p className="font-semibold text-slate-800">
                        {fmtData(c.data_compra)}
                        {c.retroativo && (
                          <Badge variant="warning" className="ml-2 align-middle">
                            retroativo
                          </Badge>
                        )}
                      </p>
                      <p className="text-slate-600 tabular-nums">
                        {fmtQtd(c.quantidade)} {selecionado.unidade_uso} por {fmtMoney(c.valor_total_rs)} (
                        {fmtPreco(c.valor_total_rs / c.quantidade)}/{selecionado.unidade_uso})
                      </p>
                      {c.fornecedor && <p className="text-slate-500 truncate">Fornecedor: {c.fornecedor}</p>}
                      {c.observacao && <p className="text-slate-500">{c.observacao}</p>}
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      {excluindoId === c.id ? (
                        <Loader2 className="w-4 h-4 text-sky-500 animate-spin" />
                      ) : (
                        <>
                          <button
                            type="button"
                            onClick={() => abrirCompra(c)}
                            className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100"
                            aria-label="Editar compra"
                          >
                            <Pencil className="w-4 h-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => excluirCompra(c)}
                            className="p-1.5 rounded-lg text-red-500 hover:bg-red-50"
                            aria-label="Excluir compra"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Novo insumo ── */}
      <Dialog
        open={insumoAberto}
        onOpenChange={setInsumoAberto}
        title="Novo insumo"
        description="Cadastre o produto; o preço vem das compras registradas depois"
      >
        <form onSubmit={salvarInsumo} className="space-y-4 pt-2">
          <div>
            <Label htmlFor="insumo-nome">Nome *</Label>
            <Input
              id="insumo-nome"
              required
              maxLength={120}
              value={insumoForm.nome}
              onChange={(e) => setInsumoForm({ ...insumoForm, nome: e.target.value })}
              placeholder="Ex: Cal"
              className="mt-1"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="insumo-unidade">Unidade de uso *</Label>
              <Input
                id="insumo-unidade"
                required
                maxLength={20}
                value={insumoForm.unidade}
                onChange={(e) => setInsumoForm({ ...insumoForm, unidade: e.target.value })}
                placeholder="Ex: kg"
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="insumo-categoria">Categoria do custo *</Label>
              <select
                id="insumo-categoria"
                value={insumoForm.categoria}
                onChange={(e) => setInsumoForm({ ...insumoForm, categoria: e.target.value as CategoriaCusto })}
                className="w-full mt-1 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-slate-800 focus:border-sky-500 focus:outline-none h-11"
              >
                {CATEGORIAS_INSUMO.map((c) => (
                  <option key={c} value={c}>
                    {CATEGORIAS[c]}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="pt-2 flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setInsumoAberto(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={salvando}>
              {salvando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              Cadastrar insumo
            </Button>
          </div>
        </form>
      </Dialog>

      {/* ── Compra (nova ou edição) ── */}
      <Dialog
        open={compraAberta}
        onOpenChange={setCompraAberta}
        title={compraEditando ? "Editar compra" : "Registrar compra"}
        description={selecionado ? `${selecionado.nome} (${selecionado.unidade_uso})` : undefined}
      >
        <form onSubmit={salvarCompra} className="space-y-4 pt-2">
          <DataLancamento
            label="Data da compra *"
            value={compraForm.data}
            onChange={(data) => setCompraForm((f) => ({ ...f, data }))}
            retroativo={compraForm.retroativo}
            onRetroativoChange={(retroativo) => setCompraForm((f) => ({ ...f, retroativo }))}
          />
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="compra-quantidade">Quantidade{selecionado ? ` (${selecionado.unidade_uso})` : ""} *</Label>
              <Input
                id="compra-quantidade"
                required
                type="number"
                inputMode="decimal"
                step="any"
                min="0.0001"
                max="9999999999"
                value={compraForm.quantidade}
                onChange={(e) => setCompraForm({ ...compraForm, quantidade: e.target.value })}
                placeholder="Ex: 100"
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="compra-valor">Valor total (R$) *</Label>
              <Input
                id="compra-valor"
                required
                type="number"
                inputMode="decimal"
                step="0.01"
                min="0.01"
                max="9999999999"
                value={compraForm.valor}
                onChange={(e) => setCompraForm({ ...compraForm, valor: e.target.value })}
                placeholder="Ex: 300.00"
                className="mt-1"
              />
            </div>
          </div>
          <div>
            <Label htmlFor="compra-fornecedor">Fornecedor</Label>
            <Input
              id="compra-fornecedor"
              maxLength={120}
              value={compraForm.fornecedor}
              onChange={(e) => setCompraForm({ ...compraForm, fornecedor: e.target.value })}
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="compra-observacao">Observação</Label>
            <Input
              id="compra-observacao"
              maxLength={500}
              value={compraForm.observacao}
              onChange={(e) => setCompraForm({ ...compraForm, observacao: e.target.value })}
              className="mt-1"
            />
          </div>
          <div className="pt-2 flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setCompraAberta(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={salvando}>
              {salvando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              {compraEditando ? "Salvar compra" : "Registrar compra"}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
