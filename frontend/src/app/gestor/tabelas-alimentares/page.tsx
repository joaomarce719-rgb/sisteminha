"use client";

import { useEffect, useState } from "react";
import {
  Utensils,
  Plus,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Star,
  Sliders,
  History,
  Info,
  Trash2,
} from "lucide-react";
import { tabelasAlimentaresApi } from "@/lib/api";
import type { TabelaAlimentar, FaixaAlimentarItem } from "@/lib/types";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { toast } from "@/components/ui/toast";

export default function TabelasAlimentaresPage() {
  const [tabelas, setTabelas] = useState<TabelaAlimentar[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Form states
  const [formNome, setFormNome] = useState("");
  const [formDescricao, setFormDescricao] = useState("");
  const [formIsPadrao, setFormIsPadrao] = useState(false);
  const [faixas, setFaixas] = useState<FaixaAlimentarItem[]>([
    { peso_g: 2.0, taxa_pct: 7.15 },
    { peso_g: 5.0, taxa_pct: 5.05 },
    { peso_g: 10.0, taxa_pct: 3.88 },
    { peso_g: 15.0, taxa_pct: 3.33 },
    { peso_g: 20.0, taxa_pct: 2.98 },
  ]);

  const carregarTabelas = async () => {
    setLoading(true);
    try {
      const data = await tabelasAlimentaresApi.listar(false);
      setTabelas(data);
    } catch (err: any) {
      toast.error("Erro ao carregar tabelas", err.message || "Tente novamente");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarTabelas();
  }, []);

  const handleAddFaixa = () => {
    const ultimoPeso = faixas.length > 0 ? faixas[faixas.length - 1].peso_g + 5 : 2.0;
    const ultimaTaxa = faixas.length > 0 ? Math.max(1.0, faixas[faixas.length - 1].taxa_pct - 0.5) : 5.0;
    setFaixas([...faixas, { peso_g: ultimoPeso, taxa_pct: ultimaTaxa }]);
  };

  const handleRemoveFaixa = (index: number) => {
    if (faixas.length <= 2) {
      toast.error("Mínimo de 2 pontos", "A interpolação requer ao menos duas faixas.");
      return;
    }
    setFaixas(faixas.filter((_, i) => i !== index));
  };

  const handleUpdateFaixa = (index: number, campo: keyof FaixaAlimentarItem, valor: number) => {
    const novas = [...faixas];
    novas[index] = { ...novas[index], [campo]: valor };
    setFaixas(novas);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formNome.trim()) {
      toast.error("Campo obrigatório", "Informe o nome da tabela.");
      return;
    }
    setSubmitting(true);
    try {
      await tabelasAlimentaresApi.criar({
        nome: formNome.trim(),
        descricao: formDescricao.trim() || null,
        is_padrao: formIsPadrao,
        faixas: faixas.map((f) => ({ peso_g: Number(f.peso_g), taxa_pct: Number(f.taxa_pct) })),
      });
      toast.success("Tabela Alimentar salva", "Nova versão cadastrada com sucesso!");
      setModalOpen(false);
      setFormNome("");
      setFormDescricao("");
      setFormIsPadrao(false);
      carregarTabelas();
    } catch (err: any) {
      toast.error("Falha ao salvar", err.message || "Verifique os dados.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDefinirPadrao = async (t: TabelaAlimentar) => {
    try {
      await tabelasAlimentaresApi.atualizar(t.id, { is_padrao: true });
      toast.success("Tabela padrão alterada", `${t.nome} (v${t.versao}) agora é o padrão de cálculo.`);
      carregarTabelas();
    } catch (err: any) {
      toast.error("Erro ao definir padrão", err.message || "Tente novamente");
    }
  };

  const handleToggleAtivo = async (t: TabelaAlimentar) => {
    try {
      await tabelasAlimentaresApi.atualizar(t.id, { ativo: !t.ativo });
      toast.success(
        t.ativo ? "Tabela desativada" : "Tabela ativada",
        `${t.nome} (v${t.versao}) status atualizado.`
      );
      carregarTabelas();
    } catch (err: any) {
      toast.error("Erro ao alterar status", err.message || "Tente novamente");
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <Utensils className="w-7 h-7 text-emerald-600" />
            Tabelas Alimentares (RF-010)
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Parametrização e versionamento de curvas de arraçoamento baseadas em biomassa e peso médio
          </p>
        </div>
        <Button
          onClick={() => setModalOpen(true)}
          className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm font-semibold"
        >
          <Plus className="w-4 h-4 mr-2" />
          Nova Tabela / Versão
        </Button>
      </div>

      {/* Nota Explicativa */}
      <div className="bg-ocean-50 border border-ocean-200/80 rounded-2xl p-4 flex items-start gap-3">
        <Info className="w-5 h-5 text-ocean-600 shrink-0 mt-0.5" />
        <div className="text-xs text-ocean-950 space-y-1">
          <p className="font-semibold">Critério 5 & Clifford (1992)</p>
          <p className="text-ocean-800 leading-relaxed">
            O algoritmo de recomendação diária calcula a taxa de alimentação a partir de interpolação linear dos
            pontos calibrados. A tabela de <strong>Clifford (1992)</strong> vem pré-configurada como padrão do sistema.
            Você pode criar variações customizadas para viveiros de alta densidade ou fases específicas.
          </p>
        </div>
      </div>

      {/* Listagem */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-24 bg-white rounded-2xl border border-slate-200">
          <Loader2 className="w-8 h-8 text-emerald-600 animate-spin mb-2" />
          <p className="text-xs text-slate-400">Carregando tabelas de arraçoamento...</p>
        </div>
      ) : tabelas.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center">
          <Sliders className="w-12 h-12 text-slate-400 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-800">Nenhuma tabela cadastrada</h3>
          <p className="text-xs text-slate-500 mt-1 mb-4">Clique no botão acima para cadastrar a primeira tabela.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {tabelas.map((tab) => (
            <Card
              key={tab.id}
              className={`border transition-all duration-200 ${
                tab.is_padrao
                  ? "border-emerald-300 ring-2 ring-emerald-100 shadow-md"
                  : "border-slate-200 hover:border-slate-300 shadow-sm"
              }`}
            >
              <CardHeader className="pb-3 border-b border-slate-100 flex flex-row items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-lg font-bold text-slate-900">{tab.nome}</CardTitle>
                    <Badge variant="outline" className="text-xs bg-slate-50 text-slate-700">
                      v{tab.versao}
                    </Badge>
                  </div>
                  {tab.descricao && (
                    <p className="text-xs text-slate-500 mt-1 line-clamp-2">{tab.descricao}</p>
                  )}
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  {tab.is_padrao && (
                    <Badge variant="success" className="bg-emerald-500 text-white gap-1 text-[11px]">
                      <Star className="w-3 h-3 fill-white" />
                      Padrão
                    </Badge>
                  )}
                  <Badge variant={tab.ativo ? "secondary" : "destructive"} className="text-[11px]">
                    {tab.ativo ? "Ativa" : "Inativa"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                {/* Tabela de Faixas */}
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                      <tr>
                        <th className="py-2 px-3">Peso Médio (g)</th>
                        <th className="py-2 px-3">Taxa Alimentar (%)</th>
                        <th className="py-2 px-3 text-right">Ração / 1.000 kg B</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {tab.faixas.map((f, i) => (
                        <tr key={i} className="hover:bg-slate-50/60">
                          <td className="py-2 px-3 font-medium text-slate-800">{f.peso_g.toFixed(1)} g</td>
                          <td className="py-2 px-3 text-emerald-700 font-semibold">{f.taxa_pct.toFixed(2)} %</td>
                          <td className="py-2 px-3 text-right text-slate-600">
                            {(1000 * (f.taxa_pct / 100)).toFixed(1)} kg/dia
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Ações */}
                <div className="flex items-center justify-between pt-2">
                  <span className="text-[11px] text-slate-400">
                    Cadastrada em {new Date(tab.created_at).toLocaleDateString("pt-BR")}
                  </span>
                  <div className="flex items-center gap-2">
                    {!tab.is_padrao && tab.ativo && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDefinirPadrao(tab)}
                        className="text-xs h-8 text-emerald-700 border-emerald-300 hover:bg-emerald-50"
                      >
                        Tornar Padrão
                      </Button>
                    )}
                    {!tab.is_padrao && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleToggleAtivo(tab)}
                        className={`text-xs h-8 ${tab.ativo ? "text-slate-500 hover:text-red-600" : "text-emerald-600 hover:bg-emerald-50"}`}
                      >
                        {tab.ativo ? "Desativar" : "Reativar"}
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Modal Criar Nova Tabela / Nova Versão */}
      <Dialog
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Cadastrar Tabela de Arraçoamento"
        description="Defina os nós de calibração para interpolação da ração diária (% da biomassa)"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="nome">Identificação / Nome *</Label>
            <Input
              id="nome"
              required
              value={formNome}
              onChange={(e) => setFormNome(e.target.value)}
              placeholder="Ex: Tabela Super Intensiva 2026"
              className="mt-1"
            />
          </div>

          <div>
            <Label htmlFor="descricao">Descrição (Opcional)</Label>
            <Input
              id="descricao"
              value={formDescricao}
              onChange={(e) => setFormDescricao(e.target.value)}
              placeholder="Ex: Ajustada para camarões acima de 10g com ração 35% PB"
              className="mt-1"
            />
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="is_padrao"
              checked={formIsPadrao}
              onChange={(e) => setFormIsPadrao(e.target.checked)}
              className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 w-4 h-4 cursor-pointer"
            />
            <label htmlFor="is_padrao" className="text-xs text-slate-700 font-medium cursor-pointer">
              Definir como tabela padrão do sistema para novos ciclos
            </label>
          </div>

          {/* Faixas Dinâmicas */}
          <div className="pt-2">
            <div className="flex items-center justify-between mb-2">
              <Label className="text-xs uppercase tracking-wider font-bold text-slate-600">
                Pontos de Calibração ({faixas.length})
              </Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleAddFaixa}
                className="h-7 text-xs border-emerald-300 text-emerald-700 hover:bg-emerald-50"
              >
                <Plus className="w-3.5 h-3.5 mr-1" />
                Adicionar Ponto
              </Button>
            </div>

            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {faixas.map((f, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-3 p-2 rounded-xl bg-slate-50 border border-slate-200"
                >
                  <div className="flex-1">
                    <span className="text-[10px] text-slate-400 block">Peso Médio (g)</span>
                    <Input
                      type="number"
                      step="0.1"
                      min="0.1"
                      value={f.peso_g}
                      onChange={(e) => handleUpdateFaixa(idx, "peso_g", parseFloat(e.target.value) || 0)}
                      className="h-8 text-xs mt-0.5 bg-white"
                    />
                  </div>
                  <div className="flex-1">
                    <span className="text-[10px] text-slate-400 block">Taxa Alimentar (% da biomassa)</span>
                    <Input
                      type="number"
                      step="0.01"
                      min="0.01"
                      value={f.taxa_pct}
                      onChange={(e) => handleUpdateFaixa(idx, "taxa_pct", parseFloat(e.target.value) || 0)}
                      className="h-8 text-xs mt-0.5 bg-white font-semibold text-emerald-700"
                    />
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemoveFaixa(idx)}
                    className="h-8 w-8 p-0 text-slate-400 hover:text-red-600 mt-4"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-4 flex gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => setModalOpen(false)}
              className="flex-1"
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={submitting}
              className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CheckCircle2 className="w-4 h-4 mr-2" />}
              Salvar Tabela
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
