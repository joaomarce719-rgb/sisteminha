"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Shell, LogOut, Moon } from "lucide-react";
import { clearToken, getStoredUser } from "@/lib/api";

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
    router.push("/login");
  };

  if (!user) return null;

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top bar */}
      <header className="sticky top-0 z-30 bg-[#0d1321]/95 backdrop-blur-lg border-b border-[var(--border-subtle)]">
        <div className="flex items-center justify-between px-4 py-3 max-w-2xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/30 flex items-center justify-center">
              <Moon className="w-4.5 h-4.5 text-amber-400" />
            </div>
            <div>
              <h1 className="font-bold text-sm text-[var(--text-primary)]">SAD Carcinicultura</h1>
              <span className="text-xs text-amber-400 font-medium">Vigia Noturno</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="text-right mr-2">
              <p className="text-sm font-medium text-[var(--text-primary)]">{user.nome}</p>
              <p className="text-xs text-amber-400">Vigia</p>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 rounded-xl text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10 transition-all"
            >
              <LogOut className="w-5 h-5" />
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
