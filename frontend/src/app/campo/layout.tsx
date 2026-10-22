"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Shell, LogOut, Utensils, Scale } from "lucide-react";
import Link from "next/link";
import { clearToken } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import { toast } from "@/components/ui/toast";

const NAV_ITEMS = [
  { href: "/campo/manejo", label: "Manejo Alimentar", icon: Utensils },
  { href: "/campo/biometria", label: "Biometria de Campo", icon: Scale },
];

export default function CampoLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { montado, user: sessao } = useSessao();
  const user = sessao?.role === "CAMPO" || sessao?.role === "GESTOR" ? sessao : null;

  useEffect(() => {
    if (montado && !user) router.push("/login");
  }, [montado, user, router]);

  const handleLogout = () => {
    clearToken();
    toast.info("Sessão encerrada", "Até logo!");
    router.push("/login");
  };

  if (!user) return null;

  return (
    <div className="min-h-screen flex flex-col bg-[#f8fafc]">
      {/* Header Mobile / Campo (Inspirado no Dark Navy das Imagens de Inspiração) */}
      <header className="sticky top-0 z-30 bg-[#0c1427] text-white shadow-md border-b border-slate-800">
        <div className="flex items-center justify-between px-4 py-3 max-w-2xl mx-auto">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Shell className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-extrabold text-sm tracking-tight text-white">SAD Carcinicultura</h1>
              <span className="text-[11px] font-semibold text-emerald-400">Operador de Campo</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {user.role === "GESTOR" && (
              <Link href="/gestor/dashboard" className="text-xs font-semibold text-emerald-300 hover:text-white">
                Painel do gestor
              </Link>
            )}
            <div className="text-right hidden sm:block">
              <p className="text-xs font-bold text-white">{user.nome}</p>
              <p className="text-[10px] text-slate-400">Manejo Ativo</p>
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

        {/* Abas de Navegação Inferiores da Barra */}
        <nav className="flex border-t border-slate-800 bg-[#0c1427]/80 backdrop-blur-sm">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-xs font-bold transition-all border-b-2 ${
                  isActive
                    ? "border-emerald-400 text-emerald-300 bg-white/5"
                    : "border-transparent text-slate-400 hover:text-white"
                }`}
              >
                <item.icon className="w-4 h-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>

      {/* Conteúdo Central */}
      <main className="flex-1 p-4 max-w-2xl mx-auto w-full">
        {children}
      </main>
    </div>
  );
}
