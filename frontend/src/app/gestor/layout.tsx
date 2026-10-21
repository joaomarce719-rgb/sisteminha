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
  Shield,
  ShieldCheck,
  Utensils,
} from "lucide-react";
import { clearToken, getStoredUser, isSuperadmin, type StoredUser } from "@/lib/api";

const NAV_ITEMS = [
  { href: "/gestor/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/gestor/viveiros", label: "Viveiros & Ciclos", icon: Shell },
  { href: "/gestor/simulacao", label: "Simulador ΔV", icon: TrendingUp },
  { href: "/gestor/financeiro", label: "Financeiro", icon: DollarSign },
  { href: "/gestor/tabelas-alimentares", label: "Tabelas Alimentares", icon: Utensils },
  { href: "/gestor/painel-noturno", label: "Painel Noturno", icon: Moon },
  { href: "/gestor/auditoria", label: "Auditoria", icon: ShieldCheck },
  { href: "/gestor/usuarios", label: "Operadores da Fazenda", icon: Users },
  { href: "/admin", label: "Painel Superadmin", icon: Shield },
];

export default function GestorLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<StoredUser | null>(null);
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
        className={`fixed lg:sticky top-0 left-0 z-50 h-screen w-72 bg-[#0c1427] border-r border-slate-800/80 flex flex-col transition-transform duration-300 lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Logo */}
        <div className="p-6 flex items-center gap-3 border-b border-slate-800">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-ocean-500 to-sky-400 flex items-center justify-center shadow-lg shadow-ocean-500/20">
            <Shell className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="font-bold text-base text-white">SAD Carcinicultura</h2>
            <span className="text-xs text-sky-400 font-semibold uppercase tracking-wider">Gestor</span>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="ml-auto lg:hidden text-slate-400 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-4 space-y-1.5 overflow-y-auto">
          {NAV_ITEMS.filter((item) => {
            if (item.href === "/admin") {
              return isSuperadmin(user);
            }
            return true;
          }).map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all ${
                  isActive
                    ? "bg-sky-500/15 text-sky-400 border border-sky-500/30 shadow-sm"
                    : "text-slate-400 hover:bg-white/5 hover:text-slate-100"
                }`}
              >
                <item.icon className="w-5 h-5" />
                {item.label}
                {isActive && <ChevronRight className="w-4 h-4 ml-auto text-sky-400" />}
              </Link>
            );
          })}
        </nav>

        {/* User */}
        <div className="p-4 border-t border-slate-800">
          <div className="flex items-center gap-3 px-3 mb-3">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-sky-600 to-emerald-500 flex items-center justify-center text-white font-bold text-sm">
              {user.nome.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-white truncate">
                {user.nome}
              </p>
              <p className="text-xs text-sky-400">Gestor / Dono</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-4 py-2.5 rounded-xl text-sm text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-all font-semibold"
          >
            <LogOut className="w-4 h-4" />
            Sair
          </button>
        </div>
      </aside>

      {/* Main Content Area com fundo limpo enterprise */}
      <main className="flex-1 min-w-0 bg-[#f8fafc]">
        {/* Top bar (mobile) */}
        <div className="lg:hidden sticky top-0 z-30 flex items-center gap-3 p-4 bg-white/95 backdrop-blur-lg border-b border-slate-200">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-xl hover:bg-slate-100"
          >
            <Menu className="w-5 h-5 text-slate-700" />
          </button>
          <h1 className="font-bold text-slate-900">SAD Carcinicultura</h1>
        </div>

        <div className="p-4 sm:p-6 lg:p-8">{children}</div>
      </main>
    </div>
  );
}
