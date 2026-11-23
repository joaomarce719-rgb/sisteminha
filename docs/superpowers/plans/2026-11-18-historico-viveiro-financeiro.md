# Histórico do viveiro, insumos, vendas e Financeiro — Plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Registrar, por viveiro e ciclo, o preparo antes do cultivo, os insumos (com custo médio), a ração, os desbastes e a despesca, e calcular a lucratividade real do ciclo.

**Architecture:** Camadas atuais (`models/` → `schemas/` → `routers/` → `services/`). Insumos geram custos operacionais automaticamente, então financeiro, custo diário e simulador seguem funcionando. Vendas passam a ser a fonte única da receita, e uma função central de população desconta os animais vendidos. O ciclo nasce `PLANEJADO` e só vira `ATIVO` pela ação "povoar".

**Tech Stack:** FastAPI síncrono, SQLAlchemy 2, Pydantic v2, Alembic, pytest (`TestClient`, SQLite temporário), Next.js 16, Tailwind v4.

**Spec:** `docs/superpowers/specs/2026-11-18-historico-viveiro-financeiro-design.md` (ler junto; as seções citadas abaixo como §n são dela).

## Global Constraints

- Código, comentários, mensagens de commit e UI em português do Brasil.
- Migrações Alembic por etapa de entrega: **0009** (etapa 1), **0010** (etapa 2), **0011** (etapa 3). A 0008 já está aplicada no Supabase. Cada migração segue o padrão da `0008` (guarda com inspector, `batch_alter_table`).
- Colunas de fase, tipo e status são **texto** (`String`) validado por schema (`Literal`/enum Python), nunca enum nativo do Postgres.
- Toda rota nova que receba ID ou liste dados aplica o escopo por organização (`services/escopo.py`). Recurso de outra organização responde 404. Rotas aninhadas usam `dependencies=[Depends(verificar_ciclo_da_organizacao)]`.
- Mutações chamam `registrar_auditoria(db, acao, entidade, registro_id, usuario, dados_anteriores, dados_novos)`.
- Valores em reais só para GESTOR. Para CAMPO e VIGIA os campos de valor vêm `None` (mesmo padrão de `mostrar_financeiro` em `routers/ciclos.py::metricas_atuais`).
- Preço unitário de insumo com 4 casas (`Numeric(12,4)`); só o total do custo é arredondado a centavos.
- `RACAO` e `POS_LARVAS` não são aceitas como categoria de insumo.
- Data passada só com `retroativo=true` nas compras, usos de insumo e vendas (regra também na API). Data futura é sempre recusada. Custos manuais, biometrias e manejos existentes não mudam.
- No SQLite os UUIDs são gravados em 32 dígitos hexadecimais e as chaves estrangeiras são aplicadas.
- Handlers síncronos (`def`), sessão com `get_db()`; não usar `async def` com a sessão síncrona.
- Telas novas seguem `inspiracao/` (sidebar `#0c1427`, fundo `#f8fafc`, cards brancos) e `src/components/ui/`. Antes de escrever código Next, ler o guia em `frontend/node_modules/next/dist/docs/`.
- Fechamento de cada tarefa: backend `cd backend && .venv/Scripts/python.exe -m pytest tests -q` verde; frontend `cd frontend && npx tsc --noEmit` e `npm run lint` com 0 erros. Não há testes automatizados de frontend: a verificação de tela é manual (passos descritos em cada tarefa).

## Review Focus

Entradas que o spec implica e que mais prejudicam quem usa, da mais provável para a menos:

1. Desbaste que retira mais animais que a população estimada: população nunca negativa, FCA `None`, nenhuma divisão por zero (Tarefa 8).
2. Compra e uso na mesma data, e uso antes de qualquer compra: compra processa antes do uso; sem compra o uso fica pendente de valor (Tarefas 2 e 4).
3. Compra corrigida ou excluída que muda o custo de usos já lançados, inclusive em ciclo finalizado (Tarefa 4).
4. Ciclo planejado e abandonado que prende o viveiro: precisa de ação "cancelar planejamento" (Tarefa 12). O spec não previa esta ação; está neste plano e deve entrar no spec.
5. Recurso de outra organização (insumo, uso, venda, etapa, histórico) acessado por ID (testes de isolamento em cada tarefa de rota).

## Mapa de arquivos

Backend, novos: `models/insumo.py` (Insumo, CompraInsumo, ConsumoInsumo), `models/venda_ciclo.py`, `models/etapa_preparo.py`, `services/regras_data.py`, `services/insumos.py`, `services/populacao.py`, `services/historico.py`, `schemas/insumo.py`, `schemas/venda.py`, `schemas/etapa_preparo.py`, `schemas/financeiro.py`, `routers/insumos.py`, `routers/usos_insumo.py`, `routers/vendas.py`, `routers/etapas_preparo.py`, migrações 0009 a 0011. Registro em `main.py` e `models/__init__.py`.

Backend, alterados: `models/custo_operacional.py`, `models/ciclo_produtivo.py`, `services/regras_ciclo.py`, `services/decision_engine.py`, `services/sobrevivencia.py`, `routers/ciclos.py`, `routers/custos.py`, `routers/manejos.py`, `routers/rondas.py`, `routers/simulacao.py`, `routers/viveiros.py`, `schemas/ciclo.py`, `schemas/custo.py`, `tests/conftest.py`.

Frontend, novos: `components/ui/data-lancamento.tsx`, `app/gestor/insumos/page.tsx`, `components/insumos/uso-insumo-form.tsx`, `components/viveiro/*` (preparo, vendas, histórico), `app/campo/insumos/page.tsx`, `app/campo/preparo/page.tsx`. Alterados: `lib/api.ts`, `lib/types.ts`, `app/gestor/layout.tsx` (menu), `app/gestor/viveiros/[id]/page.tsx`, `app/gestor/financeiro/page.tsx`, `app/campo/layout.tsx`.

---

## Etapa 0 — Preparação

### Task 0: Branch e documentos

- [ ] **Step 1:** `git checkout -b feat/historico-viveiro-financeiro` (a partir da `main` atualizada).
- [ ] **Step 2:** Commit do design e do plano: `git add docs/superpowers && git commit -m "docs: design e plano de histórico do viveiro, insumos, vendas e financeiro"`.

---

## Etapa 1 — Insumos, compras, uso e custo médio

### Task 1: Fase nos custos, regra de data retroativa e tabelas de insumo (migração 0009)

**Files:**
- Create: `backend/src/services/regras_data.py`, `backend/src/models/insumo.py`, `backend/migrations/versions/0009_insumos_compras_usos_e_fase_dos_custos.py`
- Modify: `backend/src/services/regras_ciclo.py` (`validar_data_no_ciclo`), `backend/src/models/custo_operacional.py`, `backend/src/models/enums.py`, `backend/src/models/__init__.py`
- Test: `backend/tests/test_regras_data.py`

