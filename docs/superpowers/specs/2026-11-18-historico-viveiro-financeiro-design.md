# Histórico do viveiro, insumos com custo médio, vendas com desbaste e Financeiro

Data: 2026-11-18 · Projeto: SAD Carcinicultura (monorepo `backend/` FastAPI + `frontend/` Next.js)

## 1. Intenção e porquê

O gestor precisa enxergar, para cada viveiro, a vida inteira de cada ciclo: o preparo do ambiente antes do cultivo, todos os insumos usados e em que quantidade, a ração consumida, os desbastes e a despesca final, e o resultado financeiro. Com isso ele calcula a lucratividade real de cada ciclo e compara ciclos do mesmo viveiro.

Hoje o sistema não permite isso:
- `CustoOperacional` guarda só data, categoria, descrição e valor. Não há quantidade, unidade nem fase (preparo, cultivo, despesca).
- O ciclo nasce no povoamento. Não há onde registrar o preparo.
- Não existe registro de venda. Há apenas um `receita_real_rs` único ao encerrar o ciclo, que não comporta desbastes.
- Não existe uma visão consolidada por viveiro.
- A tela Financeiro mostra os custos acumulados de um ciclo, sem vendas, sem fases e sem resultado do ciclo fechado.

Requisitos de referência (`documentacao_base/documento_de_requisitos_de_software.md`): RF-012 (ração), RF-014 (FCA), RF-015 (custos por categoria e período), RF-016 (vendas: biomassa, preço, faixa de gramatura, data), RF-017 e RF-018 (receita, custo, lucro, margem). Os códigos RF/RN citados nos comentários do código seguem numeração antiga e não batem com o documento atual.

## 2. Objetivos

1. **Insumos com cadastro e custo médio.** Cadastro de insumos por organização, registro de compras (gestor) e registro de uso por ciclo (gestor e campo). O custo de cada uso é a quantidade vezes o preço médio ponderado das compras no momento do uso.
2. **Fase nos custos.** Todo custo passa a ter uma fase: PREPARO, CULTIVO ou DESPESCA. Lançamentos existentes ficam como CULTIVO.
3. **Etapas do preparo.** Checklist por ciclo com datas e status (secagem, calagem, adubação, abastecimento, tratamento da água, outra). Uso de insumo pode ser ligado a uma etapa.
4. **Vendas com desbaste.** Um ciclo tem várias vendas: desbastes (retiradas parciais durante o cultivo, para reduzir densidade, acelerar crescimento e gerar caixa) e a despesca final. Cada venda reduz a população do viveiro nos cálculos.
5. **Histórico do viveiro.** Por viveiro, lista de ciclos e, por ciclo, linha do tempo e resumo: período, pós-larvas, etapas do preparo, insumos e quantidades, ração (kg e R$), desbastes, biomassa produzida, peso final, sobrevivência, FCA, receita, custo, lucro e margem.
6. **Financeiro completo.** Custos por fase e categoria desde o preparo, vendas, receita, lucro, margem e custo por kg produzido. O lucro é parcial enquanto o ciclo está ativo e definitivo quando está finalizado.

## 3. Fora do escopo e anti-objetivos

Fora do escopo (nesta entrega):
- Pedido de compra, pagamento, logística, nota fiscal, contabilidade fiscal, cadastro completo de fornecedor (o fornecedor é um texto livre opcional na compra).
- Estoque por viveiro (o saldo é por organização).
- Mudanças em ROA/ROE, dashboard integrado e alertas, além do que o efeito do desbaste exigir.

Anti-objetivos (se acontecer, a entrega falhou mesmo que "funcione"):
- O operador de campo ver preço, valor em reais, compras ou receita de vendas.
- Dupla contagem de custo (um uso de insumo contado como consumo e também como custo manual).
- Alterar silenciosamente números de ciclos já fechados. Custos de uso só mudam por reprocessamento determinístico (seção 5.2) ou por correção explícita do gestor.
- Quebrar métricas existentes: `custo_operacional_total_rs`, custo diário estimado, FCA, simulação ΔV.
- Esquecer o desbaste em algum ponto que usa população ou biomassa (seção 5.4).

## 4. Restrições herdadas do projeto

