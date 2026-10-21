"""Testes isolados dos cálculos, schemas e do teste TC001 do backend SAD.

Não importa main/config/database, não abre rede, não altera o projeto nem o banco.
Executar como processo separado. Requer numpy e pydantic >= 2.
SAD_BACKEND_PATH pode apontar para outra cópia do backend.
"""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from datetime import date, datetime, timedelta, timezone
from types import ModuleType, SimpleNamespace
import unittest
import uuid

BACKEND = Path(os.environ.get(
    "SAD_BACKEND_PATH",
    r"C:\Users\jm_montmaia\Desktop\sisteminha\backend",
))
OUTPUT = Path(__file__).parent
sys.dont_write_bytecode = True


def load_source(name, relative):
    path = BACKEND / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Carrega somente módulos sem persistência. Evita __init__ com imports de ORM.
# Os nomes temporários são restaurados após o carregamento.
saved_modules = dict(sys.modules)
try:
    for name in ("src", "src.models", "src.services", "src.schemas"):
        package = ModuleType(name)
        package.__path__ = []
        sys.modules[name] = package
    enums = load_source("src.models.enums", "src/models/enums.py")
    engine = load_source("src.services.decision_engine", "src/services/decision_engine.py")
    alerts = load_source("src.services.alert_engine", "src/services/alert_engine.py")
    bio = load_source("src.schemas.biometria", "src/schemas/biometria.py")
    costs = load_source("src.schemas.custo", "src/schemas/custo.py")
    ponds = load_source("src.schemas.viveiro", "src/schemas/viveiro.py")
    simulations = load_source("src.schemas.simulacao", "src/schemas/simulacao.py")
finally:
    for name in list(sys.modules):
        if name == "src" or name.startswith("src."):
            if name in saved_modules:
                sys.modules[name] = saved_modules[name]
            else:
                del sys.modules[name]

from pydantic import ValidationError


def delta_case(**changes):
    inputs = dict(
        dias_horizonte=10,
        peso_medio_atual_g=10.0,
        ganho_diario_g=0.2,
        populacao_atual=80000,
        mortalidade_diaria_pct=0.0,
        custo_operacional_total=15000.0,
        preco_atual_kg=22.0,
        preco_futuro_kg=25.0,
        custo_diario_racao_energia=120.0,
        biomassa_atual_kg=800.0,
    )
    inputs.update(changes)
    return engine.simular_delta_v(**inputs)


class TestCalculos(unittest.TestCase):
    def test_delta_v_oraculo_exato(self):
        # 960 kg * 25 = 24000; CO projetado = 16200.
        # LO atual = 800 * 22 - 15000 = 2600.
        r = delta_case()
        self.assertEqual(r.peso_medio_projetado_g, 12)
        self.assertEqual(r.biomassa_projetada_kg, 960)
        self.assertEqual(r.receita_projetada, 24000)
        self.assertEqual(r.custo_adicional, 1200)
        self.assertEqual(r.lucro_projetado, 7800)
        self.assertEqual(r.delta_v, 5200)
        self.assertEqual(r.recomendacao, enums.RecomendacaoDespesca.MANTER_CULTIVO)

    def test_delta_v_negativo(self):
        r = delta_case(custo_diario_racao_energia=1000)
        self.assertEqual(r.delta_v, -3600)
        self.assertEqual(r.recomendacao, enums.RecomendacaoDespesca.DESPESCA_IMEDIATA)

    def test_delta_v_empate(self):
        r = delta_case(ganho_diario_g=0, preco_futuro_kg=22,
                       custo_diario_racao_energia=0)
        self.assertEqual(r.delta_v, 0)
        self.assertEqual(r.recomendacao, enums.RecomendacaoDespesca.DESPESCA_IMEDIATA)

    def test_delta_v_mortalidade_composta(self):
        # 80000 * 0.99**10 -> 72350 indivíduos, truncamento atual.
        r = delta_case(mortalidade_diaria_pct=1)
        self.assertEqual(r.biomassa_projetada_kg, 868.20)
        self.assertEqual(r.receita_projetada, 21705)
        self.assertEqual(r.delta_v, 2905)

    def test_delta_v_preco_futuro_ausente(self):
        self.assertEqual(delta_case(preco_futuro_kg=None).delta_v, 2320)

    def test_delta_v_custo_passado_nao_altera_decisao_marginal(self):
        a, b = delta_case(), delta_case(custo_operacional_total=25000)
        self.assertEqual(a.delta_v, b.delta_v)
        self.assertEqual(a.lucro_projetado - b.lucro_projetado, 10000)

    def test_aumento_custo_diario_reduz_delta_v(self):
        a, b = delta_case(), delta_case(custo_diario_racao_energia=121)
        self.assertEqual(a.delta_v - b.delta_v, 10)

    def test_crescimento_entre_biometrias(self):
        self.assertAlmostEqual(engine.calcular_ganho_diario(10, 12, 10), 0.2)
        self.assertAlmostEqual(engine.calcular_ganho_semanal(0.2), 1.4)

    def test_clifford_interpolacao_exata_implementada(self):
        # Caracterização dos 5 nós atuais, não validação da tabela técnica completa.
        self.assertAlmostEqual(engine.taxa_alimentar_clifford(3.5), 6.10)

    def test_tabela_customizada_nao_ordenada(self):
        self.assertAlmostEqual(engine.taxa_alimentar(2, [(3, 7), (1, 9.5)]), 8.25)

    def test_biomassa_zero_receita_zero_margem_indisponivel(self):
        r = engine.calcular_metricas_economicas([100], 0, 25)
        self.assertEqual(r.receita_bruta, 0)
        self.assertEqual(r.lucro_operacional, -100)
        self.assertIsNone(r.margem_operacional_pct)

    def test_prejuizo_preserva_valor_negativo(self):
        r = engine.calcular_metricas_economicas([30000], 1000, 25)
        self.assertEqual(r.lucro_operacional, -5000)
        self.assertEqual(r.margem_operacional_pct, -20)

    def test_roa_roe_com_prejuizo(self):
        self.assertEqual(engine.calcular_roa(-15000, 100000), -15)
        self.assertEqual(engine.calcular_roe(-15000, 50000), -30)

    def test_hiperdensidade_no_limite(self):
        self.assertFalse(engine.verificar_hiperdensidade(50))
        self.assertTrue(engine.verificar_hiperdensidade(50.001))


