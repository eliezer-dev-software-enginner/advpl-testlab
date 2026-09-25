# TODO.md — Roadmap e Status do AdvPL TestLab

> Status: `[ ]` pendente · `[~]` em andamento · `[x]` concluido.
> Atualizar este arquivo ao final de cada tarefa.

---

## Foco atual

### desafio0-Fat006

- [x] Validar os quatro fontes reais na ordem das dependencias.
- [x] Executar consolidacao, preview, montagem da NF-e e gravacao simulada na SC5.
- [x] Cobrir nota de entrada e falha de bloqueio sem persistencia.
- [x] Garantir em teste que fixtures versionados dos desafios declarem todas as sete secoes, mesmo vazias.
- [ ] Integrar ou comparar resultados com AppServer/DBAccess/emissor NF-e reais.

### TRNSOL01 headless

- [x] Validar o fonte real e as dependencias locais.
- [x] Executar browse, menu, modelo/view, envio, aprovacao, rejeicao, processamento e cancelamento.
- [x] Cobrir erro de item, transacao com rollback e grid filtrado pela solicitacao corrente.
- [x] Configurar indices Z03/Z05, dialogo, confirmacoes e parametros no fixture real.
- [ ] Validar callbacks de controles `@` internamente e integrar com AppServer/DBAccess/SMTP reais.

Estado: fluxos de negocio cobertos em memoria; integracao Protheus permanece externa ao TestLab.

### TRNSOL02 integral pelo interpretador

- [x] Validar as tres funcoes do arquivo pelo lexer e parser.
- [x] Remover o adaptador especializado de `executor.py`.
- [x] Executar `Z04CON()` pelo `FixtureInterpreter`.
- [x] Executar `fAskFiltros()` com dialogo configurado no fixture.
- [x] Simular `FWExecStatement`, parametros e abertura de alias.
- [x] Implementar navegacao e leitura do alias temporario.
- [x] Simular `FWBrowse` com descricao, colunas e legendas.
- [x] Executar `fGerarExcel()` com arquivo virtual.
- [x] Cobrir cancelamento, consulta vazia, browse e exportacao.
- [x] Adicionar o comando `-validate`.
- [x] Rejeitar leituras de identificadores nao declarados em `-validate` e `-run`.
- [x] Rejeitar chamadas de funcoes inexistentes e aceitar funcoes simuladas no fixture.
- [x] Carregar dependencias locais declaradas por `//usePrw('arquivo.prw')`.
- [x] Validar o grafo `usePrw` respeitando escopo de `Static Function` por arquivo; raiz deve falhar se um dependente chamar auxiliar estatico de outro `.prw`.
- [x] Validar e executar `ENVEMAIL.prw` com SMTP e envio simulados em memoria.
- [x] Validar e executar integralmente `NOTIFSOL.prw` nos eventos ENVIO, APROVACAO, REJEICAO e PROCESSAMENTO.
- [x] Aceitar argumentos da funcao de entrada pela CLI com `--args-json`.

Status: `[x]` — concluido em 22/09/2026.

### Executor de `.prw` — primeiro caso completo

- [x] Criar a CLI `advpl-testlab -run arquivo.prw`.
- [x] Descobrir automaticamente a primeira `User Function`.
- [x] Descobrir `testlab.jsonc` ou `testlab.json` no projeto alvo, com fallback para os nomes antigos.
- [x] Criar fixture de Z04, Z05 e Z06 em `desafios-aprendizado/desafio1-solicitacao-compra`.
- [x] Executar `TRNSOL02.prw` sem alterar o fonte.
- [x] Simular `FWExecStatement` e renderizar `FWBrowse` no terminal.
- [x] Cobrir o fluxo com testes automatizados.

Status: `[x]` — primeiro corte concluido em 21/09/2026.

### Fase 2 — Leitura basica de tabela

- [x] Definir o objeto de runtime de alias e registro corrente para consultas temporarias.
- [x] Normalizar aliases e campos como case-insensitive.
- [ ] Implementar abertura de alias simulado por `DBUseArea` ou adaptacao minima equivalente.
- [ ] Implementar leitura do primeiro registro por `FieldGet` antes de introduzir sintaxe nova.
- [ ] Definir o comportamento de tabela vazia e alias inexistente.
- [ ] Criar fixture, `.prw` de aceite e testes automatizados.
- [ ] Documentar desenho, codigo, saida real e fora de escopo em `docs/fase-2-*.md`.