- Stack: FastAPI síncrono, SQLAlchemy 2 (`Mapped`), Pydantic v2, Alembic, Next.js 16 (ler `frontend/node_modules/next/dist/docs/` antes de escrever código Next), UI e código em português do Brasil.
- Toda mudança de modelo precisa de migração. As próximas são 0009 em diante (a 0008 já está aplicada no Supabase). Colunas de tipo/fase/status novas são texto validado pelo schema, não enum nativo do Postgres, como `regra_arredondamento` na migração 0008. Houve problema real de enum nativo antes (`status_ciclo`/`PAUSADO`).
- Isolamento por organização (`services/escopo.py`): toda rota nova que receba ID ou liste dados aplica o escopo, e `tests/test_isolamento_organizacao.py` deve cobrir o acesso cruzado dos recursos novos. Rotas aninhadas em `/ciclos/{ciclo_id}/...` usam `verificar_ciclo_da_organizacao`.
- Auditoria (`registrar_auditoria`) nas mutações de insumos, compras, usos, vendas, etapas e custos.
- Dados financeiros só para GESTOR, no mesmo padrão de `mostrar_financeiro` em `routers/ciclos.py::metricas_atuais`: campos de valor vêm `None` para outros papéis.
- No SQLite os UUIDs são gravados em 32 dígitos hexadecimais e as chaves estrangeiras são aplicadas.
- Novas telas seguem o visual de `inspiracao/` (sidebar navy `#0c1427`, fundo `#f8fafc`, cards brancos) e os componentes de `src/components/ui/`.
- Testes em `backend/tests/` com as fixtures de `conftest.py`; `npm run lint` e `npx tsc --noEmit` sem erros.
- O documento de requisitos é a fonte de verdade e hoje lista "compra, venda ou logística de insumos como processo transacional" como fora do escopo inicial (seção 5.2 do documento). O registro de compras desta entrega é leve (só para custo médio), mas o documento deve ser atualizado: novos requisitos funcionais no final da lista de RFs e uma nota na seção "Fora do escopo inicial" esclarecendo o que entra.

## 5. Decisões já tomadas

### 5.1 Modelo de dados

Todas as tabelas herdam `AuditMixin` e têm dono por organização (direto ou via ciclo).

- **insumos** (por organização): nome (único por organização, sem diferenciar maiúsculas), unidade de uso (texto: kg, L, un, saco...), categoria de custo gerada (valor de `CategoriaCusto`, padrão OUTROS), ativo. As categorias RACAO e POS_LARVAS **não** são aceitas em insumos: a ração continua sendo custo RACAO lançado à mão mais os manejos alimentares, e as pós-larvas continuam sendo o custo lançado no povoamento. Isso evita pedir ao campo o mesmo quilo em dois lugares e dupla contagem do maior custo do ciclo.
- **compras_insumo**: insumo, data da compra, quantidade na unidade de uso (> 0), valor total em R$ (> 0), fornecedor (texto opcional), observação. A interface ajuda a converter embalagem em unidade de uso (3 sacos de 25 kg a R$ 80 cada = 75 kg por R$ 240), mas o que se grava é quantidade e valor total.
- **consumos_insumo** (uso): ciclo, insumo, data do uso, quantidade (> 0), fase, etapa do preparo (opcional), custo operacional gerado (opcional), preço unitário aplicado (R$ por unidade de uso, 4 casas; vazio = pendente de valor), quem registrou, observação.
- **custos_operacionais**: nova coluna `fase` (padrão CULTIVO).
- **etapas_preparo**: ciclo, tipo (SECAGEM, CALAGEM, ADUBACAO, ABASTECIMENTO, TRATAMENTO_AGUA, OUTRA), data de início, data de fim, status (PENDENTE, EM_ANDAMENTO, CONCLUIDA, NAO_REALIZADA), observação (por exemplo, o motivo de não ter sido realizada). Ao planejar um ciclo, a lista sugerida (as cinco primeiras etapas, em ordem) é criada como PENDENTE; o gestor pode editar, remover e acrescentar etapas.
- **vendas**: ciclo, data da venda, tipo (DESBASTE ou DESPESCA_FINAL), biomassa em kg (> 0), peso médio em g (> 0, define a faixa de preço), animais estimados (inteiro, derivado de biomassa × 1000 ÷ peso médio), preço por kg, valor total (= biomassa × preço), comprador (texto opcional). O preço vem sugerido pela tabela de preços (`buscar_preco_por_gramatura` com a regra de arredondamento da organização) e é editável.

