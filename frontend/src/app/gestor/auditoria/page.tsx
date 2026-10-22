"use client";

import { useEffect, useState } from "react";
import {
  ShieldCheck,
  Loader2,
  Eye,
  FileText,
} from "lucide-react";
import { auditoriaApi } from "@/lib/api";
import { mensagemErro } from "@/lib/utils";
import type { LogAuditoria } from "@/lib/types";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/toast";

export default function AuditoriaPage() {
  const [logs, setLogs] = useState<LogAuditoria[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [entidadeFiltro, setEntidadeFiltro] = useState<string>("");
  const [acaoFiltro, setAcaoFiltro] = useState<string>("");
  const [selectedLog, setSelectedLog] = useState<LogAuditoria | null>(null);

  const carregarLogs = async () => {
    try {
      const data = await auditoriaApi.listar({
        entidade: entidadeFiltro || undefined,
        acao: acaoFiltro || undefined,
        limite: 100,
      });
      setLogs(data.items);
      setTotal(data.total);
    } catch (err) {
      toast.error("Erro ao carregar auditoria", mensagemErro(err, "Tente novamente"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Os setState do carregamento só ocorrem após o await (não são síncronos no efeito)
    (async () => {
      await carregarLogs();
    })();
  }, [entidadeFiltro, acaoFiltro]);

  const getActionBadge = (acao: string) => {
    switch (acao) {
      case "CRIAR":
      case "CRIAR_CICLO":
      case "CRIAR_CUSTO":
        return <Badge variant="success" className="bg-emerald-600 text-white font-mono text-[10px]">{acao}</Badge>;
      case "ATUALIZAR":
      case "EDITAR":
        return <Badge variant="secondary" className="bg-blue-600 text-white font-mono text-[10px]">{acao}</Badge>;
      case "ENCERRAR_CICLO":
        return <Badge variant="destructive" className="bg-purple-600 text-white font-mono text-[10px]">{acao}</Badge>;
      case "EXCLUIR":
        return <Badge variant="destructive" className="bg-red-600 text-white font-mono text-[10px]">{acao}</Badge>;
      default:
        return <Badge variant="outline" className="font-mono text-[10px]">{acao}</Badge>;
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
            <ShieldCheck className="w-7 h-7 text-ocean-600" />
            Trilha de Auditoria (RF-027)
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Registro imutável de eventos críticos com rastreabilidade completa e diff de dados antes/depois
          </p>
          {!loading && (
            <p className="text-xs text-slate-400 mt-1">
              Exibindo {logs.length} de {total} eventos
            </p>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={carregarLogs}
          disabled={loading}
          className="border-slate-300 text-slate-700"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : null}
          Atualizar Trilha
        </Button>
      </div>

      {/* Barra de Filtros */}
      <div className="flex flex-wrap items-center gap-3 bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm">
        <div className="flex-1 min-w-[200px]">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-1">
            Entidade
          </span>
          <select
            value={entidadeFiltro}
            onChange={(e) => setEntidadeFiltro(e.target.value)}
            className="w-full text-xs h-9 px-3 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-ocean-500"
          >
            <option value="">Todas as Entidades</option>
            <option value="CicloProdutivo">CicloProdutivo</option>
            <option value="CustoOperacional">CustoOperacional</option>
            <option value="TabelaAlimentar">TabelaAlimentar</option>
            <option value="Biometria">Biometria</option>
            <option value="Usuario">Usuario</option>
          </select>
        </div>

        <div className="flex-1 min-w-[200px]">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-1">
            Tipo de Ação
          </span>
          <select
            value={acaoFiltro}
            onChange={(e) => setAcaoFiltro(e.target.value)}
            className="w-full text-xs h-9 px-3 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-ocean-500"
          >
            <option value="">Todas as Ações</option>
            <option value="CRIAR_CICLO">CRIAR_CICLO</option>
            <option value="ENCERRAR_CICLO">ENCERRAR_CICLO</option>
            <option value="CRIAR_CUSTO">CRIAR_CUSTO</option>
            <option value="CRIAR">CRIAR</option>
            <option value="ATUALIZAR">ATUALIZAR</option>
            <option value="EXCLUIR">EXCLUIR</option>
          </select>
        </div>

        {(entidadeFiltro || acaoFiltro) && (
          <div className="pt-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setEntidadeFiltro("");
                setAcaoFiltro("");
              }}
              className="text-xs text-slate-500 hover:text-slate-800"
            >
              Limpar Filtros
            </Button>
          </div>
        )}
      </div>

      {/* Tabela de Logs */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-24 bg-white rounded-2xl border border-slate-200">
          <Loader2 className="w-8 h-8 text-ocean-600 animate-spin mb-2" />
          <p className="text-xs text-slate-400">Consultando trilha de auditoria...</p>
        </div>
      ) : logs.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center">
          <FileText className="w-12 h-12 text-slate-400 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-800">Nenhum evento registrado</h3>
          <p className="text-xs text-slate-500 mt-1">
            Os registros de auditoria surgirão automaticamente conforme ciclos forem criados, encerrados ou despesas forem lançadas.
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider font-semibold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Data / Hora</th>
                  <th className="py-3 px-4">Usuário</th>
                  <th className="py-3 px-4">Ação</th>
                  <th className="py-3 px-4">Entidade</th>
                  <th className="py-3 px-4">ID do Registro</th>
                  <th className="py-3 px-4 text-center">Diff / Dados</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4 text-slate-600 whitespace-nowrap">
                      {new Date(log.created_at).toLocaleString("pt-BR", {
                        day: "2-digit",
                        month: "2-digit",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-900">
                      {log.usuario_nome || "Sistema"}
                    </td>
                    <td className="py-3 px-4">{getActionBadge(log.acao)}</td>
                    <td className="py-3 px-4 text-slate-700 font-mono text-[11px] font-semibold">
                      {log.entidade}
                    </td>
                    <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                      {log.registro_id.slice(0, 8)}...
                    </td>
                    <td className="py-3 px-4 text-center">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedLog(log)}
                        className="h-7 text-xs text-ocean-600 hover:text-ocean-700 hover:bg-ocean-50 gap-1"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Ver Diff
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal de Detalhe e Diff Antes / Depois (Critério 10) */}
      <Dialog
        open={Boolean(selectedLog)}
        onClose={() => setSelectedLog(null)}
        title="Detalhes do Log de Auditoria"
        description={`Registro ${selectedLog?.id.slice(0, 8)} — ${selectedLog?.acao} em ${selectedLog?.entidade}`}
      >
        {selectedLog && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Responsável</span>
                <span className="font-semibold text-slate-800">{selectedLog.usuario_nome || "Sistema"}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Data & Hora</span>
                <span className="font-semibold text-slate-800">
                  {new Date(selectedLog.created_at).toLocaleString("pt-BR")}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Ação Realizada</span>
                <div className="mt-0.5">{getActionBadge(selectedLog.acao)}</div>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Registro ID</span>
                <span className="font-mono text-slate-700 text-[11px] truncate block">
                  {selectedLog.registro_id}
                </span>
              </div>
            </div>

            {/* Comparação Antes vs Depois */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-xs font-bold text-red-700 uppercase tracking-wider mb-1 flex items-center gap-1">
                  <span>Estado Anterior</span>
                </div>
                <div className="p-3 rounded-xl bg-red-50/50 border border-red-200 text-red-900 font-mono text-[11px] max-h-60 overflow-y-auto">
                  {selectedLog.dados_anteriores ? (
                    <pre className="whitespace-pre-wrap">
                      {JSON.stringify(selectedLog.dados_anteriores, null, 2)}
                    </pre>
                  ) : (
                    <span className="text-slate-400 italic">Nenhum estado anterior (registro novo)</span>
                  )}
                </div>
              </div>

              <div>
                <div className="text-xs font-bold text-emerald-700 uppercase tracking-wider mb-1 flex items-center gap-1">
                  <span>Estado Novo (Atualizado)</span>
                </div>
                <div className="p-3 rounded-xl bg-emerald-50/50 border border-emerald-200 text-emerald-900 font-mono text-[11px] max-h-60 overflow-y-auto">
                  {selectedLog.dados_novos ? (
                    <pre className="whitespace-pre-wrap">
                      {JSON.stringify(selectedLog.dados_novos, null, 2)}
                    </pre>
                  ) : (
                    <span className="text-slate-400 italic">Nenhum estado novo (registro excluído)</span>
                  )}
                </div>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <Button variant="outline" onClick={() => setSelectedLog(null)} className="text-xs">
                Fechar
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
}
