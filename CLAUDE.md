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
.venv/Scripts/python.exe -m alembic upgrade head                         # aplica migrações (produção)
.venv/Scripts/python.exe -m alembic revision --autogenerate -m "descricao" # nova migração após mudar modelos
.venv/Scripts/python.exe -m alembic check                                # banco difere dos modelos?
```

Frontend (dentro de `frontend/`):

```bash
npm run dev        # http://localhost:3000 — exige o backend em 127.0.0.1:8000
npm run build
npm run lint       # eslint (0 erros; mantenha assim)
npx tsc --noEmit
```

`frontend/AGENTS.md`: o Next.js 16 tem APIs diferentes do que você conhece — leia o guia em `frontend/node_modules/next/dist/docs/` antes de escrever código Next (ex.: middleware agora é `proxy.ts`).

## Configuração e banco

- `src/config.py` (pydantic-settings) lê `backend/.env`; modelo em `backend/.env.example`. Sem `DATABASE_URL`, usa `sqlite:///./local_dev.db`. Produção usa Postgres/Supabase via **pg8000** (driver síncrono).
- Se o banco remoto falhar na inicialização, a app aborta, a menos que `DB_FALLBACK_SQLITE=true`.
- Esquema versionado com **Alembic** (`backend/alembic.ini`, `backend/migrations/`, revisões 0001–0011; o `env.py` usa o engine de `src.database`, com `render_as_batch` no SQLite). Toda mudança de modelo precisa de uma migração. Com `APP_DEBUG=true`, `init_db()` aplica as migrações (`executar_migracoes`) e cria organização, propriedade, usuários de demonstração (senha `senha123`, só se não existirem), tabela de preços e tabela alimentar padrão. Bancos antigos sem `alembic_version` recebem as tabelas ausentes e são marcados na revisão `0001`. Em produção rode `alembic upgrade head`. Com `APP_DEBUG=false` é obrigatório definir `JWT_SECRET_KEY`.
- No SQLite, UUIDs são gravados como 32 dígitos hexadecimais sem hífen e as chaves estrangeiras são aplicadas (`PRAGMA foreign_keys=ON`); scripts que escrevem direto no banco devem seguir esse formato.
- Testes em `backend/tests/`: `test_decision_engine.py`/`test_regressoes_sad.py` são unitários; `test_api_*.py` sobem a API via `TestClient`. O `conftest.py` define as variáveis de ambiente (SQLite temporário, `SUPERADMIN_EMAILS=admin@sad.com`) **antes** de importar `src` e expõe as fixtures `client`, `gestor`, `admin`, `campo`, `vigia` (headers já autenticados com as contas seed), `login`, `novo_viveiro` e `novo_ciclo`. `novo_ciclo` (e o helper `planejar_e_povoar(client, headers, viveiro_id, ...)`) planeja o ciclo, marca todas as etapas do preparo como `NAO_REALIZADA` e povoa, devolvendo o ciclo ATIVO; testes que precisam de ciclo ativo devem usá-los, pois `POST /ciclos/` sozinho só planeja. O banco é compartilhado na sessão: use `unico()` para identificadores.

## Arquitetura do backend

Camadas em `backend/src/`: `models/` (SQLAlchemy 2, `Mapped`) → `schemas/` (Pydantic v2) → `routers/` (um por recurso, todos registrados em `main.py`) → `services/` (regras de negócio puras).

