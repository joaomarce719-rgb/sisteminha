# Relatório Executivo de Testes Automatizados TestSprite — Frontend SAD Carcinicultura

**Data de Execução:** 14 de Outubro de 2026  
**Ambiente:** Frontend Next.js 16 + React 19 (App Router) + Backend FastAPI integrado ao Supabase PostgreSQL  
**Plano de Testes:** 30 Casos de Teste Ponta a Ponta (`TC001` a `TC030`)  
**Resultado Geral:** **22 APROVADOS (73.3%)**, 6 BLOQUEADOS (20%), 2 FALHAS (6.7%)  
**Taxa de Sucesso dos Testes Executados:** **91.7%** (22 aprovados de 24 testes executados)

---

## 1️⃣ Document Metadata

* **Projeto:** SAD Carcinicultura — Interface Web (Frontend)
* **Data:** 14/10/2026
* **Automação:** TestSprite MCP Runner com Playwright Headless
* **Banco de Dados Conectado:** Supabase PostgreSQL 17 (`aws-0-us-west-2.pooler.supabase.com:6543`)
* **Backend de Suporte:** FastAPI 4.0.0 em `http://127.0.0.1:8000`
* **Frontend Testado:** Next.js Production Build em `http://localhost:3000`
* **Usuário de Teste Validado:** `testedoapp1@gmail.com` (Perfil `GESTOR`)

---

## 2️⃣ Requirement Validation Summary

### 🔐 Grupo 1: Autenticação, Controle de Acesso e RBAC (RF-014, RNF-012)
* **TC001 — Sign in and reach authorized landing area:** **PASSED**  
  *Login com credenciais corporativas autenticadas com sucesso e navegação imediata ao painel autorizado.*
* **TC003 — Reject invalid sign-in credentials:** **FAILED**  
  *Submissão com credenciais inválidas bloqueia o acesso, mas o componente Toast de erro tem tempo de exibição curto que Playwright não capturou a tempo no DOM.*
* **TC024 — Assign a role to a user and save the change:** **PASSED**  
  *Gestão de usuários, alteração de permissões e persistência de papéis RBAC validados com sucesso.*

### 🦐 Grupo 2: Gestão de Viveiros e Ciclos Produtivos (RF-001, RF-002, RN-001)
* **TC004 — Start a stocking cycle successfully:** **PASSED**  
  *Abertura de ciclo produtivo com povoamento de pós-larvas e data de início.*
* **TC006 — Create a pond and start a stocking cycle:** **PASSED**  
  *Criação de novo viveiro escavado e vinculação imediata a um novo lote.*
* **TC007 — Create a pond and make it available for cycles:** **PASSED**  
  *Criação e disponibilização de viveiro no inventário da fazenda.*
* **TC023 — Edit a pond and preserve the updated record:** **PASSED**  
  *Edição de atributos físicos do viveiro com persistência no Supabase.*
* **TC028 — Edit a pond and inactivate it:** **PASSED**  
  *Inativação de viveiro e garantia de integridade histórica.*

### ⚖️ Grupo 3: Amostragem Biométrica e Manejo Alimentar (RF-007, RF-008, RN-004, RN-005)
* **TC005 — Register a biometric sampling and calculate indicators:** **PASSED**  
  *Coleta biométrica, peso médio, uniformidade percentual e ganho de peso.*
* **TC008 — Record biometry for an active cycle:** **PASSED**  
  *Registro rotineiro de amostragem em ciclo em andamento.*
* **TC011 — Register biometry for an active cycle:** **PASSED**  
  *Validação de formulário de biometria e sincronização de dados.*
* **TC013 — Register a biometric sample for an active cycle:** **PASSED**  
  *Lançamento e persistência de biomassa amostrada.*
* **TC015 — Record feeding and environmental measurements for an active cycle:** **PASSED**  
  *Lançamento de arraçoamento diário e parâmetros de qualidade de água.*
* **TC019 — Record an environmental measurement:** **PASSED**  
  *Registro de oxigênio dissolvido e variáveis ambientais.*
* **TC025 — Review and use the active feeding table for planning:** **PASSED**  
  *Consulta de tabelas alimentares ativas e cálculo da taxa diária de ração.*
* **TC027 — Update the active feeding table version:** **PASSED**  
  *Versionamento e atualização das tabelas de alimentação.*

### 💰 Grupo 4: Gestão Financeira, Custos e Comercialização (RF-011, RN-011)
* **TC014 — Register a sale and update profitability indicators:** **PASSED**  
  *Registro de despesca comercial e apuração de receita bruta.*
* **TC016 — Register a cost and update financial indicators:** **PASSED**  
  *Lançamento de custos operacionais (ração, energia, insumos) e atualização do DRE.*
* **TC017 — Enter costs and a sale and review updated financial indicators:** **PASSED**  
  *Cálculo de margem operacional, lucro bruto e custo total acumulado.*

### 📈 Grupo 5: Motor Bioeconômico de Decisão ΔV (RF-010, RN-007)
* **TC021 — Compare a modified simulation against the realized scenario:** **PASSED**  
  *Comparação de cenários preditivos com diferentes taxas de crescimento e preços de mercado.*
* **TC026 — Compare two cycles on the dashboard:** **PASSED**  
  *Visualização comparativa de desempenho bioeconômico entre lotes.*
* **TC029 — Keep simulation results from changing operational records:** **PASSED**  
  *Garantia de isolamento estrito: simulações não afetam nem corrompem registros de campo.*

### 🛡️ Grupo 6: Rastreabilidade, Auditoria e Governança (RF-027, RNF-017)
* **TC030 — Trace an indicator back to its inputs and versions:** **PASSED**  
  *Rastreabilidade completa de indicadores até suas fontes de dados e versões de tabela.*

---

## 3️⃣ Coverage & Matching Metrics

| Métrica | Valor Obtido |
|---|---|
| **Total de Testes Planejados** | 30 casos |
| **Testes Aprovados (PASSED)** | **22 casos (73.3%)** |
| **Testes Bloqueados por Rota (BLOCKED)** | 6 casos (20.0%) |
| **Testes Reprovados (FAILED)** | 2 casos (6.7%) |
| **Acurácia em Execuções Diretas** | **91.7%** (22 aprovados de 24 executados) |
| **Cobertura de Telas Principais** | 100% (Dashboard, Viveiros, Biometria, Manejo, Financeiro, Auditoria) |

---

## 4️⃣ Key Gaps / Risks

1. **Rotas com Alias e Redirecionamento (Causa dos 6 testes BLOCKED):**
   * Os testes `TC002`, `TC009`, `TC010`, `TC018`, `TC020` e `TC022` tentaram acessar rotas sem o prefixo `/gestor` (por exemplo: acessaram `/viveiros` ou `/simulacao` diretamente em vez de `/gestor/viveiros` e `/gestor/simulacao`).
   * **Recomendação:** Adicionar redirects no Next.js (`next.config.ts`) mapeando `/viveiros` ➔ `/gestor/viveiros` e `/simulacao` ➔ `/gestor/simulacao`.

2. **Captura de Mensagens de Erro pelo Playwright (TC003 e TC012):**
   * O sistema exibe o alerta de erro usando `toast.error`, que pode desaparecer antes da asserção do Playwright quando executado em modo headless de alta velocidade.
   * **Recomendação:** Garantir tempo de exibição mínimo de 5 segundos para toasts ou manter mensagem de texto persistente no DOM.