**Interfaces:**
- Produces:
  - `exigir_retroativo_para_data_passada(data: date, retroativo: bool, rotulo: str) -> None` (HTTPException 422 se `data > hoje`; 422 se `data < hoje` sem `retroativo`, mensagem contém "retroativo").
  - `validar_data_no_ciclo(ciclo, data_registro: date, rotulo: str, fase: str = "CULTIVO") -> None` (com `fase == "PREPARO"` não recusa data anterior ao povoamento).
  - `enums.FaseCusto(str, Enum)`: `PREPARO`, `CULTIVO`, `DESPESCA`.
  - Modelos: `Insumo(organizacao_id, nome, nome_chave, unidade_uso, categoria, ativo)` com `UniqueConstraint(organizacao_id, nome_chave)`; `CompraInsumo(insumo_id, data_compra, quantidade Numeric(14,4), valor_total_rs Numeric(12,2), fornecedor, observacao, retroativo)`; `ConsumoInsumo(ciclo_id, insumo_id, data_uso, quantidade Numeric(14,4), fase String(10), custo_id FK custos_operacionais SET NULL, preco_unitario_rs Numeric(12,4) null, preco_corrigido_rs Numeric(12,4) null, registrado_por FK usuarios SET NULL, observacao, retroativo, recalculado_em DateTime null)`; `CustoOperacional.fase String(10)` padrão `"CULTIVO"` (`server_default`).

- [ ] **Step 1: Write the failing tests** em `test_regras_data.py`: `test_hoje_sem_retroativo_passa`; `test_passada_sem_retroativo_da_422_citando_retroativo`; `test_passada_com_retroativo_passa`; `test_futura_da_422_mesmo_com_retroativo`; `test_preparo_aceita_data_anterior_ao_povoamento` (com `fase="PREPARO"` não levanta; sem `fase` levanta 422 "anterior ao povoamento").
- [ ] **Step 2: Run** `cd backend && .venv/Scripts/python.exe -m pytest tests/test_regras_data.py -q` — falha (ImportError).
- [ ] **Step 3: Implement** as duas funções e o parâmetro `fase`.
- [ ] **Step 4: Add** `FaseCusto`, os três modelos (registrar em `models/__init__.py`) e `CustoOperacional.fase`; escrever a migração 0009 (cria as três tabelas e a coluna `fase` com guardas).
- [ ] **Step 5: Verify migração** (esperado: sem erro e "No new upgrade operations detected."):
  `DATABASE_URL=sqlite:///./chk_tmp.db .venv/Scripts/python.exe -m alembic upgrade head && DATABASE_URL=sqlite:///./chk_tmp.db .venv/Scripts/python.exe -m alembic check; rm -f chk_tmp.db`
- [ ] **Step 6: Run** `pytest tests -q` — tudo verde.
- [ ] **Step 7: Commit** `feat(insumos): fase nos custos, regra de data retroativa e tabelas de insumo`.

### Task 2: Cálculo do preço médio (função pura)

**Files:**
- Create: `backend/src/services/insumos.py`
- Test: `backend/tests/test_insumos_preco_medio.py`

**Interfaces:**
- Produces (em `services/insumos.py`):
  - `@dataclass(frozen=True) EventoInsumo(id: UUID, tipo: Literal["COMPRA","USO"], data: date, criado_em: datetime, quantidade: float, valor_total_rs: float | None = None, preco_corrigido_rs: float | None = None)`
  - `@dataclass(frozen=True) ResultadoUso(uso_id: UUID, preco_unitario_rs: float | None, saldo_apos: float)` (`None` = pendente de valor)
  - `aplicar_preco_medio(eventos: list[EventoInsumo]) -> tuple[list[ResultadoUso], float | None, float]` → (resultado de cada uso, preço médio final, saldo final).

- [ ] **Step 1: Write the failing tests** (valores do §5.2):
  - `test_exemplo_da_cal`: compra 100 kg R$ 300; compra 100 kg R$ 400; uso 50 kg → preço do uso `3.50`, `saldo_apos == 150`; compra 150 kg R$ 750 → preço médio final `4.25`, saldo final `300`.
  - `test_compra_processa_antes_do_uso_na_mesma_data`.
  - `test_uso_sem_compra_anterior_fica_pendente` (`preco_unitario_rs is None`, `saldo_apos == -quantidade`).
  - `test_saldo_insuficiente_usa_ultimo_preco_medio_e_fica_negativo`: compra 100 kg R$ 300, uso 120 kg → preço `3.00`, `saldo_apos == -20`; em seguida compra 100 kg R$ 500 → preço médio `5.00` (saldo negativo é ignorado no cálculo do novo preço médio).
  - `test_preco_corrigido_vence_o_preco_medio`.
  - `test_ordem_por_data_depois_tipo_depois_criacao`: lista fora de ordem produz o mesmo resultado que a ordenada.
- [ ] **Step 2: Run** `pytest tests/test_insumos_preco_medio.py -q` — falha.
- [ ] **Step 3: Implement** `aplicar_preco_medio`: ordenar por `(data, 0 se COMPRA e 1 se USO, criado_em)`; na compra, `base = max(saldo, 0)` e `pm = (base * pm + valor) / (base + qtd)`; no uso, preço = `preco_corrigido_rs` ou `pm` (ou `None` se ainda não há compra), a saída não altera `pm`.
- [ ] **Step 4: Run** — passa.
- [ ] **Step 5: Commit** `feat(insumos): cálculo do preço médio ponderado móvel`.

### Task 3: Rotas de insumos e compras

**Files:**
- Create: `backend/src/schemas/insumo.py`, `backend/src/routers/insumos.py`
- Modify: `backend/src/main.py` (incluir `insumos.router`), `backend/src/services/escopo.py` (`insumo_da_organizacao`)
- Test: `backend/tests/test_api_insumos.py`

**Interfaces:**
- Consumes: `exigir_retroativo_para_data_passada`, modelos da Tarefa 1.
- Produces:
  - `escopo.insumo_da_organizacao(db, insumo_id: UUID, user) -> Insumo` (404 de outra organização).
  - Rotas (prefixo `/api/v1/insumos`): `POST ""` e `PUT /{id}` (GESTOR); `GET ""` (GESTOR, CAMPO, VIGIA; o VIGIA recebe só nome e unidade); `POST /{id}/compras`, `GET /{id}/compras`, `PUT /{id}/compras/{compra_id}`, `DELETE /{id}/compras/{compra_id}` (GESTOR). Compras chamam `services.insumos.reprocessar_insumo(db, insumo_id)` (definida na Tarefa 4; nesta tarefa o ponto de chamada existe como função com corpo `pass`, e a Tarefa 4 a implementa).
  - `InsumoCreate{nome, unidade_uso, categoria: CategoriaCusto = OUTROS}` (422 para `RACAO` e `POS_LARVAS`); `InsumoResponse{id, nome, unidade_uso, categoria, ativo, saldo: float | None, preco_medio_rs: float | None, saldo_negativo: bool | None}` (`preco_medio_rs` e `saldo_negativo` só para GESTOR; `saldo` não vai para o VIGIA); `CompraCreate{data_compra, quantidade > 0, valor_total_rs > 0, fornecedor?, observacao?, retroativo: bool = False}`.

