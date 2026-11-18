"use client";

import { useEffect, useState } from "react";
import { Loader2, Pencil, Trash2 } from "lucide-react";
import { usosInsumoApi } from "@/lib/api";
import { mensagemErro } from "@/lib/utils";
import type { FaseCusto, UsoInsumo } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/toast";

export const fmtQtd = (v: number) => v.toLocaleString("pt-BR", { maximumFractionDigits: 4 });
export const fmtMoney = (v: number) =>
  `R$ ${v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
// O preço unitário tem 4 casas (a API só arredonda o total a centavos)
export const fmtPreco = (v: number) =>
  `R$ ${v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`;
export const fmtData = (d: string) => new Date(`${d}T00:00:00`).toLocaleDateString("pt-BR");

const FASES: Record<FaseCusto, string> = { PREPARO: "Preparo", CULTIVO: "Cultivo", DESPESCA: "Despesca" };

/** Usos de insumo do ciclo; `usos` é null até a primeira resposta e para ciclo vazio (""). */
export function useUsosInsumo(cicloId: string) {
  // Guardados com o ciclo a que pertencem: trocar de ciclo não mostra a lista do anterior
  const [carregado, setCarregado] = useState<{ cicloId: string; lista: UsoInsumo[] } | null>(null);
  const [versao, setVersao] = useState(0);

  useEffect(() => {
    if (!cicloId) return;
    let ativo = true;
    usosInsumoApi
      .listar(cicloId)
      .then((lista) => {
        if (ativo) setCarregado({ cicloId, lista });
      })
      .catch((err) => {
        if (ativo) {
          setCarregado({ cicloId, lista: [] });
          toast.error("Não foi possível carregar os usos de insumo", mensagemErro(err, "Tente novamente"));
        }
      });
    return () => {
      ativo = false;
    };
  }, [cicloId, versao]);

  return {
    usos: carregado && carregado.cicloId === cicloId ? carregado.lista : null,
    recarregar: () => setVersao((v) => v + 1),
  };
}

export interface ListaUsosInsumoProps {
  usos: UsoInsumo[] | null;
  /** Gestor: mostra os botões de editar e excluir. */
  onEditar?: (uso: UsoInsumo) => void;
  onExcluir?: (uso: UsoInsumo) => void;
  excluindoId?: string | null;
}

/** Os campos de valor só vêm preenchidos para o gestor: para os demais papéis a lista mostra só quantidades. */
export function ListaUsosInsumo({ usos, onEditar, onExcluir, excluindoId }: ListaUsosInsumoProps) {
  if (usos === null) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="w-5 h-5 text-sky-500 animate-spin" />
      </div>
    );
  }
  if (usos.length === 0) {
    return <p className="py-8 text-center text-xs text-slate-400">Nenhum uso de insumo registrado neste ciclo.</p>;
  }

  return (
    <ul className="divide-y divide-slate-100">
      {usos.map((u) => (
        <li key={u.id} className="py-3 flex items-start justify-between gap-3 text-xs">
          <div className="min-w-0 space-y-0.5">
            <p className="font-semibold text-slate-800 flex flex-wrap items-center gap-x-2 gap-y-1">
              <span>
                {fmtData(u.data_uso)} · {u.insumo_nome}
              </span>
              {u.pendente_de_valor && <Badge variant="destructive">pendente de valor</Badge>}
              {u.preco_corrigido_rs != null && <Badge variant="secondary">preço fixo</Badge>}
              {u.retroativo && <Badge variant="warning">retroativo</Badge>}
              {u.recalculado_em && (
                <Badge variant="info" title={`Recalculado em ${new Date(u.recalculado_em).toLocaleDateString("pt-BR")}`}>
                  recalculado
                </Badge>
              )}
            </p>
            <p className="text-slate-600 tabular-nums">
              {fmtQtd(u.quantidade)} {u.unidade_uso} · {FASES[u.fase]}
              {u.valor_rs != null && u.preco_unitario_rs != null && (
                <>
                  {" "}
                  · <strong className="text-slate-800">{fmtMoney(u.valor_rs)}</strong> ({fmtPreco(u.preco_unitario_rs)}/
                  {u.unidade_uso})
                </>
              )}
            </p>
            {u.observacao && <p className="text-slate-500">{u.observacao}</p>}
          </div>
          {(onEditar || onExcluir) && (
            <div className="flex items-center gap-1 shrink-0">
              {excluindoId === u.id ? (
                <Loader2 className="w-4 h-4 text-sky-500 animate-spin" />
              ) : (
                <>
                  {onEditar && (
                    <button
                      type="button"
                      onClick={() => onEditar(u)}
                      className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100"
                      aria-label="Editar uso"
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                  )}
                  {onExcluir && (
                    <button
                      type="button"
                      onClick={() => onExcluir(u)}
                      className="p-1.5 rounded-lg text-red-500 hover:bg-red-50"
                      aria-label="Excluir uso"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </>
              )}
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}