class TestAlertas(unittest.TestCase):
    def test_o2_abaixo_2_5(self):
        self.assertEqual(alerts.classificar_oxigenio(2.499), enums.ClassificacaoOxigenio.EMERGENCIA)

    def test_o2_exatamente_2_5(self):
        self.assertEqual(alerts.classificar_oxigenio(2.5), enums.ClassificacaoOxigenio.ALERTA)

    def test_o2_abaixo_4(self):
        self.assertEqual(alerts.classificar_oxigenio(3.999), enums.ClassificacaoOxigenio.ALERTA)

    def test_o2_exatamente_4(self):
        self.assertEqual(alerts.classificar_oxigenio(4), enums.ClassificacaoOxigenio.NORMAL)

    def test_comportamento_emergencia_com_o2_normal(self):
        r = alerts.gerar_alerta_oxigenio(5, enums.ComportamentoCamarao.FLOR_DAGUA_BOQUEANDO, "viv-teste")
        self.assertEqual(r.nivel, alerts.NivelAlerta.CRITICO)
        self.assertEqual(r.viveiro_id, "viv-teste")

    def test_o2_normal_sem_alerta(self):
        self.assertIsNone(alerts.gerar_alerta_oxigenio(5, enums.ComportamentoCamarao.NORMAL_FUNDO, "v"))

    def test_intervalo_biometria_15_dias(self):
        today = date(2026, 10, 13)
        self.assertIsNone(alerts.verificar_intervalo_biometria(today-timedelta(days=15), today))

    def test_intervalo_biometria_16_dias(self):
        today = date(2026, 10, 13)
        self.assertEqual(alerts.verificar_intervalo_biometria(today-timedelta(days=16), today).codigo,
                         "BIOMETRIA_ATRASADA")

    def test_sobras_interrompidas_nao_sao_consecutivas(self):
        self.assertIsNone(alerts.verificar_sobras_consecutivas(
            ["SOBRA_EXCESSIVA", "SOBRA_EXCESSIVA", "SEM_SOBRA", "SOBRA_EXCESSIVA"]))

    def test_tres_sobras_consecutivas(self):
        self.assertEqual(alerts.verificar_sobras_consecutivas(["SOBRA_EXCESSIVA"]*3).codigo,
                         "SOBRAS_EXCESSIVAS_CONSECUTIVAS")

    def test_aeracao_limite_75_pct(self):
        self.assertIsNone(alerts.verificar_aeracao_noturna(75, 3000, 2))
        self.assertEqual(alerts.verificar_aeracao_noturna(74.99, 3000, 2).codigo,
                         "AERACAO_INSUFICIENTE")

    def test_aeracao_fora_horario(self):
        self.assertIsNone(alerts.verificar_aeracao_noturna(50, 3000, 6))


