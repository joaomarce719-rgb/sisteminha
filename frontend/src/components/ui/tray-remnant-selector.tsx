import * as React from "react";
import { CheckCircle2, AlertCircle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export type NivelSobra = "SEM_SOBRA" | "SOBRA_LEVE" | "SOBRA_MODERADA" | "SOBRA_EXCESSIVA";

export interface TrayRemnantSelectorProps {
  value: NivelSobra;
  onChange: (val: NivelSobra) => void;
  className?: string;
}

export function TrayRemnantSelector({
  value,
  onChange,
  className,
}: TrayRemnantSelectorProps) {
  const options = [
    {
      id: "SEM_SOBRA" as NivelSobra,
      label: "Nenhuma",
      subtitle: "100% consumida",
      action: "(Aumentar)",
      icon: CheckCircle2,
      activeColor: "border-emerald-500 bg-emerald-50/80 text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-500",
      iconColor: "text-emerald-600 dark:text-emerald-400",
    },
    {
      id: "SOBRA_LEVE" as NivelSobra,
      label: "Pouca",
      subtitle: "Consumo ideal",
      action: "(Manter)",
      icon: AlertCircle,
      activeColor: "border-amber-500 bg-amber-50/80 text-amber-900 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-500",
      iconColor: "text-amber-600 dark:text-amber-400",
    },
    {
      id: "SOBRA_EXCESSIVA" as NivelSobra,
      label: "Muita",
      subtitle: "Sobra excessiva",
      action: "(Reduzir)",
      icon: XCircle,
      activeColor: "border-red-500 bg-red-50/80 text-red-900 dark:bg-red-950/40 dark:text-red-300 dark:border-red-500",
      iconColor: "text-red-600 dark:text-red-400",
    },
  ];

  return (
    <div
      className={cn(
        "rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151d2e]",
        className
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-bold text-slate-800 dark:text-slate-100">
          Sobras nas Bandejas (Comedouros)
        </span>
        <span className="rounded-full bg-amber-50 border border-amber-200 px-2 py-0.5 text-[11px] font-semibold text-amber-700 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800/40">
          Regra Fuzzy
        </span>
      </div>

      <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
        Verifique as bandejas de controle após a dispersão para calibrar os próximos tratos:
      </p>

      <div className="grid grid-cols-3 gap-2.5">
        {options.map((opt) => {
          const isSelected = value === opt.id || (opt.id === "SOBRA_LEVE" && value === "SOBRA_MODERADA");
          const Icon = opt.icon;

          return (
            <button
              key={opt.id}
              type="button"
              onClick={() => onChange(opt.id)}
              className={cn(
                "relative flex flex-col items-center justify-between rounded-xl border-2 p-3 text-center transition-all active:scale-95",
                isSelected
                  ? opt.activeColor
                  : "border-slate-200/80 bg-slate-50/50 text-slate-600 hover:border-slate-300 hover:bg-slate-100/50 dark:border-white/10 dark:bg-white/5 dark:text-slate-400 dark:hover:bg-white/10"
              )}
            >
              <Icon className={cn("h-5 w-5 mb-1.5", isSelected ? opt.iconColor : "text-slate-400")} />
              <span className="text-sm font-bold leading-tight">{opt.label}</span>
              <span className="text-[10px] font-medium opacity-80 mt-1 leading-tight">
                {opt.subtitle}
              </span>
              <span className="text-[10px] font-extrabold mt-0.5 leading-tight">
                {opt.action}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