- [ ] **Step 1: Write the failing tests** em `test_api_insumos.py`: `test_gestor_cria_insumo`; `test_nome_duplicado_sem_diferenciar_maiusculas_da_409`; `test_categoria_racao_e_pos_larvas_da_422`; `test_campo_lista_insumos_com_saldo_e_sem_preco` (`preco_medio_rs is None`); `test_vigia_lista_insumos_so_com_nome_e_unidade` (`saldo` e `preco_medio_rs` são `None`); `test_campo_nao_cria_insumo_nem_compra` (403); `test_compra_com_data_passada_exige_retroativo` (422 sem a marca, 201 com); `test_compra_atualiza_saldo_e_preco_medio_do_exemplo_da_cal` (após as duas primeiras compras do §5.2: `saldo == 200`, `preco_medio_rs == 3.5`); `test_insumo_de_outra_organizacao_da_404` (reutilizar a fixture de segunda organização de `tests/test_isolamento_organizacao.py`); `test_compras_ficam_na_auditoria`.
- [ ] **Step 2: Run** — falha (404 nas rotas).
- [ ] **Step 3: Implement** schemas, rotas e `insumo_da_organizacao`; saldo = soma das compras − soma dos usos; auditoria (`CRIAR_INSUMO`, `ATUALIZAR_INSUMO`, `CRIAR_COMPRA_INSUMO`, `ATUALIZAR_COMPRA_INSUMO`, `EXCLUIR_COMPRA_INSUMO`).
- [ ] **Step 4: Run** `pytest tests/test_api_insumos.py -q` — passa.
- [ ] **Step 5: Commit** `feat(insumos): cadastro de insumos e compras`.

### Task 4: Uso de insumo, custo automático e reprocessamento

**Files:**
- Create: `backend/src/schemas/uso_insumo.py`, `backend/src/routers/usos_insumo.py`
- Modify: `backend/src/services/insumos.py` (`reprocessar_insumo`), `backend/src/routers/custos.py` (`deletar_custo`), `backend/src/main.py`
- Test: `backend/tests/test_api_usos_insumo.py`

**Interfaces:**
- Consumes: `aplicar_preco_medio`, `EventoInsumo` (Tarefa 2); `validar_data_no_ciclo(..., fase)`, `exigir_retroativo_para_data_passada`.
- Produces:
  - `services.insumos.reprocessar_insumo(db: Session, insumo_id: UUID) -> None`: carrega compras e usos do insumo, chama `aplicar_preco_medio`, grava `preco_unitario_rs` de cada uso e cria, atualiza ou remove o `CustoOperacional` ligado (`custo_id`): categoria do insumo, descrição `"<nome> (<qtd> <unidade>)"`, valor `round(qtd * preco, 2)`, fase do uso. Uso pendente não tem custo. Se o custo de um uso de ciclo `FINALIZADO` mudar, grava `recalculado_em` e auditoria.
  - Rotas (`/api/v1/ciclos/{ciclo_id}/usos-insumo`, com `verificar_ciclo_da_organizacao`): `POST` (GESTOR, CAMPO e VIGIA: o vigia aplica produtos de madrugada); `GET` (GESTOR e CAMPO; o VIGIA recebe 403); `PUT /{uso_id}` e `DELETE /{uso_id}` (GESTOR). Status do ciclo: `PLANEJADO` só fase `PREPARO`; `ATIVO`/`PAUSADO` qualquer fase; `FINALIZADO` só GESTOR; `CANCELADO` recusa.
  - `UsoInsumoCreate{insumo_id, data_uso, quantidade > 0, fase: FaseCusto, observacao?, retroativo: bool = False, preco_corrigido_rs: float | None}` (`preco_corrigido_rs` só GESTOR; CAMPO enviando → 403); `UsoInsumoResponse{id, insumo_id, insumo_nome, unidade_uso, data_uso, quantidade, fase, retroativo, observacao, preco_unitario_rs | None, valor_rs | None, pendente_de_valor: bool | None, recalculado_em | None}` (valores e `pendente_de_valor` só para GESTOR).
  - `custos.deletar_custo` responde 409 ("custo gerado por uso de insumo; exclua o uso") quando algum `ConsumoInsumo.custo_id` aponta para ele.

- [ ] **Step 1: Write the failing tests** (`test_api_usos_insumo.py`, valores do §5.2):
  - `test_uso_gera_custo_automatico`: compra 100 kg R$ 300; uso de 50 kg → `valor_rs == 150.0` e o custo aparece em `GET /ciclos/{id}/custos/` com `categoria` do insumo e `fase`.
  - `test_campo_lanca_uso_e_nao_ve_valores`: resposta com `preco_unitario_rs`, `valor_rs` e `pendente_de_valor` `None`; `custos` continua 403 para CAMPO.
  - `test_campo_nao_pode_corrigir_preco` (403); `test_vigia_lanca_uso_sem_ver_valores_e_nao_lista_usos` (POST 201 com valores `None`; GET 403).
  - `test_uso_sem_compra_fica_pendente_e_sem_custo` e `test_compra_retroativa_gera_o_custo_pendente` (compra com `data_compra` ≤ data do uso e `retroativo=true` → custo aparece).
  - `test_uso_e_compra_no_mesmo_dia_usam_a_compra`.
  - `test_saldo_insuficiente_aceita_e_marca_saldo_negativo` (`InsumoResponse.saldo_negativo is True` para GESTOR).
  - `test_excluir_compra_deixa_usos_pendentes_e_remove_o_custo`; `test_alterar_valor_da_compra_recalcula_o_custo_do_uso`.
  - `test_ciclo_finalizado_registra_recalculado_em`: finalizar o ciclo (usar helper de encerramento dos testes existentes), alterar a compra, `recalculado_em` preenchido.
  - `test_data_passada_exige_retroativo`; `test_data_futura_da_422`; `test_insumo_inativo_da_422`; `test_excluir_custo_gerado_por_uso_da_409`.
  - Isolamento: `test_ciclo_ou_insumo_de_outra_organizacao_da_404`.
- [ ] **Step 2: Run** — falha.
- [ ] **Step 3: Implement** schemas, rotas, `reprocessar_insumo` (substitui o `pass` da Tarefa 3) e o bloqueio em `deletar_custo`. `reprocessar_insumo` roda a cada criação, edição ou exclusão de compra e de uso.
- [ ] **Step 4: Run** `pytest tests/test_api_usos_insumo.py tests/test_api_insumos.py -q` — passa.
- [ ] **Step 5: Run** `pytest tests -q` — verde.
- [ ] **Step 6: Commit** `feat(insumos): uso de insumo com custo automático e reprocessamento`.

### Task 5: Fase nos custos manuais e custo diário sem preparo e despesca

**Files:**
- Modify: `backend/src/schemas/custo.py` (`CustoCreate.fase: FaseCusto = CULTIVO`, `CustoResponse.fase`), `backend/src/routers/simulacao.py` (`custos_fixos_total` só fase `CULTIVO`), qualquer outro chamador de `estimar_custo_diario` (buscar com `grep -rn estimar_custo_diario backend/src`)
- Test: `backend/tests/test_custo_diario_fases.py`

**Interfaces:**
- Consumes: `CustoOperacional.fase` (Tarefa 1).
- Produces: `custo_diario_rs` da simulação ignora custos `PREPARO` e `DESPESCA`; `co_total` e `lucro_operacional_atual_rs` continuam somando todos.

