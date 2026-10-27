"""Conferência dos cálculos contra os documentos de referência.

Os valores esperados são calculados à mão com as fórmulas dos documentos
("Fórmulas e Parâmetros - SAD Carcinicultura" e "Dados essenciais"), sem chamar
o motor de decisão, e comparados com o que o motor e a API devolvem.
"""

from datetime import date
from itertools import pairwise, permutations

import pytest

from src.services.decision_engine import buscar_preco_por_gramatura as buscar
from src.services.decision_engine import simular_delta_v, taxa_alimentar_clifford

# Tabela 1 (peso g, consumo alimentar g, taxa alimentar %), adaptada de Clifford (1992),
# transcrita do documento "Dados essenciais BIOLOGICO".
TABELA_1 = [
    (2.0, 0.143, 7.15), (3.0, 0.184, 6.13), (4.0, 0.220, 5.50), (5.0, 0.253, 5.05),
    (6.0, 0.283, 4.71), (7.0, 0.311, 4.44), (8.0, 0.338, 4.22), (9.0, 0.364, 4.04),
    (10.0, 0.388, 3.88), (11.0, 0.412, 3.74), (12.0, 0.435, 3.62), (13.0, 0.457, 3.51),
    (14.0, 0.478, 3.42), (15.0, 0.499, 3.33), (16.0, 0.519, 3.25), (17.0, 0.539, 3.17),
    (18.0, 0.559, 3.10), (19.0, 0.578, 3.04), (20.0, 0.596, 2.98),
]


def _preco_da_faixa(client, gestor, peso_g: float) -> float:
    """Preço vigente da gramatura, lido da tabela de preços (exige uma única faixa)."""
    faixas = client.get("/api/v1/precos-mercado/", headers=gestor).json()
    candidatas = [f for f in faixas if f["faixa_gramatura_min"] <= peso_g <= f["faixa_gramatura_max"]]
    assert len(candidatas) == 1, f"peso {peso_g} g cai em {len(candidatas)} faixas: {candidatas}"
    return float(candidatas[0]["preco_por_kg"])


def _ciclo(client, gestor, novo_viveiro, pls=300_000, custo_pl=3_000.0, peso_pl=None):
    viveiro = novo_viveiro(10_000.0)
    corpo = {"viveiro_id": viveiro["id"], "data_povoamento": "2026-08-01",
             "quantidade_pos_larvas": pls, "custo_aquisicao_pl": custo_pl}
    if peso_pl is not None:
        corpo["peso_medio_pl_g"] = peso_pl
    r = client.post("/api/v1/ciclos/", json=corpo, headers=gestor)
    assert r.status_code == 201, r.text
    return f"/api/v1/ciclos/{r.json()['id']}"


def _biometria(client, gestor, url, dia, peso):
    r = client.post(f"{url}/biometrias/", json={"data_medicao": dia, "quantidade_amostrada": 50,
                                                "peso_medio_g": peso}, headers=gestor)
    assert r.status_code == 201, r.text


def _custo(client, gestor, url, valor, categoria="RACAO"):
    r = client.post(f"{url}/custos/", json={"data_lancamento": "2026-09-10", "categoria": categoria,
                                            "descricao": "Lançamento", "valor_rs": valor}, headers=gestor)
    assert r.status_code == 201, r.text


# ── Tabela alimentar (Tabela 1) ───────────────────────

@pytest.mark.parametrize("peso,consumo,taxa", TABELA_1)
def test_tabela_clifford_igual_ao_documento(peso, consumo, taxa):
    assert taxa_alimentar_clifford(peso) == taxa
    # O documento é coerente: taxa = consumo individual / peso corporal (arredondamento de 2 casas)
    assert consumo / peso * 100 == pytest.approx(taxa, abs=0.01)


def test_interpolacao_no_ponto_medio_de_cada_intervalo():
    for (p1, _, t1), (p2, _, t2) in pairwise(TABELA_1):
        assert taxa_alimentar_clifford((p1 + p2) / 2) == pytest.approx((t1 + t2) / 2)


def test_fora_da_tabela_mantem_a_taxa_do_extremo():
    # A Tabela 1 vai de 2 g a 20 g; fora dela o motor repete a taxa do extremo
    assert taxa_alimentar_clifford(1.0) == 7.15
    assert taxa_alimentar_clifford(25.0) == 2.98


