import * as React from "react";
import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

export type MetricAccent = "ocean" | "emerald" | "coral" | "amber" | "slate" | "red" | "purple";

export interface MetricCardProps extends React.HTMLAttributes<HTMLDivElement> {
  label?: string;
  title?: string;
  value: string | number;
  unit?: string;
  subtitle?: string;
  badge?: {
    text: string;
    variant?: "success" | "warning" | "destructive" | "info" | "neutral";
  };
  icon?: LucideIcon;
  accentColor?: MetricAccent;
  accent?: string;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
}

export function MetricCard({
  label,
  title,
  value,
  unit,
  subtitle,
  badge,
  icon: Icon,
  accentColor,
  accent,
  trend,
  className,
  ...props
}: MetricCardProps) {
  const chosenAccent = ((accentColor || accent || "ocean") as MetricAccent);

  const accentStyles: Record<MetricAccent, string> = {
    ocean: "border-t-4 border-t-sky-500",
    emerald: "border-t-4 border-t-emerald-500",
    coral: "border-t-4 border-t-red-500",
    red: "border-t-4 border-t-red-500",
    amber: "border-t-4 border-t-amber-500",
    slate: "border-t-4 border-t-slate-400",
    purple: "border-t-4 border-t-purple-500",
  };

  const iconBgStyles: Record<MetricAccent, string> = {
    ocean: "bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20",
    emerald: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
    coral: "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20",
    red: "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20",
    amber: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
    slate: "bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20",
    purple: "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20",
  };

  const effectiveLabel = title || label || "";

  return (
    <div
      className={cn(
        "relative rounded-2xl bg-white p-5 shadow-sm border border-slate-200/80 transition-all hover:shadow-md dark:bg-[#151d2e] dark:border-white/10",
        accentStyles[chosenAccent] || accentStyles.ocean,
        className
      )}
      {...props}
    >
      <div className="flex items-start justify-between">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            {effectiveLabel}
          </span>
          <div className="mt-2 flex items-baseline gap-1">
            <span className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">
              {value}
            </span>
            {unit && (
              <span className="text-xs font-semibold text-slate-400 dark:text-slate-500">
                {unit}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
              {subtitle}
            </p>
          )}
        </div>

        {Icon && (
          <div
            className={cn(
              "flex h-11 w-11 items-center justify-center rounded-xl border",
              iconBgStyles[chosenAccent] || iconBgStyles.ocean
            )}
          >
            <Icon className="h-5 w-5" />
          </div>
        )}
      </div>

      {/* Rodapé: Badge ou Tendência */}
      <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2.5 dark:border-white/5">
        {trend && (
          <span
            className={cn(
              "text-xs font-bold",
              trend.isPositive ? "text-emerald-600" : "text-red-500"
            )}
          >
            {trend.isPositive ? "↑ " : "↓ "}
            {trend.value}
          </span>
        )}

        {badge && (
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-bold tracking-wide uppercase",
              badge.variant === "success" && "bg-emerald-50 text-emerald-700 border border-emerald-200",
              badge.variant === "warning" && "bg-amber-50 text-amber-700 border border-amber-200",
              badge.variant === "destructive" && "bg-red-50 text-red-700 border border-red-200",
              badge.variant === "info" && "bg-sky-50 text-sky-700 border border-sky-200",
              (!badge.variant || badge.variant === "neutral") && "bg-slate-100 text-slate-600 border border-slate-200"
            )}
          >
            {badge.text}
          </span>
        )}
      </div>
    </div>
  );
}