O preparo usa o ciclo no status PLANEJADO que já existe. Não se cria status novo. Todo ciclo novo nasce PLANEJADO e passa pelo preparo (seção 5.7). A coluna `data_povoamento` guarda a data prevista até o povoamento e passa a guardar a data real em seguida.

### 5.2 Insumos: preço médio ponderado móvel

- Em cada compra: `preço médio = (saldo × preço médio anterior + valor da compra) ÷ (saldo + quantidade comprada)`. O saldo é a soma das compras menos a soma dos usos do insumo na organização.
- Em cada uso: custo = quantidade × preço médio vigente na data do uso. O saldo diminui e o preço médio não muda na saída. Cada uso gera um `CustoOperacional` (categoria do insumo, descrição com o nome do insumo, fase do uso, valor) ligado ao uso. Assim, financeiro, custo diário estimado e simulador continuam funcionando sem mudança. Excluir ou corrigir o uso atualiza ou remove o custo gerado.
- **Fase e custo diário.** Custos de fase PREPARO e DESPESCA entram no custo total, no lucro e no lucro de despescar hoje, mas **não** no custo diário estimado (`estimar_custo_diario` passa a considerar só custos de fase CULTIVO). Sem isso, gastos pontuais do preparo (cal, secagem, abastecimento) inflariam o custo diário de manter o viveiro e poderiam inverter a recomendação do ΔV. O `co_total` do simulador continua somando todos os custos.
- **Data passada só por opção explícita (lançamento retroativo).** Nas compras de insumo, nos usos de insumo e nas vendas, a data nasce como hoje e fica travada. Para informar uma data anterior a hoje, o usuário marca "Lançamento retroativo", o que libera o seletor de datas e mostra o aviso de que o custo médio do insumo será recalculado. A regra vale também na API: um campo `retroativo` (padrão falso) é obrigatório quando a data é anterior a hoje, e sem ele a rota responde 422 com mensagem clara, para que um erro de digitação ou um cliente fora da interface não grave data passada sem querer. Datas no futuro continuam recusadas, e a data continua não podendo ser anterior ao povoamento, exceto nos lançamentos de fase PREPARO. O lançamento retroativo fica marcado e auditado, e o gestor vê um indicador "retroativo" no item. CAMPO e VIGIA também podem marcar retroativo no uso de insumo (esquecer de lançar o dia anterior é comum). Esta regra não muda as telas e rotas que já existem (custos manuais, biometrias, manejos). As datas das etapas do preparo não seguem esta regra, porque podem ser planejadas no futuro.
- Eventos fora de ordem: qualquer inclusão, alteração ou exclusão de compra ou uso com data passada dispara o **reprocessamento** do insumo: reaplica compras e usos em ordem de data (na mesma data, compras antes de usos, depois pela ordem de criação) e recalcula preço aplicado e custo gerado de todos os usos daquele insumo. Os volumes são pequenos; o reprocessamento é feito de forma síncrona.
- Uso com saldo insuficiente: permitido, para não travar a operação no campo. Usa o último preço médio conhecido e o gestor vê aviso de saldo negativo.
- Insumo sem nenhuma compra anterior ao uso: o uso fica "pendente de valor" (sem preço, sem custo gerado) até haver uma compra anterior ou igual na data, e então o reprocessamento gera o custo. Um aviso aparece para o gestor.
- Estoque que já existe hoje entra como uma compra com o preço pago.
- O gestor pode corrigir o preço unitário aplicado a um uso específico (por exemplo pela nota fiscal). A correção explícita fica auditada e é preservada pelo reprocessamento.
- O preço unitário guarda 4 casas; o valor do custo é arredondado a centavos só no total do uso.

### 5.3 Vendas e finalização do ciclo

