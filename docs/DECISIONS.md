# DECISIONS.md — Registro de Decisoes de Arquitetura

> Formato ADR: estado, contexto, decisao e consequencias. Novas decisoes estruturais devem ser registradas antes da implementacao.

---

## ADR-001 — Projeto separado do LivrePL

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** O harness precisa evoluir com simulacoes do framework Protheus sem aumentar o escopo do interpretador de linguagem pura.
- **Decisao:** Manter o AdvPL TestLab em repositorio e diretorio proprios, usando o LivrePL como dependencia local em diretorio irmao.
- **Consequencias:** O LivrePL original permanece intacto. A estrutura atual exige que `livrePL/` e `advpl-testlab/` tenham o mesmo diretorio pai.

## ADR-002 — Extensao por heranca e registro de builtins

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** Funcoes como `GetMV` pertencem ao framework Protheus, nao a sintaxe central do AdvPL.
- **Decisao:** Criar `FixtureInterpreter(Interpreter)` e estender `_build_builtins()` chamando primeiro `super()`.
- **Consequencias:** Lexer, parser, escopos e builtins originais sao reutilizados sem duplicacao. Sintaxe nova so sera introduzida quando um caso real exigir.

## ADR-003 — Parametro ausente em GetMV gera erro

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** Retornar `NIL` para parametro ausente pode esconder fixture incompleto e produzir falso positivo na regra de negocio.
- **Decisao:** `GetMV` gera `AdvPLRuntimeError` contendo o nome do parametro quando a chave nao existe.
- **Consequencias:** Testes falham cedo e com mensagem clara. Um valor default podera ser proposto futuramente como extensao explicita da assinatura.

## ADR-004 — Formato evolutivo de tabelas no fixture

- **Data:** 21/09/2026
- **Estado:** Substituida pela ADR-008
- **Contexto:** A forma inicial usa uma lista de registros, mas fases futuras podem precisar de metadados de campos, indices e ordem.
- **Decisao:** Aceitar tanto lista simples quanto objeto JSON por alias, preservando o formato inicial.
- **Consequencias:** Fixtures atuais nao precisam ser migrados. A semantica do objeto com metadados sera definida na Fase 2.

## ADR-005 — Nome AdvPL TestLab

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** O nome provisorio `livrepl-fixture-harness` era tecnico e pouco memoravel.
- **Decisao:** Adotar **AdvPL TestLab**, com diretorio e repositorio `advpl-testlab`.
- **Consequencias:** Codigo e documentacao usam o novo nome; o vinculo tecnico com o LivrePL continua descrito no README e no CONTEXT.

## ADR-006 — Fontes funcionais do desafio1 como corpus de evolucao

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** Exemplos artificiais confirmam infraestrutura, mas nao revelam todas as assinaturas, sintaxes e combinacoes usadas em customizacoes Protheus reais.
- **Decisao:** Usar `desafios-aprendizado/desafio1-solicitacao-compra` como corpus de referencia, isolando primeiro funcoes puras e depois avancando para aliases, navegacao e escrita.
- **Consequencias:** Cada builtin novo precisa estar ligado a um caso concreto. O corpus de origem nao e copiado integralmente nem alterado; trechos portaveis ficam em `examples/real-cases/` com origem documentada.

## ADR-007 — GetMV com default preserva modo estrito

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** `U_SolMailCfg()` usa a assinatura real `GetMV(cParam, lHelp, uDefault)`, enquanto a Fase 1 suportava somente um argumento e gerava erro para chaves ausentes.
- **Decisao:** Aceitar de um a tres argumentos. O terceiro argumento e retornado apenas quando o parametro nao existe; sem terceiro argumento, a ausencia continua gerando `AdvPLRuntimeError`. `lHelp` e aceito sem efeito de interface.
- **Consequencias:** Fixtures incompletos continuam falhando no modo estrito e fontes reais podem declarar defaults de texto, numero, logico ou valor calculado.

## ADR-008 — Colecoes JSON como listas de objetos nomeados

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** O formato inicial representava `parametros` e `tabelas` como objetos. Foi definido que ambas as colecoes devem ser listas e que cada tabela deve possuir um objeto proprio para registros e futuros metadados.
- **Decisao:** Novos fixtures usam `parametros: [{"NOME": valor}]` e `tabelas: [{"ALIAS": {"registros": []}}]`. Cada item declara exatamente um nome; duplicidades case-insensitive sao rejeitadas.
- **Consequencias:** A ordem declarada fica explicita e o objeto da tabela pode evoluir sem mudar a colecao. O carregador normaliza internamente para dicionarios e continua aceitando o formato antigo apenas para compatibilidade.