Status: `[ ]`

## Concluido

### UI headless e MsgYesNo deterministico

- [x] Adaptar `Define MSDialog` para saida textual sem SmartClient.
- [x] Ignorar controles `@ ...` e `Activate Dialog` sem executar UI.
- [x] Implementar `MsgAlert` e `MsgInfo` como texto no terminal.
- [x] Implementar `MsgYesNo` sem saida textual.
- [x] Resolver `MsgYesNo` por fonte e conteudo em `especificidadesPrw`.
- [x] Preservar o retorno global legado em `funcoes`.
- [x] Falhar quando nao houver resposta deterministica.
- [x] Cobrir fontes e chamadas multiplas com testes automatizados.

Status: `[x]` — concluido em 22/09/2026.

### Fase 1b — Casos reais do desafio1

- [x] Mapear `TRNSOL01.prw`, `TRNSOL02.prw`, `ENVEMAIL.prw` e `NOTIFSOL.prw`.
- [x] Isolar `U_SolMailCfg()` como primeiro caso real portavel.
- [x] Estender `GetMV` para aceitar `lHelp` e `uDefault`.
- [x] Preservar o erro de parametro ausente quando nao houver default.
- [x] Isolar `TextoHtml()` como segundo caso real portavel.
- [x] Implementar `StrTran` e `Chr` na camada do TestLab.
- [x] Verificar o ciclo TDD e ampliar a suite para nove testes.

Status: `[x]` — concluido em 21/09/2026.

### Schema JSON canonico

- [x] Migrar `parametros` de objeto para lista de objetos com uma chave.
- [x] Migrar `tabelas` de objeto para lista de aliases.
- [x] Representar cada alias como objeto com `registros`.
- [x] Rejeitar parametros e aliases duplicados sem diferenciar maiusculas/minusculas.
- [x] Preservar leitura do formato legado.
- [x] Atualizar fixtures, testes e documentacao.

Status: `[x]` — concluido em 21/09/2026.

### Fase 0 — Levantamento

- [x] Mapear APIs prioritarias do framework Protheus.
- [x] Escolher camada separada sobre o LivrePL.
- [x] Evitar alteracoes prematuras no lexer/parser.
- [x] Documentar arquitetura inicial.

Status: `[x]` — concluido em 21/09/2026.

### Fase 1 — GetMV lendo JSON

- [x] Criar carregador e validador de fixture.
- [x] Injetar `Fixture` no construtor de `FixtureInterpreter`.
- [x] Registrar `GetMV` como builtin adicional.
- [x] Normalizar nomes de parametros de forma case-insensitive.
- [x] Gerar erro claro para parametro ausente.
- [x] Criar CLI, exemplo e fixture de aceite.
- [x] Executar cinco testes automatizados com sucesso.
- [x] Verificar saida ponta a ponta `000007`.
- [x] Executar regressao basica do LivrePL.

Status: `[x]` — concluido em 21/09/2026.

## Roadmap posterior

### Fase 3 — Navegacao e busca

- [x] Implementar `DBSeek` sobre registros do fixture.
- [x] Implementar `DbSkip`.
- [x] Implementar `Eof()` e `Deleted()`; `Bof()` permanece pendente.
- [x] Validar `While` percorrendo tabela completa.
- [x] Usar `TabelaItensEmail()` de `NOTIFSOL.prw` como caso de aceite real.

### Fase 4 — Escrita simulada

- [ ] Implementar `RecLock` e desbloqueio em memoria.
- [ ] Implementar atribuicao de campo no registro corrente.
- [x] Definir `MsgAlert` como saida textual; `ConOut` continua pendente.
- [ ] Garantir que o fixture de entrada no disco nao seja alterado involuntariamente.
- [x] Confirmar por teste que cenarios MVC nao alteram a fixture de origem.

### Fase 5 — Casos de teste declarativos

