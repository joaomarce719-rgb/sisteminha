"""SAD Carcinicultura — Rotas de Ciclos Produtivos (RF-02, RF-09)."""

from dataclasses import asdict
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.escopo import (
    org_do_usuario,
    verificar_ciclo_da_organizacao,
    viveiro_da_organizacao,
)
from src.services.audit import registrar_auditoria, snapshot
from src.models.biometria import Biometria
from src.models.ciclo_produtivo import CicloProdutivo
from src.models.custo_operacional import CustoOperacional
from src.models.enums import CategoriaCusto, RoleUsuario, StatusCiclo
from src.models.etapa_preparo import EtapaPreparo
from src.models.insumo import ConsumoInsumo
from src.models.manejo_alimentar import ManejoAlimentar
from src.models.tabela_alimentar import TabelaAlimentar
from src.models.venda_ciclo import VendaCiclo
from src.models.viveiro import Viveiro
from src.routers.vendas import colunas_da_venda, sincronizar_totais_do_ciclo
from src.schemas.ciclo import (
    CicloEncerrar,
    CicloPlanejar,
    CicloPovoar,
    CicloReagendar,
    CicloResponse,
    MetricasAtuaisResponse,
)
from src.schemas.financeiro import FinanceiroCicloResponse
from src.schemas.etapa_preparo import ETAPAS_SUGERIDAS, STATUS_ETAPA_EM_ABERTO
from src.schemas.venda import VendaCreate
from src.services.auth_service import get_current_user, has_role
from src.services import decision_engine as de
from src.services.alimentacao import pontos_alimentares
from src.services.sobrevivencia import confrontar_vivos, ordenar, peso_na_data
from src.services import populacao as pv
from src.services.historico import resumo_do_ciclo, situacao_atual
from src.services.insumos import reprocessar_insumo
from src.services.regras_ciclo import ciclo_aberto_do_viveiro, exigir_povoamento
from src.services.regras_ciclo import obter_ciclo as buscar_ciclo  # a rota GET se chama obter_ciclo
from src.services.regras_data import hoje_da_fazenda

router = APIRouter(prefix="/api/v1/ciclos", tags=["Ciclos Produtivos"])


def _validar_tabela_alimentar(db: Session, tabela_id: UUID | None, organizacao_id: UUID) -> None:
    if tabela_id is None:
        return
    tabela = db.get(TabelaAlimentar, tabela_id)
    if not tabela or not tabela.ativo or tabela.organizacao_id not in (None, organizacao_id):
        raise HTTPException(status_code=404, detail="Tabela alimentar não encontrada ou inativa.")


def _viveiro_livre(db: Session, viveiro_id: UUID, user, exceto_id: UUID | None = None) -> Viveiro:
    """Viveiro ativo da organização e sem outro ciclo aberto (PLANEJADO, ATIVO ou PAUSADO)."""
    viveiro = viveiro_da_organizacao(db, viveiro_id, user)
    if not viveiro.status_ativo:
        raise HTTPException(status_code=400, detail="Viveiro inativo.")
    if ciclo_aberto_do_viveiro(db, viveiro_id, exceto_id=exceto_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este viveiro já possui um ciclo PLANEJADO, ATIVO ou PAUSADO.",
        )
    return viveiro


def _ciclo_planejado(db: Session, ciclo_id: UUID, acao: str) -> CicloProdutivo:
    ciclo = buscar_ciclo(db, ciclo_id)
    if ciclo.status != StatusCiclo.PLANEJADO:
        raise HTTPException(status_code=400, detail=f"Somente ciclos PLANEJADOS podem ser {acao}.")
    return ciclo


