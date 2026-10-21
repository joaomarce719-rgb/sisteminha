import * as React from "react";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface StepperCounterProps {
  label: string;
  unit: string;
  value: number;
  step?: number;
  min?: number;
  max?: number;
  onChange: (val: number) => void;
  icon?: LucideIcon;
  badge?: string;
  helperText?: string;
  quickAddOptions?: number[];
  className?: string;
}

export function StepperCounter({
  label,
  unit,
  value,
  step = 1,
  min = 0,
  max = 99999,
  onChange,
  icon: Icon,
  badge,
  helperText,
  quickAddOptions,
  className,
}: StepperCounterProps) {
  const [isEditing, setIsEditing] = React.useState(false);
  const [inputValue, setInputValue] = React.useState(String(value));
  const [valorAnterior, setValorAnterior] = React.useState(value);
  if (value !== valorAnterior) {
    setValorAnterior(value);
    setInputValue(String(value));
  }

  const handleDecrement = (amount = step) => {
    const next = Math.max(min, Number((value - amount).toFixed(2)));
    onChange(next);
  };

  const handleIncrement = (amount = step) => {
    const next = Math.min(max, Number((value + amount).toFixed(2)));
    onChange(next);
  };

  const handleBlur = () => {
    setIsEditing(false);
    const parsed = parseFloat(inputValue);
    if (!isNaN(parsed)) {
      onChange(Math.max(min, Math.min(max, parsed)));
    } else {
      setInputValue(String(value));
    }
  };

  return (
    <div
      className={cn(
        "rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm transition-all dark:border-white/10 dark:bg-[#151d2e]",
        className
      )}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {Icon && (
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-50 text-sky-600 dark:bg-sky-950/40 dark:text-sky-400">
              <Icon className="h-4 w-4" />
            </div>
          )}
          <span className="text-sm font-bold text-slate-800 dark:text-slate-100">
            {label}
          </span>
        </div>

        {badge && (
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {badge}
          </span>
        )}
      </div>

      {/* Stepper Controls Row */}
      <div className="flex items-center justify-between gap-3">
        {/* Decrement Button */}
        <button
          type="button"
          onClick={() => handleDecrement()}
          disabled={value <= min}
          className="flex h-14 w-16 items-center justify-center rounded-xl bg-slate-100 text-slate-700 font-bold transition-all hover:bg-slate-200 active:scale-95 disabled:opacity-40 disabled:pointer-events-none dark:bg-white/5 dark:text-slate-200 dark:hover:bg-white/10"
        >
          <span className="flex flex-col items-center text-xs leading-none">
            <span className="text-base font-extrabold">-{step}</span>
            <span className="text-[10px] text-slate-400 font-medium uppercase">{unit}</span>
          </span>
        </button>

        {/* Center Display / Input */}
        <div className="flex flex-1 flex-col items-center justify-center text-center">
          {isEditing ? (
            <input
              type="number"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onBlur={handleBlur}
              autoFocus
              className="w-28 text-center text-3xl font-extrabold text-slate-900 border-b-2 border-ocean-500 focus:outline-none dark:text-white dark:bg-transparent"
            />
          ) : (
            <button
              type="button"
              onClick={() => setIsEditing(true)}
              className="group flex flex-col items-center"
            >
              <span className="text-3xl font-extrabold tracking-tight text-slate-900 tabular-nums dark:text-white group-hover:text-ocean-500 transition-colors">
                {value}
              </span>
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mt-0.5">
                {unit} (toque para digitar)
              </span>
            </button>
          )}
        </div>

        {/* Increment Button */}
        <button
          type="button"
          onClick={() => handleIncrement()}
          disabled={value >= max}
          className="flex h-14 w-16 items-center justify-center rounded-xl bg-gradient-to-r from-ocean-600 to-ocean-500 text-white font-bold shadow-md shadow-ocean-500/20 transition-all hover:from-ocean-500 hover:to-ocean-400 active:scale-95 disabled:opacity-40 disabled:pointer-events-none"
        >
          <span className="flex flex-col items-center text-xs leading-none">
            <span className="text-base font-extrabold">+{step}</span>
            <span className="text-[10px] text-sky-100 font-medium uppercase">{unit}</span>
          </span>
        </button>
      </div>

      {/* Helper text or Quick options */}
      {(helperText || quickAddOptions) && (
        <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-xs dark:border-white/5">
          {helperText && (
            <span className="text-slate-500 dark:text-slate-400">{helperText}</span>
          )}
          {quickAddOptions && (
            <div className="flex gap-1.5 ml-auto">
              {quickAddOptions.map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => onChange(opt)}
                  className="rounded-lg bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-700 hover:bg-slate-200 dark:bg-white/5 dark:text-slate-300 dark:hover:bg-white/10"
                >
                  {opt} {unit}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
