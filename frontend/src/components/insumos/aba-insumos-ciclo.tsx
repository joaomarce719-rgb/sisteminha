"use client";

import { useState } from "react";
import { AlertTriangle, Plus } from "lucide-react";
import { usosInsumoApi } from "@/lib/api";
import { mensagemErro } from "@/lib/utils";
import type { EtapaPreparo, FaseCusto, UsoInsumo } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { toast } from "@/components/ui/toast";
import { fmtData, fmtQtd, ListaUsosInsumo, useUsosInsumo } from "@/components/insumos/lista-usos-insumo";
import { UsoInsumoForm } from "@/components/insumos/uso-insumo-form";

export interface AbaInsumosCicloProps {
  cicloId: string;
  onAlterado?: () => void;
  /** Fase dos usos lançados; o ciclo planejado usa PREPARO. */
  fase?: FaseCusto;
  /** Etapas do preparo, para ligar o uso a uma etapa. */
  etapas?: EtapaPreparo[];
  /** O formulário deixa escolher a fase de cada uso (ciclo em curso); `fase` vira só o padrão. */
  escolherFase?: boolean;
}

/** Aba "Insumos" do ciclo para o gestor: lista os usos com valores e permite lançar, corrigir e excluir. */
export function AbaInsumosCiclo({ cicloId, onAlterado, fase = "CULTIVO", etapas, escolherFase }: AbaInsumosCicloProps) {
  const { usos, recarregar } = useUsosInsumo(cicloId);
  const [aberto, setAberto] = useState(false);
  const [editando, setEditando] = useState<UsoInsumo | null>(null);
  const [excluindoId, setExcluindoId] = useState<string | null>(null);

  // O uso muda o custo do ciclo: quem hospeda a aba atualiza os indicadores
  const alterado = () => {
    recarregar();
    onAlterado?.();
  };

  const abrir = (uso: UsoInsumo | null) => {
    setEditando(uso);
    setAberto(true);
  };

  const excluir = async (uso: UsoInsumo) => {
    const resumo = `${fmtQtd(uso.quantidade)} ${uso.unidade_uso} de ${uso.insumo_nome} em ${fmtData(uso.data_uso)}`;
    if (!window.confirm(`Excluir o uso de ${resumo}? O custo gerado por ele também será excluído.`)) return;
    setExcluindoId(uso.id);
    try {
      await usosInsumoApi.excluir(cicloId, uso.id);
      toast.success("Uso excluído", resumo);
      alterado();
    } catch (err) {
      toast.error("Erro ao excluir o uso", mensagemErro(err, "Tente novamente"));
    } finally {
      setExcluindoId(null);
    }
  };

  const pendentes = (usos ?? []).filter((u) => u.pendente_de_valor).length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-bold text-slate-900 text-base">
          {fase === "PREPARO" ? "Insumos usados no preparo" : "Insumos usados no ciclo"}
        </h3>
        <Button size="sm" onClick={() => abrir(null)}>
          <Plus className="w-4 h-4 mr-2" />
          Registrar uso
        </Button>
      </div>

      {pendentes > 0 && (
        <div className="flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            {pendentes === 1 ? "1 uso está pendente de valor" : `${pendentes} usos estão pendentes de valor`}: registre
            a compra do insumo em Insumos e Compras ou corrija o preço do uso. O custo só entra no ciclo depois disso.
          </span>
        </div>
      )}

      <div className="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-sm">
        <ListaUsosInsumo usos={usos} onEditar={abrir} onExcluir={excluir} excluindoId={excluindoId} />
      </div>

      <Dialog
        open={aberto}
        onOpenChange={setAberto}
        title={editando ? "Editar uso de insumo" : "Registrar uso de insumo"}
        description="O custo é gerado pelo preço médio do insumo na data do uso"
        className="max-h-[90vh] overflow-y-auto"
      >
        <div className="pt-2">
          <UsoInsumoForm
            cicloId={cicloId}
            fase={fase}
            escolherFase={escolherFase}
            etapas={etapas}
            uso={editando ?? undefined}
            gestor
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
