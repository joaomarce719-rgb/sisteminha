"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Shell, Waves, Eye, EyeOff, LogIn, AlertTriangle } from "lucide-react";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [showSenha, setShowSenha] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await login(email, senha);

      // Redirecionar conforme papel (RN-08)
      switch (data.role) {
        case "CAMPO":
          router.push("/campo/manejo");
          break;
        case "VIGIA":
          router.push("/vigia/ronda");
          break;
        case "GESTOR":
          router.push("/gestor/dashboard");
          break;
        default:
          router.push("/");
      }
    } catch (err: any) {
      setError(err.message || "Falha na autenticação");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden px-4">
      {/* Background animation */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 w-80 h-80 bg-ocean-500/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-shrimp-500/8 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-pond-500/5 rounded-full blur-3xl" />
      </div>

      <div className="glass-card p-8 sm:p-10 w-full max-w-md relative z-10">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-ocean-500 to-shrimp-500 flex items-center justify-center mb-4 shadow-lg shadow-ocean-500/20">
            <Shell className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold gradient-text">SAD Carcinicultura</h1>
          <p className="text-[var(--text-secondary)] text-sm mt-1">
            Sistema de Apoio à Decisão
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm mb-6">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="seu@email.com"
              className="w-full px-4 py-3 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all"
            />
          </div>

          <div>
            <label
              htmlFor="senha"
              className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5"
            >
              Senha
            </label>
            <div className="relative">
              <input
                id="senha"
                type={showSenha ? "text" : "password"}
                required
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                placeholder="••••••••"
                minLength={6}
                className="w-full px-4 py-3 pr-12 rounded-xl bg-white/5 border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-ocean-500 focus:ring-1 focus:ring-ocean-500/50 transition-all"
              />
              <button
                type="button"
                onClick={() => setShowSenha(!showSenha)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors"
              >
                {showSenha ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-ocean-600 to-ocean-500 text-white font-semibold text-base flex items-center justify-center gap-2 hover:from-ocean-500 hover:to-ocean-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-ocean-500/20 hover:shadow-ocean-500/30 active:scale-[0.98]"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <LogIn className="w-5 h-5" />
                Entrar
              </>
            )}
          </button>
        </form>

        {/* Developer Bypass Mode */}
        <div className="mt-6 pt-6 border-t border-[var(--border-subtle)]">
          <p className="text-xs text-center text-[var(--text-muted)] mb-3">Modo Desenvolvedor (Bypass Backend)</p>
          <div className="flex flex-col gap-2">
            <button
              type="button"
              onClick={() => {
                localStorage.setItem("sad_token", "fake-token");
                localStorage.setItem("sad_user", JSON.stringify({ nome: "Gestor Dev", role: "GESTOR" }));
                router.push("/gestor/dashboard");
              }}
              className="w-full py-2 rounded-lg bg-ocean-500/10 text-ocean-400 text-sm font-medium hover:bg-ocean-500/20 transition-all border border-ocean-500/20"
            >
              Entrar como GESTOR
            </button>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  localStorage.setItem("sad_token", "fake-token");
                  localStorage.setItem("sad_user", JSON.stringify({ nome: "Campo Dev", role: "CAMPO" }));
                  router.push("/campo/manejo");
                }}
                className="flex-1 py-2 rounded-lg bg-pond-500/10 text-pond-400 text-sm font-medium hover:bg-pond-500/20 transition-all border border-pond-500/20"
              >
                Entrar como CAMPO
              </button>
              <button
                type="button"
                onClick={() => {
                  localStorage.setItem("sad_token", "fake-token");
                  localStorage.setItem("sad_user", JSON.stringify({ nome: "Vigia Dev", role: "VIGIA" }));
                  router.push("/vigia/ronda");
                }}
                className="flex-1 py-2 rounded-lg bg-amber-500/10 text-amber-400 text-sm font-medium hover:bg-amber-500/20 transition-all border border-amber-500/20"
              >
                Entrar como VIGIA
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-center gap-1.5 mt-8 text-xs text-[var(--text-muted)]">
          <Waves className="w-3.5 h-3.5" />
          <span>Litopenaeus vannamei — Vale do Jaguaribe</span>
        </div>
      </div>
    </div>
  );
}