- [ ] **Step 1: Write the failing tests:** ciclo ativo com custos lançados e biometrias (usar os helpers de `tests/test_simulacao.py`); registrar `GET .../simular-despesca/comparativo` antes e depois de lançar um custo `PREPARO` de R$ 12.000 (`fase="PREPARO"`): `custo_diario_rs` igual nas duas chamadas, `lucro_operacional_atual_rs` menor em 12.000; `test_custo_manual_aceita_fase_e_devolve_na_resposta`; `test_fase_invalida_da_422`.
- [ ] **Step 2: Run** — falha.
- [ ] **Step 3: Implement** o campo, a resposta e o filtro por fase.
- [ ] **Step 4: Run** `pytest tests -q` — verde.
- [ ] **Step 5: Commit** `feat(custos): fase nos custos e custo diário só com custos do cultivo`.

### Task 6: Frontend — tipos, campo de data retroativa, insumos e compras (gestor)

**Files:**
- Create: `frontend/src/components/ui/data-lancamento.tsx`, `frontend/src/app/gestor/insumos/page.tsx`
- Modify: `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`, `frontend/src/app/gestor/layout.tsx` (item de menu "Insumos")

**Interfaces:**
- Produces: `DataLancamento({ value, onChange, retroativo, onRetroativoChange, label })` (data nasce hoje e travada; a caixa "Lançamento retroativo" libera o seletor e mostra o aviso de recálculo do custo médio); `insumosApi.{listar, criar, atualizar, compras.{listar, criar, atualizar, excluir}}`; `usosInsumoApi.{listar, criar, atualizar, excluir}`; tipos `Insumo`, `CompraInsumo`, `UsoInsumo`, `FaseCusto`.

- [ ] **Step 1: Implement** tipos, clientes de API (padrão `apiFetch` de `lib/api.ts`), `DataLancamento` e a página de insumos: lista com saldo, preço médio e selo "saldo negativo"; formulário de novo insumo; painel de compras do insumo selecionado (com `DataLancamento`).
- [ ] **Step 2: Verify** `cd frontend && npx tsc --noEmit && npm run lint` — 0 erros.
- [ ] **Step 3: Verify manual** (backend em `127.0.0.1:8000`, `npm run dev`): entrar como `gestor@sad.com`; criar o insumo "Cal" (kg); registrar as compras do §5.2 e conferir saldo 200 kg e preço médio R$ 3,50; marcar uma compra com data de ontem sem a caixa retroativa e conferir que o seletor está travado.
- [ ] **Step 4: Commit** `feat(frontend): cadastro de insumos e compras`.

### Task 7: Frontend — uso de insumo (gestor e campo)

**Files:**
- Create: `frontend/src/components/insumos/uso-insumo-form.tsx`, `frontend/src/app/campo/insumos/page.tsx`, `frontend/src/app/vigia/insumos/page.tsx`
- Modify: `frontend/src/app/gestor/viveiros/[id]/page.tsx` (nova aba "Insumos" do ciclo), `frontend/src/app/campo/layout.tsx` e `frontend/src/app/vigia/layout.tsx` (item de menu)

**Interfaces:**
- Consumes: `usosInsumoApi`, `insumosApi.listar`, `DataLancamento` (Tarefa 6).
- Produces: `UsoInsumoForm({ cicloId, fase, onSalvo })`; o gestor vê preço e valor e pode corrigir o preço do uso; o campo só informa insumo, quantidade, data e observação e vê o saldo em quantidade; o vigia usa o mesmo formulário (lista de insumos só com nome e unidade) e não vê a lista de usos.

- [ ] **Step 1: Implement** o formulário, a aba "Insumos" (lista de usos com selo "pendente de valor", "retroativo" e "recalculado") e a página do campo.
- [ ] **Step 2: Verify** `npx tsc --noEmit && npm run lint` — 0 erros.
- [ ] **Step 3: Verify manual:** como gestor, lançar 50 kg de cal num ciclo ativo e ver o custo R$ 175,00 (preço médio 3,50); como `campo@sad.com`, lançar um uso e conferir que nenhum valor em reais aparece; lançar um insumo sem compra e ver "pendente de valor".
- [ ] **Step 4: Commit** `feat(frontend): uso de insumo por gestor e campo`.

---

## Etapa 2 — Vendas, desbaste e efeitos nos cálculos

### Task 8: Função central de população, FCA, densidade e lucro com vendas

> Esta tarefa vem antes das rotas de venda porque define o contrato que elas alimentam. Os testes usam objetos simples com os atributos de uma venda.

**Files:**
- Create: `backend/src/services/populacao.py`
- Modify: `backend/src/services/decision_engine.py`, `backend/src/services/sobrevivencia.py`, `backend/src/routers/ciclos.py` (`metricas_atuais`), `backend/src/routers/manejos.py` (três pontos que chamam `calcular_populacao_atual` e a chamada de `sobrevivencia_implicita_pct`/`confrontar_vivos`), `backend/src/routers/rondas.py` (`_biomassa_estimada_kg_ha`), `backend/src/routers/simulacao.py` (`_executar_simulacao`), `backend/src/schemas/ciclo.py` (`MetricasAtuaisResponse`)
- Test: `backend/tests/test_populacao_vendas.py`

**Interfaces:**
- Produces:
  - `services.populacao`: `animais_vendidos_ate(vendas: Iterable, ate: date | None = None) -> int`; `biomassa_vendida_kg(vendas: Iterable) -> float`; `receita_realizada_rs(vendas: Iterable) -> float`; `populacao_vigente(pos_larvas: int, taxa_sobrev_pct: float, vendas: Iterable, ate: date | None = None) -> int` = `max(0, calcular_populacao_atual(...) - animais_vendidos_ate(...))`. Cada venda expõe `data_venda`, `animais_estimados`, `biomassa_kg`, `valor_total_rs`.
  - `decision_engine.calcular_fca(racao_total_kg, biomassa_atual_kg, biomassa_inicial_kg, biomassa_vendida_kg: float = 0.0)` (ganho = atual + vendida − inicial).
  - `decision_engine.calcular_metricas_economicas(custos, biomassa_kg, preco_venda_kg, receita_realizada_rs: float = 0.0)` (receita e lucro estimados incluem a receita já realizada).
  - `decision_engine.simular_delta_v(..., receita_realizada_rs: float = 0.0)` (somada ao lucro atual e ao projetado, então o ΔV não muda).
  - `sobrevivencia.sobrevivencia_implicita_pct(dias, pos_larvas, peso_na_data, taxa_pct, ate, vendidos_ate: Callable[[date], int] = lambda d: 0)`: cada dia vale `min(100, (biomassa_implicita_kg * 1000 / peso + vendidos_ate(d)) / pos_larvas * 100)`. `confrontar_vivos(..., vendidos_ate=...)` repassa o parâmetro; `por_mortos` e `mortos_dia / pos_larvas` não mudam (a taxa continua sendo a sobrevivência natural das pós-larvas originais).
  - `MetricasAtuaisResponse` ganha `densidade_atual: float | None`, `receita_realizada_rs: float | None`, `lucro_realizado_rs: float | None` (só GESTOR); `lucro_operacional_rs` passa a ser o lucro estimado se despescar hoje, já incluindo as vendas.
  - `SimulacaoResponse.lucro_operacional_atual_rs` inclui a receita realizada.
  - Os pontos de `routers/manejos.py` que hoje calculam população de uma data passada chamam `populacao_vigente(..., ate=<essa data>)`.