## Evidencias da entrega inicial

## ADR-009 — Executor hibrido para fontes reais

- **Data:** 21/09/2026
- **Estado:** Substituida pela ADR-013
- **Contexto:** `TRNSOL02.prw` combina linguagem AdvPL, SQL via `FWExecStatement`, alias dinamico e interface `FWBrowse`, recursos ainda nao compreendidos integralmente pelo LivrePL.
- **Decisao:** A CLI descobre a primeira `User Function` e usa o LivrePL para fontes dentro da cobertura atual. Quando encontra o padrao de consulta com `FWExecStatement` e `FWBrowse`, usa um adaptador headless guiado pelo proprio fonte e por `consultas` do fixture.
- **Consequencias:** O fonte original executa sem alteracao e sem Protheus. O adaptador nao representa ainda semantica arbitraria de todas as APIs; sua cobertura sera substituida incrementalmente por objetos, aliases e builtins genericos.

## ADR-010 — Fixture localizado junto ao projeto alvo

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** O comando deve funcionar no diretorio do `.prw`, sem exigir caminhos relativos ao repositorio do TestLab.
- **Decisao:** Procurar `advpl-testlab.json` no diretorio do fonte e, em seguida, nos diretorios pais. `--fixture` continua disponivel para sobrescrita explicita.
- **Consequencias:** Cada projeto AdvPL pode versionar sua propria simulacao. O fixture de `desafios-aprendizado` contem Z02 a Z06 e a consulta de aceite de `Z04CON`.

## ADR-011 — Confirmacoes identificadas por fonte e conteudo

- **Data:** 22/09/2026
- **Estado:** Aceita
- **Contexto:** `MsgYesNo` pode aparecer varias vezes no mesmo fonte e em fontes diferentes. Um unico retorno global nao identifica qual decisao esta sendo simulada e pode esconder cenarios incompletos.
- **Decisao:** Configurar confirmacoes em `especificidadesPrw`, usando `fonte`, `nome`, `conteudo` e `retorno`. O conteudo corresponde aos argumentos ja avaliados e formatados como chamada AdvPL. `MsgYesNo` exige retorno logico e nao produz texto.
- **Consequencias:** Cada decisao fica explicita e deterministica. Regras ausentes falham cedo. O retorno global anterior em `funcoes` permanece como fallback de compatibilidade.

## ADR-012 — Interface Protheus representada como efeito textual

- **Data:** 22/09/2026
- **Estado:** Aceita
- **Contexto:** Testes headless precisam observar mensagens e atravessar fontes com declaracoes de dialogo sem depender de SmartClient.
- **Decisao:** Representar `Define MSDialog`, `MsgAlert` e `MsgInfo` por linhas no terminal. Controles `@` e `Activate Dialog` sao no-op. Nenhuma janela e criada e nenhuma acao de botao e executada.
- **Consequencias:** Mensagens tornam-se verificaveis em testes. Fluxos que dependem de preenchimento ou clique em controles ainda precisam de simulacao propria.

## ADR-013 — TRNSOL02 sempre passa pelo interpretador

- **Data:** 22/09/2026
- **Estado:** Aceita
- **Contexto:** O adaptador inicial reconhecia `FWExecStatement` e `FWBrowse`, mas nao executava o corpo de `Z04CON`, `fAskFiltros` ou `fGerarExcel`.
- **Decisao:** Remover a deteccao especializada do executor. Todo fonte passa pelo preparo sintatico, parser e `FixtureInterpreter`. Integracoes externas sao objetos e builtins simulados: dialogos, statements, aliases, browse e arquivos virtuais.
- **Consequencias:** As tres funcoes de `TRNSOL02.prw` sao validadas e executadas nos cenarios automatizados. SQL, UI e sistema de arquivos continuam headless e deterministas.

## ADR-014 — Validacao de sintaxe independente da execucao

