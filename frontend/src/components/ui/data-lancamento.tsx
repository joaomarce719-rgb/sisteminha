"use client";

import * as React from "react";
import { AlertTriangle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/** Hoje como "AAAA-MM-DD" no fuso local (toISOString usaria UTC e, à noite no Brasil, já seria amanhã). */
export function hojeLocal(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export interface DataLancamentoProps {
  /** Data "AAAA-MM-DD"; o formulário começa com `hojeLocal()`. */
  value: string;
  onChange: (data: string) => void;
  retroativo: boolean;
  onRetroativoChange: (retroativo: boolean) => void;
  label: string;
  /** Aviso do que o lançamento retroativo recalcula; o padrão vale para o uso de insumo. */
  aviso?: string;
}

const AVISO_PADRAO =
  "O custo médio do insumo será recalculado com este lançamento, e os usos já registrados a partir desta data podem mudar de valor.";

/**
 * Data de um lançamento: nasce hoje e travada. A caixa "Lançamento retroativo" libera o seletor
 * (nunca para o futuro) e avisa do recálculo; a API aplica a mesma regra via `retroativo`.
 */
export function DataLancamento({
  value,
  onChange,
  retroativo,
  onRetroativoChange,
  label,
  aviso = AVISO_PADRAO,
}: DataLancamentoProps) {
  const id = React.useId();

  const alternar = (marcado: boolean) => {
    // Desmarcar volta a data para hoje: a API recusa data passada sem a marca de retroativo
    if (!marcado) onChange(hojeLocal());
    onRetroativoChange(marcado);
  };

  return (
    <div className="space-y-2">
      <div>
        <Label htmlFor={`${id}-data`}>{label}</Label>
        <Input
          id={`${id}-data`}
          type="date"
          required
          value={value}
          max={hojeLocal()}
          disabled={!retroativo}
          onChange={(e) => onChange(e.target.value)}
          className="mt-1"
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id={`${id}-retroativo`}
          checked={retroativo}
          onChange={(e) => alternar(e.target.checked)}
          className="rounded border-slate-300 text-sky-600 focus:ring-sky-500 w-4 h-4 cursor-pointer"
        />
        <label htmlFor={`${id}-retroativo`} className="text-xs text-slate-700 font-medium cursor-pointer">
          Lançamento retroativo
        </label>
      </div>

      {retroativo && (
        <div className="flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{aviso}</span>
        </div>
      )}
    </div>
  );
}