- [ ] Definir fixture de entrada e resultado esperado no mesmo caso de teste.
- [x] Definir casos MVC nomeados com entrada e expectativa de inclusao.
- [ ] Comparar retorno de funcao.
- [ ] Comparar saida capturada.
- [ ] Comparar estado final das tabelas simuladas.
- [x] Comparar `totalRegistros` final nos cenarios MVC de inclusao.
- [ ] Produzir relatorio claro de divergencias.

## Pendencias tecnicas continuas

- [x] Validar a convencao estrita de ordem de declaracoes (`LOCAL`/`STATIC`, `PRIVATE`, `PUBLIC`) no inicio de cada rotina, com erro localizado.
- [x] Expor perfil de nomes moderno ou legado na validacao e execucao, usando a politica do LivrePL.
- [x] Separar a suite propria dos testes de integracao que leem `desafios-aprendizado`.
- [x] Aceitar fixtures `.jsonc` comentados e manter leitura de `.json` estrito.
- [x] Validar referencias a `PRIVATE` em funcoes auxiliares sem promover `LOCAL` a global, e apontar a linha efetiva de nomes ausentes.
- [x] Rejeitar `VIEWDEF.<modulo>` desconhecido e campos ausentes em `SetPrimaryKey`, mesmo quando menu/modelo MVC nao sao executados pelo browse headless.
- [x] Rejeitar `ADD OPTION ACTION 'U_<nome>'` sem `User Function` carregada, inclusive quando o menu nao e executado; reproduz a remocao de `Z04CAN` em `TRNSOL01.prw`.
- [x] Rejeitar IDs literais desconhecidos em `GetValue` quando `AddFields`/`AddGrid` declaram os submodelos no mesmo fonte.
- [x] Interpretar `PREPARE ENVIRONMENT`/`RESET ENVIRONMENT` para o EX1 com empresa/filial simuladas.
- [x] Implementar `--persist` opcional em `state.json`, com gravacao atomica, recarga e testes de falha/MVC1.
- [x] Cobrir as primitivas ISAM solicitadas em memoria, incluindo filtros, bloqueios, navegacao, exclusao logica e apelidos de indice.
- [x] Simular `GetSXENum(cAlias, cCampo)` com regra de numeracao por campo e continuidade via `state.json`.
- [x] Documentar no README um bloco copiavel com as chaves comuns de `ambiente` e distinguir globais especificas de cada fonte.
- [x] Iniciar debug VS Code via DAP com breakpoints, passos, pilha e variaveis em fontes `.prw` e `//usePrw`.
- [x] Documentar FAQ passo a passo para iniciar o Extension Development Host e depurar um `.prw`.
- [ ] Testar a extensao visualmente no Extension Development Host e preparar distribuicao VSIX.
- [ ] Ampliar coordenadas do parser para instrucoes sem expressao e controles adaptados; depois avaliar ganchos reutilizaveis no LivrePL.
- [ ] Adicionar breakpoints condicionais, avaliacao de expressoes e parada em excecoes ao depurador.
- [ ] Avaliar reservas confirmadas/canceladas por `ConfirmSX8` e `RollbackSX8` sem fingir equivalencia ao servidor de numeracao.
- [ ] Refinar a fidelidade de `SoftLock`, RDDs e commits intermediarios para cenarios que dependam do DBAccess real.
- [ ] Definir bloqueio de concorrencia para gravacoes simultaneas no mesmo `state.json`.
- [ ] Avaliar empacotamento ou configuracao explicita do caminho do LivrePL sem quebrar o uso atual por diretorios irmaos.
- [ ] Generalizar objetos `FWExecStatement`/`FWBrowse` no runtime, removendo a deteccao especializada quando houver cobertura equivalente.
- [ ] Aplicar filtros da consulta simulada sobre Z04/Z05 em vez de usar resultados precomputados.
- [ ] Adicionar CI quando houver repositorio remoto configurado.
- [ ] Manter README, CONTEXT e DECISIONS sincronizados com cada fase.
- [ ] Cobrir validacoes antecipadas de `U_EnviarEmailSolicitacao()` com `At` e `Left`, sem simular SMTP.

---

*Ultima atualizacao: 22/09/2026*