- **Data:** 22/09/2026
- **Estado:** Aceita
- **Contexto:** Executar somente a funcao de entrada nao oferece um comando explicito para conferir todas as funcoes de um fonte sem exigir fixture de runtime.
- **Decisao:** Disponibilizar `advpl-testlab -validate arquivo.prw`, usando o mesmo preparo e parser de `-run` sem executar nenhuma funcao.
- **Consequencias:** Sintaxe sem suporte falha antes da execucao e informa a linha. O `TRNSOL02.prw` valida tres funcoes.

## ADR-015 — Diagnostico usa coordenadas do fonte original

- **Data:** 22/09/2026
- **Estado:** Aceita
- **Contexto:** O pre-processador removia diretivas como `#include`, deslocando as linhas entregues ao parser. Alem disso, uma atribuicao incompleta era percebida somente no token `NEWLINE` seguinte.
- **Decisao:** Preservar uma linha vazia para cada diretiva removida e, quando o token inesperado for a quebra de linha, apontar a instrucao anterior. A CLI mostra tipo, mensagem, trecho, marcador, arquivo, linha e coluna, com ANSI vermelho apenas em terminais interativos.
- **Consequencias:** Um erro em `Local nI :=` na linha 31 passa a ser informado como `arquivo.prw:31`, mesmo com diretivas no inicio do fonte. `NO_COLOR` e saidas sem TTY continuam produzindo texto puro.

## ADR-016 — Validacao distingue identificador de literal Nil

- **Data:** 22/09/2026
- **Estado:** Aceita
- **Contexto:** O parser aceita corretamente qualquer identificador, mas `-validate` encerrava apos a analise sintatica. Assim, `Local oStmt := Nilo` era aceito e somente poderia falhar se a execucao alcancasse essa linha.
- **Decisao:** Executar uma analise semantica sobre a AST antes de `-validate` e `-run`. Leituras devem corresponder a parametro, declaracao local/estatica/privada/publica, variavel criada por atribuicao ou global simulada conhecida.
- **Consequencias:** `Nilo` gera `SemanticError` antes de qualquer execucao, com arquivo, linha e coluna. `Nil` continua literal. Atribuicoes sem declaracao continuam podendo criar `PRIVATE` implicitamente, conforme a semantica ja adotada pelo LivrePL.

## ADR-017 — Chamadas devem resolver para uma funcao conhecida

- **Data:** 22/09/2026
- **Estado:** Aceita
- **Contexto:** Uma chamada e sintaticamente valida independentemente do nome. Por isso, `GetAreaTESTE()` passava no parser e so falharia ao ser executada.
- **Decisao:** A analise semantica aceita apenas funcoes do fonte, built-ins do LivrePL/TestLab, classes instanciaveis ou funcoes simuladas em `funcoes` no fixture. `-validate` descobre o fixture do projeto e tambem respeita `--fixture` explicito.
- **Consequencias:** Erros de digitacao em nomes de funcao falham antes de qualquer efeito colateral. Integracoes externas ainda podem ser declaradas deterministicamente no JSON.

## ADR-018 — Dependencias locais explicitas e SMTP headless

- **Data:** 22/09/2026
- **Estado:** Aceita
- **Contexto:** Fontes AdvPL reais chamam `User Function` de outros `.prw`, mas o comentario nao padrao que registra essa relacao era apenas orientativo. `ENVEMAIL.prw` tambem depende de objetos SMTP que nao podem acessar rede durante testes.
- **Decisao:** Interpretar `//usePrw('arquivo.prw')` como metadado local recursivo, resolver o caminho relativo e carregar as funcoes referenciadas. Simular `TMailManager`/`TMailMessage` em memoria, com resultados controlados por `ambiente` e captura de mensagens sem credenciais.
- **Consequencias:** Pessoas, agentes e TestLab compartilham um mapa de dependencias direto. Chamadas `U_Nome()` resolvem uma `User Function Nome()` carregada. Testes de e-mail exercitam toda a logica sem conexao SMTP ou envio real.

## ADR-019 — NOTIFSOL usa aliases estaticos e argumentos de entrada deterministas

- **Data:** 22/09/2026
- **Estado:** Aceita
- **Contexto:** `NOTIFSOL.prw` depende de Z02/Z03, navegacao por indice, `While` direto e de um parametro `cEvento`, que nao podia ser informado pela CLI.
- **Decisao:** Adaptar aliases estaticos para o runtime em memoria, implementar navegacao de prefixo por `DbSeek` e expor `--args-json` como array de argumentos da funcao de entrada.
- **Consequencias:** Todos os eventos do fonte executam deterministicamente sem DBAccess ou SMTP. A busca simula a chave pela ordem dos campos do registro e nao substitui a definicao real de indices do Protheus.

