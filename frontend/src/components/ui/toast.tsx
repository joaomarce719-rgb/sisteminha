"use client";

import * as React from "react";
import { CheckCircle2, AlertTriangle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastType = "success" | "error" | "info";

interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
  description?: string;
}

interface ToastContextType {
  toasts: ToastItem[];
  addToast: (type: ToastType, message: string, description?: string, durationMs?: number) => void;
  removeToast: (id: string) => void;
}

declare global {
  interface Window {
    /** Ponte para o helper `toast` fora da árvore React (registrada pelo <Toaster />). */
    __sad_add_toast?: ToastContextType["addToast"];
  }
}

const ToastContext = React.createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);

  const addToast = React.useCallback(
    (type: ToastType, message: string, description?: string, durationMs = 4000) => {
      const id = Math.random().toString(36).substring(2, 9);
      setToasts((prev) => [...prev, { id, type, message, description }]);

      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, durationMs);
    },
    []
  );

  const removeToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToasterOverlay toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
}

function ToasterOverlay({
  toasts,
  onRemove,
}: {
  toasts: ToastItem[];
  onRemove: (id: string) => void;
}) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-5 right-5 z-[9999] flex flex-col gap-2.5 max-w-sm w-full pointer-events-none">
      {toasts.map((t) => {
        const isSuccess = t.type === "success";
        const isError = t.type === "error";

        return (
          <div
            key={t.id}
            className={cn(
              "pointer-events-auto flex items-start gap-3 rounded-2xl p-4 shadow-xl border backdrop-blur-md transition-all animate-in slide-in-from-top-2",
              isSuccess && "bg-white/95 border-emerald-200 text-slate-900 shadow-emerald-500/10",
              isError && "bg-white/95 border-red-200 text-slate-900 shadow-red-500/10",
              !isSuccess && !isError && "bg-white/95 border-slate-200 text-slate-900 shadow-sky-500/10"
            )}
          >
            {isSuccess && (
              <div className="rounded-xl bg-emerald-50 p-1.5 text-emerald-600 border border-emerald-200 shrink-0">
                <CheckCircle2 className="h-5 w-5" />
              </div>
            )}
            {isError && (
              <div className="rounded-xl bg-red-50 p-1.5 text-red-600 border border-red-200 shrink-0">
                <AlertTriangle className="h-5 w-5" />
              </div>
            )}
            {!isSuccess && !isError && (
              <div className="rounded-xl bg-sky-50 p-1.5 text-sky-600 border border-sky-200 shrink-0">
                <Info className="h-5 w-5" />
              </div>
            )}

            <div className="flex-1 min-w-0 pt-0.5">
              <p className="text-sm font-bold leading-tight">{t.message}</p>
              {t.description && (
                <p className="text-xs text-slate-500 mt-0.5 leading-snug">
                  {t.description}
                </p>
              )}
            </div>

            <button
              onClick={() => onRemove(t.id)}
              className="text-slate-400 hover:text-slate-600 p-1 -mr-1 rounded-lg"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}

// Global hook / helper
export const toast = {
  success: (message: string, description?: string, durationMs?: number) => {
    if (typeof window !== "undefined" && window.__sad_add_toast) {
      window.__sad_add_toast("success", message, description, durationMs);
    }
  },
  error: (message: string, description?: string, durationMs?: number) => {
    if (typeof window !== "undefined" && window.__sad_add_toast) {
      window.__sad_add_toast("error", message, description, durationMs);
    }
  },
  info: (message: string, description?: string) => {
    if (typeof window !== "undefined" && window.__sad_add_toast) {
      window.__sad_add_toast("info", message, description);
    }
  },
};

export function Toaster() {
  const context = React.useContext(ToastContext);
  React.useEffect(() => {
    if (context) {
      window.__sad_add_toast = context.addToast;
    }
    return () => {
      delete window.__sad_add_toast;
    };
  }, [context]);

  return null;
}