class TestValidacao(unittest.TestCase):
    # Os testes de rejeição usam os limites declarados pelos próprios schemas.
    # Defaults somente devem ser aplicados se autorizados; não a zero explícito.
    def test_viveiro_area_negativa_rejeitada(self):
        with self.assertRaises(ValidationError):
            ponds.ViveiroCreate(identificacao="V1", area_util_m2=-1)

    def test_viveiro_area_zero_rejeitada(self):
        with self.assertRaises(ValidationError):
            ponds.ViveiroCreate(identificacao="V1", area_util_m2=0)

    def test_viveiro_area_obrigatoria(self):
        with self.assertRaises(ValidationError):
            ponds.ViveiroCreate(identificacao="V1")

    def test_viveiro_alias_valido(self):
        r = ponds.ViveiroCreate(nome="V1", area_m2=2000)
        self.assertEqual(r.area_util_m2, 2000)
        self.assertEqual(r.identificacao, "V1")

    def test_custo_negativo_rejeitado(self):
        with self.assertRaises(ValidationError):
            costs.CustoCreate(descricao="Ração", valor_rs=-1)

    def test_custo_zero_rejeitado(self):
        with self.assertRaises(ValidationError):
            costs.CustoCreate(descricao="Ração", valor_rs=0)

    def test_custo_valor_obrigatorio(self):
        with self.assertRaises(ValidationError):
            costs.CustoCreate(descricao="Ração")

    def test_custo_alias_valido(self):
        r = costs.CustoCreate(descricao="Ração", valor=123.45, categoria="RACAO")
        self.assertEqual(r.valor_rs, 123.45)
        self.assertEqual(r.categoria, enums.CategoriaCusto.RACAO)

    def test_biometria_amostra_negativa_rejeitada(self):
        with self.assertRaises(ValidationError):
            bio.BiometriaCreate(peso_medio_g=10, quantidade_amostrada=-1)

    def test_biometria_amostra_zero_rejeitada(self):
        with self.assertRaises(ValidationError):
            bio.BiometriaCreate(peso_medio_g=10, quantidade_amostrada=0)

    def test_biometria_uniformidade_zero_preservada(self):
        r = bio.BiometriaResponse.model_validate(dict(
            id=uuid.uuid4(), ciclo_id=uuid.uuid4(), data_medicao=date(2026, 10, 13),
            peso_medio_g=10, quantidade_amostrada=30,
            uniformidade_percentual=0, created_at=datetime(2026, 10, 13)))
        self.assertEqual(r.uniformidade_percentual, 0)
        self.assertEqual(r.uniformidade_percent, 0)

    def test_biometria_uniformidade_fora_faixa(self):
        with self.assertRaises(ValidationError):
            bio.BiometriaCreate(peso_medio_g=10, uniformidade_percentual=101)

    def test_biometria_peso_zero_rejeitado(self):
        with self.assertRaises(ValidationError):
            bio.BiometriaCreate(peso_medio_g=0)

    def test_horizonte_canonico_invalido(self):
        with self.assertRaises(ValidationError):
            simulations.SimulacaoRequest(dias_horizonte=8)

    def test_horizonte_canonico_valido(self):
        self.assertEqual(simulations.SimulacaoRequest(dias_horizonte=10).dias_horizonte, 10)


class TestConfiabilidadeSuiteAntiga(unittest.TestCase):
    def test_tc001_nao_esconde_falha_quando_registro_nao_tem_id(self):
        """Executa só a função original, com HTTP falso e nenhuma rede."""
        path = BACKEND / "testsprite_tests/TC001_test_authentication_api_login_with_valid_credentials.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                        and n.name == "test_authentication_api_login_with_valid_credentials")
        class FakeResponse:
            status_code = 500
            text = "falha simulada de cadastro"
        fake_requests = SimpleNamespace(post=lambda *a, **k: FakeResponse())
        namespace = dict(requests=fake_requests, uuid=uuid, RequestException=RuntimeError,
                         BASE_URL="http://offline.invalid", REGISTER_PATH="/register",
                         LOGIN_PATH="/login", TIMEOUT=1)
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"), namespace)
        with self.assertRaises(AssertionError):
            namespace[function.name]()


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    import numpy
    import pydantic
    checked_sources = [
        "src/models/enums.py", "src/services/decision_engine.py",
        "src/services/alert_engine.py", "src/schemas/biometria.py",
        "src/schemas/custo.py", "src/schemas/viveiro.py",
        "src/schemas/simulacao.py",
        "testsprite_tests/TC001_test_authentication_api_login_with_valid_credentials.py",
    ]
    summary = dict(
        executed_at_utc=datetime.now(timezone.utc).isoformat(),
        python=sys.version,
        dependencies=dict(numpy=numpy.__version__, pydantic=pydantic.__version__),
        source_sha256={relative: hashlib.sha256((BACKEND / relative).read_bytes()).hexdigest()
                       for relative in checked_sources},
        backend=str(BACKEND), tests_run=result.testsRun,
        passed=result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
        failures=[dict(test=str(t), traceback=tb) for t, tb in result.failures],
        errors=[dict(test=str(t), traceback=tb) for t, tb in result.errors],
        skipped=[dict(test=str(t), reason=r) for t, r in result.skipped],
        scope="Somente funções, schemas e reprodução offline do TC001; sem HTTP/banco/fuzzy",
    )
    (OUTPUT / "resultado_regressoes.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(0 if result.wasSuccessful() else 1)