- Um ciclo pode ter vários desbastes e **várias vendas do tipo DESPESCA_FINAL** (a despesca final pode ser vendida a mais de um comprador ou em cargas com pesos diferentes). Não há restrição de unicidade. Só o gestor lança vendas (a venda traz valores).
- **Fonte única de verdade:** a soma das vendas. Financeiro e histórico leem a soma das vendas ao vivo. As colunas `biomassa_colhida_kg` e `receita_real_rs` do ciclo são mantidas em sincronia (recalculadas a cada mudança em vendas do ciclo) para compatibilidade com o que já as lê.
- **Encerramento (`CicloEncerrar` atual):** `biomassa_colhida_kg` e `receita_real_rs` do payload passam a ser opcionais. Se vierem, o sistema registra uma venda DESPESCA_FINAL adicional com esses valores, peso médio da última biometria e preço = receita ÷ biomassa. Se não vierem, usa as vendas já registradas. O encerramento exige ao menos uma venda DESPESCA_FINAL e biometria final. `data_despesca_real` é a data da última venda DESPESCA_FINAL (ou a data de hoje quando a venda vem do payload).
- **Encerramento bloqueado** enquanto houver usos de insumo "pendentes de valor" no ciclo, com mensagem que diz quantos são. O gestor resolve registrando a compra faltante ou corrigindo o preço do uso. Assim o lucro "definitivo" nunca omite custo em silêncio.
- **Ciclo FINALIZADO:** o gestor ainda pode corrigir vendas, usos e compras (a correção do preço médio de uma compra antiga muda custos de ciclos fechados por causa do reprocessamento). Toda correção é auditada e a tela do ciclo mostra um aviso de "valores recalculados em <data>" para o gestor. CAMPO e VIGIA não alteram ciclo finalizado.

### 5.4 Efeito do desbaste nos cálculos

Um desbaste retira animais da água. Todo ponto que usa população ou biomassa passa a descontar os animais vendidos:

- **População atual** = pós-larvas × taxa de sobrevivência vigente − soma dos animais estimados das vendas (nunca abaixo de zero). Deve existir uma função central única, usada por `routers/ciclos.py::metricas_atuais`, `routers/manejos.py` (várias chamadas, inclusive o consumo relativo do motor fuzzy), `routers/rondas.py` e `routers/simulacao.py`. Hoje essas rotas chamam `calcular_populacao_atual(pos_larvas, taxa)` diretamente.
- **Sobrevivência:** a `taxa` de sobrevivência continua sendo a sobrevivência natural das pós-larvas originais. Os estimadores de `services/sobrevivencia.py` (`sobrevivencia_implicita_pct`, `confrontar_vivos`) e as contas por mortos em `routers/manejos.py` (hoje divididos por `pos_larvas`) passam a considerar os **animais já vendidos até aquela data**: a sobrevivência implícita de um dia é `(animais indicados pela ração + vendidos até o dia) ÷ pós-larvas`, o que preserva a `taxa` como sobrevivência natural das pós-larvas originais; as contas por mortos contados não mudam. Sem isso, o consumo de ração menor depois de um desbaste seria lido como mortalidade, e o ajuste fuzzy semanal derrubaria a taxa de sobrevivência até 12 pontos percentuais por semana.
- **Função central com data de referência:** a função de população recebe uma data ("até"). `registrar_manejo` calcula a população de uma data passada e não pode descontar vendas posteriores a ela. Sem data, vale hoje.
- **Biomassa atual** decorre da população atual × peso médio.
- **FCA** = ração total ÷ (biomassa atual + biomassa vendida − biomassa inicial). O parâmetro `biomassa_atual_kg` de `calcular_fca` recebe a soma.
- **Densidade:** mantém-se a densidade de povoamento e passa a existir também a densidade atual (população atual ÷ área).
- **Lucro e simulação:** o lucro de despescar hoje e o lucro projetado incluem a receita já recebida de vendas anteriores. O ΔV (diferença entre projetado e hoje) não muda por isso, mas os valores absolutos passam a ser corretos. A varredura dia a dia (`melhor_dia`) já existe e continua valendo.
- Os números de densidade, FCA e simulação de ciclos com desbaste mudam em relação ao que o sistema mostrava antes. Ciclos sem venda não mudam.

### 5.5 Permissões

