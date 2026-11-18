"use client";

import { useEffect, useState } from "react";
import { Loader2, Plus } from "lucide-react";
import { insumosApi, usosInsumoApi } from "@/lib/api";
import { cn, mensagemErro } from "@/lib/utils";
import type { FaseCusto, Insumo, UsoInsumo } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { DataLancamento, hojeLocal } from "@/components/ui/data-lancamento";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/toast";
import { fmtPreco, fmtQtd } from "@/components/insumos/lista-usos-insumo";

export interface UsoInsumoFormProps {
  cicloId: string;
  /** Fase do custo gerado pelo uso. */
  fase: FaseCusto;
  onSalvo: (uso: UsoInsumo) => void;
  /** Uso a corrigir (só o gestor edita); sem ele, o formulário lança um uso novo. */
  uso?: UsoInsumo;
  /** Gestor: vê o preço médio do insumo e pode fixar o preço unitário do uso. */
  gestor?: boolean;
  /** Mostra o botão "Cancelar" (formulário dentro de um diálogo). */
  onCancelar?: () => void;
}

/**
 * Lançamento de uso de insumo no ciclo. A lista de insumos já vem da API conforme o papel: o vigia
 * recebe só nome e unidade, o campo soma o saldo em quantidade e o gestor, o preço médio.
 */
