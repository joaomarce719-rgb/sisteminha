"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import {
  Shell,
  LayoutDashboard,
  FlaskConical,
  DollarSign,
  BarChart3,
  Users,
  Moon,
  Settings,
  LogOut,
  Menu,
  X,
  ChevronRight,
  TrendingUp,
} from "lucide-react";
import { clearToken, getStoredUser } from "@/lib/api";

const NAV_ITEMS = [
  { href: "/gestor/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/gestor/viveiros", label: "Viveiros & Ciclos", icon: Shell },
  { href: "/gestor/simulacao", label: "Simulador ΔV", icon: TrendingUp },
  { href: "/gestor/financeiro", label: "Financeiro", icon: DollarSign },
  { href: "/gestor/painel-noturno", label: "Painel Noturno", icon: Moon },
  { href: "/gestor/usuarios", label: "Usuários", icon: Users },
];

export default function GestorLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<{ nome: string; role: string } | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    const stored = getStoredUser();
    if (!stored || stored.role !== "GESTOR") {
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
    <div className="min-h-screen flex">
      {/* Sidebar overlay (mobile) */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:sticky top-0 left-0 z-50 h-screen w-72 bg-[#0d1321] border-r border-[var(--border-subtle)] flex flex-col transition-transform duration-300 lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Logo */}
        <div className="p-6 flex items-center gap-3 border-b border-[var(--border-subtle)]">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-ocean-500 to-shrimp-500 flex items-center justify-center shadow-lg shadow-ocean-500/20">
            <Shell className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="font-bold text-base text-[var(--text-primary)]">SAD Carcinicultura</h2>
            <span className="text-xs text-ocean-400 font-medium">Gestor</span>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="ml-auto lg:hidden text-[var(--text-muted)]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? "bg-ocean-500/15 text-ocean-400 border border-ocean-500/25"
                    : "text-[var(--text-secondary)] hover:bg-white/5 hover:text-[var(--text-primary)]"
                }`}
              >
                <item.icon className="w-5 h-5" />
                {item.label}
                {isActive && <ChevronRight className="w-4 h-4 ml-auto" />}
              </Link>
            );
          })}
        </nav>

        {/* User */}
        <div className="p-4 border-t border-[var(--border-subtle)]">
          <div className="flex items-center gap-3 px-3 mb-3">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-ocean-600 to-pond-500 flex items-center justify-center text-white font-bold text-sm">
              {user.nome.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                {user.nome}
              </p>
              <p className="text-xs text-ocean-400">Gestor / Dono</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-4 py-2.5 rounded-xl text-sm text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10 transition-all"
          >
            <LogOut className="w-4 h-4" />
            Sair
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 min-w-0">
        {/* Top bar (mobile) */}
        <div className="lg:hidden sticky top-0 z-30 flex items-center gap-3 p-4 bg-[var(--bg-primary)]/95 backdrop-blur-lg border-b border-[var(--border-subtle)]">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-xl hover:bg-white/5"
          >
            <Menu className="w-5 h-5 text-[var(--text-secondary)]" />
          </button>
          <h1 className="font-semibold text-[var(--text-primary)]">SAD Carcinicultura</h1>
        </div>

        <div className="p-4 sm:p-6 lg:p-8">{children}</div>
      </main>
    </div>
  );
}