## ADR-020 — TRNSOL01 usa indices declarados e transacoes em memoria

- **Data:** 22/09/2026
- **Estado:** Aceita
- **Contexto:** Os fluxos de `TRNSOL01.prw` precisam de ordem/chave Z03/Z05, bloqueios, rollback e formularios MVC sem AppServer.
- **Decisao:** Permitir `indices` por tabela no fixture, navegar Z04/Z05/Z06 em memoria, filtrar o grid pelo cabecalho corrente e criar adaptadores headless para MVC/dialogo. Uma falha `RECLOCK_ALIAS: false` permite exercitar rollback deterministico.
- **Consequencias:** Os fluxos de negocio podem ser testados sem efeitos externos; layout e callbacks de controles `@` nao sao executados/validados internamente, e os indices nao sao importados de SX2/SIX.

## ADR-021 — FAT006 usa contexto do ponto de entrada em fixture local

- **Data:** 22/09/2026
- **Estado:** Aceita
- **Contexto:** Os fontes FAT006 recebem `PARAMIXB` e buffers de tela do Protheus e consultam/gravam SC5 sem depender de uma sessao real.
- **Decisao:** Expor variaveis declaradas em `ambiente` como globais semanticas, adaptar indices de matriz e metodos de alias necessarios, e simular `ErrorBlock` apenas como armazenamento/restauracao do bloco.
- **Consequencias:** Os caminhos exercitados ficam reproduziveis em memoria; a semantica completa de erro, bloqueio concorrente e emissao fiscal continua fora do TestLab.

## ADR-022 — Um fixture por pasta de desafio

- **Data:** 22/09/2026
- **Estado:** Aceita
- **Contexto:** O desafio0 tinha JSON junto aos fontes; o desafio1 herdava um JSON da raiz do repositorio.
- **Decisao:** Mover o fixture do desafio1 para `desafio1-solicitacao-compra/advpl-testlab.json` e recomendar um fixture local por caso. A busca da CLI continua priorizando o diretorio do `.prw`.
- **Consequencias:** Os cenarios nao se misturam; caminhos explicitos dos testes e da documentacao foram atualizados, sem alterar o executor.

## ADR-023 — JSONC para fixtures comentados

- **Data:** 23/09/2026
- **Estado:** Aceita
- **Contexto:** Os cenarios reais precisam explicar escolhas de dados sem perder a legibilidade; JSON estrito nao permite comentarios.
- **Decisao:** Ler `.jsonc` com comentarios de linha/bloco e virgulas finais, mantendo `.json` estrito. A descoberta prefere `.jsonc` quando ambos estao no mesmo diretorio, sem mudar a prioridade do diretorio mais proximo.
- **Consequencias:** Os cenarios podem ser comentados sem dependencias externas; fixtures JSON antigos continuam funcionando.

## ADR-024 — Suite propria sem dependencias no corpus externo

- **Data:** 23/09/2026
- **Estado:** Aceita
- **Contexto:** Testes do TestLab liam `.prw` e fixtures do projeto `desafios-aprendizado`; testes de `TRNSOL02.prw` ficavam ignorados porque o fonte nao existe no corpus atual.
- **Decisao:** Manter testes unitarios e fixtures locais no TestLab; transferir os testes de integracao dos desafios para `desafios-aprendizado/tests` e retirar testes obsoletos que exigiam `TRNSOL02.prw`.
- **Consequencias:** A suite do TestLab roda independentemente do projeto dos desafios; as integracoes reais continuam testaveis no projeto que possui os fontes.

## ADR-025 — Perfil de nomes delegado ao LivrePL

- **Data:** 23/09/2026
- **Estado:** Aceita
- **Contexto:** O limite historico de dez caracteres afeta a identidade de simbolos, nao apenas a camada simulada do Protheus.
- **Decisao:** Expor `--name-profile modern|legacy10` em validacao e execucao e delegar a politica ao LivrePL. A validacao semantica do TestLab usa a mesma chave normalizada, incluindo funcoes de fixture.
- **Consequencias:** Nao ha regras de truncamento independentes nos dois projetos; o padrao moderno preserva a compatibilidade existente.