- [ ] **Step 1: Write the failing tests** (`test_populacao_vendas.py`):
  - `test_populacao_desconta_animais_vendidos`: 300.000 PL, taxa 80 %, venda de 10.000 animais → 230.000.
  - `test_venda_posterior_a_data_de_referencia_nao_desconta`.
  - `test_desbaste_maior_que_a_populacao_zera_sem_ficar_negativo`: população 0; `calcular_fca` com ganho ≤ 0 devolve `None`; nenhuma divisão por zero em `metricas`.
  - `test_fca_soma_a_biomassa_vendida`: ração 1.000 kg, atual 400, vendida 200, inicial 0 → FCA `1000 / 600`.
  - `test_implicita_com_vendidos`: 100.000 PL, peso 10 g, ração do dia 20 kg, taxa 4 %, `MIN_DIAS_COM_REGISTRO` dias iguais → sem vendas `50.0`; com `vendidos_ate=lambda d: 10_000` → `60.0`.
  - `test_delta_v_nao_muda_com_receita_realizada_mas_lucro_sim`.
  - `test_metricas_economicas_incluem_receita_realizada`.
- [ ] **Step 2: Run** — falha.
- [ ] **Step 3: Implement** o módulo e as alterações de assinatura (todos os novos parâmetros têm padrão neutro, então os testes existentes continuam passando); trocar as chamadas listadas em `files`. A lista de vendas vem de `ciclo.vendas` (relação criada na Tarefa 9; até lá os callers passam lista vazia via `getattr(ciclo, "vendas", [])`).
- [ ] **Step 4: Run** `pytest tests -q` — verde (nenhum teste existente muda de número, pois não há vendas).
- [ ] **Step 5: Commit** `feat(vendas): população, FCA e lucro descontam e somam as vendas`.

### Task 9: Modelo e rotas de vendas (migração 0010)

**Files:**
- Create: `backend/src/models/venda_ciclo.py`, `backend/src/schemas/venda.py`, `backend/src/routers/vendas.py`, `backend/migrations/versions/0010_vendas_do_ciclo.py`
- Modify: `backend/src/models/ciclo_produtivo.py` (relação `vendas`, cascade como as demais), `backend/src/models/__init__.py`, `backend/src/main.py`
- Test: `backend/tests/test_api_vendas.py`

**Interfaces:**
- Consumes: `exigir_retroativo_para_data_passada`, `validar_data_no_ciclo`, `buscar_preco_por_gramatura`, `tabela_vigente`, `regra_da_organizacao`.
- Produces:
  - Modelo `VendaCiclo(ciclo_id, data_venda, tipo String(14), biomassa_kg Numeric(12,2), peso_medio_g Numeric(8,2), animais_estimados Integer, preco_kg Numeric(10,2), valor_total_rs Numeric(12,2), comprador, observacao, retroativo)`.
  - `routers/vendas.py::sincronizar_totais_do_ciclo(db, ciclo) -> None`: com o ciclo `FINALIZADO`, `ciclo.biomassa_colhida_kg` e `ciclo.receita_real_rs` passam a ser a soma das vendas.
  - Rotas `/api/v1/ciclos/{ciclo_id}/vendas` (só GESTOR): `POST`, `GET`, `PUT /{id}`, `DELETE /{id}`, `GET /preco-sugerido?peso_medio_g=` → `{preco_kg: float | None}`. `VendaCreate{data_venda, tipo: Literal["DESBASTE","DESPESCA_FINAL"], biomassa_kg > 0, peso_medio_g > 0, preco_kg: float | None, comprador?, observacao?, retroativo: bool = False}` (sem `preco_kg` usa o sugerido, 422 se não houver). `VendaResponse` inclui `retroativo`, `animais_estimados = round(biomassa_kg * 1000 / peso_medio_g)` e `valor_total_rs = biomassa_kg * preco_kg`. `CompraInsumo` e os usos também devolvem `retroativo` (o gestor vê o indicador no item).
  - Status: `DESBASTE` só em `ATIVO`/`PAUSADO`; `DESPESCA_FINAL` em `ATIVO`/`PAUSADO` e, como correção, `FINALIZADO`; `PLANEJADO` e `CANCELADO` recusam (400).

- [ ] **Step 1: Write the failing tests:** `test_desbaste_calcula_animais_e_valor` (200 kg, 20 g, R$ 20/kg → `animais_estimados == 10000`, `valor_total_rs == 4000.0`); `test_preco_omitido_usa_a_tabela_de_precos`; `test_sem_preco_na_tabela_e_sem_preco_da_422`; `test_data_passada_exige_retroativo`; `test_desbaste_em_ciclo_finalizado_da_400`; `test_campo_nao_acessa_vendas` (403); `test_venda_de_outra_organizacao_da_404`; `test_excluir_venda_de_ciclo_finalizado_ressincroniza_totais`; `test_populacao_da_metrica_cai_depois_do_desbaste` (chamar `metricas-atuais` antes e depois; `populacao_estimada` cai em `animais_estimados` e `densidade_atual` cai).
- [ ] **Step 2: Run** — falha.
- [ ] **Step 3: Implement** modelo, migração 0010 (com verificação do Step 5 da Tarefa 1), schemas, rotas e a relação `CicloProdutivo.vendas`; remover o `getattr` provisório da Tarefa 8. Auditoria: `CRIAR_VENDA`, `ATUALIZAR_VENDA`, `EXCLUIR_VENDA`.
- [ ] **Step 4: Run** `pytest tests/test_api_vendas.py -q` e `pytest tests -q` — verdes.
- [ ] **Step 5: Commit** `feat(vendas): vendas do ciclo com desbaste`.

### Task 10: Encerramento do ciclo com vendas

**Files:**
- Modify: `backend/src/schemas/ciclo.py` (`CicloEncerrar`), `backend/src/routers/ciclos.py` (`encerrar_ciclo`)
- Test: `backend/tests/test_api_encerramento.py`

**Interfaces:**
- Consumes: `VendaCiclo`, `sincronizar_totais_do_ciclo`, `peso_na_data` (de `services/sobrevivencia.py`).
- Produces: `CicloEncerrar{data_despesca_real: date | None, biomassa_colhida_kg: float | None (> 0), receita_real_rs: float | None (>= 0)}` (as duas últimas vêm juntas ou nenhuma). Regras do §5.3: payload com valores cria uma venda `DESPESCA_FINAL` (peso médio da última biometria, 422 se não houver biometria; preço = receita ÷ biomassa); sem payload usa as vendas existentes; exige ao menos uma `DESPESCA_FINAL`; **bloqueia (409)** com mensagem com a contagem de usos de insumo pendentes de valor; `data_despesca_real` = informada, senão data da última `DESPESCA_FINAL`, senão hoje; sincroniza os totais.

