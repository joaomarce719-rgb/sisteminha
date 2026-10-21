import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-ocean-500/15 text-ocean-600 dark:text-ocean-400 border border-ocean-500/30",
        secondary:
          "border-transparent bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200",
        destructive:
          "bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30",
        outline: "text-slate-700 border border-slate-200 dark:text-slate-300 dark:border-white/10",
        success:
          "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30",
        warning:
          "bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30",
        info:
          "bg-sky-500/15 text-sky-600 dark:text-sky-400 border border-sky-500/30",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