- **Sessão síncrona**: `get_db()` faz `commit` automático ao fim da requisição e `rollback` em erro. Os routers costumam só `db.flush()`; alguns (organizações, propriedades, tabelas alimentares) chamam `db.commit()` explicitamente. Handlers e dependências são `def` síncronos (o FastAPI os executa em threadpool); não use `async def` com a sessão síncrona, pois bloquearia o event loop. Exceção: `dados_da_requisicao` em `routers/auth.py`, que lê o corpo bruto do login/cadastro.
- Todos os modelos herdam `AuditMixin` (`models/base.py`): `id` UUID, `created_at`, `updated_at`. Coleções (biometrias, manejos, custos, ciclos de um viveiro etc.) são carregadas sob demanda (lazy padrão); só relações muitos-para-um usadas nas respostas usam `lazy="selectin"`. Evite reintroduzir `selectin` em coleções: ele carregava todo o histórico em cascata.
- **Hierarquia de domínio**: Organização → (Propriedade) → Viveiro → CicloProdutivo → (Biometria, ManejoAlimentar, CustoOperacional, EtapaPreparo, VendaCiclo, ConsumoInsumo, SimulacaoDespesca, RondaNoturna → MonitoramentoAerador, Alerta). Os insumos ficam direto na organização: Organização → Insumo → (CompraInsumo, ConsumoInsumo).
- **Isolamento por organização** (`services/escopo.py`): o dono de todo dado operacional é `Viveiro.organizacao_id`; usuários, preços (`TabelaPrecoMercado`), tabelas alimentares (`organizacao_id` NULL = referência global somente leitura) e logs de auditoria também têm `organizacao_id`. Routers aninhados em `/ciclos/{ciclo_id}/...` declaram `dependencies=[Depends(verificar_ciclo_da_organizacao)]`; rotas por ID usam `ciclo_da_organizacao`/`viveiro_da_organizacao` (404 para outra organização) e listas filtram com `ids_ciclos_da_organizacao`. Toda rota nova que receba um ID ou liste dados precisa aplicar o escopo; `tests/test_isolamento_organizacao.py` cobre o acesso cruzado. Rotas de `/admin` restritas por `require_superadmin` são globais.
- **Rotas aninhadas e globais**: biometrias, manejos, custos e simulação têm um router sob `/api/v1/ciclos/{ciclo_id}/...` (usado pelo frontend) e um `global_router` (`/api/v1/biometrias`, `/manejos`, `/custos`, `/simulacao`) criado para os testes do TestSprite.
- **Schemas tolerantes**: vários schemas têm `model_validator(mode="before")` que aceitam aliases (`data`, `valor`, `nome`, `area`…) e preenchem campos virtuais na resposta. Ao mudar um campo, verifique o `populate_virtual_fields` / `map_aliases` correspondente.
- **RBAC**: papéis `CAMPO`, `VIGIA`, `GESTOR` (`models/enums.py`). Proteja rotas com `Depends(has_role([...]))` de `services/auth_service.py` (ou os atalhos de `src/dependencies.py`). JWT HS256 carrega `sub`, `email`, `role`, `nome`. "Superadmin" = GESTOR cujo e-mail está na variável `SUPERADMIN_EMAILS` (`auth_service.is_superadmin` / `require_superadmin`); o login e o `/auth/me` devolvem `is_superadmin`, que o frontend guarda em `sad_user`. O auto-cadastro público cria contas CAMPO inativas até um GESTOR aprovar.
- **Auditoria**: chame `services/audit.registrar_auditoria(db, acao, entidade, registro_id, usuario, dados_anteriores, dados_novos)` nas mutações relevantes (hoje feito em ciclos, custos, insumos, compras, usos de insumo, vendas, etapas do preparo, organizações, propriedades e tabelas alimentares).

### Motores de decisão (`services/`)
- `decision_engine.py`: fórmulas zootécnicas e econômicas — densidade, população/biomassa, FCA e sua classificação, taxa alimentar por interpolação (tabela de Clifford 1992 ou pontos de uma `TabelaAlimentar`), métricas econômicas, ROA/ROE, e o algoritmo **ΔV** (`simular_delta_v`) que compara o lucro projetado num horizonte de 7/10/15 dias com o lucro de despescar hoje. `GET /simulacao/comparativo` varre 30 dias e devolve também o `melhor_dia`. O custo diário estimado (`estimar_custo_diario`) usa só custos de fase CULTIVO; PREPARO e DESPESCA entram no custo total e no lucro, mas não nele.
- `fuzzy_engine.py`: sistema scikit-fuzzy (construído uma vez, singleton) que estima o ajuste de sobrevivência a partir de consumo relativo, nível de sobra na bandeja e tendência de crescimento. Cada `POST` de manejo alimentar roda a inferência e grava `taxa_sobrevivencia_estimada_fuzzy`; o valor mais recente é a sobrevivência usada por métricas, recomendação e simulação. O ΔS é **semanal**: o router aplica a fração proporcional aos dias desde o manejo anterior (`ajuste_no_periodo`). A base de regras é completa (consumo × sobra + crescimento); `tests/test_fuzzy.py` verifica a cobertura de todo o universo.
- `alert_engine.py`: regras de alerta (O₂, aeração noturna, energia/aeradores, biometria atrasada, sobras consecutivas, ΔV negativo). O `POST` de ronda grava os alertas disparados na tabela `alertas` (modelo `Alerta`, status ABERTO/RESOLVIDO) e os devolve na resposta; `routers/alertas.py` lista e resolve. O frontend envia `data_hora_ronda` com o offset local (`localInputParaIso`) para que a janela 00h–05h30 use o horário da fazenda.
- `routers/ciclos.py::metricas_atuais` é o ponto que consolida tudo (densidade, sobrevivência, biomassa, FCA, ração sugerida, financeiro); os dados financeiros só vão para GESTOR.