- [ ] **Step 1: Write the failing tests:** `test_encerrar_com_payload_cria_venda_final` (preço = receita ÷ biomassa); `test_encerrar_sem_venda_final_da_422`; `test_encerrar_soma_varias_vendas` (desbaste + final → `biomassa_colhida_kg` e `receita_real_rs` somados); `test_encerrar_bloqueado_por_uso_pendente_de_valor` (mensagem cita a quantidade); `test_encerrar_sem_biometria_com_payload_da_422`; `test_data_despesca_real_padrao`.
- [ ] **Step 2: Run** — falha.
- [ ] **Step 3: Implement.** Os testes existentes que chamam `/encerrar` com os três campos continuam válidos.
- [ ] **Step 4: Run** `pytest tests -q` — verde.
- [ ] **Step 5: Commit** `feat(ciclos): encerramento soma as vendas e bloqueia uso sem valor`.

### Task 11: Frontend — vendas, desbaste e rótulos dos lucros

**Files:**
- Create: `frontend/src/components/viveiro/vendas-ciclo.tsx`
- Modify: `frontend/src/lib/types.ts` (`VendaCiclo`, campos novos de `MetricasAtuais`), `frontend/src/lib/api.ts` (`vendasApi`), `frontend/src/app/gestor/viveiros/[id]/page.tsx` (aba "Vendas"; diálogo de encerrar com campos opcionais; cartões de métricas com "Densidade atual", "Lucro realizado" e "Lucro estimado se despescar hoje")

**Interfaces:**
- Consumes: `DataLancamento` (Tarefa 6), `vendasApi.{listar, criar, atualizar, excluir, precoSugerido}`.

- [ ] **Step 1: Implement.** O formulário de venda sugere o preço pela tabela quando o peso médio é informado e permite editar.
- [ ] **Step 2: Verify** `npx tsc --noEmit && npm run lint` — 0 erros.
- [ ] **Step 3: Verify manual:** em um ciclo ativo, lançar um desbaste de 200 kg e conferir que a população estimada e a densidade atual caem e que aparecem os dois lucros com rótulos diferentes; encerrar o ciclo e conferir que a receita é a soma das vendas.
- [ ] **Step 4: Commit** `feat(frontend): vendas, desbaste e lucros rotulados`.

---

## Etapa 3 — Ciclo em preparo (quebra o fluxo atual)

> Publicar o backend desta etapa só depois de aplicar a migração 0011 no Supabase (remove `NOT NULL` das pós-larvas).
>
> As Tarefas 12 e 13 são entregues no mesmo PR: ao fim da Tarefa 12 a suíte antiga fica vermelha por desenho (a criação de ciclo mudou), e a Tarefa 13 devolve tudo ao verde. Não publicar entre as duas.

### Task 12: Planejar, preparar, povoar e cancelar (migração 0011)

**Files:**
- Create: `backend/src/models/etapa_preparo.py`, `backend/src/schemas/etapa_preparo.py`, `backend/src/routers/etapas_preparo.py`, `backend/migrations/versions/0011_ciclo_em_preparo.py`
- Modify: `backend/src/models/ciclo_produtivo.py` (`quantidade_pos_larvas` e `custo_aquisicao_pl` opcionais; relação `etapas_preparo`), `backend/src/models/insumo.py` (`ConsumoInsumo.etapa_id` FK `etapas_preparo` SET NULL), `backend/src/services/regras_ciclo.py` (`STATUS_CICLO_ABERTO` inclui `PLANEJADO`), `backend/src/schemas/ciclo.py` (`CicloPlanejar`, `CicloPovoar`, `CicloResponse` tolerante), `backend/src/routers/ciclos.py`, `backend/src/main.py`
- Test: `backend/tests/test_api_preparo.py`

**Interfaces:**
- Produces:
  - `CicloPlanejar{viveiro_id: UUID, data_povoamento: date, tabela_alimentar_id: UUID | None}` com `model_config = {"extra": "forbid"}`. A data prevista aceita qualquer data (é só uma previsão; o reagendamento corrige). `POST /api/v1/ciclos/` (GESTOR) passa a **planejar**: cria `CicloProdutivo(status=PLANEJADO)` com `quantidade_pos_larvas` e `custo_aquisicao_pl` vazios e as cinco etapas sugeridas (`SECAGEM`, `CALAGEM`, `ADUBACAO`, `ABASTECIMENTO`, `TRATAMENTO_AGUA`, `status=PENDENTE`, `ordem` 1 a 5). 409 se o viveiro já tem ciclo `PLANEJADO`, `ATIVO` ou `PAUSADO`; 400 viveiro inativo; valida a tabela alimentar como hoje.
  - `CicloPovoar{data_povoamento: date, quantidade_pos_larvas: int > 0, custo_aquisicao_pl: float >= 0, peso_medio_pl_g: float | None (0 a 5), laboratorio_origem: str | None (<= 120)}`. `POST /api/v1/ciclos/{ciclo_id}/povoar` (GESTOR): só ciclo `PLANEJADO`; **409 enquanto houver etapa `PENDENTE` ou `EM_ANDAMENTO`** (mensagem lista quantas); revalida a regra de um ciclo aberto por viveiro; grava os campos, cria o custo `POS_LARVAS` (como o `criar_ciclo` atual faz) na data real, muda para `ATIVO`, audita `POVOAR_CICLO`.
  - `CicloReagendar{data_povoamento: date | None, tabela_alimentar_id: UUID | None, viveiro_id: UUID | None}` com `extra = forbid` (só os campos enviados mudam). `PATCH /api/v1/ciclos/{ciclo_id}/planejamento` (GESTOR): só ciclo `PLANEJADO`; mudar `viveiro_id` revalida viveiro ativo da organização e a regra de um ciclo aberto (409); valida a tabela alimentar como o planejar; audita `REAGENDAR_CICLO`. Etapas, usos e custos já lançados permanecem no ciclo.
  - `POST /api/v1/ciclos/{ciclo_id}/cancelar` (GESTOR): só `PLANEJADO` → `CANCELADO`, audita `CANCELAR_CICLO`.
  - `EtapaPreparo(ciclo_id, tipo String(20), data_inicio, data_fim, status String(14), observacao String(255), ordem)`; status `PENDENTE`, `EM_ANDAMENTO`, `CONCLUIDA`, `NAO_REALIZADA`. Rotas `/api/v1/ciclos/{ciclo_id}/etapas-preparo`: `GET` (GESTOR, CAMPO, VIGIA); `POST` e `DELETE /{id}` (GESTOR); `PATCH /{id}` (GESTOR e CAMPO: `status`, `data_inicio`, `data_fim`, `observacao`). Datas das etapas podem ser futuras (não seguem a regra retroativa).
  - `ConsumoInsumo.etapa_id` aceito em `UsoInsumoCreate` (opcional; a etapa precisa ser do mesmo ciclo).
  - `CicloResponse`: `quantidade_pos_larvas` e `custo_aquisicao_pl` podem ser `None`; `densidade_inicial` `None`. `metricas-atuais` e `manejos-alimentares/recomendacao` de ciclo `PLANEJADO` respondem **409** "Ciclo ainda em preparo" (decisão deste plano: resposta tratada, sem erro 500). Exportação CSV e listagens toleram `None`.