| Recurso | GESTOR | CAMPO | VIGIA |
|---|---|---|---|
| Cadastro de insumos | cria e edita, vê preços | vê nome, unidade e saldo (só quantidade) | vê só nome e unidade (para escolher o produto usado); sem saldo |
| Compras | cria, edita, exclui, vê valores | sem acesso | sem acesso |
| Uso de insumo | cria, edita, exclui, corrige preço | cria e vê os usos do ciclo só com quantidade (campos de valor vêm `None`) | cria (por exemplo, produto usado de madrugada para equilibrar os parâmetros); não consulta a lista de usos |
| Etapas do preparo | cria, edita, exclui | vê e atualiza status e datas | sem acesso |
| Vendas | cria, edita, exclui | sem acesso | sem acesso |
| Custos operacionais, Financeiro, histórico com valores | acesso total | sem valores em reais | sem valores em reais |

Decisão do dono do produto: o VIGIA lança uso de insumo, porque aplica produtos durante a noite, mas não consulta o histórico de usos. Para escolher o produto ele precisa ver a lista de insumos, só com nome e unidade.

### 5.6 Histórico e Financeiro

- **Histórico do viveiro:** rota por viveiro (por exemplo `GET /viveiros/{id}/historico`) com a lista de ciclos e o resumo de cada um (campos do objetivo 5). Para campo e vigia, os campos em reais vêm `None`.
- **Aba Histórico** no detalhe do viveiro, em linha do tempo: preparo (etapas e insumos), povoamento, biometrias, insumos e ração, desbastes, despesca final e resultado. `frontend/src/app/gestor/viveiros/[id]/page.tsx` já tem mais de 1.300 linhas; o conteúdo novo vai em componente separado.
- **Financeiro:** custos por fase e categoria, vendas, receita, lucro, margem e custo por kg produzido (custo total ÷ biomassa total vendida).
- **Dois números de lucro, sempre com rótulo próprio.** *Lucro realizado* = receita das vendas − custos lançados até a data; é o número principal do Financeiro e, com o ciclo finalizado, é o definitivo. *Lucro estimado se despescar hoje* = lucro realizado + biomassa atual na água × preço de hoje; é o que `metricas_atuais` já mostra, agora incluindo as vendas anteriores. Nenhuma tela mostra "lucro" sem dizer qual dos dois é.
- **Ciclo finalizado:** sobrevivência final = animais vendidos ÷ pós-larvas × 100. Peso final = peso médio ponderado pela biomassa das vendas DESPESCA_FINAL. FCA final = ração total ÷ (biomassa vendida total − biomassa inicial), com a biomassa atual forçada a zero (a água foi esvaziada); não se conta população estimada restante.
- **Detalhe de insumos e ração:** insumos agregados por tipo com quantidade e custo; ração por período com kg, custo e FCA parcial. O preço médio do kg de ração sai do custo de ração lançado dividido pelos kg dos manejos, como já faz `estimar_custo_diario`.

### 5.7 Ciclo: planejar, preparar e povoar (preparo obrigatório)

Decisão do dono do produto: **todo ciclo novo passa obrigatoriamente pelo preparo**. Lá o gestor marca, etapa por etapa, se ela foi feita ou não.

