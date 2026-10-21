# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projeto

SAD Carcinicultura — sistema de apoio à decisão para cultivo de camarão (*Litopenaeus vannamei*). Monorepo com `backend/` (FastAPI) e `frontend/` (Next.js). Código, comentários, mensagens de commit e UI em português do Brasil.

Regras do projeto (de `.agents/rules/`):
- A fonte de verdade dos requisitos é `documentacao_base/documento_de_requisitos_de_software.md` — consulte-a para dúvidas e para conferir aderência. Atenção: os códigos RF/RN citados nos comentários do código seguem uma numeração antiga e **não** batem com a do documento atual.
- Novas telas devem seguir o visual das imagens em `inspiracao/` (sidebar navy `#0c1427`, fundo `#f8fafc`, cards brancos).

## Comandos

Backend (rodar de dentro de `backend/`, pois `.env` é lido relativo ao diretório atual; venv em `backend/.venv`, Python 3.11):

```bash
.venv/Scripts/python.exe -m uvicorn src.main:app --reload --port 8000   # API + Swagger em /docs
.venv/Scripts/python.exe -m pytest tests -q                              # todos os testes
.venv/Scripts/python.exe -m pytest tests/test_decision_engine.py::test_densidade_estocagem   # um teste
.venv/Scripts/python.exe -m src.seed                                     # carga de exemplo (viveiros/preços)
```

Frontend (dentro de `frontend/`):

```bash
npm run dev        # http://localhost:3000 — exige o backend em 127.0.0.1:8000
npm run build
npm run lint       # eslint (há muitos erros pré-existentes de no-explicit-any/no-unused-vars)
npx tsc --noEmit
```

`frontend/AGENTS.md`: o Next.js 16 tem APIs diferentes do que você conhece — leia o guia em `frontend/node_modules/next/dist/docs/` antes de escrever código Next (ex.: middleware agora é `proxy.ts`).

## Configuração e banco

- `src/config.py` (pydantic-settings) lê `backend/.env`; modelo em `backend/.env.example`. Sem `DATABASE_URL`, usa `sqlite:///./local_dev.db`. Produção usa Postgres/Supabase via **pg8000** (driver síncrono).
- Se o banco remoto falhar na inicialização, a app aborta, a menos que `DB_FALLBACK_SQLITE=true`.
- Não há migrações: `init_db()` (`src/database.py`) roda `Base.metadata.create_all` e cria organização, propriedade, usuários de demonstração (senha `senha123`, só se ainda não existirem) e tabela de preços — **somente quando `APP_DEBUG=true`**. Com `APP_DEBUG=false` é obrigatório definir `JWT_SECRET_KEY`. `create_all` não altera tabelas existentes; mudanças de coluna exigem ajuste manual do banco.
- Testes em `backend/tests/`: `test_decision_engine.py`/`test_regressoes_sad.py` são unitários; `test_api_*.py` sobem a API via `TestClient`. O `conftest.py` define as variáveis de ambiente (SQLite temporário, `SUPERADMIN_EMAILS=admin@sad.com`) **antes** de importar `src` e expõe as fixtures `client`, `gestor`, `admin`, `campo`, `vigia` (headers já autenticados com as contas seed), `login`, `novo_viveiro` e `novo_ciclo`. O banco é compartilhado na sessão: use `unico()` para identificadores.

## Arquitetura do backend

Camadas em `backend/src/`: `models/` (SQLAlchemy 2, `Mapped`) → `schemas/` (Pydantic v2) → `routers/` (um por recurso, todos registrados em `main.py`) → `services/` (regras de negócio puras).

