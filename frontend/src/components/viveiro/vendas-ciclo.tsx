"use client";

import { useEffect, useState } from "react";
import { Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { vendasApi } from "@/lib/api";
import { mensagemErro } from "@/lib/utils";
import type { TipoVenda, VendaCiclo } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataLancamento, hojeLocal } from "@/components/ui/data-lancamento";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/toast";
import { fmtData, fmtMoney, fmtQtd } from "@/components/insumos/lista-usos-insumo";

export const TIPOS_VENDA: Record<TipoVenda, string> = { DESBASTE: "Desbaste", DESPESCA_FINAL: "Despesca final" };

/**
 * Vendas do ciclo. `vendas` é null enquanto carrega e quando a leitura falha (`falhou`): quem decide
 * algo com base na lista (como o encerramento) não deve tratar a falha como "sem vendas".
 */
export function useVendasCiclo(cicloId: string) {
  // Guardadas com o ciclo a que pertencem: trocar de ciclo não mostra a lista do anterior
  const [carregado, setCarregado] = useState<{ cicloId: string; lista: VendaCiclo[] | null } | null>(null);
  const [versao, setVersao] = useState(0);

  useEffect(() => {
    if (!cicloId) return;
    let ativo = true;
    vendasApi
      .listar(cicloId)
      .then((lista) => {
        if (ativo) setCarregado({ cicloId, lista });
      })
      .catch((err) => {
        if (ativo) {
          setCarregado({ cicloId, lista: null });
          toast.error("Não foi possível carregar as vendas", mensagemErro(err, "Tente novamente"));
        }
      });
    return () => {
      ativo = false;
    };
  }, [cicloId, versao]);

  const atual = carregado && carregado.cicloId === cicloId ? carregado : null;
  return {
    vendas: atual?.lista ?? null,
    falhou: atual !== null && atual.lista === null,
    recarregar: () => setVersao((v) => v + 1),
  };
}

const AVISO_RETROATIVO = "Uma venda retroativa recalcula a população, o FCA e o lucro do ciclo a partir desta data.";

interface VendaFormProps {
  cicloId: string;
  /** Venda a corrigir; sem ela, o formulário lança uma venda nova. */
  venda?: VendaCiclo;
  onSalvo: () => void;
  onCancelar: () => void;
}

