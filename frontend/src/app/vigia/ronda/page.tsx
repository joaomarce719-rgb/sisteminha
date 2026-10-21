"use client";

import { useEffect, useState } from "react";
import {
  Moon,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Droplets,
  Thermometer,
  Wind,
  Zap,
  Wrench,
} from "lucide-react";
import { ciclosApi, viveirosApi, rondasApi } from "@/lib/api";
import type { CicloProdutivo, Viveiro, RondaNoturna } from "@/lib/types";
import { StepperCounter } from "@/components/ui/stepper-counter";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/toast";
import { agoraLocalInput, localInputParaIso, mensagemErro } from "@/lib/utils";

const COMP_OPTIONS = [
  { value: "NORMAL_FUNDO", label: "Normal (Fundo)", desc: "Comportamento calmo no fundo", icon: "🟢", color: "emerald" },
  { value: "FLOR_DAGUA_BOQUEANDO", label: "Boqueando / Flor d'água", desc: "Superfície por asfixia", icon: "🔴", color: "red" },
  { value: "NATACAO_AGITADA", label: "Natação Agitada", desc: "Estresse ou predadores", icon: "🟡", color: "amber" },
  { value: "ECDISE_MASSIVA", label: "Ecdise Massiva", desc: "Muda coletiva de carapaça", icon: "🟣", color: "purple" },
  { value: "PRESENCA_BORDAS", label: "Presença nas Bordas", desc: "Aglomeração nos taludes", icon: "🟠", color: "orange" },
];

const ENERGIA_OPTIONS = [
  { value: "REDE_CONCESSIONARIA", label: "Rede Elétrica", icon: Zap },
  { value: "GERADOR_DIESEL", label: "Gerador Diesel", icon: Wrench },
  { value: "SEM_ENERGIA_QUEDA", label: "Queda / Sem Energia", icon: AlertTriangle },
];