def test_tabela_padrao_gravada_no_banco_e_a_do_documento(client, gestor):
    tabelas = client.get("/api/v1/tabelas-alimentares/", headers=gestor).json()
    padrao = [t for t in tabelas if t["nome"].startswith("Clifford")]
    assert padrao, "tabela padrão de Clifford não encontrada"
    pontos = [(f["peso_g"], f["taxa_pct"]) for f in padrao[0]["faixas"]]
    assert pontos == [(p, t) for p, _, t in TABELA_1]


# ── Indicadores biológicos, de manejo e financeiros (API) ─────

def test_metricas_conferem_com_o_calculo_manual(client, gestor, novo_viveiro):
    url = _ciclo(client, gestor, novo_viveiro, peso_pl=0.002)
    _biometria(client, gestor, url, "2026-09-01", 10.5)
    r = client.post(f"{url}/manejos-alimentares/", json={"data_registro": "2026-09-02", "quantidade_racao_kg": 3_500,
                                                         "sobra_bandeja_nivel": "SEM_SOBRA"}, headers=gestor)
    assert r.status_code == 201, r.text
    _custo(client, gestor, url, 20_000)
    m = client.get(f"{url}/metricas-atuais", headers=gestor).json()

    sobrev = m["taxa_sobrevivencia_fuzzy_pct"]  # entrada vinda do motor fuzzy
    assert 0 < sobrev <= 100

    # D = N / A
    assert m["densidade_estocagem"] == 30.0
    # Pop_Atual = Pop_Inicial × Sobrevivência
    pop = int(300_000 * sobrev / 100)
    assert m["populacao_estimada"] == pop
    # Biomassa = (Pop_Atual × Peso_Médio) / 1000
    biomassa = pop * 10.5 / 1000
    assert m["biomassa_atual_kg"] == pytest.approx(biomassa, abs=0.01)
    # FCA = Ração_Total / (Biomassa_final − Biomassa_inicial); inicial = 300.000 PLs × 0,002 g = 0,6 kg
    fca = 3_500 / (biomassa - 0.6)
    assert m["fca_atual"] == pytest.approx(fca, abs=0.001)
    assert m["classificacao_fca"] == ("ALTA_EFICIENCIA" if fca <= 1.2 else "FAIXA_PADRAO" if fca <= 1.6
                                      else "DESPERDICIO_INDICADO")
    # Taxa em 10,5 g: ponto médio entre 10 g (3,88%) e 11 g (3,74%); ração = Biomassa × taxa
    assert m["taxa_alimentar_clifford_pct"] == 3.81
    assert m["racao_diaria_sugerida_kg"] == pytest.approx(biomassa * 0.0381, abs=0.01)
    # Financeiro: CO = PLs (3.000) + ração (20.000)
    preco = _preco_da_faixa(client, gestor, 10.5)
    receita = biomassa * preco
    lucro = receita - 23_000
    assert m["preco_venda_atual_rs_kg"] == preco
    assert m["custo_operacional_total_rs"] == 23_000
    assert m["receita_bruta_estimada_rs"] == pytest.approx(receita, abs=0.01)
    assert m["lucro_operacional_rs"] == pytest.approx(lucro, abs=0.01)
    assert m["margem_operacional_pct"] == pytest.approx(lucro / receita * 100, abs=0.01)


def test_fca_sem_peso_da_pl_considera_biomassa_inicial_zero(client, gestor, novo_viveiro):
    url = _ciclo(client, gestor, novo_viveiro)  # sem peso_medio_pl_g
    _biometria(client, gestor, url, "2026-09-01", 10.5)
    client.post(f"{url}/manejos-alimentares/", json={"data_registro": "2026-09-02", "quantidade_racao_kg": 3_500,
                                                     "sobra_bandeja_nivel": "SEM_SOBRA"}, headers=gestor)
    m = client.get(f"{url}/metricas-atuais", headers=gestor).json()
    assert m["fca_atual"] == pytest.approx(3_500 / m["biomassa_atual_kg"], abs=0.001)


# ── Simulação ΔV (API) ────────────────────────────────

def _ciclo_para_simulacao(client, gestor, novo_viveiro):
    """300.000 PLs, 100% de sobrevivência (sem manejos), 10,6 g → 11,6 g em 14 dias, CO = 15.000."""
    url = _ciclo(client, gestor, novo_viveiro)
    _biometria(client, gestor, url, "2026-09-01", 10.6)
    _biometria(client, gestor, url, "2026-09-15", 11.6)
    _custo(client, gestor, url, 12_000)  # + 3.000 das PLs
    return url