- [ ] **Step 1: Write the failing tests** (`test_api_preparo.py`): `test_planejar_cria_ciclo_planejado_com_cinco_etapas`; `test_planejar_com_campos_de_pos_larvas_da_422` (extra proibido); `test_planejar_em_viveiro_com_ciclo_aberto_da_409` (parametrizar `PLANEJADO`, `ATIVO`, `PAUSADO`); `test_povoar_bloqueado_com_etapa_pendente` (409); `test_povoar_com_etapas_resolvidas_ativa_e_lanca_custo_de_pos_larvas`; `test_povoar_exige_ciclo_planejado`; `test_reagendar_muda_data_e_tabela_so_em_ciclo_planejado` (ciclo ativo → 400; etapas e usos já lançados continuam no ciclo); `test_reagendar_para_viveiro_ocupado_da_409`; `test_reagendar_com_campo_desconhecido_da_422`; `test_campo_nao_reagenda` (403); `test_cancelar_so_ciclo_planejado_e_libera_o_viveiro` (depois de cancelar, planejar de novo no mesmo viveiro dá 201); `test_campo_atualiza_etapa_mas_nao_cria_nem_planeja`; `test_campo_nao_planeja_nem_povoa` (403); `test_uso_de_insumo_em_ciclo_planejado_so_na_fase_preparo` e `test_uso_pode_ligar_a_etapa`; `test_venda_em_ciclo_planejado_da_400`; `test_metricas_de_ciclo_planejado_da_409`; `test_ciclo_ou_etapa_de_outra_organizacao_da_404`; `test_data_de_preparo_anterior_ao_povoamento_em_ciclo_existente_com_retroativo` (registrar uso fase `PREPARO` em ciclo `ATIVO` com data anterior ao povoamento).
- [ ] **Step 2: Run** — falha.
- [ ] **Step 3: Implement** modelos, migração 0011 (verificar como no Step 5 da Tarefa 1; no SQLite usa `batch_alter_table`), schemas e rotas; reescrever `criar_ciclo` como planejar; mover o conteúdo atual de `criar_ciclo` (viveiro ativo, custo de PL, auditoria) para `povoar`.
- [ ] **Step 4: Run** `pytest tests/test_api_preparo.py -q` — passa (os demais testes ainda falham até a Tarefa 13).
- [ ] **Step 5: Commit** `feat(ciclos): ciclo em preparo com planejar, etapas, povoar e cancelar`.

### Task 13: Migrar fixtures e testes para planejar e povoar

**Files:**
- Modify: `backend/tests/conftest.py` (`novo_ciclo`), `backend/tests/test_api_dados_reais.py`, `test_api_integridade.py`, `test_calculos_referencia.py`, `test_isolamento_organizacao.py`, `test_simulacao_safra.py`, `test_sobrevivencia.py`; scripts de `backend/testsprite_tests/` que criam ciclo
- Test: a própria suíte

**Interfaces:**
- Produces (em `tests/conftest.py`): `planejar_e_povoar(client, headers, viveiro_id: str, data_povoamento: str = "2026-08-01", pls: int = 300_000, custo_pl: float = 3_000.0, **extra) -> dict` → planeja, marca todas as etapas `NAO_REALIZADA`, povoa e devolve o ciclo ativo. `novo_ciclo` passa a usá-la. Testes que chamam `/api/v1/ciclos/` com pós-larvas passam a usar o helper; os que validam limites dos campos de pós-larvas (`gt=0`, `ge=0`, `peso_medio_pl_g`) passam a validar `/povoar`.

- [ ] **Step 1:** Rodar `pytest tests -q`, anotar os testes que falham e corrigi-los com o helper (importar com `from tests.conftest import planejar_e_povoar`).
- [ ] **Step 2: Run** `pytest tests -q` — **toda a suíte verde** (esperado: ao menos os 223 testes anteriores mais os novos).
- [ ] **Step 3:** Nos scripts de `backend/testsprite_tests/` que fazem `POST /api/v1/ciclos/` com pós-larvas, trocar pelo fluxo planejar, resolver etapas e povoar. São planos gerados e pouco confiáveis (ver `CLAUDE.md`), então trocar só a criação do ciclo, sem reexecutá-los.
- [ ] **Step 4: Commit** `test: fixtures e testes passam a planejar e povoar o ciclo`.

### Task 14: Frontend — Planejar ciclo, preparo e Povoar

**Files:**
- Create: `frontend/src/components/viveiro/preparo-ciclo.tsx`, `frontend/src/app/campo/preparo/page.tsx`
- Modify: `frontend/src/lib/types.ts` (`StatusCiclo` já inclui `PLANEJADO`; `EtapaPreparo`; campos de pós-larvas opcionais em `CicloProdutivo`), `frontend/src/lib/api.ts` (`ciclosApi.criar` passa a planejar; `ciclosApi.povoar`, `cancelar`; `etapasPreparoApi`), `frontend/src/app/gestor/viveiros/[id]/page.tsx` (substituir o diálogo de criar ciclo, linhas ~75 a 230, por "Planejar ciclo": data prevista e tabela alimentar), `frontend/src/app/gestor/viveiros/page.tsx` (listagens que leem pós-larvas toleram vazio), `frontend/src/app/campo/layout.tsx`

**Interfaces:**
- Produces: painel "Preparo" do ciclo planejado: checklist de etapas com seletor de status (pendente, em andamento, feita, não realizada), datas e observação; uso de insumo (`UsoInsumoForm` com `fase="PREPARO"` e seletor de etapa); custo manual de fase `PREPARO`; botão **Reagendar** (data prevista, tabela alimentar e viveiro); botão **Povoar** (diálogo: data real, pós-larvas, custo, peso médio da PL, laboratório) desabilitado, com o motivo, enquanto houver etapa pendente ou em andamento; botão **Cancelar planejamento**. Página do campo para atualizar o status das etapas e lançar insumos.

- [ ] **Step 1: Implement.** Ciclos `PLANEJADO` não chamam `metricas`/`recomendacao`.
- [ ] **Step 2: Verify** `npx tsc --noEmit && npm run lint` — 0 erros.
- [ ] **Step 3: Verify manual:** planejar um ciclo num viveiro livre; ver as cinco etapas; tentar povoar e ver o bloqueio; marcar as etapas (uma como "não realizada"); lançar 200 kg de cal na calagem; povoar e conferir que o ciclo vira ativo e o custo das pós-larvas aparece; planejar e cancelar outro e conferir que o viveiro volta a ficar livre; como `campo@sad.com`, atualizar o status de uma etapa.
- [ ] **Step 4: Commit** `feat(frontend): planejar ciclo, preparo e povoamento`.

---

## Etapa 4 — Histórico e Financeiro

### Task 15: Financeiro do ciclo e histórico do viveiro (API)

**Files:**
- Create: `backend/src/services/historico.py`, `backend/src/schemas/financeiro.py`
- Modify: `backend/src/routers/ciclos.py` (`GET /{ciclo_id}/financeiro`), `backend/src/routers/viveiros.py` (`GET /{viveiro_id}/historico`)
- Test: `backend/tests/test_api_historico_financeiro.py`

