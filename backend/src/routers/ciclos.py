"""SAD Carcinicultura — Rotas de Ciclos Produtivos (RF-02, RF-09)."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.audit import registrar_auditoria, snapshot
from src.models.biometria import Biometria
from src.models.ciclo_produtivo import CicloProdutivo
from src.models.custo_operacional import CustoOperacional
from src.models.enums import RoleUsuario, StatusCiclo
from src.models.manejo_alimentar import ManejoAlimentar
from src.models.tabela_preco import TabelaPrecoMercado
from src.models.viveiro import Viveiro
from src.schemas.ciclo import CicloCreate, CicloEncerrar, CicloResponse, MetricasAtuaisResponse
from src.services.auth_service import get_current_user, has_role
from src.services import decision_engine as de
from src.services.regras_ciclo import ciclo_aberto_do_viveiro

router = APIRouter(prefix="/api/v1/ciclos", tags=["Ciclos Produtivos"])


@router.post("", response_model=CicloResponse, status_code=201)
@router.post("/", response_model=CicloResponse, status_code=201)
async def criar_ciclo(
    payload: CicloCreate,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Abre um novo ciclo produtivo em um viveiro (RF-02)."""
    # Verificar viveiro
    viv_result = db.execute(select(Viveiro).where(Viveiro.id == payload.viveiro_id))
    viveiro = viv_result.scalar_one_or_none()
    if not viveiro:
        raise HTTPException(status_code=404, detail="Viveiro não encontrado.")
    if not viveiro.status_ativo:
        raise HTTPException(status_code=400, detail="Viveiro inativo.")

    # Um ciclo aberto (ATIVO ou PAUSADO) por viveiro
    if ciclo_aberto_do_viveiro(db, payload.viveiro_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este viveiro já possui um ciclo ATIVO ou PAUSADO.",
        )

    if payload.tabela_alimentar_id is not None:
        from src.models.tabela_alimentar import TabelaAlimentar
        tabela = db.get(TabelaAlimentar, payload.tabela_alimentar_id)
        if not tabela or not tabela.ativo:
            raise HTTPException(status_code=404, detail="Tabela alimentar não encontrada ou inativa.")

    # Verificar densidade (RN-01)
    densidade = de.calcular_densidade(payload.quantidade_pos_larvas, viveiro.area_util_m2)

    ciclo_data = payload.model_dump()

    import uuid
    ciclo_id = uuid.uuid4()
    ciclo = CicloProdutivo(
        id=ciclo_id,
        **ciclo_data,
        status=StatusCiclo.ATIVO,
    )
    db.add(ciclo)
    db.flush()

    # Auto-lançar custo de PLs
    from src.models.custo_operacional import CustoOperacional
    from src.models.enums import CategoriaCusto
    custo_pl = CustoOperacional(
        id=uuid.uuid4(),
        ciclo_id=ciclo.id,
        data_lancamento=payload.data_povoamento,
        categoria=CategoriaCusto.POS_LARVAS,
        descricao=f"Aquisição de {payload.quantidade_pos_larvas:,} PLs",
        valor_rs=payload.custo_aquisicao_pl,
    )
    db.add(custo_pl)
    db.flush()

    registrar_auditoria(
        db=db,
        acao="CRIAR_CICLO",
        entidade="CicloProdutivo",
        registro_id=ciclo.id,
        usuario=_user,
        dados_novos={
            "viveiro_id": str(ciclo.viveiro_id),
            "data_povoamento": str(ciclo.data_povoamento),
            "quantidade_pos_larvas": ciclo.quantidade_pos_larvas,
            "custo_aquisicao_pl": float(ciclo.custo_aquisicao_pl),
            "laboratorio_origem": ciclo.laboratorio_origem,
        },
    )

    db.refresh(ciclo)
    return ciclo