def test_delta_v_manter_conferido_a_mao(client, gestor, novo_viveiro):
    url = _ciclo_para_simulacao(client, gestor, novo_viveiro)
    r = client.post(f"{url}/simular-despesca/", json={"dias_horizonte": 15, "custo_diario_rs": 500}, headers=gestor)
    assert r.status_code == 200, r.text
    s = r.json()

    ganho = (11.6 - 10.6) / 14                       # g/dia
    peso_proj = 11.6 + ganho * 15                    # 12,6714 g
    bio_atual = 300_000 * 11.6 / 1000                # 3.480 kg
    bio_proj = 300_000 * peso_proj / 1000            # 3.801,43 kg
    preco_atual = _preco_da_faixa(client, gestor, 11.6)
    preco_futuro = _preco_da_faixa(client, gestor, peso_proj)
    assert preco_futuro > preco_atual                # o lote muda de faixa de preço
    lo_atual = bio_atual * preco_atual - 15_000
    lucro_proj = bio_proj * preco_futuro - (15_000 + 500 * 15)
    delta = lucro_proj - lo_atual

    assert s["peso_medio_projetado_g"] == pytest.approx(peso_proj, abs=0.01)
    assert s["biomassa_atual_kg"] == pytest.approx(bio_atual, abs=0.01)
    assert s["biomassa_projetada_kg"] == pytest.approx(bio_proj, abs=0.01)
    assert s["lucro_operacional_atual_rs"] == pytest.approx(lo_atual, abs=0.01)
    assert s["receita_projetada_rs"] == pytest.approx(bio_proj * preco_futuro, abs=0.02)
    assert s["custo_adicional_projetado_rs"] == 7_500
    assert s["lucro_projetado_rs"] == pytest.approx(lucro_proj, abs=0.02)
    assert s["delta_v_rs"] == pytest.approx(delta, abs=0.02)
    assert delta > 0 and s["recomendacao"] == "MANTER_CULTIVO"


def test_delta_v_despesca_imediata_conferido_a_mao(client, gestor, novo_viveiro):
    url = _ciclo_para_simulacao(client, gestor, novo_viveiro)
    r = client.post(f"{url}/simular-despesca/", json={"dias_horizonte": 7, "custo_diario_rs": 5_000}, headers=gestor)
    assert r.status_code == 200, r.text
    s = r.json()

    peso_proj = 11.6 + (1.0 / 14) * 7                # 12,1 g
    bio_atual = 300_000 * 11.6 / 1000
    bio_proj = 300_000 * peso_proj / 1000
    preco_atual = _preco_da_faixa(client, gestor, 11.6)
    preco_futuro = _preco_da_faixa(client, gestor, peso_proj)
    delta = (bio_proj * preco_futuro - (15_000 + 5_000 * 7)) - (bio_atual * preco_atual - 15_000)

    assert s["delta_v_rs"] == pytest.approx(delta, abs=0.02)
    assert delta <= 0 and s["recomendacao"] == "DESPESCA_IMEDIATA"


def test_delta_v_igual_a_zero_recomenda_despescar(client, gestor, novo_viveiro):
    # Regra do documento: ΔV ≤ 0 → despesca imediata (empate não justifica manter o cultivo)
    r = simular_delta_v(
        dias_horizonte=7, peso_medio_atual_g=10, ganho_diario_g=0, populacao_atual=1000,
        mortalidade_diaria_pct=0, custo_operacional_total=0, preco_atual_kg=10, preco_futuro_kg=10,
        custo_diario_racao_energia=0, biomassa_atual_kg=10,
    )
    assert r.delta_v == 0 and r.recomendacao.value == "DESPESCA_IMEDIATA"


# ── Preço na borda entre faixas ───────────────────────

def _faixa(minimo, maximo, preco, vigencia=None):
    return {"faixa_gramatura_min": minimo, "faixa_gramatura_max": maximo, "preco_por_kg": preco,
            "vigencia_inicio": vigencia}


def test_preco_na_borda_vale_a_faixa_de_cima_em_qualquer_ordem():
    tabela = [_faixa(8, 10, 18.5), _faixa(10, 12, 21.0), _faixa(12, 14, 24.5)]
    for ordem in permutations(tabela):
        assert buscar(10.0, list(ordem)) == 21.0
        assert buscar(12.0, list(ordem)) == 24.5
        assert buscar(9.99, list(ordem)) == 18.5
        assert buscar(8.0, list(ordem)) == 18.5      # borda inferior da primeira faixa
        assert buscar(14.0, list(ordem)) == 24.5     # borda superior da última faixa
        assert buscar(14.01, list(ordem)) is None
        assert buscar(7.99, list(ordem)) is None