**Interfaces:**
- Consumes: `populacao.*` (Tarefa 8), vendas, usos de insumo, etapas, custos com fase.
- Produces:
  - `services.historico.resumo_do_ciclo(db, ciclo, mostrar_valores: bool) -> dict` (usado pelas duas rotas).
  - `GET /api/v1/ciclos/{ciclo_id}/financeiro` (GESTOR) → `FinanceiroCicloResponse{custos_por_fase: dict[str, float], custos_por_categoria: dict[str, float], custos_fase_categoria: list[{fase, categoria, total_rs}], vendas: list, receita_realizada_rs, custo_total_rs, lucro_realizado_rs, margem_realizada_pct | None, lucro_estimado_se_despescar_hoje_rs | None (None em ciclo finalizado ou sem biometria/preço), custo_por_kg_rs | None (custo total ÷ biomassa vendida), definitivo: bool (ciclo FINALIZADO), usos_pendentes: int, valores_recalculados_em: datetime | None}`.
  - `GET /api/v1/viveiros/{viveiro_id}/historico` (GESTOR, CAMPO, VIGIA) → lista de ciclos, mais recente primeiro, cada um com: `ciclo_id, status, data_povoamento, data_despesca_real, quantidade_pos_larvas, etapas[{tipo,status,datas}], insumos[{insumo_id,nome,unidade_uso,quantidade_total,custo_total_rs|None}], racao_total_kg, racao_custo_rs|None, racao_por_semana[{inicio, fim, kg, custo_rs|None, fca_parcial|None}] (semanas a partir do povoamento; custo = kg × preço médio do kg de ração; fca_parcial = ração acumulada até a semana ÷ ganho de biomassa estimado até ela, `None` sem biometria), vendas{quantidade,biomassa_total_kg,receita_rs|None}, peso_final_g (peso médio ponderado pela biomassa das vendas DESPESCA_FINAL), sobrevivencia_final_pct (animais vendidos ÷ pós-larvas × 100), fca (final: ração ÷ (biomassa vendida − biomassa inicial); ativo: o FCA atual), custo_total_rs|None, lucro_realizado_rs|None, margem_pct|None, custo_por_kg_rs|None`. Para CAMPO e VIGIA todo campo em reais vem `None`. Ciclo `PLANEJADO` aparece com pós-larvas `None`.

- [ ] **Step 1: Write the failing tests:** ciclo finalizado com dois desbastes e uma despesca final, um custo de ração e um uso de insumo; conferir `receita_realizada_rs` (soma das vendas), `custo_total_rs`, `lucro_realizado_rs = receita − custo`, `custo_por_kg_rs = custo ÷ biomassa vendida`, `definitivo is True`, `lucro_estimado_se_despescar_hoje_rs is None`; ciclo ativo: `definitivo is False` e lucro estimado = realizado + biomassa atual × preço; `test_usos_pendentes_contados`; `test_historico_traz_sobrevivencia_e_peso_final` (valores calculados à mão); `test_campo_ve_historico_sem_valores_em_reais` (todos `None`) e recebe 403 em `/financeiro`; `test_viveiro_de_outra_organizacao_da_404`; `test_ciclo_planejado_aparece_no_historico`; `test_racao_por_semana_soma_os_manejos` (a soma dos `kg` semanais é igual à ração acumulada do ciclo).
- [ ] **Step 2: Run** — falha.
- [ ] **Step 3: Implement.** Ração em R$ e preço médio do kg: custo `RACAO` lançado ÷ kg dos manejos (mesma lógica de `estimar_custo_diario`).
- [ ] **Step 4: Run** `pytest tests -q` — verde.
- [ ] **Step 5: Commit** `feat(financeiro): financeiro do ciclo e histórico do viveiro`.

### Task 16: Frontend — aba Histórico e Financeiro completo

**Files:**
- Create: `frontend/src/components/viveiro/historico-viveiro.tsx`
- Modify: `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts` (`financeiroApi`, `viveirosApi.historico`), `frontend/src/app/gestor/viveiros/[id]/page.tsx` (aba "Histórico"), `frontend/src/app/gestor/financeiro/page.tsx`

**Interfaces:**
- Produces: aba "Histórico" em linha do tempo por ciclo (preparo e etapas, povoamento, insumos e ração, desbastes, despesca final, resultado); Financeiro com custos por fase e categoria, vendas, receita, **lucro realizado** e **lucro estimado se despescar hoje** (sempre rotulados), margem, custo por kg, selo "parcial" ou "definitivo", e aviso de "valores recalculados em <data>" e de "N usos sem valor". CAMPO e VIGIA não veem valores em reais.

- [ ] **Step 1: Implement.**
- [ ] **Step 2: Verify** `npx tsc --noEmit && npm run lint` — 0 erros.
- [ ] **Step 3: Verify manual:** num viveiro com ciclo finalizado e outro ativo, conferir a linha do tempo e os totais do Financeiro contra a conta feita à mão (receita das vendas − custos), e que `campo@sad.com` vê o histórico sem valores.
- [ ] **Step 4: Commit** `feat(frontend): histórico do viveiro e financeiro completo`.

### Task 17: Documentação e verificação final

**Files:**
- Modify: `documentacao_base/documento_de_requisitos_de_software.md` (novos RFs ao final da lista de RFs: insumos e compras com custo médio, etapas do preparo, vendas com desbaste, histórico do viveiro, lucro realizado e estimado; nota na seção 5.2 "Fora do escopo inicial" esclarecendo que o registro de compras para custo médio entra e o processo transacional não), `CLAUDE.md` (hierarquia de domínio, fluxo planejar e povoar, fixture `planejar_e_povoar`, insumos/vendas/preparo nas regras)

- [ ] **Step 1:** Atualizar os dois documentos.
- [ ] **Step 2: Run** `cd backend && .venv/Scripts/python.exe -m pytest tests -q` — verde.
- [ ] **Step 3: Run** (esperado: sem erro e "No new upgrade operations detected.") `DATABASE_URL=sqlite:///./chk_tmp.db .venv/Scripts/python.exe -m alembic upgrade head && DATABASE_URL=sqlite:///./chk_tmp.db .venv/Scripts/python.exe -m alembic check; rm -f chk_tmp.db`
- [ ] **Step 4: Run** `cd frontend && npx tsc --noEmit && npm run lint` — 0 erros.
- [ ] **Step 5: Commit** `docs: requisitos e CLAUDE.md com insumos, vendas e preparo`.

### Task 18: Publicação (somente com aprovação do usuário, uma por vez)

Esta tarefa altera o banco de produção e **exige confirmação explícita do usuário antes de cada passo**.

- [ ] **Step 1:** Abrir o PR da branch `feat/historico-viveiro-financeiro` para a `main`.
- [ ] **Step 2:** Com aprovação, aplicar `alembic upgrade head` no Supabase (0009, 0010 e 0011) **antes** de publicar o backend novo. Se o `DATABASE_URL` não for alcançável, aplicar pelo SQL das migrações via conector do Supabase, como foi feito com a 0008, e atualizar `alembic_version` para `0011`.
- [ ] **Step 3:** Só então publicar o backend e o frontend.
