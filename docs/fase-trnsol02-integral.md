# TRNSOL02 integral pelo interpretador

## Objetivo

Validar o arquivo `TRNSOL02.prw` inteiro e executar suas tres funcoes pelo `FixtureInterpreter`, removendo o adaptador que apenas extraia colunas e imprimia registros pre-calculados.

## Preparacao de sintaxe

Antes do parser, o TestLab preserva uma linha de saida para cada linha de entrada e adapta construcoes do fonte para operacoes equivalentes do runtime:

- `!expressao` para negacao reconhecida pelo LivrePL;
- argumentos `@variavel` para a chamada suportada pelo parser;
- `(cAlias)->(Metodo())` para chamada do alias em memoria;
- `(cAlias)->CAMPO` para leitura do registro corrente;
- `nCnt++` para incremento suportado;
- macros de dialogo para builtins headless.

O comando `advpl-testlab -validate TRNSOL02.prw` analisa as tres funcoes sem executar a entrada. Erros de lexer e parser mantem o numero da linha do fonte.

## Execucao

`Z04CON()` monta o SQL e a lista de parametros normalmente. `FWExecStatement` guarda esses valores e `OpenAlias()` carrega os registros declarados em `consultas.Z04CON`. O alias implementa topo, fim, avanco, leitura de campo e fechamento.

`fAskFiltros()` e executada. O fixture configura seu dialogo por fonte e titulo e aplica `LRET = true` ou `false` durante `Activate Dialog`.

`fGerarExcel()` e executada quando `MsgYesNo` retorna `true`. `FCreate`, `FWrite` e `FClose` mantem o conteudo somente em memoria. `TIME` e `CUSERLOCAL` podem vir de `ambiente`.

## Cenarios verificados

- cancelamento do dialogo de filtros;
- consulta sem registros e `MsgAlert` correspondente;
- consulta com registros e browse textual;
- recusa da exportacao;
- confirmacao e geracao virtual do HTML com contagem correta;
- validacao isolada das tres funcoes do arquivo.

## Limites

- nao ha banco SQL real; os resultados sao fornecidos pelo fixture;
- filtros nao sao aplicados automaticamente sobre Z04/Z05;
- controles visuais nao recebem interacao real;
- passagem por referencia e aceita na sintaxe, mas ainda nao propaga genericamente alteracoes ao chamador;
- arquivos exportados permanecem em memoria.

## Evidencias

```text
[OK] Sintaxe valida: TRNSOL02.prw (3 funcao(oes))
[MSDIALOG] Consulta de Solicitacoes - Filtros
Consulta de Solicitacoes Internas
```

A suite completa possui trinta e tres testes automatizados e a regressao do LivrePL permanece aprovada.