def test_mesma_faixa_com_duas_vigencias_vale_a_mais_recente():
    antiga = _faixa(10, 12, 20.0, date(2026, 1, 1))
    nova = _faixa(10, 12, 22.0, date(2026, 6, 1))
    assert buscar(11.0, [antiga, nova]) == 22.0
    assert buscar(11.0, [nova, antiga]) == 22.0


def test_preco_na_borda_e_o_mesmo_na_tela_e_na_simulacao(client, gestor, novo_viveiro):
    """Com 10,0 g (divisa entre 8–10 e 10–12) as duas rotas usam o preço da faixa de cima."""
    url = _ciclo(client, gestor, novo_viveiro)
    _biometria(client, gestor, url, "2026-09-01", 9.0)
    _biometria(client, gestor, url, "2026-09-15", 10.0)
    _custo(client, gestor, url, 12_000)
    faixas = client.get("/api/v1/precos-mercado/", headers=gestor).json()
    esperado = next(float(f["preco_por_kg"]) for f in faixas if f["faixa_gramatura_min"] == 10.0)
    metricas = client.get(f"{url}/metricas-atuais", headers=gestor).json()
    sim = client.post(f"{url}/simular-despesca/", json={"dias_horizonte": 7}, headers=gestor).json()
    assert metricas["preco_venda_atual_rs_kg"] == esperado
    assert sim["preco_atual_rs_kg"] == esperado


# ── Tabela de preços sem sobreposição ─────────────────

@pytest.fixture
def gestor_sem_precos(client, admin, login):
    """Gestor de uma organização nova, sem faixas de preço cadastradas."""
    from tests.conftest import unico
    org = client.post("/api/v1/organizacoes/", json={"nome": "Fazenda Preços", "identificador": unico("PRC")},
                      headers=admin)
    assert org.status_code == 201, org.text
    email = f"{unico('gestorprc')}@x.com"
    r = client.post("/api/v1/admin/gestores", json={"nome_completo": "Gestor Preços", "email": email,
                                                    "senha": "abc12345", "organizacao_id": org.json()["id"]},
                    headers=admin)
    assert r.status_code == 201, r.text
    return login(email, "abc12345")


def _criar_faixa(client, headers, minimo, maximo, preco=20.0, inicio="2026-01-01", fim=None):
    return client.post("/api/v1/precos-mercado/", json={
        "faixa_gramatura_min": minimo, "faixa_gramatura_max": maximo, "preco_por_kg": preco,
        "vigencia_inicio": inicio, "vigencia_fim": fim}, headers=headers)


def test_faixas_vizinhas_sao_aceitas(client, gestor_sem_precos):
    assert _criar_faixa(client, gestor_sem_precos, 8, 10).status_code == 201
    assert _criar_faixa(client, gestor_sem_precos, 10, 12).status_code == 201
    assert _criar_faixa(client, gestor_sem_precos, 14, 16).status_code == 201   # com vão no meio


def test_faixa_sobreposta_e_recusada(client, gestor_sem_precos):
    assert _criar_faixa(client, gestor_sem_precos, 8, 10).status_code == 201
    for minimo, maximo in ((9, 11), (8, 10), (7, 12), (8.5, 9.5)):
        r = _criar_faixa(client, gestor_sem_precos, minimo, maximo)
        assert r.status_code == 409, (minimo, maximo, r.text)
        assert "sobrepõe" in r.json()["detail"]


def test_mesma_faixa_em_periodos_diferentes_e_aceita(client, gestor_sem_precos):
    assert _criar_faixa(client, gestor_sem_precos, 8, 10, 18.0, "2026-01-01", "2026-05-31").status_code == 201
    assert _criar_faixa(client, gestor_sem_precos, 8, 10, 19.0, "2026-06-01").status_code == 201
    # ...mas não um período que invade o anterior
    assert _criar_faixa(client, gestor_sem_precos, 8, 10, 19.5, "2026-05-15").status_code == 409


def test_estender_vigencia_para_dentro_de_outra_faixa_e_recusado(client, gestor_sem_precos):
    antiga = _criar_faixa(client, gestor_sem_precos, 8, 10, 18.0, "2026-01-01", "2026-05-31").json()
    assert _criar_faixa(client, gestor_sem_precos, 8, 10, 19.0, "2026-06-01").status_code == 201
    r = client.put(f"/api/v1/precos-mercado/{antiga['id']}", json={"vigencia_fim": "2026-07-31"},
                   headers=gestor_sem_precos)
    assert r.status_code == 409