function VendaForm({ cicloId, venda, onSalvo, onCancelar }: VendaFormProps) {
  const [tipo, setTipo] = useState<TipoVenda>(venda?.tipo ?? "DESBASTE");
  const [data, setData] = useState(venda?.data_venda ?? hojeLocal());
  // Venda de dias atrás editada hoje já é retroativa, mesmo que na época não fosse
  const [retroativo, setRetroativo] = useState(venda ? venda.retroativo || venda.data_venda < hojeLocal() : false);
  const [biomassa, setBiomassa] = useState(venda ? String(venda.biomassa_kg) : "");
  const [peso, setPeso] = useState(venda ? String(venda.peso_medio_g) : "");
  // null = o preço acompanha a sugestão da tabela; texto (inclusive vazio) = o usuário mexeu no campo
  const [preco, setPreco] = useState<string | null>(venda ? String(venda.preco_kg) : null);
  const [sugestao, setSugestao] = useState<{ peso: number; preco: number | null } | null>(null);
  const [comprador, setComprador] = useState(venda?.comprador ?? "");
  const [observacao, setObservacao] = useState(venda?.observacao ?? "");
  const [salvando, setSalvando] = useState(false);

  const pesoNum = parseFloat(peso);

  // Sugere o preço da tabela quando o peso médio muda (com pequena espera enquanto se digita)
  useEffect(() => {
    if (!(pesoNum >= 0.01 && pesoNum <= 999_999)) return;
    let ativo = true;
    const espera = setTimeout(() => {
      vendasApi
        .precoSugerido(cicloId, pesoNum)
        .then((r) => {
          if (ativo) setSugestao({ peso: pesoNum, preco: r.preco_kg });
        })
        .catch(() => {}); // sem sugestão o usuário informa o preço
    }, 400);
    return () => {
      ativo = false;
      clearTimeout(espera);
    };
  }, [cicloId, pesoNum]);

  // A sugestão só vale para o peso que ela consultou
  const sugestaoAtual = sugestao && sugestao.peso === pesoNum ? sugestao : null;
  const precoTexto = preco ?? (sugestaoAtual?.preco != null ? String(sugestaoAtual.preco) : "");
  const biomassaNum = parseFloat(biomassa);
  const precoNum = parseFloat(precoTexto);

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    setSalvando(true);
    const payload = {
      data_venda: data,
      tipo,
      biomassa_kg: biomassaNum,
      peso_medio_g: pesoNum,
      // Vazio: a API usa o preço da tabela para o peso médio
      preco_kg: precoTexto !== "" ? precoNum : null,
      comprador: comprador.trim() || null,
      observacao: observacao.trim() || null,
      // A caixa marcada com a data de hoje não é retroativa de fato
      retroativo: retroativo && data < hojeLocal(),
    };
    try {
      if (venda) await vendasApi.atualizar(cicloId, venda.id, payload);
      else await vendasApi.criar(cicloId, payload);
      toast.success(
        venda ? "Venda atualizada!" : "Venda registrada!",
        `${TIPOS_VENDA[tipo]} de ${fmtQtd(biomassaNum)} kg em ${fmtData(data)}.`
      );
      onSalvo();
    } catch (err) {
      toast.error("Erro ao salvar a venda", mensagemErro(err, "Tente novamente"));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <form onSubmit={salvar} className="space-y-4">
      <div>
        <Label htmlFor="venda-tipo">Tipo da venda *</Label>
        <select
          id="venda-tipo"
          required
          value={tipo}
          onChange={(e) => setTipo(e.target.value as TipoVenda)}
          className="w-full mt-1 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-slate-800 focus:border-sky-500 focus:outline-none h-11"
        >
          <option value="DESBASTE">Desbaste (retira parte dos animais; o ciclo continua)</option>
          <option value="DESPESCA_FINAL">Despesca final (carga da colheita final)</option>
        </select>
      </div>

      <DataLancamento
        label="Data da venda *"
        value={data}
        onChange={setData}
        retroativo={retroativo}
        onRetroativoChange={setRetroativo}
        aviso={AVISO_RETROATIVO}
      />

      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="venda-biomassa">Biomassa vendida (kg) *</Label>
          <Input
            id="venda-biomassa"
            required
            type="number"
            inputMode="decimal"
            step="any"
            min="0.01"
            max="9999999999"
            value={biomassa}
            onChange={(e) => setBiomassa(e.target.value)}
            placeholder="Ex: 200"
            className="mt-1"
          />
        </div>
        <div>
          <Label htmlFor="venda-peso">Peso médio (g) *</Label>
          <Input
            id="venda-peso"
            required
            type="number"
            inputMode="decimal"
            step="any"
            min="0.01"
            max="999999"
            value={peso}
            onChange={(e) => setPeso(e.target.value)}
            placeholder="Ex: 12.5"
            className="mt-1"
          />
        </div>
      </div>

      <div>
        <Label htmlFor="venda-preco">Preço por kg (R$)</Label>
        <Input
          id="venda-preco"
          type="number"
          inputMode="decimal"
          step="any"
          min="0"
          max="99999999"
          value={precoTexto}
          onChange={(e) => setPreco(e.target.value)}
          placeholder="Em branco: preço da tabela"
          className="mt-1"
        />
        <p className="mt-1 text-xs text-slate-500">
          {sugestaoAtual === null
            ? "Informe o peso médio para ver o preço sugerido pela tabela de preços."
            : sugestaoAtual.preco === null
              ? "Sem faixa na tabela de preços para este peso: informe o preço por kg."
              : `Sugerido pela tabela de preços: ${fmtMoney(sugestaoAtual.preco)}/kg. Você pode alterar.`}
        </p>
        {biomassaNum > 0 && pesoNum > 0 && (
          <p className="mt-0.5 text-xs text-slate-600 tabular-nums">
            Sai da população: cerca de <strong>{Math.round((biomassaNum * 1000) / pesoNum).toLocaleString("pt-BR")}</strong>{" "}
            animais
            {precoNum >= 0 && (
              <>
                {" "}
                · valor da venda: <strong>{fmtMoney(biomassaNum * precoNum)}</strong>
              </>
            )}
          </p>
        )}
      </div>

      <div>
        <Label htmlFor="venda-comprador">Comprador</Label>
        <Input
          id="venda-comprador"
          maxLength={120}
          value={comprador}
          onChange={(e) => setComprador(e.target.value)}
          className="mt-1"
        />
      </div>

      <div>
        <Label htmlFor="venda-observacao">Observação</Label>
        <Input
          id="venda-observacao"
          maxLength={500}
          value={observacao}
          onChange={(e) => setObservacao(e.target.value)}
          className="mt-1"
        />
      </div>

      <div className="pt-2 flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancelar}>
          Cancelar
        </Button>
        <Button type="submit" disabled={salvando}>
          {salvando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          {venda ? "Salvar venda" : "Registrar venda"}
        </Button>
      </div>
    </form>
  );
}

/** Aba "Vendas" do ciclo (só gestor): lista os desbastes e as cargas da despesca final, com lançar, corrigir e excluir. */
export function VendasCiclo({ cicloId, onAlterado }: { cicloId: string; onAlterado?: () => void }) {
  const { vendas, falhou, recarregar } = useVendasCiclo(cicloId);
  const [aberto, setAberto] = useState(false);
  const [editando, setEditando] = useState<VendaCiclo | null>(null);
  const [excluindoId, setExcluindoId] = useState<string | null>(null);

  // A venda muda população, FCA e lucro: quem hospeda a aba atualiza os indicadores
  const alterado = () => {
    recarregar();
    onAlterado?.();
  };

  const abrir = (venda: VendaCiclo | null) => {
    setEditando(venda);
    setAberto(true);
  };

  const excluir = async (v: VendaCiclo) => {
    const resumo = `${TIPOS_VENDA[v.tipo].toLowerCase()} de ${fmtQtd(v.biomassa_kg)} kg em ${fmtData(v.data_venda)}`;
    if (!window.confirm(`Excluir a venda: ${resumo}? Os animais dela voltam à população do ciclo.`)) return;
    setExcluindoId(v.id);
    try {
      await vendasApi.excluir(cicloId, v.id);
      toast.success("Venda excluída", resumo);
      alterado();
    } catch (err) {
      toast.error("Erro ao excluir a venda", mensagemErro(err, "Tente novamente"));
    } finally {
      setExcluindoId(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-bold text-slate-900 text-base">Vendas do ciclo</h3>
        <Button size="sm" onClick={() => abrir(null)}>
          <Plus className="w-4 h-4 mr-2" />
          Registrar venda
        </Button>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-sm">
        {vendas === null && !falhou && (
          <div className="flex justify-center py-8">
            <Loader2 className="w-5 h-5 text-sky-500 animate-spin" />
          </div>
        )}
        {falhou && <p className="py-8 text-center text-xs text-red-500">Não foi possível carregar as vendas.</p>}
        {vendas !== null && vendas.length === 0 && (
          <p className="py-8 text-center text-xs text-slate-400">Nenhuma venda registrada neste ciclo.</p>
        )}
        {vendas !== null && vendas.length > 0 && (
          <ul className="divide-y divide-slate-100">
            {vendas.map((v) => (
              <li key={v.id} className="py-3 flex items-start justify-between gap-3 text-xs">
                <div className="min-w-0 space-y-0.5">
                  <p className="font-semibold text-slate-800 flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span>{fmtData(v.data_venda)}</span>
                    <Badge variant={v.tipo === "DESPESCA_FINAL" ? "success" : "info"}>{TIPOS_VENDA[v.tipo]}</Badge>
                    {v.retroativo && <Badge variant="warning">retroativo</Badge>}
                  </p>
                  <p className="text-slate-600 tabular-nums">
                    {fmtQtd(v.biomassa_kg)} kg · {fmtQtd(v.peso_medio_g)} g ·{" "}
                    {v.animais_estimados.toLocaleString("pt-BR")} animais · {fmtMoney(v.preco_kg)}/kg ·{" "}
                    <strong className="text-slate-800">{fmtMoney(v.valor_total_rs)}</strong>
                  </p>
                  {v.comprador && <p className="text-slate-500">Comprador: {v.comprador}</p>}
                  {v.observacao && <p className="text-slate-500">{v.observacao}</p>}
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {excluindoId === v.id ? (
                    <Loader2 className="w-4 h-4 text-sky-500 animate-spin" />
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={() => abrir(v)}
                        className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100"
                        aria-label="Editar venda"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => excluir(v)}
                        className="p-1.5 rounded-lg text-red-500 hover:bg-red-50"
                        aria-label="Excluir venda"
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
      </div>

      <Dialog
        open={aberto}
        onOpenChange={setAberto}
        title={editando ? "Editar venda" : "Registrar venda"}
        description="Os animais vendidos saem da população; a receita entra no lucro realizado"
        className="max-h-[90vh] overflow-y-auto"
      >
        <div className="pt-2">
          <VendaForm
            cicloId={cicloId}
            venda={editando ?? undefined}
            onCancelar={() => setAberto(false)}
            onSalvo={() => {
              setAberto(false);
              alterado();
            }}
          />
        </div>
      </Dialog>
    </div>
  );
}