## ADR-026 — PRIVATE na validacao semantica

- **Data:** 23/09/2026
- **Estado:** Aceita
- **Contexto:** Fontes MVC declaram `PRIVATE` na entrada e a consultam em funcoes auxiliares. A verificacao isolada por funcao acusa falso positivo e aponta a primeira ocorrencia do nome, nao a leitura.
- **Decisao:** Considerar nomes `PRIVATE` declarados em qualquer fonte carregado como potencialmente visiveis entre funcoes na analise estatica. Manter `LOCAL` restrito a sua funcao. A disponibilidade efetiva de `PRIVATE` continua sendo verificada em tempo de execucao pelo escopo dinamico do LivrePL. Usar a linha do no da AST para localizar erros semanticos.
- **Consequencias:** `-validate` nao garante que uma rota runtime tenha inicializado a `PRIVATE`; em compensacao, nao bloqueia codigo AdvPL valido com escopo dinamico.

## ADR-027 — Validacoes MVC ligadas ao fonte e a fixture

- **Data:** 23/09/2026
- **Estado:** Aceita
- **Contexto:** O browse headless nao executa automaticamente `MenuDef` ou `ModelDef`, entao `VIEWDEF` com nome de modulo inexistente e `SetPrimaryKey` com campo ausente podiam passar em `-run`.
- **Decisao:** Validar estaticamente acoes literais `VIEWDEF.<modulo>` de `ADD OPTION` contra as `User Function` carregadas, e campos literais de `SetPrimaryKey` contra o dicionario da fixture. Campos de chave calculados dinamicamente tambem serao verificados quando `SetPrimaryKey` for executado.
- **Consequencias:** `-validate` e `-run` falham cedo nesses erros, inclusive em funcoes MVC que a entrada nao chamou. A verificacao estatica nao pretende cobrir acoes ou chaves construidas dinamicamente.

## ADR-028 — Cenarios MVC nomeados com inclusao isolada

- **Data:** 23/09/2026
- **Estado:** Aceita
- **Contexto:** O browse headless nao exercitava o `bPost` de `MPFormModel`, e a validacao de inclusao precisava de entradas e expectativas reproduziveis.
- **Decisao:** Adicionar `cenariosMvc` a fixture JSONC e `--mvc-case` ao `-run`. Ao ativar o browse, chamar `ModelDef` no escopo da entrada, aplicar `dados` a um unico `AddFields`, executar o `bPost`, incluir somente em memoria quando ele aprovar e conferir `esperado.salvou`, `totalRegistros` e `registro` quando informados.
- **Consequencias:** Cada invocacao comeca dos registros originais. Nao ha escrita no fixture nem simulacao de UI, `ViewDef`, grid ou AppServer. Ausencia de `bPost`, modelo/campo desconhecido e divergencia de expectativa produzem falha explicita.

## ADR-029 — Validacao antecipada de IDs de submodelo MVC

- **Data:** 24/09/2026
- **Estado:** Aceita
- **Contexto:** `-run` sem cenario apenas abre o browse e nao chama `ModelDef`/`bPost`; um `GetValue('ZA1MASTE', ...)` incorreto passava, embora falhasse com `--mvc-case`.
- **Decisao:** Quando um fonte declara IDs literais em `AddFields`/`AddGrid`, conferir os primeiros argumentos literais de `GetValue` com dois argumentos contra esses IDs na analise semantica. Se houver declaracao de ID dinamico, nao presumir que o conjunto literal seja completo. Manter verificacao runtime para IDs dinamicos e fontes separados.
- **Consequencias:** `-validate` e `-run` apontam o typo na linha do `GetValue`, mesmo sem executar a pos-validacao. A analise estatica nao tenta inferir fluxos de dados nem IDs formados em tempo de execucao.

## ADR-030 — Ambiente headless e direcao para persistencia

