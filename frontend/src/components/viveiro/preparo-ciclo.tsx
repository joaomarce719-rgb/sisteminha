"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Ban,
  CalendarClock,
  ClipboardList,
  Loader2,
  Plus,
  Save,
  Sprout,
  Trash2,
} from "lucide-react";
import { ciclosApi, custosApi, etapasPreparoApi, tabelasAlimentaresApi, viveirosApi } from "@/lib/api";
import { mensagemErro } from "@/lib/utils";
import { etapasEmAberto, nomeEtapa, ROTULO_STATUS_ETAPA } from "@/lib/etapas-preparo";
import type {
  CategoriaCusto,
  CicloProdutivo,
  CustoOperacional,
  EtapaPreparo,
  StatusEtapa,
  TabelaAlimentar,
  Viveiro,
} from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { hojeLocal } from "@/components/ui/data-lancamento";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/toast";
import { AbaInsumosCiclo } from "@/components/insumos/aba-insumos-ciclo";
import { fmtData, fmtMoney } from "@/components/insumos/lista-usos-insumo";

const CLASSE_SELECT =
  "w-full mt-1 rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-800 focus:border-sky-500 focus:outline-none h-11 disabled:opacity-60";

const MENSAGEM_ERRO_FORM =
  "flex items-center gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm mb-4";

const OPCOES_STATUS: StatusEtapa[] = ["PENDENTE", "EM_ANDAMENTO", "CONCLUIDA", "NAO_REALIZADA"];

const VARIANTE_STATUS = {
  PENDENTE: "secondary",
  EM_ANDAMENTO: "info",
  CONCLUIDA: "success",
  NAO_REALIZADA: "warning",
} as const;

// ── Leituras ─────────────────────────────────────────────

/** Etapas do preparo do ciclo; `etapas` é null enquanto carrega e quando a leitura falha (`falhou`). */
export function useEtapasPreparo(cicloId: string) {
  // Guardadas com o ciclo a que pertencem: trocar de ciclo não mostra a lista do anterior
  const [carregado, setCarregado] = useState<{ cicloId: string; lista: EtapaPreparo[] | null } | null>(null);
  const [versao, setVersao] = useState(0);

  useEffect(() => {
    if (!cicloId) return;
    let ativo = true;
    etapasPreparoApi
      .listar(cicloId)
      .then((lista) => {
        if (ativo) setCarregado({ cicloId, lista });
      })
      .catch((err) => {
        if (ativo) {
          setCarregado({ cicloId, lista: null });
          toast.error("Não foi possível carregar as etapas do preparo", mensagemErro(err, "Tente novamente"));
        }
      });
    return () => {
      ativo = false;
    };
  }, [cicloId, versao]);

  const atual = carregado && carregado.cicloId === cicloId ? carregado : null;
  return {
    etapas: atual?.lista ?? null,
    falhou: atual !== null && atual.lista === null,
    recarregar: () => setVersao((v) => v + 1),
  };
}

/** Custos de fase PREPARO do ciclo (manuais e gerados pelo uso de insumo); só o gestor lê custos. */
function useCustosPreparo(cicloId: string) {
  const [custos, setCustos] = useState<CustoOperacional[] | null>(null);
  const [versao, setVersao] = useState(0);

  useEffect(() => {
    let ativo = true;
    custosApi
      .listar(cicloId)
      .then((lista) => {
        if (ativo) setCustos(lista.filter((c) => c.fase === "PREPARO"));
      })
      .catch((err) => {
        if (ativo) {
          setCustos([]);
          toast.error("Não foi possível carregar os custos do preparo", mensagemErro(err, "Tente novamente"));
        }
      });
    return () => {
      ativo = false;
    };
  }, [cicloId, versao]);

  return { custos, recarregar: () => setVersao((v) => v + 1) };
}

