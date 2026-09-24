# Fase EX1 — ambiente e insercao em memoria

## Objetivo e desenho

O comando AdvPL `PREPARE ENVIRONMENT EMPRESA ... FILIAL ...` e convertido em chamada ao builtin `TestLabPrepareEnvironment`, preservando a linha do fonte para diagnosticos. Sao aceitos textos literais e variaveis simples para empresa/filial; `RESET ENVIRONMENT` limpa esse estado. Nenhum AppServer e aberto.

`Date()` devolve `DDATABASE` configurado em `ambiente` no formato `AAAA-MM-DD`. `xFilial()` sem parametro usa o alias selecionado; quando nao ha registro com campo de filial, usa a filial preparada. `Alert()` produz uma linha textual. `RecLock` e `MsUnlock` continuam manipulando apenas a copia em memoria dos registros da fixture.

## Verificacao

No diretorio `caminho-protheus/Fontes/exercicios-db/ex1`:

```text
advpl-testlab -validate EX1.prw
[OK] Sintaxe valida: EX1.prw (1 funcao(oes))

advpl-testlab -run EX1.prw
[ALERTA] Inseriu!
```

A suite propria passou com 72 testes, incluindo recarga do estado, inclusao MVC1 persistente e falhas sem gravacao. Um teste inspeciona o registro ZA2 em memoria e confirma que a fixture nao foi modificada. O `ZA1MVC.prw` real tambem foi verificado: rejeicao sem criar `state.json`, inclusao aprovada e browse seguinte exibindo dois livros.

## Persistencia implementada

`--persist` usa `state.json` no diretorio de `testlab.jsonc`. Ao iniciar, o executor carrega os registros salvos quando presentes, ou os da fixture quando ausentes. Apos sucesso com mudanca de registros, grava um arquivo temporario e o substitui atomicamente. Falha de execucao, expectativa MVC divergente ou inclusao MVC rejeitada nao escreve estado. O formato versionado guarda apenas registros por alias, nao metadados, parametros ou cenarios de teste. `state.json` invalido e rejeitado sem sobrescrita.

Salvar diretamente em `registros` do JSONC e tecnicamente possivel, mas mistura dados de teste versionados com estado mutavel, dificulta preservar comentarios e torna os testes dependentes da ordem de execucao. Por isso, nao foi ativado nem recomendado como padrao.

## Fora de escopo

Bloqueio de gravacoes concorrentes, conexao real com Protheus, todas as opcoes de `PREPARE ENVIRONMENT` (como `MODULO` e `TABLES`) e fidelidade completa ao tipo de data AdvPL.