- **Sessão síncrona**: `get_db()` faz `commit` automático ao fim da requisição e `rollback` em erro. Os routers costumam só `db.flush()`; alguns (organizações, propriedades, tabelas alimentares) chamam `db.commit()` explicitamente. Os handlers são `async def` mesmo usando sessão síncrona.
- Todos os modelos herdam `AuditMixin` (`models/base.py`): `id` UUID, `created_at`, `updated_at`. Os relacionamentos usam `lazy="selectin"`, então carregar um ciclo traz biometrias, manejos, custos, simulações e rondas.
- **Hierarquia de domínio**: Organização → Propriedade → Viveiro → CicloProdutivo → (Biometria, ManejoAlimentar, CustoOperacional, SimulacaoDespesca, RondaNoturna → MonitoramentoAerador). Não há filtro por organização nas consultas.
- **Rotas aninhadas e globais**: biometrias, manejos, custos e simulação têm um router sob `/api/v1/ciclos/{ciclo_id}/...` (usado pelo frontend) e um `global_router` (`/api/v1/biometrias`, `/manejos`, `/custos`, `/simulacao`) criado para os testes do TestSprite.
- **Schemas tolerantes**: vários schemas têm `model_validator(mode="before")` que aceitam aliases (`data`, `valor`, `nome`, `area`…) e preenchem campos virtuais na resposta. Ao mudar um campo, verifique o `populate_virtual_fields` / `map_aliases` correspondente.
- **RBAC**: papéis `CAMPO`, `VIGIA`, `GESTOR` (`models/enums.py`). Proteja rotas com `Depends(has_role([...]))` de `services/auth_service.py` (ou os atalhos de `src/dependencies.py`). JWT HS256 carrega `sub`, `email`, `role`, `nome`. "Superadmin" = GESTOR cujo e-mail está na variável `SUPERADMIN_EMAILS` (`auth_service.is_superadmin` / `require_superadmin`); o login e o `/auth/me` devolvem `is_superadmin`, que o frontend guarda em `sad_user`. O auto-cadastro público cria contas CAMPO inativas até um GESTOR aprovar.
- **Auditoria**: chame `services/audit.registrar_auditoria(db, acao, entidade, registro_id, usuario, dados_anteriores, dados_novos)` nas mutações relevantes (hoje feito em ciclos, custos, organizações, propriedades e tabelas alimentares).

### Motores de decisão (`services/`)
- `decision_engine.py`: fórmulas zootécnicas e econômicas — densidade, população/biomassa, FCA e sua classificação, taxa alimentar por interpolação (tabela de Clifford 1992 ou pontos de uma `TabelaAlimentar`), métricas econômicas, ROA/ROE, e o algoritmo **ΔV** (`simular_delta_v`) que compara o lucro projetado num horizonte de 7/10/15 dias com o lucro de despescar hoje.
- `fuzzy_engine.py`: sistema scikit-fuzzy (construído uma vez, singleton) que estima o ajuste de sobrevivência a partir de consumo relativo, nível de sobra na bandeja e tendência de crescimento. Cada `POST` de manejo alimentar roda a inferência e grava `taxa_sobrevivencia_estimada_fuzzy`; o valor mais recente é a sobrevivência usada por métricas, recomendação e simulação. Se nenhuma regra disparar, retorna o fallback `-0.5`.
- `alert_engine.py`: classificação de O₂ e alertas (aeração, biometria atrasada, sobras consecutivas, ΔV negativo).
- `routers/ciclos.py::metricas_atuais` é o ponto que consolida tudo (densidade, sobrevivência, biomassa, FCA, ração sugerida, financeiro); os dados financeiros só vão para GESTOR.

## Arquitetura do frontend

- App Router com uma área por papel: `/gestor/*` (sidebar), `/campo/*` e `/vigia/*` (mobile-first), `/admin` (superadmin). Cada `layout.tsx` é client component e redireciona para `/login` se o papel em `localStorage` não bater; não há proteção de rota no servidor.
- `src/lib/api.ts` é o único cliente HTTP: `apiFetch` usa o caminho relativo `/api/v1`, injeta o Bearer token de `localStorage` (`sad_token`, `sad_user`) e, em 401, limpa a sessão e vai para `/login`. `next.config.ts` faz o rewrite de `/api/*` para `http://127.0.0.1:8000` e redireciona atalhos (`/viveiros` → `/gestor/viveiros`, etc.).
- Componentes de UI próprios em `src/components/ui/` (estilo shadcn com `cva` + `tailwind-merge`, via `cn()` em `src/lib/utils.ts`), toasts globais via `toast` de `components/ui/toast.tsx`. Tailwind v4 com tokens em `src/app/globals.css`. Gráficos com Recharts.

## Testes E2E (TestSprite)

`backend/testsprite_tests/` e `frontend/testsprite_tests/` contêm planos e scripts gerados pelo TestSprite (MCP). Os relatórios dessas pastas não são confiáveis como evidência: marcam como aprovadas funções que não existem (ex.: registro de vendas).