function fmtDateTime(d: string) {
  return new Date(d).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export default function RondaPage() {
  const [viveiros, setViveiros] = useState<Viveiro[]>([]);
  const [ciclos, setCiclos] = useState<CicloProdutivo[]>([]);
  const [selectedCiclo, setSelectedCiclo] = useState("");
  const [rondas, setRondas] = useState<RondaNoturna[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const [dataHora, setDataHora] = useState(agoraLocalInput());
  const [o2MgL, setO2MgL] = useState<number>(4.8);
  const [tempC, setTempC] = useState<number>(28.5);
  const [comportamento, setComportamento] = useState("NORMAL_FUNDO");
  const [aeradoresInstalados, setAeradoresInstalados] = useState<number>(4);
  const [aeradoresLigados, setAeradoresLigados] = useState<number>(4);
  const [fonteEnergia, setFonteEnergia] = useState("REDE_CONCESSIONARIA");
  const [falhaMecanica, setFalhaMecanica] = useState(false);
  const [detalhesFalha, setDetalhesFalha] = useState("");
  const [observacoes, setObservacoes] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [vivs, cycs] = await Promise.all([
          viveirosApi.listar(),
          ciclosApi.listar({ status_filtro: "ATIVO" }),
        ]);
        setViveiros(vivs);
        setCiclos(cycs);
        if (cycs.length > 0) setSelectedCiclo(cycs[0].id);
      } catch {} finally { setLoading(false); }
    }
    load();
  }, []);

  useEffect(() => {
    if (!selectedCiclo) return;
    async function loadRondas() {
      try {
        const data = await rondasApi.listarPorCiclo(selectedCiclo);
        setRondas(data);
      } catch {}
    }
    loadRondas();
  }, [selectedCiclo]);

  const cicloAtual = ciclos.find((c) => c.id === selectedCiclo);
  const viveiroAtual = viveiros.find((v) => v.id === cicloAtual?.viveiro_id);

  const isO2Emergencia = o2MgL < 2.5;
  const isO2Alerta = o2MgL >= 2.5 && o2MgL < 4.0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCiclo) {
      toast.error("Selecione um viveiro com ciclo ativo");
      return;
    }
    setSubmitting(true);
    try {
      const ronda = await rondasApi.criar({
        ciclo_id: selectedCiclo,
        // Hora local com offset: as regras noturnas (00h–05h30) usam o horário da fazenda
        data_hora_ronda: localInputParaIso(dataHora),
        oxigenio_dissolvido_mg_l: o2MgL,
        temperatura_agua_c: tempC,
        comportamento,
        observacoes: observacoes || null,
        aeradores_instalados: aeradoresInstalados,
        aeradores_ligados: aeradoresLigados,
        fonte_energia: fonteEnergia,
        falha_mecanica_detectada: falhaMecanica,
        detalhes_falha: falhaMecanica ? detalhesFalha || null : null,
      });

      toast.success("Ronda registrada com sucesso!", `O₂: ${o2MgL.toFixed(1)} mg/L • Aeradores: ${aeradoresLigados}/${aeradoresInstalados}`);
      for (const alerta of ronda.alertas ?? []) {
        // Alertas ficam visíveis por mais tempo: exigem ação imediata do vigia
        toast.error(alerta.titulo, alerta.mensagem, 20000);
      }

      const data = await rondasApi.listarPorCiclo(selectedCiclo);
      setRondas(data);
      setObservacoes("");
      setDetalhesFalha("");
      setFalhaMecanica(false);
      setDataHora(agoraLocalInput());
    } catch (err) {
      toast.error("Erro ao registrar ronda", mensagemErro(err, "Tente novamente"));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-amber-500" />
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto space-y-5 pb-12">
      {/* ── Top Header Card (Inspirado nas Imagens de Ronda/Vigia) ── */}
      <div className="rounded-3xl bg-gradient-to-br from-[#0c1527] to-[#1a253a] p-6 text-white shadow-xl border border-white/10">
        <div className="flex items-center justify-between mb-3">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/20 px-3 py-1 text-xs font-bold text-amber-300 border border-amber-500/30">
            <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
            Vigia Noturno
          </div>
          <span className="text-xs text-slate-400 font-medium">
            Turno Noturno
          </span>
        </div>

        <h1 className="text-2xl font-black tracking-tight flex items-center gap-2.5">
          <Moon className="h-6 w-6 text-amber-400" />
          Ronda & Parâmetros de Água
        </h1>
        <p className="text-xs text-slate-300 mt-1">
          Monitoramento crítico de oxigênio dissolvido ($O_2$), aeradores e sanidade.
        </p>
      </div>

      {/* ── Seletor de Viveiro ── */}
      <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151d2e]">
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Viveiro Inspecionado
          </label>
          {cicloAtual && (
            <Badge variant="success">Lote #{cicloAtual.id.substring(0, 6)}</Badge>
          )}
        </div>

        <select
          value={selectedCiclo}
          onChange={(e) => setSelectedCiclo(e.target.value)}
          className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-800 focus:border-amber-500 focus:outline-none dark:border-white/10 dark:bg-white/5 dark:text-white"
        >
          {ciclos.map((c) => {
            const v = viveiros.find((viv) => viv.id === c.viveiro_id);
            return (
              <option key={c.id} value={c.id} className="text-slate-900 bg-white dark:bg-slate-900 dark:text-white">
                {v?.identificacao || "Viveiro"} — {(c.quantidade_pos_larvas / 1000).toFixed(0)}k PLs
              </option>
            );
          })}
        </select>
      </div>

      {/* ── Formulário da Ronda ── */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Alerta de O2 Crítico em Destaque */}
        {isO2Emergencia && (
          <div className="rounded-2xl border-2 border-red-500 bg-red-50 p-4 text-red-900 animate-pulse flex items-start gap-3 shadow-lg shadow-red-500/20">
            <AlertTriangle className="h-6 w-6 text-red-600 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-black text-sm uppercase tracking-wide text-red-700">
                Emergência: Hipóxia Crítica (&lt; 2.5 mg/L)
              </h4>
              <p className="text-xs text-red-600 font-medium mt-0.5">
                Risco de asfixia imediata e perda massiva. Ligue todos os aeradores disponíveis agora!
              </p>
            </div>
          </div>
        )}

        {/* Stepper para Oxigênio Dissolvido */}
        <StepperCounter
          label="Oxigênio Dissolvido (O₂)"
          unit="mg/L"
          value={o2MgL}
          step={0.1}
          min={0.0}
          max={15.0}
          onChange={(val) => setO2MgL(val)}
          icon={Droplets}
          badge={isO2Emergencia ? "EMERGÊNCIA" : isO2Alerta ? "ALERTA" : "NORMAL"}
          helperText="Medição no ponto central ou oposto ao aerador"
          quickAddOptions={[1.8, 2.5, 3.5, 4.5, 5.5]}
        />

        {/* Stepper para Temperatura */}
        <StepperCounter
          label="Temperatura da Água"
          unit="°C"
          value={tempC}
          step={0.5}
          min={15.0}
          max={40.0}
          onChange={(val) => setTempC(val)}
          icon={Thermometer}
          badge="Termômetro"
          quickAddOptions={[26.0, 27.5, 28.5, 30.0]}
        />

        {/* Aeradores Ligados vs Instalados */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151d2e]">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Wind className="h-4 w-4 text-sky-500" />
              <span className="text-sm font-bold text-slate-800 dark:text-slate-100">
                Aeradores em Funcionamento
              </span>
            </div>
            <Badge variant="info">{aeradoresLigados} de {aeradoresInstalados} Ligados</Badge>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                Instalados no Viveiro
              </label>
              <input
                type="number"
                min={1}
                max={20}
                value={aeradoresInstalados}
                onChange={(e) => setAeradoresInstalados(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-center text-lg font-bold text-slate-800 focus:outline-none dark:border-white/10 dark:bg-white/5 dark:text-white"
              />
            </div>
            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                Ligados Nesta Ronda
              </label>
              <input
                type="number"
                min={0}
                max={aeradoresInstalados}
                value={aeradoresLigados}
                onChange={(e) => setAeradoresLigados(Math.min(aeradoresInstalados, Math.max(0, parseInt(e.target.value) || 0)))}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-center text-lg font-bold text-slate-800 focus:outline-none dark:border-white/10 dark:bg-white/5 dark:text-white"
              />
            </div>
          </div>

          {/* Quick Tap Buttons para aeradores */}
          <div className="flex gap-2">
            {[0, 1, 2, 3, 4, 6].filter((n) => n <= aeradoresInstalados).map((num) => (
              <button
                key={num}
                type="button"
                onClick={() => setAeradoresLigados(num)}
                className={`flex-1 rounded-lg py-1.5 text-xs font-bold transition-all ${
                  aeradoresLigados === num
                    ? "bg-sky-500 text-white shadow-sm"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-white/5 dark:text-slate-300"
                }`}
              >
                {num}
              </button>
            ))}
          </div>
        </div>

        {/* Comportamento do Camarão */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151d2e]">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-bold text-slate-800 dark:text-slate-100">
              Comportamento do Camarão
            </span>
            <span className="text-xs text-slate-400">Inspeção Visual</span>
          </div>

          <div className="space-y-2">
            {COMP_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setComportamento(opt.value)}
                className={`w-full flex items-center justify-between rounded-xl border p-3 text-left transition-all ${
                  comportamento === opt.value
                    ? "border-sky-500 bg-sky-50/70 text-sky-950 font-bold dark:bg-sky-950/40 dark:text-sky-200"
                    : "border-slate-200 bg-slate-50/40 text-slate-600 hover:bg-slate-100/50 dark:border-white/10 dark:bg-white/5 dark:text-slate-400"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-base">{opt.icon}</span>
                  <div>
                    <div className="text-xs font-bold leading-tight">{opt.label}</div>
                    <div className="text-[11px] text-slate-500 font-normal mt-0.5">{opt.desc}</div>
                  </div>
                </div>
                {comportamento === opt.value && (
                  <CheckCircle2 className="h-4 w-4 text-sky-600 shrink-0" />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Fonte de Energia */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151d2e]">
          <span className="text-sm font-bold text-slate-800 dark:text-slate-100 block mb-3">
            Fonte de Energia do Viveiro
          </span>
          <div className="grid grid-cols-3 gap-2">
            {ENERGIA_OPTIONS.map((opt) => {
              const Icon = opt.icon;
              const isSelected = fonteEnergia === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setFonteEnergia(opt.value)}
                  className={`flex flex-col items-center justify-center rounded-xl border p-2.5 text-center text-xs font-semibold transition-all ${
                    isSelected
                      ? "border-amber-500 bg-amber-50 text-amber-900 font-bold dark:bg-amber-950/40 dark:text-amber-300"
                      : "border-slate-200 bg-slate-50/50 text-slate-600 hover:border-slate-300 dark:border-white/10 dark:bg-white/5 dark:text-slate-400"
                  }`}
                >
                  <Icon className="h-4 w-4 mb-1 text-slate-500" />
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Botão de Envio de Alta Visibilidade */}
        <Button
          type="submit"
          disabled={submitting}
          size="lg"
          className="w-full text-base font-bold shadow-lg shadow-amber-500/20 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 h-13"
        >
          {submitting ? (
            <div className="flex items-center gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              Gravando Ronda...
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5" />
              Confirmar Ronda Noturna
            </div>
          )}
        </Button>
      </form>

      {/* ── Histórico Recente de Rondas ── */}
      <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#151d2e]">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
          Últimas Inspeções Registradas
        </h3>

        {rondas.length === 0 ? (
          <p className="text-xs text-slate-400 italic">Nenhuma ronda gravada neste ciclo.</p>
        ) : (
          <div className="space-y-2.5">
            {rondas.slice(0, 5).map((r) => {
              const o2Critico = r.oxigenio_dissolvido_mg_l < 2.5;
              const o2Alerta = r.oxigenio_dissolvido_mg_l >= 2.5 && r.oxigenio_dissolvido_mg_l < 4.0;

              return (
                <div
                  key={r.id}
                  className="flex items-center justify-between rounded-xl bg-slate-50 p-3 text-xs dark:bg-white/5"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-extrabold text-slate-900 dark:text-white text-sm">
                        {r.oxigenio_dissolvido_mg_l.toFixed(1)} mg/L
                      </span>
                      <span className="text-slate-400">• {r.temperatura_agua_c.toFixed(1)}°C</span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-0.5">{fmtDateTime(r.data_hora_ronda)}</p>
                  </div>

                  <div className="text-right">
                    <Badge variant={o2Critico ? "destructive" : o2Alerta ? "warning" : "success"}>
                      {o2Critico ? "Emergência" : o2Alerta ? "Alerta" : "Normal"}
                    </Badge>
                    <span className="text-[11px] text-slate-400 block mt-0.5">
                      {r.aeradores_ligados}/{r.aeradores_instalados} aeradores
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