- **Data:** 24/09/2026
- **Estado:** Aceita para ambiente; persistencia proposta, nao implementada
- **Contexto:** `EX1.prw` usa `PREPARE ENVIRONMENT`, inclui em ZA2 por `RecLock` e chama `Date()`, `xFilial()` e `Alert()`. O usuario tambem perguntou sobre guardar registros entre execucoes.
- **Decisao:** Adaptar os comandos de ambiente a builtins do TestLab, sem alterar o LivrePL. Empresa/filial vivem apenas no runtime; `Date()` le `DDATABASE` e `xFilial()` sem alias usa a area corrente. Para persistencia futura, preferir opt-in por arquivo de estado JSON separado, mantendo `advpl-testlab.jsonc` como fixture versionada imutavel.
- **Consequencias:** O EX1 executa e insere em memoria. Persistir diretamente em `registros` do JSONC nao e o padrao recomendado: alteraria a entrada do teste, seus comentarios/formatacao e a repetibilidade. A proposta de arquivo separado precisa definir carregamento, gravacao atomica, recuperacao de falhas e concorrencia antes de ser implementada.

## ADR-031 — Nome padrao do fixture `testlab.jsonc`

- **Data:** 24/09/2026
- **Estado:** Aceita
- **Contexto:** O nome `advpl-testlab.jsonc` repete o prefixo do projeto e o usuario pediu removê-lo.
- **Decisao:** Usar `testlab.jsonc` como nome canonico. Na descoberta automatica, preferir `testlab.jsonc` e `testlab.json` no diretorio mais proximo do fonte; manter `advpl-testlab.jsonc` e `advpl-testlab.json` como fallback legado.
- **Consequencias:** Fixtures versionados passam a usar o nome curto; comandos antigos com `--fixture` explicito continuam possiveis enquanto o arquivo existir. A compatibilidade de leitura nao implica manter copias duplicadas de fixtures.

## ADR-032 — Snapshot persistente opt-in em `state.json`

- **Data:** 24/09/2026
- **Estado:** Aceita
- **Contexto:** O usuario aprovou a separacao entre fixture e estado mutavel e escolheu o nome `state.json`. Inclusoes por `RecLock` e MVC1 devem sobreviver a outra execucao quando solicitadas.
- **Decisao:** `--persist` carrega `state.json` no diretorio da fixture, sobrepondo apenas os registros dos aliases declarados. Depois de execucao bem-sucedida, se os registros mudaram, grava snapshot versionado por arquivo temporario seguido de substituicao atomica. Sem a opcao, ignora o estado e preserva o comportamento deterministico anterior.
- **Consequencias:** `testlab.jsonc` nao muda; falha de parse/runtime ou expectativa MVC nao grava. Aliases desconhecidos e arquivo de estado invalido geram erro explicito. Gravacoes concorrentes no mesmo estado nao possuem lock nesta fase; executar em serie.

## ADR-033 — Primitivas ISAM em memoria

- **Data:** 24/09/2026
- **Estado:** Aceita
- **Contexto:** O usuario pediu suporte a navegacao, bloqueios, filtros, exclusao e commit para testar fontes AdvPL reais.
- **Decisao:** Implementar as chamadas sobre aliases do fixture, com recnos baseados em 1, exclusao logica e bloqueios locais ao interpretador. `DbOrderNickname(cApelido)` resolve `apelidosIndices` do fixture; `Select()` nao troca a area corrente. `DbCommit` e `DbCommitAll` nao gravam estado no meio da execucao; `--persist` continua fazendo snapshot somente apos sucesso.
- **Consequencias:** Os fluxos podem ser testados deterministicamente sem DBAccess. Nao se promete equivalencia de RDD, concorrencia, soft locks reais, SQL ou flush intermediario; essas limitacoes devem permanecer explicitas no README.

## ADR-034 — Numeracao deterministica de `GetSXENum`

- **Data:** 24/09/2026
- **Estado:** Aceita
- **Contexto:** `EX1.prw` passou a usar `GetSXENum("ZA2", "ZA2_COD")` e o fixture nao declara o tamanho do campo. Com `--persist`, o codigo precisa avancar entre execucoes.
- **Decisao:** Configurar `numeracao` por tabela e campo com `digitos` e `inicio`. Derivar o proximo codigo do maior valor numerico dos registros carregados, incluindo `state.json`, e reservar chamadas adicionais na mesma execucao.
- **Consequencias:** O caso de dois argumentos e deterministico e dispensa SXE/SXF. O simulador nao implementa reserva distribuida, `ConfirmSX8` ou `RollbackSX8`; sem registro salvo, o numero pode ser reutilizado na proxima execucao.

## ADR-035 — Depurador DAP externo ao LivrePL no primeiro corte