@router.get("", response_model=list[CicloResponse])
@router.get("/", response_model=list[CicloResponse])
async def listar_ciclos(
    viveiro_id: UUID | None = None,
    status_filtro: StatusCiclo | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Lista ciclos com filtros opcionais."""
    query = select(CicloProdutivo).order_by(CicloProdutivo.data_povoamento.desc())
    if viveiro_id:
        query = query.where(CicloProdutivo.viveiro_id == viveiro_id)
    if status_filtro:
        query = query.where(CicloProdutivo.status == status_filtro)
    result = db.execute(query)
    return result.scalars().all()


@router.get("/{ciclo_id}", response_model=CicloResponse)
async def obter_ciclo(
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


@router.post("/{ciclo_id}/encerrar", response_model=CicloResponse)
async def encerrar_ciclo(
    ciclo_id: UUID,
    payload: CicloEncerrar,
    db: Session = Depends(get_db),
    _user=Depends(has_role([RoleUsuario.GESTOR])),
):
    """Encerra o ciclo com dados da despesca real (RF-02)."""
    result = db.execute(select(CicloProdutivo).where(CicloProdutivo.id == ciclo_id))
    ciclo = result.scalar_one_or_none()
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo não encontrado.")
    if ciclo.status not in (StatusCiclo.ATIVO, StatusCiclo.PAUSADO):
        raise HTTPException(status_code=400, detail="Somente ciclos ATIVOS ou PAUSADOS podem ser encerrados.")
    if payload.data_despesca_real < ciclo.data_povoamento:
        raise HTTPException(status_code=422, detail="A despesca não pode ser anterior ao povoamento.")

    dados_ant = {
        "status": ciclo.status.value,
        "data_despesca_real": str(ciclo.data_despesca_real) if ciclo.data_despesca_real else None,
        "biomassa_colhida_kg": ciclo.biomassa_colhida_kg,
        "receita_real_rs": float(ciclo.receita_real_rs) if ciclo.receita_real_rs else None,
    }

    ciclo.status = StatusCiclo.FINALIZADO
    ciclo.data_despesca_real = payload.data_despesca_real
    ciclo.biomassa_colhida_kg = payload.biomassa_colhida_kg
    ciclo.receita_real_rs = payload.receita_real_rs
    db.add(ciclo)
    db.flush()

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
        },
    )

    db.refresh(ciclo)
    return ciclo


@router.post("/{ciclo_id}/pausar", response_model=CicloResponse)
async def pausar_ciclo(
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


@router.post("/{ciclo_id}/retomar", response_model=CicloResponse)
async def retomar_ciclo(
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


@router.get("/{ciclo_id}/metricas-atuais", response_model=MetricasAtuaisResponse)
async def metricas_atuais(
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

    viveiro = ciclo.viveiro
    hoje = date.today()
    dias_cultivo = (hoje - ciclo.data_povoamento).days

    # Densidade
    densidade = de.calcular_densidade(ciclo.quantidade_pos_larvas, viveiro.area_util_m2)
    alerta_hiper = de.verificar_hiperdensidade(densidade)

    # Entradas faltantes para rastreabilidade (RN-015)
    entradas_faltantes: list[str] = []

    # Última biometria
    biometrias = sorted(ciclo.biometrias, key=lambda b: b.data_medicao)
    if biometrias:
        peso_medio = biometrias[-1].peso_medio_g
    else:
        peso_medio = None
        entradas_faltantes.append("biometria")

    # Sobrevivência fuzzy mais recente
    manejos = sorted(ciclo.manejos_alimentares, key=lambda m: m.data_registro)
    taxa_sobrev = 100.0
    for m in manejos:
        if m.taxa_sobrevivencia_estimada_fuzzy is not None:
            taxa_sobrev = m.taxa_sobrevivencia_estimada_fuzzy

    # População e biomassa
    pop_atual = de.calcular_populacao_atual(ciclo.quantidade_pos_larvas, taxa_sobrev)
    if peso_medio is not None:
        biomassa_atual = de.calcular_biomassa_kg(pop_atual, peso_medio)
        biomassa_inicial = de.calcular_biomassa_kg(
            ciclo.quantidade_pos_larvas, biometrias[0].peso_medio_g
        )
    else:
        biomassa_atual = None
        biomassa_inicial = None

    # Ração acumulada
    racao_total = sum(m.quantidade_racao_kg for m in manejos)

    # FCA
    fca = None
    class_fca = None
    if biomassa_atual is not None and biomassa_inicial is not None:
        fca = de.calcular_fca(racao_total, biomassa_atual, biomassa_inicial)
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

    # Preço de mercado vigente
    preco_kg = None
    if peso_medio is not None:
        preco_result = db.execute(
            select(TabelaPrecoMercado).where(
                TabelaPrecoMercado.faixa_gramatura_min <= peso_medio,
                TabelaPrecoMercado.faixa_gramatura_max >= peso_medio,
                TabelaPrecoMercado.vigencia_inicio <= hoje,
            ).order_by(TabelaPrecoMercado.vigencia_inicio.desc()).limit(1)
        )
        preco_row = preco_result.scalar_one_or_none()
        if preco_row:
            preco_kg = float(preco_row.preco_por_kg)
        else:
            entradas_faltantes.append("preco_mercado")
    else:
        entradas_faltantes.append("preco_mercado")

    metricas = de.calcular_metricas_economicas(custos_vals, biomassa_atual, preco_kg)

    # Restringir dados financeiros conforme perfil
    user = _user
    mostrar_financeiro = hasattr(user, 'papel') and user.papel == RoleUsuario.GESTOR

    return MetricasAtuaisResponse(
        ciclo_id=ciclo.id,
        viveiro_identificacao=viveiro.identificacao,
        dias_cultivo=dias_cultivo,
        densidade_estocagem=round(densidade, 2),
        alerta_hiperdensidade=alerta_hiper,
        populacao_inicial=ciclo.quantidade_pos_larvas,
        taxa_sobrevivencia_fuzzy_pct=taxa_sobrev,
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
        entradas_faltantes=entradas_faltantes,
    )


@router.get("/{ciclo_id}/exportar-csv")
async def exportar_ciclo_csv(
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
        f"PLs: {ciclo.quantidade_pos_larvas}",
        f"Custo: R$ {float(ciclo.custo_aquisicao_pl):.2f}".replace(".", ","),
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


@router.delete("/{ciclo_id}", status_code=status.HTTP_200_OK)
async def deletar_ciclo(
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
    db.delete(ciclo)
    db.flush()
    return {"detail": "Ciclo excluído com sucesso.", "id": str(ciclo_id)}