function useTabelasAlimentares() {
  const [tabelas, setTabelas] = useState<TabelaAlimentar[]>([]);
  useEffect(() => {
    let ativo = true;
    tabelasAlimentaresApi
      .listar(true)
      .then((lista) => {
        if (ativo) setTabelas(lista);
      })
      .catch(() => {}); // sem a lista fica só o padrão do sistema
    return () => {
      ativo = false;
    };
  }, []);
  return tabelas;
}

// ── Checklist de etapas (gestor e campo) ─────────────────

function LinhaEtapa({
  cicloId,
  etapa,
  gestor,
  onAlterado,
}: {
  cicloId: string;
  etapa: EtapaPreparo;
  gestor: boolean;
  onAlterado: () => void;
}) {
  const [inicio, setInicio] = useState(etapa.data_inicio ?? "");
  const [fim, setFim] = useState(etapa.data_fim ?? "");
  const [observacao, setObservacao] = useState(etapa.observacao ?? "");
  const [salvando, setSalvando] = useState(false);

  const alterou =
    inicio !== (etapa.data_inicio ?? "") || fim !== (etapa.data_fim ?? "") || observacao !== (etapa.observacao ?? "");

  const atualizar = async (dados: Record<string, unknown>) => {
    setSalvando(true);
    try {
      await etapasPreparoApi.atualizar(cicloId, etapa.id, dados);
      toast.success("Etapa atualizada", nomeEtapa(etapa));
      onAlterado();
    } catch (err) {
      toast.error("Erro ao atualizar a etapa", mensagemErro(err, "Tente novamente"));
    } finally {
      setSalvando(false);
    }
  };

  const excluir = async () => {
    if (
      !window.confirm(
        `Excluir a etapa "${nomeEtapa(etapa)}"? Os usos de insumo ligados a ela continuam no ciclo, sem etapa.`
      )
    )
      return;
    setSalvando(true);
    try {
      await etapasPreparoApi.excluir(cicloId, etapa.id);
      toast.success("Etapa excluída", nomeEtapa(etapa));
      onAlterado();
    } catch (err) {
      toast.error("Erro ao excluir a etapa", mensagemErro(err, "Tente novamente"));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <li className="py-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <p className="font-semibold text-slate-800 text-sm">{nomeEtapa(etapa)}</p>
        <Badge variant={VARIANTE_STATUS[etapa.status]}>{ROTULO_STATUS_ETAPA[etapa.status]}</Badge>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <Label htmlFor={`etapa-status-${etapa.id}`}>Situação</Label>
          <select
            id={`etapa-status-${etapa.id}`}
            value={etapa.status}
            disabled={salvando}
            onChange={(e) => atualizar({ status: e.target.value })}
            className={CLASSE_SELECT}
          >
            {OPCOES_STATUS.map((s) => (
              <option key={s} value={s}>
                {ROTULO_STATUS_ETAPA[s]}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor={`etapa-inicio-${etapa.id}`}>Início</Label>
          <Input
            id={`etapa-inicio-${etapa.id}`}
            type="date"
            value={inicio}
            onChange={(e) => setInicio(e.target.value)}
            className="mt-1"
          />
        </div>
        <div>
          <Label htmlFor={`etapa-fim-${etapa.id}`}>Fim</Label>
          <Input
            id={`etapa-fim-${etapa.id}`}
            type="date"
            min={inicio || undefined}
            value={fim}
            onChange={(e) => setFim(e.target.value)}
            className="mt-1"
          />
        </div>
      </div>

      <div className="flex items-end gap-2">
        <div className="flex-1 min-w-0">
          <Label htmlFor={`etapa-obs-${etapa.id}`}>Observação</Label>
          <Input
            id={`etapa-obs-${etapa.id}`}
            maxLength={255}
            value={observacao}
            onChange={(e) => setObservacao(e.target.value)}
            className="mt-1"
          />
        </div>
        {alterou && (
          <Button
            type="button"
            size="sm"
            disabled={salvando}
            className="h-11"
            onClick={() =>
              atualizar({
                data_inicio: inicio || null,
                data_fim: fim || null,
                observacao: observacao.trim() || null,
              })
            }
          >
            {salvando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Salvar
          </Button>
        )}
        {gestor && (
          <button
            type="button"
            onClick={excluir}
            disabled={salvando}
            className="h-11 p-2.5 rounded-xl text-red-500 hover:bg-red-50 disabled:opacity-50"
            aria-label={`Excluir etapa ${nomeEtapa(etapa)}`}
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>
    </li>
  );
}

function NovaEtapa({ cicloId, onCriada }: { cicloId: string; onCriada: () => void }) {
  const [aberto, setAberto] = useState(false);
  const [descricao, setDescricao] = useState("");
  const [salvando, setSalvando] = useState(false);

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    setSalvando(true);
    try {
      // A etapa "Outra" não tem nome próprio: a descrição vai na observação
      await etapasPreparoApi.criar(cicloId, { tipo: "OUTRA", observacao: descricao.trim() });
      toast.success("Etapa adicionada", descricao.trim());
      setDescricao("");
      setAberto(false);
      onCriada();
    } catch (err) {
      toast.error("Erro ao adicionar a etapa", mensagemErro(err, "Tente novamente"));
    } finally {
      setSalvando(false);
    }
  };

  if (!aberto) {
    return (
      <Button type="button" variant="outline" size="sm" onClick={() => setAberto(true)}>
        <Plus className="w-4 h-4" />
        Adicionar etapa
      </Button>
    );
  }

  return (
    <form onSubmit={salvar} className="flex items-end gap-2">
      <div className="flex-1 min-w-0">
        <Label htmlFor="nova-etapa">Descrição da nova etapa *</Label>
        <Input
          id="nova-etapa"
          required
          maxLength={255}
          value={descricao}
          onChange={(e) => setDescricao(e.target.value)}
          placeholder="Ex: Reparo da comporta"
          className="mt-1"
        />
      </div>
      <Button type="submit" size="sm" disabled={salvando || !descricao.trim()} className="h-11">
        {salvando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
        Adicionar
      </Button>
      <Button type="button" variant="outline" size="sm" onClick={() => setAberto(false)} className="h-11">
        Cancelar
      </Button>
    </form>
  );
}

/**
 * Checklist das etapas do preparo. O gestor também adiciona e exclui etapas; o campo só atualiza situação,
 * datas e observação (a API aplica a mesma regra).
 */
export function ChecklistEtapas({
  cicloId,
  etapas,
  falhou,
  gestor = false,
  onAlterado,
}: {
  cicloId: string;
  etapas: EtapaPreparo[] | null;
  falhou: boolean;
  gestor?: boolean;
  onAlterado: () => void;
}) {
  if (falhou) return <p className="py-6 text-center text-xs text-red-500">Não foi possível carregar as etapas.</p>;
  if (etapas === null) {
    return (
      <div className="flex justify-center py-6">
        <Loader2 className="w-5 h-5 text-sky-500 animate-spin" />
      </div>
    );
  }

  const resolvidas = etapas.length - etapasEmAberto(etapas);
  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500">
        {resolvidas} de {etapas.length} {etapas.length === 1 ? "etapa resolvida" : "etapas resolvidas"} (feitas ou não
        realizadas).
      </p>
      {etapas.length === 0 ? (
        <p className="py-4 text-center text-xs text-slate-400">Nenhuma etapa neste preparo.</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {etapas.map((etapa) => (
            <LinhaEtapa key={etapa.id} cicloId={cicloId} etapa={etapa} gestor={gestor} onAlterado={onAlterado} />
          ))}
        </ul>
      )}
      {gestor && <NovaEtapa cicloId={cicloId} onCriada={onAlterado} />}
    </div>
  );
}

// ── Planejar, reagendar e povoar ─────────────────────────

function SeletorTabela({
  id,
  tabelas,
  value,
  onChange,
}: {
  id: string;
  tabelas: TabelaAlimentar[];
  value: string;
  onChange: (valor: string) => void;
}) {
  return (
    <div>
      <Label htmlFor={id}>Tabela de Arraçoamento</Label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className={CLASSE_SELECT}>
        <option value="">Clifford (1992) — Padrão do Sistema</option>
        {tabelas.map((t) => (
          <option key={t.id} value={t.id}>
            {t.nome} (v{t.versao}) {t.is_padrao ? "★ [Padrão]" : ""}
          </option>
        ))}
      </select>
      <p className="text-[11px] text-slate-400 mt-1">
        Define os pontos de calibração utilizados no cálculo algorítmico da ração diária
      </p>
    </div>
  );
}

/** Planeja o ciclo do viveiro (montado só enquanto aberto): data prevista e tabela alimentar; as pós-larvas entram ao povoar. */
export function PlanejarCicloDialog({
  onClose,
  onCreated,
  viveiroId,
}: {
  onClose: () => void;
  onCreated: () => void;
  viveiroId: string;
}) {
  const tabelas = useTabelasAlimentares();
  const [data, setData] = useState(hojeLocal());
  // null = o usuário ainda não escolheu: vale a tabela padrão
  const [tabelaEscolhida, setTabelaEscolhida] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const tabelaId = tabelaEscolhida ?? tabelas.find((t) => t.is_padrao)?.id ?? "";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await ciclosApi.criar({
        viveiro_id: viveiroId,
        data_povoamento: data,
        tabela_alimentar_id: tabelaId || null,
      });
      toast.success("Ciclo planejado!", "Marque as etapas do preparo antes de povoar o viveiro.");
      onCreated();
      onClose();
    } catch (err) {
      setError(mensagemErro(err, "Erro ao planejar ciclo"));
      toast.error("Falha ao planejar ciclo", mensagemErro(err, "Verifique os dados"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open
      onClose={onClose}
      title="Planejar Ciclo Produtivo"
      description="O viveiro passa pelo preparo antes do povoamento"
    >
      {error && (
        <div className={MENSAGEM_ERRO_FORM}>
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Label htmlFor="plano_data_povoamento">Data Prevista do Povoamento *</Label>
          <Input
            id="plano_data_povoamento"
            required
            type="date"
            value={data}
            onChange={(e) => setData(e.target.value)}
            className="mt-1"
          />
          <p className="text-[11px] text-slate-400 mt-1">É só uma previsão: a data real é informada ao povoar.</p>
        </div>

        <SeletorTabela id="plano_tabela" tabelas={tabelas} value={tabelaId} onChange={setTabelaEscolhida} />

        <div className="pt-2 flex gap-3">
          <Button type="button" variant="outline" onClick={onClose} className="flex-1">
            Cancelar
          </Button>
          <Button type="submit" disabled={loading} className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white">
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <ClipboardList className="w-4 h-4 mr-2" />}
            Planejar Ciclo
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

function ReagendarDialog({
  ciclo,
  onClose,
  onDone,
}: {
  ciclo: CicloProdutivo;
  onClose: () => void;
  onDone: () => void;
}) {
  const tabelas = useTabelasAlimentares();
  const [viveiros, setViveiros] = useState<Viveiro[] | null>(null);
  const [data, setData] = useState(ciclo.data_povoamento);
  const [viveiroId, setViveiroId] = useState(ciclo.viveiro_id);
  const [tabelaEscolhida, setTabelaEscolhida] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const tabelaId = tabelaEscolhida ?? ciclo.tabela_alimentar_id ?? "";

  useEffect(() => {
    let ativo = true;
    viveirosApi
      .listar()
      .then((lista) => {
        if (ativo) setViveiros(lista);
      })
      .catch(() => {
        if (ativo) setViveiros([]); // fica só o viveiro atual
      });
    return () => {
      ativo = false;
    };
  }, []);

  const opcoes = (viveiros ?? []).filter((v) => v.status_ativo || v.id === ciclo.viveiro_id);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await ciclosApi.reagendar(ciclo.id, {
        data_povoamento: data,
        viveiro_id: viveiroId,
        tabela_alimentar_id: tabelaId || null,
      });
      const novo = opcoes.find((v) => v.id === viveiroId);
      toast.success(
        "Ciclo reagendado",
        viveiroId !== ciclo.viveiro_id && novo
          ? `O ciclo planejado foi para o viveiro ${novo.identificacao}.`
          : `Povoamento previsto para ${fmtData(data)}.`
      );
      onDone();
      onClose();
    } catch (err) {
      setError(mensagemErro(err, "Erro ao reagendar ciclo"));
      toast.error("Falha ao reagendar ciclo", mensagemErro(err, "Verifique os dados"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open
      onClose={onClose}
      title="Reagendar Ciclo"
      description="Etapas, usos de insumo e custos já lançados continuam no ciclo"
    >
      {error && (
        <div className={MENSAGEM_ERRO_FORM}>
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Label htmlFor="reagendar_data">Data Prevista do Povoamento *</Label>
          <Input
            id="reagendar_data"
            required
            type="date"
            value={data}
            onChange={(e) => setData(e.target.value)}
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor="reagendar_viveiro">Viveiro *</Label>
          <select
            id="reagendar_viveiro"
            required
            value={viveiroId}
            disabled={viveiros === null}
            onChange={(e) => setViveiroId(e.target.value)}
            className={CLASSE_SELECT}
          >
            {viveiros === null && <option value={ciclo.viveiro_id}>Carregando viveiros...</option>}
            {opcoes.map((v) => (
              <option key={v.id} value={v.id}>
                {v.identificacao}
              </option>
            ))}
          </select>
          <p className="text-[11px] text-slate-400 mt-1">O viveiro de destino não pode ter outro ciclo aberto.</p>
        </div>

        <SeletorTabela id="reagendar_tabela" tabelas={tabelas} value={tabelaId} onChange={setTabelaEscolhida} />

        <div className="pt-2 flex gap-3">
          <Button type="button" variant="outline" onClick={onClose} className="flex-1">
            Cancelar
          </Button>
          <Button type="submit" disabled={loading} className="flex-1">
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CalendarClock className="w-4 h-4 mr-2" />}
            Reagendar
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

function PovoarDialog({
  ciclo,
  onClose,
  onDone,
}: {
  ciclo: CicloProdutivo;
  onClose: () => void;
  onDone: () => void;
}) {
  const [form, setForm] = useState({
    data_povoamento: hojeLocal(),
    quantidade_pos_larvas: "",
    custo_aquisicao_pl: "",
    peso_medio_pl_g: "",
    laboratorio_origem: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const quantidade = parseInt(form.quantidade_pos_larvas, 10);
      await ciclosApi.povoar(ciclo.id, {
        data_povoamento: form.data_povoamento,
        quantidade_pos_larvas: quantidade,
        custo_aquisicao_pl: parseFloat(form.custo_aquisicao_pl),
        peso_medio_pl_g: form.peso_medio_pl_g ? parseFloat(form.peso_medio_pl_g) : null,
        laboratorio_origem: form.laboratorio_origem.trim() || null,
      });
      toast.success("Ciclo produtivo iniciado!", `${quantidade.toLocaleString("pt-BR")} pós-larvas povoadas.`);
      onDone();
      onClose();
    } catch (err) {
      // inclui o 409 de etapas em aberto, com a contagem vinda da API
      setError(mensagemErro(err, "Erro ao povoar o ciclo"));
      toast.error("Falha ao povoar o ciclo", mensagemErro(err, "Verifique os dados"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open
      onClose={onClose}
      title="Povoar Viveiro"
      description="Povoamento de pós-larvas: o ciclo passa a ativo e o custo das pós-larvas é lançado"
      className="max-h-[90vh] overflow-y-auto"
    >
      {error && (
        <div className={MENSAGEM_ERRO_FORM}>
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Label htmlFor="data_povoamento">Data Real do Povoamento *</Label>
          <Input
            id="data_povoamento"
            required
            type="date"
            max={hojeLocal()}
            value={form.data_povoamento}
            onChange={(e) => setForm({ ...form, data_povoamento: e.target.value })}
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor="quantidade_pos_larvas">Quantidade de Pós-Larvas (PLs) *</Label>
          <Input
            id="quantidade_pos_larvas"
            required
            type="number"
            min="1"
            max="2147483647"
            step="1"
            inputMode="numeric"
            value={form.quantidade_pos_larvas}
            onChange={(e) => setForm({ ...form, quantidade_pos_larvas: e.target.value })}
            placeholder="Ex: 250000"
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor="custo_aquisicao_pl">Custo Total de Aquisição das PLs (R$) *</Label>
          <Input
            id="custo_aquisicao_pl"
            required
            type="number"
            min="0"
            max="9999999999.99"
            step="0.01"
            inputMode="decimal"
            value={form.custo_aquisicao_pl}
            onChange={(e) => setForm({ ...form, custo_aquisicao_pl: e.target.value })}
            placeholder="Ex: 3500.00"
            className="mt-1"
          />
        </div>

        <div>
          <Label htmlFor="peso_medio_pl_g">Peso Médio da PL no Povoamento (g)</Label>
          <Input
            id="peso_medio_pl_g"
            type="number"
            min="0"
            max="5"
            step="0.001"
            inputMode="decimal"
            value={form.peso_medio_pl_g}
            onChange={(e) => setForm({ ...form, peso_medio_pl_g: e.target.value })}
            placeholder="Ex: 0.01"
            className="mt-1"
          />
          <p className="text-xs text-slate-500 mt-1">
            Base da biomassa inicial no cálculo do FCA. Uma PL recém-saída do laboratório pesa cerca de 0.01 g;
            juvenis de berçário pesam mais. Se ficar vazio, a biomassa inicial é considerada desprezível.
          </p>
        </div>

        <div>
          <Label htmlFor="laboratorio_origem">Laboratório de Origem / Fornecedor</Label>
          <Input
            id="laboratorio_origem"
            maxLength={120}
            value={form.laboratorio_origem}
            onChange={(e) => setForm({ ...form, laboratorio_origem: e.target.value })}
            placeholder="Ex: Aquagenetics, Larvicultura Norte"
            className="mt-1"
          />
        </div>

        <div className="pt-2 flex gap-3">
          <Button type="button" variant="outline" onClick={onClose} className="flex-1">
            Cancelar
          </Button>
          <Button type="submit" disabled={loading} className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white">
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Activity className="w-4 h-4 mr-2" />}
            Povoar
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

// ── Custos do preparo ────────────────────────────────────

// Pós-larvas e ração têm lançamento próprio (povoamento e manejo): ficam de fora do custo manual do preparo
const CATEGORIAS_PREPARO: Partial<Record<CategoriaCusto, string>> = {
  MAO_DE_OBRA: "Mão de obra",
  ENERGIA_ELETRICA: "Energia elétrica",
  MANUTENCAO: "Manutenção",
  PROBIOTICOS_QUIMICOS: "Probióticos e químicos",
  OUTROS: "Outros",
};

function CustoPreparoDialog({
  cicloId,
  onClose,
  onSalvo,
}: {
  cicloId: string;
  onClose: () => void;
  onSalvo: () => void;
}) {
  const [form, setForm] = useState({
    data_lancamento: hojeLocal(),
    categoria: "MAO_DE_OBRA",
    descricao: "",
    valor_rs: "",
  });
  const [salvando, setSalvando] = useState(false);

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    setSalvando(true);
    try {
      const valor = parseFloat(form.valor_rs);
      await custosApi.criar(cicloId, {
        data_lancamento: form.data_lancamento,
        categoria: form.categoria,
        descricao: form.descricao.trim(),
        valor_rs: valor,
        fase: "PREPARO",
      });
      toast.success("Custo lançado", `${form.descricao.trim()} — ${fmtMoney(valor)}`);
      onSalvo();
      onClose();
    } catch (err) {
      toast.error("Erro ao lançar o custo", mensagemErro(err, "Tente novamente"));
    } finally {
      setSalvando(false);
    }
  };

  return (
    <Dialog open onClose={onClose} title="Lançar custo do preparo" description="Despesa avulsa da fase de preparo do viveiro">
      <form onSubmit={salvar} className="space-y-4">
        <div>
          <Label htmlFor="custo-data">Data *</Label>
          <Input
            id="custo-data"
            required
            type="date"
            value={form.data_lancamento}
            onChange={(e) => setForm({ ...form, data_lancamento: e.target.value })}
            className="mt-1"
          />
        </div>
        <div>
          <Label htmlFor="custo-categoria">Categoria *</Label>
          <select
            id="custo-categoria"
            value={form.categoria}
            onChange={(e) => setForm({ ...form, categoria: e.target.value })}
            className={CLASSE_SELECT}
          >
            {Object.entries(CATEGORIAS_PREPARO).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="custo-descricao">Descrição *</Label>
          <Input
            id="custo-descricao"
            required
            minLength={3}
            maxLength={255}
            value={form.descricao}
            onChange={(e) => setForm({ ...form, descricao: e.target.value })}
            placeholder="Ex: Diária da equipe de secagem"
            className="mt-1"
          />
        </div>
        <div>
          <Label htmlFor="custo-valor">Valor (R$) *</Label>
          <Input
            id="custo-valor"
            required
            type="number"
            min="0.01"
            max="9999999999.99"
            step="0.01"
            inputMode="decimal"
            value={form.valor_rs}
            onChange={(e) => setForm({ ...form, valor_rs: e.target.value })}
            placeholder="Ex: 450.00"
            className="mt-1"
          />
        </div>
        <div className="pt-2 flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button type="submit" disabled={salvando}>
            {salvando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            Lançar custo
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

function CustosPreparo({
  cicloId,
  custos,
  onAlterado,
}: {
  cicloId: string;
  custos: CustoOperacional[] | null;
  onAlterado: () => void;
}) {
  const [aberto, setAberto] = useState(false);
  const total = (custos ?? []).reduce((soma, c) => soma + c.valor_rs, 0);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="font-bold text-slate-900 text-base">Custos do preparo</h3>
          <p className="text-xs text-slate-500">Inclui o custo dos insumos usados no preparo.</p>
        </div>
        <Button size="sm" onClick={() => setAberto(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Lançar custo
        </Button>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-sm">
        {custos === null ? (
          <div className="flex justify-center py-6">
            <Loader2 className="w-5 h-5 text-sky-500 animate-spin" />
          </div>
        ) : custos.length === 0 ? (
          <p className="py-6 text-center text-xs text-slate-400">Nenhum custo lançado no preparo.</p>
        ) : (
          <>
            <ul className="divide-y divide-slate-100">
              {custos.map((c) => (
                <li key={c.id} className="py-2.5 flex items-start justify-between gap-3 text-xs">
                  <span className="min-w-0 text-slate-700">
                    {fmtData(c.data_lancamento)} · {c.descricao}
                  </span>
                  <strong className="shrink-0 tabular-nums text-slate-800">{fmtMoney(c.valor_rs)}</strong>
                </li>
              ))}
            </ul>
            <p className="pt-3 mt-1 border-t border-slate-100 text-right text-xs text-slate-500">
              Total do preparo: <strong className="text-slate-900 tabular-nums">{fmtMoney(total)}</strong>
            </p>
          </>
        )}
      </div>

      {aberto && <CustoPreparoDialog cicloId={cicloId} onClose={() => setAberto(false)} onSalvo={onAlterado} />}
    </div>
  );
}

// ── Painel do gestor ─────────────────────────────────────

/**
 * Painel "Preparo" do ciclo PLANEJADO (só gestor): etapas, insumos e custos do preparo, e as ações
 * Reagendar, Povoar e Cancelar planejamento. `onAlterado` roda quando o próprio ciclo muda (reagendar,
 * povoar, cancelar); lançamentos do preparo só atualizam este painel.
 */
export function PreparoCiclo({ ciclo, onAlterado }: { ciclo: CicloProdutivo; onAlterado: () => void }) {
  const { etapas, falhou, recarregar: recarregarEtapas } = useEtapasPreparo(ciclo.id);
  const { custos, recarregar: recarregarCustos } = useCustosPreparo(ciclo.id);
  const [dialogo, setDialogo] = useState<"reagendar" | "povoar" | null>(null);
  const [cancelando, setCancelando] = useState(false);

  const abertas = etapas ? etapasEmAberto(etapas) : 0;
  const bloqueioPovoar =
    etapas === null
      ? falhou
        ? "Não foi possível ler as etapas do preparo, então o povoamento está bloqueado."
        : "Carregando as etapas do preparo..."
      : abertas > 0
        ? `Há ${abertas === 1 ? "1 etapa pendente ou em andamento" : `${abertas} etapas pendentes ou em andamento`}: marque cada uma como feita ou não realizada para poder povoar.`
        : null;

  const cancelar = async () => {
    if (
      !window.confirm(
        "Cancelar o planejamento deste ciclo? O viveiro volta a ficar livre e o ciclo cancelado não pode ser retomado."
      )
    )
      return;
    setCancelando(true);
    try {
      await ciclosApi.cancelar(ciclo.id);
      toast.success("Planejamento cancelado", "O viveiro está livre para um novo ciclo.");
      onAlterado();
    } catch (err) {
      toast.error("Erro ao cancelar o planejamento", mensagemErro(err, "Tente novamente"));
    } finally {
      setCancelando(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-white border border-slate-200/80 p-5 shadow-sm space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
                <Sprout className="w-5 h-5 text-emerald-600" />
                Preparo do viveiro
              </h2>
              <Badge variant="info">Planejado</Badge>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Povoamento previsto para <strong className="text-slate-800">{fmtData(ciclo.data_povoamento)}</strong>.
              Marque cada etapa como feita ou não realizada para liberar o povoamento.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => setDialogo("reagendar")}>
              <CalendarClock className="w-4 h-4 mr-2 text-ocean-600" />
              Reagendar
            </Button>
            <Button
              variant="emerald"
              size="sm"
              disabled={bloqueioPovoar !== null}
              aria-describedby={bloqueioPovoar ? "povoar-bloqueio" : undefined}
              onClick={() => setDialogo("povoar")}
            >
              <Activity className="w-4 h-4 mr-2" />
              Povoar
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={cancelando}
              onClick={cancelar}
              className="border-red-300 text-red-700 hover:bg-red-50"
            >
              {cancelando ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Ban className="w-4 h-4 mr-2" />}
              Cancelar planejamento
            </Button>
          </div>
        </div>

        {bloqueioPovoar && (
          <div
            id="povoar-bloqueio"
            className="flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900"
          >
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{bloqueioPovoar}</span>
          </div>
        )}
      </div>

      <div className="space-y-4">
        <h3 className="font-bold text-slate-900 text-base">Etapas do preparo</h3>
        <div className="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-sm">
          <ChecklistEtapas cicloId={ciclo.id} etapas={etapas} falhou={falhou} gestor onAlterado={recarregarEtapas} />
        </div>
      </div>

      <AbaInsumosCiclo cicloId={ciclo.id} fase="PREPARO" etapas={etapas ?? undefined} onAlterado={recarregarCustos} />

      <CustosPreparo cicloId={ciclo.id} custos={custos} onAlterado={recarregarCustos} />

      {dialogo === "reagendar" && (
        <ReagendarDialog ciclo={ciclo} onClose={() => setDialogo(null)} onDone={onAlterado} />
      )}
      {dialogo === "povoar" && <PovoarDialog ciclo={ciclo} onClose={() => setDialogo(null)} onDone={onAlterado} />}
    </div>
  );
}