@router.post("", response_model=CicloResponse, status_code=201)
@router.post("/", response_model=CicloResponse, status_code=201)
def planejar_ciclo(
    payload: CicloPlanejar,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Planeja um ciclo: nasce PLANEJADO com as etapas sugeridas do preparo (o povoamento vem depois)."""
    viveiro = _viveiro_livre(db, payload.viveiro_id, _user)
    _validar_tabela_alimentar(db, payload.tabela_alimentar_id, viveiro.organizacao_id)

    ciclo = CicloProdutivo(**payload.model_dump(), status=StatusCiclo.PLANEJADO)
    ciclo.etapas_preparo = [
        EtapaPreparo(tipo=tipo, status="PENDENTE", ordem=ordem)
        for ordem, tipo in enumerate(ETAPAS_SUGERIDAS, start=1)
    ]
    db.add(ciclo)
    db.flush()

    registrar_auditoria(
        db=db,
        acao="PLANEJAR_CICLO",
        entidade="CicloProdutivo",
        registro_id=ciclo.id,
        usuario=_user,
        dados_novos=snapshot(ciclo),
    )
    db.refresh(ciclo)
    return ciclo


@router.post("/{ciclo_id}/povoar", dependencies=[Depends(verificar_ciclo_da_organizacao)], response_model=CicloResponse)
def povoar_ciclo(
    ciclo_id: UUID,
    payload: CicloPovoar,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Povoa o ciclo planejado: grava as pós-larvas, lança o custo delas e ativa o ciclo."""
    ciclo = _ciclo_planejado(db, ciclo_id, "povoados")
    if payload.data_povoamento > hoje_da_fazenda():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A data do povoamento não pode estar no futuro: povoe o ciclo no dia em que as pós-larvas entrarem.",
        )
    em_aberto = sum(1 for e in ciclo.etapas_preparo if e.status in STATUS_ETAPA_EM_ABERTO)
    if em_aberto:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Há {em_aberto} {'etapa' if em_aberto == 1 else 'etapas'} do preparo pendentes ou em "
            "andamento: marque cada uma como concluída ou não realizada antes de povoar.",
        )
    _viveiro_livre(db, ciclo.viveiro_id, _user, exceto_id=ciclo.id)

    antes = snapshot(ciclo)
    for campo, valor in payload.model_dump().items():
        setattr(ciclo, campo, valor)
    ciclo.status = StatusCiclo.ATIVO
    db.add(CustoOperacional(
        ciclo_id=ciclo.id,
        data_lancamento=payload.data_povoamento,
        categoria=CategoriaCusto.POS_LARVAS,
        descricao=f"Aquisição de {payload.quantidade_pos_larvas:,} PLs",
        valor_rs=payload.custo_aquisicao_pl,
    ))
    db.flush()

    registrar_auditoria(
        db=db,
        acao="POVOAR_CICLO",
        entidade="CicloProdutivo",
        registro_id=ciclo.id,
        usuario=_user,
        dados_anteriores=antes,
        dados_novos=snapshot(ciclo),
    )
    db.refresh(ciclo)
    return ciclo


