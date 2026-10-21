"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Shell, LogOut, Moon, Activity } from "lucide-react";
import { clearToken, getStoredUser } from "@/lib/api";
import { toast } from "@/components/ui/toast";

export default function VigiaLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<{ nome: string; role: string } | null>(null);

  useEffect(() => {
    const stored = getStoredUser();
    if (!stored || stored.role !== "VIGIA") {
      router.push("/login");
      return;
    }
    setUser(stored);
  }, [router]);

  const handleLogout = () => {
    clearToken();
    toast.info("Sessão do vigia encerrada", "Turno finalizado!");
    router.push("/login");
  };

  if (!user) return null;

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      {/* Top bar em Dark Navy (#0c1427) com destaque âmbar para turno noturno */}
      <header className="sticky top-0 z-30 bg-[#0c1427] text-white shadow-md border-b border-slate-800">
        <div className="flex items-center justify-between px-4 py-3 max-w-2xl mx-auto">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <Moon className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-extrabold text-sm tracking-tight text-white">SAD Carcinicultura</h1>
              <span className="text-[11px] font-semibold text-amber-400 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                Vigia Noturno • Ronda
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-xs font-bold text-white">{user.nome}</p>
              <p className="text-[10px] text-slate-400">Plantão O₂</p>
            </div>
            <button
              onClick={handleLogout}
              title="Sair do sistema"
              className="p-2 rounded-xl text-slate-400 hover:text-red-400 hover:bg-white/10 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 p-4 max-w-2xl mx-auto w-full">
        {children}
      </main>
    </div>
  );
}