### Ciclo, insumos, vendas e financeiro
- **Ciclo (planejar → povoar)**: `POST /ciclos/` só **planeja** (viveiro, data prevista, tabela alimentar opcional; corpo com campos desconhecidos dá 422) e cria o ciclo PLANEJADO com as etapas sugeridas do preparo (`/ciclos/{id}/etapas-preparo`). `POST /ciclos/{id}/povoar` (data real, pós-larvas, custo de aquisição) grava o custo POS_LARVAS e ativa o ciclo, mas é recusado enquanto houver etapa PENDENTE ou EM_ANDAMENTO (cada uma precisa estar CONCLUIDA ou NAO_REALIZADA). `PATCH /ciclos/{id}/planejamento` reagenda e `POST /ciclos/{id}/cancelar` cancela (só PLANEJADO). Um viveiro tem no máximo um ciclo aberto (PLANEJADO, ATIVO ou PAUSADO: `regras_ciclo.ciclo_aberto_do_viveiro`). Ciclo PLANEJADO não tem pós-larvas (`quantidade_pos_larvas` nulo): métricas e manejos exigem pós-larvas (`exigir_povoamento`) e biometrias, rondas e simulação exigem ciclo ativo.
- **Insumos** (`routers/insumos.py`, `usos_insumo.py`, `services/insumos.py`): cadastro por organização (RACAO e POS_LARVAS não são categorias válidas), compras por insumo e uso por ciclo. O preço é a **média ponderada móvel** das compras; cada uso gera um `CustoOperacional` (quantidade × preço médio na data, fase PREPARO/CULTIVO/DESPESCA) ligado ao uso. Qualquer compra ou uso com data passada chama `reprocessar_insumo`, que reaplica compras e usos em ordem de data. Uso sem compra anterior fica pendente de valor (sem custo) e bloqueia o encerramento (409); uso sem saldo é aceito. O custo gerado não pode ser excluído por `/custos` (409): exclua o uso. Data passada em compra, uso e venda exige `retroativo=true` (`services/regras_data.py`); data futura é sempre recusada. Valores em reais só para GESTOR; CAMPO vê saldo e usos sem valores, VIGIA só nome e unidade e cria usos.
- **Vendas e desbaste** (`routers/vendas.py`, `services/populacao.py`): um ciclo tem várias vendas (DESBASTE e DESPESCA_FINAL). A população atual vem de `populacao_vigente` (pós-larvas × sobrevivência − animais vendidos até a data), usada por métricas, manejos, rondas e simulação; a FCA soma a biomassa vendida, e `services/sobrevivencia.py` desconta as vendas para o desbaste não parecer mortalidade. `biomassa_colhida_kg` e `receita_real_rs` do ciclo são a soma das vendas, mantidas por `sincronizar_totais_do_ciclo`; `POST /ciclos/{id}/encerrar` exige ao menos uma venda de despesca final (ou cria uma com os valores do corpo).
- **Financeiro e histórico** (`services/historico.py::resumo_do_ciclo`): `GET /ciclos/{id}/financeiro` (só GESTOR) traz custos por fase e categoria, vendas, **lucro realizado** (receita das vendas − custos lançados; definitivo ao finalizar), **lucro estimado se despescar hoje** e custo por kg; sempre rotule qual lucro está sendo mostrado. `GET /viveiros/{id}/historico` lista os ciclos do viveiro com o resumo de cada um (campos em reais `None` para CAMPO e VIGIA).

## Arquitetura do frontend

- App Router com uma área por papel: `/gestor/*` (sidebar), `/campo/*` e `/vigia/*` (mobile-first, também acessíveis ao GESTOR), `/admin` (superadmin). `src/proxy.ts` (o "middleware" do Next 16) redireciona antes de renderizar com base no cookie `sad_papel`, gravado por `setStoredUser`; os layouts leem a sessão com `useSessao()` (`lib/sessao.ts`, via `useSyncExternalStore`). Ambos são apenas navegação: a autorização real é da API.
- `src/lib/api.ts` é o único cliente HTTP, tipado com as interfaces de `lib/types.ts` (sem `any`; erros capturados via `mensagemErro(err, padrao)` de `lib/utils.ts`): `apiFetch` usa o caminho relativo `/api/v1`, injeta o Bearer token de `localStorage` (`sad_token`, `sad_user`) e, em 401, limpa a sessão e vai para `/login`. `next.config.ts` faz o rewrite de `/api/*` para `BACKEND_URL` (padrão `http://127.0.0.1:8000`; ver `frontend/.env.example`) e redireciona atalhos (`/viveiros` → `/gestor/viveiros`, etc.).
- Componentes de UI próprios em `src/components/ui/` (estilo shadcn com `cva` + `tailwind-merge`, via `cn()` em `src/lib/utils.ts`), toasts globais via `toast` de `components/ui/toast.tsx`. Tailwind v4 com tokens em `src/app/globals.css`. Gráficos com Recharts.

## Testes E2E (TestSprite)

`backend/testsprite_tests/` e `frontend/testsprite_tests/` contêm planos e scripts gerados pelo TestSprite (MCP). Os relatórios dessas pastas não são confiáveis como evidência: marcam como aprovadas funções que não existiam à época, e os scripts ainda usam o antigo `POST /ciclos/` com pós-larvas (agora só planeja).