@router.patch(
    "/{ciclo_id}/planejamento", dependencies=[Depends(verificar_ciclo_da_organizacao)], response_model=CicloResponse
)
def reagendar_ciclo(
    ciclo_id: UUID,
    payload: CicloReagendar,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Muda data prevista, tabela alimentar ou viveiro do ciclo planejado; o já lançado fica no ciclo."""
    ciclo = _ciclo_planejado(db, ciclo_id, "reagendados")
    dados = payload.model_dump(exclude_unset=True)
    if "viveiro_id" in dados and dados["viveiro_id"] != ciclo.viveiro_id:
        _viveiro_livre(db, dados["viveiro_id"], _user, exceto_id=ciclo.id)
    if "tabela_alimentar_id" in dados:
        _validar_tabela_alimentar(db, dados["tabela_alimentar_id"], ciclo.viveiro.organizacao_id)

    antes = snapshot(ciclo)
    for campo, valor in dados.items():
        setattr(ciclo, campo, valor)
    db.flush()

    registrar_auditoria(
        db=db,
        acao="REAGENDAR_CICLO",
        entidade="CicloProdutivo",
        registro_id=ciclo.id,
        usuario=_user,
        dados_anteriores=antes,
        dados_novos=snapshot(ciclo),
    )
    db.refresh(ciclo)
    return ciclo


@router.post("/{ciclo_id}/cancelar", dependencies=[Depends(verificar_ciclo_da_organizacao)], response_model=CicloResponse)
def cancelar_ciclo(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Cancela um ciclo planejado que não vai acontecer, liberando o viveiro."""
    ciclo = _ciclo_planejado(db, ciclo_id, "cancelados")
    ciclo.status = StatusCiclo.CANCELADO
    db.flush()

    registrar_auditoria(
        db=db,
        acao="CANCELAR_CICLO",
        entidade="CicloProdutivo",
        registro_id=ciclo.id,
        usuario=_user,
        dados_anteriores={"status": StatusCiclo.PLANEJADO.value},
        dados_novos={"status": ciclo.status.value},
    )
    db.refresh(ciclo)
    return ciclo


@router.get("", response_model=list[CicloResponse])
@router.get("/", response_model=list[CicloResponse])
def listar_ciclos(
    viveiro_id: UUID | None = None,
    status_filtro: StatusCiclo | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Lista ciclos com filtros opcionais."""
    query = (
        select(CicloProdutivo)
        .join(Viveiro, CicloProdutivo.viveiro_id == Viveiro.id)
        .where(Viveiro.organizacao_id == org_do_usuario(_user))
        .order_by(CicloProdutivo.data_povoamento.desc())
    )
    if viveiro_id:
        query = query.where(CicloProdutivo.viveiro_id == viveiro_id)
    if status_filtro:
        query = query.where(CicloProdutivo.status == status_filtro)
    result = db.execute(query)
    return result.scalars().all()


@router.get("/{ciclo_id}", dependencies=[Depends(verificar_ciclo_da_organizacao)], response_model=CicloResponse)
def obter_ciclo(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Retorna dados de um ciclo específico."""
    result = db.execute(select(CicloProdutivo).where(CicloProdutivo.id == ciclo_id))
    ciclo = result.scalar_one_or_none()
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo não encontrado.")
    return ciclo


@router.post("/{ciclo_id}/encerrar", dependencies=[Depends(verificar_ciclo_da_organizacao)], response_model=CicloResponse)
def encerrar_ciclo(
    ciclo_id: UUID,
    payload: CicloEncerrar,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Encerra o ciclo: biomassa colhida e receita real passam a ser a soma das vendas (RF-02).

    Biomassa e receita no corpo viram uma venda DESPESCA_FINAL com o peso médio da última biometria;
    sem elas valem as vendas já lançadas, que precisam incluir ao menos uma despesca final.
    """
    result = db.execute(select(CicloProdutivo).where(CicloProdutivo.id == ciclo_id))
    ciclo = result.scalar_one_or_none()
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo não encontrado.")
    if ciclo.status not in (StatusCiclo.ATIVO, StatusCiclo.PAUSADO):
        raise HTTPException(status_code=400, detail="Somente ciclos ATIVOS ou PAUSADOS podem ser encerrados.")

    peso_final_g = peso_na_data(ciclo.biometrias, date.max)  # a da última biometria
    if peso_final_g is None:
        raise HTTPException(status_code=422, detail="Registre ao menos uma biometria antes de encerrar o ciclo.")
    pendentes = db.scalar(
        select(func.count()).select_from(ConsumoInsumo).where(
            ConsumoInsumo.ciclo_id == ciclo.id, ConsumoInsumo.preco_unitario_rs.is_(None)
        )
    )
    if pendentes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Há {pendentes} {'uso de insumo pendente' if pendentes == 1 else 'usos de insumo pendentes'} "
            "de valor: registre a compra faltante ou corrija o preço do uso antes de encerrar.",
        )

    datas_finais = list(db.scalars(
        select(VendaCiclo.data_venda).where(VendaCiclo.ciclo_id == ciclo.id, VendaCiclo.tipo == "DESPESCA_FINAL")
    ))
    hoje = hoje_da_fazenda()
    data_venda_nova = payload.data_despesca_real or hoje
    if payload.biomassa_colhida_kg is not None:
        datas_finais.append(data_venda_nova)
    if not datas_finais:
        raise HTTPException(
            status_code=422,
            detail="O encerramento exige ao menos uma venda de despesca final: "
            "informe biomassa e receita ou lance a venda antes.",
        )
    data_despesca = payload.data_despesca_real or max(datas_finais)
    if data_despesca < ciclo.data_povoamento:
        raise HTTPException(status_code=422, detail="A despesca não pode ser anterior ao povoamento.")

    venda = None
    if payload.biomassa_colhida_kg is not None:
        try:
            nova = VendaCreate(
                data_venda=data_venda_nova,
                tipo="DESPESCA_FINAL",
                biomassa_kg=payload.biomassa_colhida_kg,
                peso_medio_g=peso_final_g,
                preco_kg=payload.receita_real_rs / payload.biomassa_colhida_kg,
                retroativo=data_venda_nova < hoje,
            )
        except ValidationError:
            raise HTTPException(
                status_code=422, detail="Biomassa, receita e peso médio resultam em valores fora dos limites da venda."
            )
        colunas = colunas_da_venda(db, ciclo, nova)
        # a receita informada vale mais que o preço por kg arredondado a centavos
        colunas["valor_total_rs"] = round(payload.receita_real_rs, 2)
        venda = VendaCiclo(ciclo_id=ciclo.id, **colunas)
        db.add(venda)

    dados_ant = {
        "status": ciclo.status.value,
        "data_despesca_real": str(ciclo.data_despesca_real) if ciclo.data_despesca_real else None,
        "biomassa_colhida_kg": ciclo.biomassa_colhida_kg,
        "receita_real_rs": float(ciclo.receita_real_rs) if ciclo.receita_real_rs else None,
    }

    ciclo.status = StatusCiclo.FINALIZADO
    ciclo.data_despesca_real = data_despesca
    db.add(ciclo)
    sincronizar_totais_do_ciclo(db, ciclo)

    registrar_auditoria(
        db=db,
        acao="ENCERRAR_CICLO",
        entidade="CicloProdutivo",
        registro_id=ciclo.id,
        usuario=_user,
        dados_anteriores=dados_ant,
        dados_novos={
            "status": ciclo.status.value,
            "data_despesca_real": str(ciclo.data_despesca_real),
            "biomassa_colhida_kg": ciclo.biomassa_colhida_kg,
            "receita_real_rs": float(ciclo.receita_real_rs),
            "venda_despesca_final_id": str(venda.id) if venda else None,
        },
    )

    db.refresh(ciclo)
    return ciclo


@router.post("/{ciclo_id}/pausar", dependencies=[Depends(verificar_ciclo_da_organizacao)], response_model=CicloResponse)
def pausar_ciclo(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Pausa um ciclo produtivo ativo (RF-004)."""
    ciclo = db.get(CicloProdutivo, ciclo_id)
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo não encontrado.")
    if ciclo.status != StatusCiclo.ATIVO:
        raise HTTPException(status_code=400, detail="Somente ciclos ATIVOS podem ser pausados.")

    dados_ant = {"status": ciclo.status.value}
    ciclo.status = StatusCiclo.PAUSADO
    db.add(ciclo)
    db.flush()

    registrar_auditoria(
        db=db,
        acao="PAUSAR_CICLO",
        entidade="CicloProdutivo",
        registro_id=ciclo.id,
        usuario=_user,
        dados_anteriores=dados_ant,
        dados_novos={"status": ciclo.status.value},
    )
    db.refresh(ciclo)
    return ciclo


@router.post("/{ciclo_id}/retomar", dependencies=[Depends(verificar_ciclo_da_organizacao)], response_model=CicloResponse)
def retomar_ciclo(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Retoma um ciclo produtivo pausado (RF-004)."""
    ciclo = db.get(CicloProdutivo, ciclo_id)
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo não encontrado.")
    if ciclo.status != StatusCiclo.PAUSADO:
        raise HTTPException(status_code=400, detail="Somente ciclos PAUSADOS podem ser retomados.")
    if ciclo_aberto_do_viveiro(db, ciclo.viveiro_id, exceto_id=ciclo.id):
        raise HTTPException(status_code=409, detail="O viveiro já possui outro ciclo aberto.")

    dados_ant = {"status": ciclo.status.value}
    ciclo.status = StatusCiclo.ATIVO
    db.add(ciclo)
    db.flush()

    registrar_auditoria(
        db=db,
        acao="RETOMAR_CICLO",
        entidade="CicloProdutivo",
        registro_id=ciclo.id,
        usuario=_user,
        dados_anteriores=dados_ant,
        dados_novos={"status": ciclo.status.value},
    )
    db.refresh(ciclo)
    return ciclo


@router.get("/{ciclo_id}/metricas-atuais", dependencies=[Depends(verificar_ciclo_da_organizacao)], response_model=MetricasAtuaisResponse)
def metricas_atuais(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Retorna métricas consolidadas do ciclo (RF-09, RN-01..06)."""
    # Buscar ciclo com viveiro
    result = db.execute(select(CicloProdutivo).where(CicloProdutivo.id == ciclo_id))
    ciclo = result.scalar_one_or_none()
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo não encontrado.")
    exigir_povoamento(ciclo)

    viveiro = ciclo.viveiro
    hoje = date.today()
    dias_cultivo = (hoje - ciclo.data_povoamento).days

    # Densidade
    densidade = de.calcular_densidade(ciclo.quantidade_pos_larvas, viveiro.area_util_m2)
    alerta_hiper = de.verificar_hiperdensidade(densidade)

    # Entradas faltantes para rastreabilidade (RN-015)
    entradas_faltantes: list[str] = []

    # Peso da última biometria, sobrevivência vigente (mortos, consumo × tabela e fuzzy),
    # população descontados os animais vendidos, biomassa e preço de hoje
    atual = situacao_atual(db, ciclo, hoje)
    peso_medio, taxa_sobrev, pop_atual = atual.peso_medio_g, atual.taxa_sobrevivencia_pct, atual.populacao
    biomassa_atual, preco_kg = atual.biomassa_kg, atual.preco_kg
    if peso_medio is None:
        entradas_faltantes.append("biometria")

    biometrias = sorted(ciclo.biometrias, key=lambda b: b.data_medicao)
    manejos = ordenar(ciclo.manejos_alimentares)
    vendas = ciclo.vendas
    pontos = pontos_alimentares(ciclo, db)
    confronto = confrontar_vivos(
        manejos,
        ciclo.quantidade_pos_larvas,
        lambda data: peso_na_data(biometrias, data),
        lambda peso: de.taxa_alimentar(peso, pontos),
        hoje,
        vendidos_ate=lambda data: pv.animais_vendidos_ate(vendas, data),
    )

    densidade_atual = de.calcular_densidade(pop_atual, viveiro.area_util_m2)
    # Biomassa inicial = biomassa no povoamento (PLs × peso da PL); sem o peso, considerada desprezível
    biomassa_inicial = de.calcular_biomassa_kg(ciclo.quantidade_pos_larvas, ciclo.peso_medio_pl_g or 0.0)

    # Ração acumulada
    racao_total = sum(m.quantidade_racao_kg for m in manejos)

    # FCA
    fca = None
    class_fca = None
    if biomassa_atual is not None:
        fca = de.calcular_fca(racao_total, biomassa_atual, biomassa_inicial, pv.biomassa_vendida_kg(vendas))
        class_fca = de.classificar_fca(fca)

    # Clifford
    taxa_clifford = de.taxa_alimentar_clifford(peso_medio) if peso_medio is not None else None
    racao_diaria = (
        de.calcular_racao_diaria(biomassa_atual, peso_medio)
        if (biomassa_atual is not None and peso_medio is not None)
        else None
    )

    # Custos
    custos_vals = [float(c.valor_rs) for c in ciclo.custos_operacionais]

    if preco_kg is None:
        entradas_faltantes.append("preco_mercado")

    receita_realizada = pv.receita_realizada_rs(vendas)
    # lucro_operacional = lucro estimado se despescar hoje, já com a receita das vendas
    metricas = de.calcular_metricas_economicas(custos_vals, biomassa_atual, preco_kg, receita_realizada)

    # Restringir dados financeiros conforme perfil
    user = _user
    mostrar_financeiro = hasattr(user, 'papel') and user.papel == RoleUsuario.GESTOR

    return MetricasAtuaisResponse(
        ciclo_id=ciclo.id,
        viveiro_identificacao=viveiro.identificacao,
        dias_cultivo=dias_cultivo,
        densidade_estocagem=round(densidade, 2),
        densidade_atual=round(densidade_atual, 2),
        alerta_hiperdensidade=alerta_hiper,
        populacao_inicial=ciclo.quantidade_pos_larvas,
        taxa_sobrevivencia_fuzzy_pct=taxa_sobrev,
        confronto_vivos=asdict(confronto),
        populacao_estimada=pop_atual,
        peso_medio_atual_g=round(peso_medio, 2) if peso_medio is not None else None,
        biomassa_atual_kg=round(biomassa_atual, 2) if biomassa_atual is not None else None,
        racao_acumulada_kg=round(racao_total, 2),
        fca_atual=round(fca, 3) if fca is not None else None,
        classificacao_fca=class_fca.value if class_fca else None,
        taxa_alimentar_clifford_pct=round(taxa_clifford, 2) if taxa_clifford is not None else None,
        racao_diaria_sugerida_kg=round(racao_diaria, 2) if racao_diaria is not None else None,
        custo_operacional_total_rs=round(metricas.custo_operacional_total, 2) if mostrar_financeiro else None,
        receita_bruta_estimada_rs=round(metricas.receita_bruta, 2) if (metricas.receita_bruta is not None and mostrar_financeiro) else None,
        lucro_operacional_rs=round(metricas.lucro_operacional, 2) if (metricas.lucro_operacional is not None and mostrar_financeiro) else None,
        margem_operacional_pct=round(metricas.margem_operacional_pct, 2) if (metricas.margem_operacional_pct is not None and mostrar_financeiro) else None,
        preco_venda_atual_rs_kg=preco_kg if mostrar_financeiro else None,
        receita_realizada_rs=round(receita_realizada, 2) if mostrar_financeiro else None,
        lucro_realizado_rs=round(receita_realizada - metricas.custo_operacional_total, 2) if mostrar_financeiro else None,
        entradas_faltantes=entradas_faltantes,
    )


@router.get(
    "/{ciclo_id}/financeiro", dependencies=[Depends(verificar_ciclo_da_organizacao)],
    response_model=FinanceiroCicloResponse,
)
def financeiro_do_ciclo(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Custos por fase e categoria, vendas, lucro realizado e lucro estimado se despescar hoje (seção 5.6)."""
    resumo = resumo_do_ciclo(db, buscar_ciclo(db, ciclo_id), mostrar_valores=True)
    return FinanceiroCicloResponse(**{**resumo, "vendas": resumo["vendas_lista"]})


@router.get("/{ciclo_id}/exportar-csv", dependencies=[Depends(verificar_ciclo_da_organizacao)])
def exportar_ciclo_csv(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Exporta histórico zootécnico e biometrias do ciclo em CSV (RF-025, UC-012)."""
    import csv
    import io
    from fastapi.responses import Response

    result = db.execute(select(CicloProdutivo).where(CicloProdutivo.id == ciclo_id))
    ciclo = result.scalar_one_or_none()
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo não encontrado.")

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Tipo_Registro", "Data", "Parametro_1", "Parametro_2", "Parametro_3", "Observacoes"])

    # Povoamento
    writer.writerow([
        "POVOAMENTO",
        ciclo.data_povoamento.isoformat(),
        f"PLs: {ciclo.quantidade_pos_larvas or ''}",
        f"Custo: R$ {float(ciclo.custo_aquisicao_pl or 0):.2f}".replace(".", ","),
        ciclo.laboratorio_origem or "",
        "",
    ])

    # Biometrias
    for b in sorted(ciclo.biometrias, key=lambda x: x.data_medicao):
        writer.writerow([
            "BIOMETRIA",
            b.data_medicao.isoformat(),
            f"PesoMedio: {b.peso_medio_g}g",
            f"Amostra: {b.quantidade_amostrada} un",
            f"Uniformidade: {b.uniformidade_percentual or ''}%",
            b.observacoes or "",
        ])

    # Manejos
    for m in sorted(ciclo.manejos_alimentares, key=lambda x: x.data_registro):
        writer.writerow([
            "MANEJO",
            m.data_registro.isoformat(),
            f"Racao: {m.quantidade_racao_kg}kg",
            f"Sobra: {m.sobra_bandeja_nivel.value}",
            f"SobrevivenciaEst: {m.taxa_sobrevivencia_estimada_fuzzy or ''}%",
            "",
        ])

    registrar_auditoria(db, "EXPORTAR", "CicloProdutivo", ciclo.id, _user, dados_novos={"formato": "csv"})
    content = output.getvalue().encode("utf-8-sig")
    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="relatorio_ciclo_{str(ciclo_id)[:8]}.csv"'
        },
    )


@router.delete("/{ciclo_id}", dependencies=[Depends(verificar_ciclo_da_organizacao)], status_code=status.HTTP_200_OK)
def deletar_ciclo(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Exclui um ciclo produtivo."""
    result = db.execute(select(CicloProdutivo).where(CicloProdutivo.id == ciclo_id))
    ciclo = result.scalar_one_or_none()
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo não encontrado.")
    registrar_auditoria(db, "EXCLUIR", "CicloProdutivo", ciclo.id, _user, dados_anteriores=snapshot(ciclo))
    # os usos somem por CASCADE; o preço médio dos insumos usados muda para os outros ciclos
    insumos_usados = db.scalars(
        select(ConsumoInsumo.insumo_id).where(ConsumoInsumo.ciclo_id == ciclo.id).distinct()
    ).all()
    db.delete(ciclo)
    db.flush()
    for insumo_id in insumos_usados:
        reprocessar_insumo(db, insumo_id, _user)
    return {"detail": "Ciclo excluído com sucesso.", "id": str(ciclo_id)}