- **Data:** 25/09/2026
- **Estado:** Aceita para MVP
- **Contexto:** O usuario pediu debug de `.prw` no VS Code e autorizou alterar o LivrePL se necessario.
- **Decisao:** Instrumentar `FixtureInterpreter.exec_stmt` por subclasse, mapear declaracoes compiladas a fonte e expor pausas por um adaptador DAP Python iniciado por extensao VS Code local. Nao alterar o LivrePL enquanto a cobertura inicial puder ser entregue pela camada TestLab.
- **Consequencias:** Breakpoints em linhas executaveis de fontes e dependencias, passos, pilha e variaveis funcionam em testes automatizados. VSIX, parada em excecoes, Watch e coordenadas de instrucoes sem expressao ficam para fases seguintes; quando exigirem mudanca na base, ela sera feita no LivrePL com testes proprios.

## ADR-036 — Ordem estrita de declaracoes no TestLab

- **Data:** 25/09/2026
- **Estado:** Aceita
- **Contexto:** O usuario quer detectar `LOCAL` declarado no meio da funcao e seguir a ordem `LOCAL`, `PRIVATE`, `PUBLIC`. A documentacao oficial da TOTVS informa que AdvPL nao exige declaracoes no inicio; portanto, a ordem solicitada e uma convencao de projeto, nao sintaxe universal.
- **Decisao:** Validar por funcao/metodo que `LOCAL`/`STATIC`, `PRIVATE` e `PUBLIC` aparecam nessa sequencia, somente antes do primeiro comando executavel. O LivrePL preserva a linha dos nos `VarDecl`, mas nao impoe essa restricao ao seu parser geral.
- **Consequencias:** `-validate` e `-run` do TestLab rejeitam declaracoes tardias ou invertidas com `SemanticError` localizado. Um teste de integracao com `LOCAL` tardio foi atualizado sem alterar a logica. Suítes: TestLab 94, LivrePL 55, desafios-aprendizado 33 casos aprovados. A CLI `-validate tests/fixtures/declaration_out_of_order.prw` retorna erro na linha 3, coluna 5.

## ADR-037 — FAQ de debug e configuracao de desenvolvimento versionada

- **Data:** 25/09/2026
- **Estado:** Aceita
- **Contexto:** O usuario pediu um roteiro reproduzivel para abrir e executar o debug no VS Code. O `launch.json` da extensao existia localmente, mas estava oculto pela regra generica `.vscode/` do Git.
- **Decisao:** Versionar apenas `vscode-extension/.vscode/launch.json` como excecao ao ignore e acrescentar FAQ no README com instalacao, duas janelas, configuracao do projeto alvo, comandos de passo e diagnosticos comuns.
- **Consequencias:** Um clone novo consegue iniciar o Extension Development Host com `F5` sem criar manualmente a configuracao da extensao. O usuario ainda precisa criar seu proprio `.vscode/launch.json` no projeto alvo; a extensao permanece em desenvolvimento, sem VSIX publicada.

- Teste de aceite da CLI: saida `000007`.
- Cinco testes automatizados executados e aprovados.
- Nove testes automatizados executados e aprovados apos incorporar os primeiros casos reais.
- Treze testes automatizados executados e aprovados apos migrar o schema JSON.
- Dezesseis testes automatizados executados e aprovados com o executor de `TRNSOL02.prw`.
- Trinta e tres testes automatizados executados e aprovados com o `TRNSOL02.prw` integral pelo interpretador.
- Dois testes de regressao adicionados para coordenadas e cor do diagnostico; a suite passa a ter trinta e cinco casos.
- Um teste semantico adicional eleva a suite para trinta e seis casos aprovados.
- Dois testes adicionais cobrem funcao inexistente e funcao simulada, totalizando trinta e oito casos aprovados.
- Seis testes adicionais cobrem `usePrw` e `ENVEMAIL`, totalizando quarenta e quatro casos.
- Quatro testes adicionais cobrem validacao, eventos e CLI do `NOTIFSOL`, totalizando quarenta e oito casos (nove ignorados sem o antigo `TRNSOL02`).
- Regressao do LivrePL aprovada com `exemplos/ola.prw`, `exemplos/todas-etapas.prw` e `interpreter.py`.

---

*Ultima atualizacao: 22/09/2026*
