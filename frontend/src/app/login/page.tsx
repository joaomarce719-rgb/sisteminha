"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Shell,
  Waves,
  Eye,
  EyeOff,
  LogIn,
  AlertTriangle,
  ShieldCheck,
  UserCheck,
  UserPlus,
  Sparkles,
  CheckCircle2,
} from "lucide-react";
import { login, registrarUsuario } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/toast";

export default function LoginPage() {
  const router = useRouter();
  const [tab, setTab] = useState<"login" | "register">("login");

  // Estado do formulário de Login
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [showSenha, setShowSenha] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Estado do formulário de Novo Usuário (Cadastro)
  const [regNome, setRegNome] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regTelefone, setRegTelefone] = useState("");
  const [regSenha, setRegSenha] = useState("");
  const [regConfirmaSenha, setRegConfirmaSenha] = useState("");
  const [regShowSenha, setRegShowSenha] = useState(false);
  const [regLoading, setRegLoading] = useState(false);
  const [regError, setRegError] = useState("");

  const handleRedirect = (role: string, targetEmail?: string) => {
    let dest = "/gestor/dashboard";
    if (role === "CAMPO") {
      dest = "/campo/manejo";
    } else if (role === "VIGIA") {
      dest = "/vigia/ronda";
    } else if (role === "GESTOR") {
      dest = "/gestor/dashboard";
    }

    if (typeof window !== "undefined") {
      window.location.href = dest;
    } else {
      router.push(dest);
    }
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const cleanEmail = email.trim().toLowerCase();
    const cleanSenha = senha.trim();

    if (!cleanEmail || !cleanSenha) {
      setError("Informe o e-mail e a senha de acesso.");
      return;
    }

    setLoading(true);

    try {
      const data = await login(cleanEmail, cleanSenha);
      toast.success("Login realizado com sucesso!", `Bem-vindo, ${data.nome || "Operador"}`);
      handleRedirect(data.role, cleanEmail);
    } catch (err: any) {
      const msg = err.message || "Falha na autenticação. Verifique seu e-mail e senha.";
      setError(msg);
      toast.error("Erro no login", msg);
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegError("");

    if (!regNome.trim()) {
      setRegError("Informe o nome completo do novo usuário.");
      return;
    }
    if (!regEmail.trim()) {
      setRegError("Informe o e-mail corporativo.");
      return;
    }
    if (regSenha.length < 6) {
      setRegError("A senha de acesso deve ter pelo menos 6 caracteres.");
      return;
    }
    if (regSenha !== regConfirmaSenha) {
      setRegError("A confirmação da senha não coincide com a senha digitada.");
      return;
    }

    setRegLoading(true);
    try {
      const novo = await registrarUsuario({
        nome_completo: regNome.trim(),
        email: regEmail.trim(),
        senha: regSenha,
        telefone_emergencia: regTelefone.trim() || undefined,
      });

      if (!novo.ativo) {
        // Contas novas aguardam aprovação de um gestor, que define o perfil de acesso
        toast.success("Cadastro enviado!", "Aguarde a aprovação de um gestor para acessar o sistema.");
        setEmail(regEmail.trim());
        setTab("login");
        return;
      }

      // Primeiro usuário do sistema: conta já ativa como gestor
      const loginData = await login(regEmail.trim(), regSenha);
      toast.info(`Bem-vindo, ${loginData.nome || regNome}!`, `Perfil ativo: ${loginData.role}`);
      handleRedirect(loginData.role);
    } catch (err: any) {
      const msg = err.message || "Erro ao criar usuário. Verifique os dados e tente novamente.";
      setRegError(msg);
      toast.error("Erro no cadastro", msg);
    } finally {
      setRegLoading(false);
    }
  };

  const handleDevBypass = async (role: "GESTOR" | "CAMPO" | "VIGIA", nome?: string) => {
    setError("");
    setLoading(true);

    const credenciais: Record<string, { email: string; pass: string }> = {
      GESTOR: { email: "gestor@sad.com", pass: "senha123" },
      CAMPO: { email: "campo@sad.com", pass: "senha123" },
      VIGIA: { email: "vigia@sad.com", pass: "senha123" },
    };

    const cred = credenciais[role] || credenciais.GESTOR;
    try {
      const data = await login(cred.email, cred.pass);
      toast.success("Autenticado com sucesso!", `Bem-vindo, ${data.nome || nome}! Perfil: ${data.role}`);
      handleRedirect(data.role, cred.email);
    } catch (err: any) {
      const msg = err.message || "Erro na autenticação automática. Verifique se o backend está ativo.";
      setError(msg);
      toast.error("Erro na autenticação", msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 relative overflow-hidden px-4 py-8">
      {/* Elementos visuais sutis de fundo */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-32 -left-32 w-96 h-96 bg-sky-200/40 rounded-full blur-3xl" />
        <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-emerald-200/30 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md relative z-10">
        <div className="bg-white rounded-3xl border border-slate-200/80 p-8 sm:p-10 shadow-xl shadow-slate-200/50">
          {/* Logo & Cabeçalho */}
          <div className="flex flex-col items-center text-center mb-6">
            <div className="w-16 h-16 rounded-2xl bg-slate-900 text-sky-400 flex items-center justify-center mb-4 shadow-lg shadow-slate-900/10 border border-slate-800">
              <Shell className="w-8 h-8" />
            </div>
            <div className="inline-flex items-center gap-1.5 rounded-full bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700 border border-sky-200 mb-2">
              <ShieldCheck className="w-3.5 h-3.5 text-sky-600" />
              SAD Carcinicultura
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              {tab === "login" ? "Acesso ao Sistema" : "Novo Usuário"}
            </h1>
            <p className="text-slate-500 text-xs mt-1">
              {tab === "login"
                ? "Sistema de Apoio à Decisão para Fazendas de Camarão"
                : "Solicite acesso; um gestor aprovará e definirá seu perfil"}
            </p>
          </div>

          {/* Seletor de Modo (Tabs Modernas) */}
          <div className="flex bg-slate-100 p-1 rounded-2xl mb-6">
            <button
              type="button"
              onClick={() => {
                setTab("login");
                setError("");
                setRegError("");
              }}
              className={`flex-1 py-2 text-xs font-bold rounded-xl transition-all ${
                tab === "login"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-900"
              }`}
            >
              Entrar no Sistema
            </button>
            <button
              type="button"
              onClick={() => {
                setTab("register");
                setError("");
                setRegError("");
              }}
              className={`flex-1 py-2 text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-1.5 ${
                tab === "register"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-900"
              }`}
            >
              <UserPlus className="w-3.5 h-3.5 text-sky-600" />
              Criar Novo Usuário
            </button>
          </div>

          {/* ══════════════════════════════════════════════════════ */}
          {/* TAB 1: FORMULÁRIO DE LOGIN                             */}
          {/* ══════════════════════════════════════════════════════ */}
          {tab === "login" && (
            <>
              {error && (
                <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-xs font-medium mb-6">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <form onSubmit={handleLoginSubmit} noValidate className="space-y-4">
                <div>
                  <Label htmlFor="email" className="text-xs font-semibold text-slate-700">
                    E-mail Corporativo
                  </Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="username"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="gestor@sad.com"
                    className="mt-1"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="senha" className="text-xs font-semibold text-slate-700">
                      Senha de Acesso
                    </Label>
                  </div>
                  <div className="relative mt-1">
                    <Input
                      id="senha"
                      name="senha"
                      type={showSenha ? "text" : "password"}
                      autoComplete="current-password"
                      value={senha}
                      onChange={(e) => setSenha(e.target.value)}
                      placeholder="••••••••"
                      className="pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowSenha(!showSenha)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                    >
                      {showSenha ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-slate-900 hover:bg-slate-800 text-white font-semibold py-2.5 mt-2 shadow-md shadow-slate-900/10"
                >
                  {loading ? (
                    <span className="flex items-center gap-2">
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Autenticando...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <LogIn className="w-4 h-4" />
                      Entrar no Sistema
                    </span>
                  )}
                </Button>

                <div className="text-center pt-2">
                  <button
                    type="button"
                    onClick={() => setTab("register")}
                    className="text-xs text-sky-600 hover:text-sky-700 font-medium inline-flex items-center gap-1 hover:underline"
                  >
                    <span>Não tem uma conta cadastrada?</span>
                    <strong className="font-semibold">Criar novo usuário</strong>
                  </button>
                </div>
              </form>

              {/* Atalhos de demonstração: somente em desenvolvimento (contas seed) */}
              {process.env.NODE_ENV === "development" && (
                <div className="mt-8 pt-6 border-t border-slate-100">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    Acesso Rápido de Teste
                  </span>
                  <Badge variant="outline" className="text-[10px] text-slate-500 border-slate-200">
                    RBAC Demo
                  </Badge>
                </div>

                <div className="space-y-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => handleDevBypass("GESTOR", "Gestor Geral")}
                    className="w-full justify-between border-slate-200 hover:bg-sky-50 hover:text-sky-700 hover:border-sky-300 transition-all text-xs font-semibold"
                  >
                    <span className="flex items-center gap-2">
                      <UserCheck className="w-3.5 h-3.5 text-sky-600" />
                      Entrar como Gestor (Visão Executiva)
                    </span>
                    <span className="text-[10px] text-slate-400 font-normal">Painel Total</span>
                  </Button>

                  <div className="grid grid-cols-2 gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => handleDevBypass("CAMPO", "Operador de Campo")}
                      className="justify-between border-slate-200 hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-300 transition-all text-xs font-semibold"
                    >
                      <span>Operador Campo</span>
                      <span className="text-[10px] text-slate-400">Trato</span>
                    </Button>

                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => handleDevBypass("VIGIA", "Vigia Noturno")}
                      className="justify-between border-slate-200 hover:bg-amber-50 hover:text-amber-700 hover:border-amber-300 transition-all text-xs font-semibold"
                    >
                      <span>Vigia Noturno</span>
                      <span className="text-[10px] text-slate-400">Ronda O₂</span>
                    </Button>
                  </div>
                </div>
              </div>
              )}
            </>
          )}

          {/* ══════════════════════════════════════════════════════ */}
          {/* TAB 2: FORMULÁRIO DE CADASTRO DE NOVO USUÁRIO          */}
          {/* ══════════════════════════════════════════════════════ */}
          {tab === "register" && (
            <form onSubmit={handleRegisterSubmit} noValidate className="space-y-3.5">
              {regError && (
                <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-xs font-medium mb-3">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{regError}</span>
                </div>
              )}

              <div>
                <Label htmlFor="regNome" className="text-xs font-semibold text-slate-700">
                  Nome Completo
                </Label>
                <Input
                  id="regNome"
                  name="nome_completo"
                  type="text"
                  value={regNome}
                  onChange={(e) => setRegNome(e.target.value)}
                  placeholder="Ex: Dr. Roberto Alencar"
                  className="mt-1"
                  required
                />
              </div>

              <div>
                <Label htmlFor="regEmail" className="text-xs font-semibold text-slate-700">
                  E-mail Corporativo
                </Label>
                <Input
                  id="regEmail"
                  name="email"
                  type="email"
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                  placeholder="roberto@fazenda.com"
                  className="mt-1"
                  required
                />
              </div>

              <div>
                <Label htmlFor="regTelefone" className="text-xs font-semibold text-slate-700">
                  Telefone / WhatsApp <span className="text-slate-400 font-normal">(Opcional)</span>
                </Label>
                <Input
                  id="regTelefone"
                  name="telefone"
                  type="tel"
                  value={regTelefone}
                  onChange={(e) => setRegTelefone(e.target.value)}
                  placeholder="(88) 99999-0000"
                  className="mt-1"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label htmlFor="regSenha" className="text-xs font-semibold text-slate-700">
                    Senha
                  </Label>
                  <div className="relative mt-1">
                    <Input
                      id="regSenha"
                      name="senha"
                      type={regShowSenha ? "text" : "password"}
                      value={regSenha}
                      onChange={(e) => setRegSenha(e.target.value)}
                      placeholder="••••••••"
                      className="pr-8 text-xs"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setRegShowSenha(!regShowSenha)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    >
                      {regShowSenha ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                <div>
                  <Label htmlFor="regConfirmaSenha" className="text-xs font-semibold text-slate-700">
                    Confirmar
                  </Label>
                  <div className="relative mt-1">
                    <Input
                      id="regConfirmaSenha"
                      name="confirma_senha"
                      type={regShowSenha ? "text" : "password"}
                      value={regConfirmaSenha}
                      onChange={(e) => setRegConfirmaSenha(e.target.value)}
                      placeholder="••••••••"
                      className="text-xs"
                      required
                    />
                  </div>
                </div>
              </div>

              <Button
                type="submit"
                disabled={regLoading}
                className="w-full bg-sky-600 hover:bg-sky-500 text-white font-semibold py-2.5 mt-3 shadow-md shadow-sky-600/20"
              >
                {regLoading ? (
                  <span className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Criando Usuário...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <UserPlus className="w-4 h-4" />
                    Solicitar Acesso
                  </span>
                )}
              </Button>

              <div className="text-center pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setTab("login")}
                  className="text-xs text-slate-500 hover:text-slate-800 font-medium inline-flex items-center gap-1 hover:underline"
                >
                  <span>Já tem cadastro?</span>
                  <strong className="text-sky-600 font-semibold">Voltar para Login</strong>
                </button>
              </div>
            </form>
          )}

          {/* Rodapé institucional */}
          <div className="flex items-center justify-center gap-1.5 mt-8 text-[11px] text-slate-400">
            <Waves className="w-3.5 h-3.5 text-sky-500" />
            <span>Litopenaeus vannamei • Vale do Jaguaribe, CE</span>
          </div>
        </div>
      </div>
    </div>
  );
}