- **Planejar ciclo** (só GESTOR): pede apenas o viveiro, a data prevista de povoamento (qualquer data, por ser só previsão) e, opcionalmente, a tabela alimentar. O ciclo nasce PLANEJADO com a lista sugerida de etapas. `POST /ciclos/` passa a fazer isto e deixa de criar ciclo ativo.
- **Preparar:** cada etapa fica PENDENTE, EM_ANDAMENTO, CONCLUIDA ou NAO_REALIZADA ("não fez"). O uso de insumo e os custos de fase PREPARO podem ser lançados no ciclo planejado, com data anterior ao povoamento (seção 5.2, regra retroativa). O campo atualiza status e datas das etapas.
- **Povoar** (só GESTOR, rota nova, por exemplo `POST /ciclos/{id}/povoar`): pede data real de povoamento, quantidade de pós-larvas, custo de aquisição e, opcionalmente, peso médio da PL e laboratório de origem. Cria o custo POS_LARVAS como o `criar_ciclo` atual já faz, grava a data real em `data_povoamento` e muda o status para ATIVO. **O povoamento é bloqueado enquanto houver etapa PENDENTE ou EM_ANDAMENTO**: cada etapa precisa estar CONCLUIDA ou NAO_REALIZADA. Assim o preparo é de fato uma passagem obrigatória, mesmo quando nenhuma etapa foi feita.
- **Um ciclo aberto por viveiro:** `ciclo_aberto_do_viveiro` passa a considerar PLANEJADO, ATIVO e PAUSADO. Só se planeja um ciclo em viveiro sem nenhum deles. Planejar, povoar e retomar revalidam a regra.
- **Reagendar** (só GESTOR): enquanto o ciclo está PLANEJADO, o gestor pode mudar a data prevista de povoamento, a tabela alimentar e o viveiro. O que já foi lançado (etapas, usos de insumo, custos) permanece no ciclo. É o caminho comum quando o plano é adiado.
- **Cancelar planejamento** (só GESTOR): um ciclo PLANEJADO que não vai acontecer pode ser cancelado (status CANCELADO), liberando o viveiro. Sem isso, um planejamento abandonado prenderia o viveiro pela regra de um ciclo aberto.
- **Migração da etapa 3** (numerada 0011 no plano de implementação; as etapas 1 e 2 usam 0009 e 0010): `quantidade_pos_larvas` e `custo_aquisicao_pl` do ciclo passam a aceitar vazio. No Supabase isso é uma alteração de produção (remover NOT NULL), a ser aplicada antes de publicar o backend novo. No SQLite usa `batch_alter_table`.
- **Código que lê as pós-larvas** (`metricas_atuais`, densidade, exportação CSV, histórico, simulação, manejos, rondas) deve tolerar ciclo PLANEJADO sem pós-larvas: densidade e população vazias, sem erro. Biometrias, manejos, rondas e simulação continuam exigindo ciclo ATIVO.
- **Ciclos que já existem** (ATIVO, PAUSADO ou FINALIZADO) não passam pelo preparo. O gestor pode registrar o preparo deles depois: etapas, usos e custos de fase PREPARO com data anterior ao povoamento e marca retroativa.
- **Quebra de compatibilidade deliberada:** clientes que enviavam pós-larvas em `POST /ciclos/` deixam de criar ciclo ativo. O corpo de planejar rejeita campos desconhecidos (422), para que um cliente antigo falhe de forma visível e não crie um ciclo planejado ignorando as pós-larvas em silêncio. Isso afeta: a fixture `novo_ciclo` em `backend/tests/conftest.py` e os testes que chamam `/api/v1/ciclos/` diretamente (`test_api_dados_reais.py`, `test_api_integridade.py`, `test_calculos_referencia.py`, `test_isolamento_organizacao.py`, `test_simulacao_safra.py`, `test_sobrevivencia.py`), o formulário de criação de ciclo em `frontend/src/app/gestor/viveiros/[id]/page.tsx` (`ciclosApi.criar`) e os scripts de `testsprite_tests/`. A fixture passa a planejar e povoar (todas as etapas marcadas como NAO_REALIZADA), para que os testes existentes continuem rodando com ciclos ativos.

## 6. Ordem de entrega

Cada etapa tem sua migração, seus testes e é entregável sozinha:

1. **Insumos:** cadastro, compras, uso, preço médio, reprocessamento, fase no custo, custo automático. Telas de cadastro, compras e uso.
2. **Vendas com desbaste:** modelo, rotas, função central de população, FCA, densidade atual, lucro, finalização do ciclo. Tela de vendas.
3. **Ciclo em preparo (planejar, etapas, povoar):** migração 0009 e a mudança de compatibilidade da seção 5.7 (fixture de testes, formulário de ciclo, testsprite), etapas do preparo com a lista sugerida e a ligação com o uso de insumo, ação "Povoar" e telas. É a etapa que quebra o fluxo atual; as etapas 1 e 2 não dependem dela.
4. **Histórico e Financeiro:** rota de histórico, aba Histórico, Financeiro completo, atualização do documento de requisitos.

## 7. O que fica para quem for construir

- Nomes exatos de rotas, schemas, colunas e componentes, seguindo os padrões do repositório.
- A forma de implementar o reprocessamento e a função central de população, desde que cumpram a seção 5.
- Detalhes de interface: layout da linha do tempo, filtros, formatação e textos.
- A estratégia de testes, desde que cubra: preço médio com compras e usos fora de ordem, uso sem saldo e sem compra, isolamento entre organizações, ocultação de valores para campo, efeito do desbaste em população, FCA e lucro, e finalização com várias vendas.
