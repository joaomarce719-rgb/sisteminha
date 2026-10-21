"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Shield,
  LogOut,
  ExternalLink,
  Shell,
} from "lucide-react";
import { clearToken, isSuperadmin } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/toast";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { montado, user: sessao } = useSessao();
  const user = sessao?.role === "GESTOR" && isSuperadmin(sessao) ? sessao : null;

  useEffect(() => {
    if (!montado || user) return;
    if (sessao?.role !== "GESTOR") {
      router.push("/login");
      return;
    }
    toast.error(
      "Acesso Restrito",
      "Este painel é de uso exclusivo da Administração Central do Sistema."
    );
    router.push("/gestor/dashboard");
  }, [montado, user, sessao, router]);

  const handleLogout = () => {
    clearToken();
    router.push("/login");
  };

  if (!user) return null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Topbar Institucional do Superadmin */}
      <header className="border-b border-slate-800/80 bg-slate-900/90 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-sky-500/10 border border-sky-500/25 flex items-center justify-center text-sky-400 shadow-sm">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-sm sm:text-base text-white tracking-tight">
                  SAD Carcinicultura
                </span>
                <Badge className="bg-sky-500/15 text-sky-400 border border-sky-500/30 text-[10px] font-bold uppercase tracking-wider">
                  Superadmin
                </Badge>
              </div>
              <p className="text-[11px] text-slate-400">
                Painel de Governança, Fazendas & Gestores
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/gestor/dashboard"
              className="hidden sm:inline-flex items-center gap-1.5 text-xs text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 px-3 py-1.5 rounded-xl transition-all font-medium"
            >
              <Shell className="w-3.5 h-3.5 text-sky-400" />
              <span>Ir para Visão da Fazenda</span>
              <ExternalLink className="w-3 h-3 text-slate-400" />
            </Link>

            <div className="h-6 w-px bg-slate-800 hidden sm:block" />

            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-sky-400">
                {user.nome.charAt(0).toUpperCase()}
              </div>
              <span className="text-xs font-semibold text-slate-300 hidden md:inline">
                {user.nome}
              </span>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={handleLogout}
              className="border-slate-800 bg-transparent text-slate-400 hover:text-red-400 hover:bg-red-500/10 hover:border-red-500/20 text-xs"
            >
              <LogOut className="w-3.5 h-3.5 mr-1.5" />
              Sair
            </Button>
          </div>
        </div>
      </header>

      {/* Conteúdo Principal */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Rodapé Institucional */}
      <footer className="border-t border-slate-800/60 py-4 text-center text-xs text-slate-400">
        Plataforma SAD Carcinicultura • Módulo de Governança e Administração Centralizada
      </footer>
    </div>
  );
}
