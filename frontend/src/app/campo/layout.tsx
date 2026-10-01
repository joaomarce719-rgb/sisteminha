"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Shell,
  LogOut,
  Menu,
  X,
  ChevronRight,
  Utensils,
  Scale,
  BarChart3,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { clearToken, getStoredUser } from "@/lib/api";

const NAV_ITEMS = [
  { href: "/campo/manejo", label: "Manejo Alimentar", icon: Utensils },
  { href: "/campo/biometria", label: "Biometria", icon: Scale },
];

export default function CampoLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<{ nome: string; role: string } | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const stored = getStoredUser();
    if (!stored || stored.role !== "CAMPO") {
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
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-pond-500/20 to-ocean-500/20 border border-pond-500/30 flex items-center justify-center">
              <Shell className="w-4.5 h-4.5 text-pond-400" />
            </div>
            <div>
              <h1 className="font-bold text-sm text-[var(--text-primary)]">SAD Carcinicultura</h1>
              <span className="text-xs text-pond-400 font-medium">Campo</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="text-right mr-2 hidden sm:block">
              <p className="text-sm font-medium text-[var(--text-primary)]">{user.nome}</p>
              <p className="text-xs text-pond-400">Operador de Campo</p>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 rounded-xl text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10 transition-all"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Bottom nav */}
        <nav className="flex border-t border-[var(--border-subtle)]">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-all border-b-2 ${
                  isActive
                    ? "border-pond-400 text-pond-400 bg-pond-500/5"
                    : "border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
                }`}
              >
                <item.icon className="w-4 h-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>

      {/* Content */}
      <main className="flex-1 p-4 max-w-2xl mx-auto w-full">
        {children}
      </main>
    </div>
  );
}