export function UsoInsumoForm({ cicloId, fase, onSalvo, uso, gestor = false, onCancelar }: UsoInsumoFormProps) {
  const [insumos, setInsumos] = useState<Insumo[] | null>(null);
  // Cada uso lançado incrementa a versão e a lista é recarregada (o saldo mudou)
  const [versao, setVersao] = useState(0);
  const [insumoId, setInsumoId] = useState(uso?.insumo_id ?? "");
  const [quantidade, setQuantidade] = useState(uso ? String(uso.quantidade) : "");
  const [data, setData] = useState(uso?.data_uso ?? hojeLocal());
  // Uso de dias atrás editado hoje já é retroativo, mesmo que na época não fosse
  const [retroativo, setRetroativo] = useState(uso ? uso.retroativo || uso.data_uso < hojeLocal() : false);
  const [observacao, setObservacao] = useState(uso?.observacao ?? "");
  const [precoCorrigido, setPrecoCorrigido] = useState("");
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    let ativo = true;
    insumosApi
      .listar()
      .then((lista) => {
        if (ativo) setInsumos(lista);
      })
      .catch((err) => {
        if (ativo) {
          setInsumos([]);
          toast.error("Não foi possível carregar os insumos", mensagemErro(err, "Tente novamente"));
        }
      });
    return () => {
      ativo = false;
    };
  }, [versao]);

  // Insumo inativo só continua na lista se for o do uso que está sendo corrigido
  const opcoes = (insumos ?? []).filter((i) => i.ativo || i.id === uso?.insumo_id);
  const escolhido = opcoes.find((i) => i.id === insumoId);

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!escolhido) return;
    setSalvando(true);
    const qtd = parseFloat(quantidade);
    const payload = {
      insumo_id: escolhido.id,
      data_uso: data,
      quantidade: qtd,
      fase: uso?.fase ?? fase,
      observacao: observacao.trim() || null,
      // A caixa marcada com a data de hoje não é retroativa de fato
      retroativo: retroativo && data < hojeLocal(),
      // Só o gestor corrige o preço; sem informar, vale o preço médio do insumo
      preco_corrigido_rs: gestor && precoCorrigido !== "" ? parseFloat(precoCorrigido) : null,
    };
    try {
      const salvo = uso
        ? await usosInsumoApi.atualizar(cicloId, uso.id, payload)
        : await usosInsumoApi.criar(cicloId, payload);
      toast.success(
        uso ? "Uso atualizado!" : "Uso registrado!",
        `${fmtQtd(qtd)} ${escolhido.unidade_uso} de ${escolhido.nome}${salvo.pendente_de_valor ? " (pendente de valor)" : ""}`
      );
      if (!uso) {
        setQuantidade("");
        setObservacao("");
        setPrecoCorrigido("");
        setData(hojeLocal());
        setRetroativo(false);
        setVersao((v) => v + 1);
      }
      onSalvo(salvo);
    } catch (err) {
      toast.error("Erro ao salvar o uso do insumo", mensagemErro(err, "Tente novamente"));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <form onSubmit={salvar} className="space-y-4">
      <div>
        <Label htmlFor="uso-insumo">Insumo *</Label>
        <select
          id="uso-insumo"
          required
          value={insumoId}
          onChange={(e) => setInsumoId(e.target.value)}
          disabled={insumos === null}
          className="w-full mt-1 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-slate-800 focus:border-sky-500 focus:outline-none h-11 disabled:opacity-60"
        >
          <option value="" disabled>
            {insumos === null ? "Carregando insumos..." : "Selecione o insumo"}
          </option>
          {opcoes.map((i) => (
            <option key={i.id} value={i.id}>
              {i.nome} ({i.unidade_uso})
            </option>
          ))}
        </select>
        {insumos !== null && opcoes.length === 0 && (
          <p className="mt-1 text-xs text-slate-500">Nenhum insumo cadastrado. O gestor cadastra em Insumos e Compras.</p>
        )}
        {escolhido && escolhido.saldo != null && (
          <p className="mt-1 text-xs text-slate-500">
            Saldo:{" "}
            <strong className={cn("tabular-nums", escolhido.saldo < 0 ? "text-red-600" : "text-slate-800")}>
              {fmtQtd(escolhido.saldo)} {escolhido.unidade_uso}
            </strong>
            {escolhido.saldo < 0 && " (negativo)"}
          </p>
        )}
        {gestor && escolhido && (
          <p className="mt-0.5 text-xs text-slate-500">
            {escolhido.preco_medio_rs == null
              ? "Sem compras registradas: o uso ficará pendente de valor."
              : `Preço médio: ${fmtPreco(escolhido.preco_medio_rs)}/${escolhido.unidade_uso}`}
          </p>
        )}
      </div>

      <div>
        <Label htmlFor="uso-quantidade">Quantidade{escolhido ? ` (${escolhido.unidade_uso})` : ""} *</Label>
        <Input
          id="uso-quantidade"
          required
          type="number"
          inputMode="decimal"
          step="any"
          min="0.0001"
          max="9999999999"
          value={quantidade}
          onChange={(e) => setQuantidade(e.target.value)}
          placeholder="Ex: 50"
          className="mt-1"
        />
      </div>

      <DataLancamento label="Data do uso *" value={data} onChange={setData} retroativo={retroativo} onRetroativoChange={setRetroativo} />

      <div>
        <Label htmlFor="uso-observacao">Observação</Label>
        <Input
          id="uso-observacao"
          maxLength={500}
          value={observacao}
          onChange={(e) => setObservacao(e.target.value)}
          className="mt-1"
        />
      </div>

      {gestor && (
        <div>
          <Label htmlFor="uso-preco">Preço unitário fixo (R$){escolhido ? ` por ${escolhido.unidade_uso}` : ""}</Label>
          <Input
            id="uso-preco"
            type="number"
            inputMode="decimal"
            step="any"
            min="0.0001"
            max="99999999"
            value={precoCorrigido}
            onChange={(e) => setPrecoCorrigido(e.target.value)}
            placeholder={
              uso?.preco_unitario_rs != null ? `Atual: ${fmtPreco(uso.preco_unitario_rs)}` : "Em branco: preço médio"
            }
            className="mt-1"
          />
          <p className="mt-1 text-xs text-slate-500">
            Use para acertar o preço pela nota fiscal; o reprocessamento mantém o valor. Em branco, vale o preço médio
            do insumo
            {uso ? " (salvar sem informar desfaz uma correção anterior)." : "."}
          </p>
        </div>
      )}

      <div className="pt-2 flex justify-end gap-2">
        {onCancelar && (
          <Button type="button" variant="outline" onClick={onCancelar}>
            Cancelar
          </Button>
        )}
        <Button type="submit" disabled={salvando || !escolhido} className={onCancelar ? "" : "w-full"}>
          {salvando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          {uso ? "Salvar uso" : "Registrar uso"}
        </Button>
      </div>
    </form>
  );
}
