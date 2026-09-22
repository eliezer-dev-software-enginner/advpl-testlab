# AdvPL TestLab

Ambiente de simulacao e testes para executar arquivos AdvPL reais com dados de fixtures JSON, sem AppServer, licenca ou banco de dados.

O projeto e separado do `livrePL`. Ele usa o interpretador como dependencia local e acrescenta builtins do framework Protheus por heranca, sem alterar o lexer, o parser ou o interpretador original.

## Estado atual

- Fase 0: levantamento e arquitetura documentados.
- Fase 1: `GetMV(cParam)` lendo `parametros` do fixture JSON.
- Fase 1b: casos reais `U_SolMailCfg()` e `TextoHtml()` extraidos do desafio1.
- Nomes de parametros sao case-insensitive.
- Parametro ausente gera erro explicito.
- `GetMV(cParam, lHelp, uDefault)` devolve o default quando a chave nao existe.
- Builtins adicionais usados pelos casos reais: `StrTran` e `Chr`.
- `parametros` e `tabelas` usam listas de objetos no formato canonico.
- Cada tabela possui `campos` opcionais e `registros`.
- CLI instalavel `advpl-testlab -run arquivo.prw` com descoberta automatica da primeira `User Function` e do fixture.
- Primeiro fonte real integrado em modo headless: `TRNSOL02.prw`. Esse caso usa um adaptador parcial e ainda não executa todo o corpo da função linha por linha.

## Estrutura

```text
advpl-testlab/
|-- fixture_runtime.py
|-- executor.py
|-- main.py
|-- pyproject.toml
|-- examples/getmv.prw
|-- examples/real-cases/sol_mail_cfg.prw
|-- fixtures/getmv.json
|-- fixtures/sol_mail_cfg.json
|-- tests/test_getmv.py
|-- tests/test_real_cases.py
`-- docs/
```

O diretorio deve permanecer como irmao de `livrePL`:

```text
protheus/
|-- livrePL/
`-- advpl-testlab/
```

## Pré-requisitos

- Python 3.10 ou mais recente disponível no terminal.
- O repositório `livrePL` em um diretório irmão deste projeto.
- Um arquivo `advpl-testlab.json` no projeto testado, ou seu caminho informado por `--fixture`.

Estrutura esperada:

```text
protheus/
|-- livrePL/
|-- advpl-testlab/
`-- meu-projeto-advpl/
    |-- advpl-testlab.json
    `-- rotina.prw
```

Não são necessários AppServer, SmartClient, licença Protheus ou banco de dados para os casos simulados.

## Instalar a CLI

```powershell
cd advpl-testlab
python -m pip install -e .
```

A instalação editável precisa ser feita apenas uma vez por ambiente Python. No Windows, se o `pip` avisar que a pasta `Scripts` do usuário não está no `PATH`, adicione a pasta indicada e abra um terminal novo. Para descobrir a base do usuário:

```powershell
python -m site --user-base
```

Normalmente o executável fica em uma subpasta como `Python314\Scripts` dentro dessa base.

Depois, a partir do diretorio de qualquer fonte:

```powershell
advpl-testlab -run TRNSOL02.prw
```

O executor procura `advpl-testlab.json` no diretorio do `.prw` e nos diretorios pais. Tambem e possivel usar `--fixture caminho.json` e `--entry NomeDaFuncao`.

```text
-run ARQUIVO.PRW       fonte AdvPL alvo da execução ou simulação
--fixture ARQUIVO.JSON fixture específico; opcional com advpl-testlab.json
--entry FUNCAO         entrada; opcional, usa a primeira User Function
```

Sem instalar, o mesmo fluxo pode ser executado dentro deste repositorio:

```powershell
python main.py -run examples/getmv.prw --fixture fixtures/getmv.json --entry ex
```

Saida:

```text
000007
```

## Rodar os testes

```powershell
python -m unittest discover -s tests -v
```

## Formato do fixture

```json
{
  "parametros": [
    {
      "MV_ADMIN": "000007"
    }
  ],
  "tabelas": [
    {
      "SB1": {
        "campos": [
          {
            "nome": "B1_COD",
            "tipo": "C",
            "tamanho": 15,
            "obrigatorio": true,
            "titulo": "Código",
            "descricao": "Código do produto"
          }
        ],
        "registros": []
      }
    }
  ]
}
```

Cada item de `parametros` deve declarar exatamente uma chave. Cada item de `tabelas` deve declarar exatamente um alias, cujo objeto possui a lista `registros` e pode possuir `campos`. As colecoes opcionais `funcoes` e `consultas` configuram respostas deterministicas para integracoes Protheus em modo headless.

O carregador ainda aceita o formato antigo baseado em objetos para manter compatibilidade, mas novos fixtures devem usar somente o formato acima.

O dicionário usa título e descrição apenas em português. `tamanho` pode ser numérico, `null` para Memo, `"padrao"` para o padrão ou uma referência como `"conforme_SB1"`.

As coleções opcionais `funcoes` e `consultas` substituem integrações externas por respostas determinísticas:

```json
{
  "funcoes": [
    {"FASKFILTROS": true},
    {"MSGYESNO": false}
  ],
  "consultas": [
    {
      "Z04CON": {
        "registros": [
          {"Z04_CODIGO": "000001", "QT_ITENS": 2, "VL_TOTAL": 350.5}
        ]
      }
    }
  ]
}
```

O nome da consulta deve coincidir, sem diferenciar maiúsculas e minúsculas, com a função de entrada.

## Testar um novo projeto

1. Crie `advpl-testlab.json` na raiz do projeto AdvPL.
2. Cadastre parâmetros, tabelas, funções externas e consultas usadas pelo fonte.
3. Abra um terminal no diretório do `.prw`.
4. Execute `advpl-testlab -run NomeDoFonte.prw`.
5. Para validar o TestLab, execute `python -m unittest discover -s tests -v` neste repositório.

## Cobertura atual

### Implementado e interpretado

Estes recursos passam pelo parser e pelo interpretador, portanto sua lógica é executada:

- descoberta automática da primeira `User Function` ou seleção explícita por `--entry`;
- descoberta de `advpl-testlab.json` no diretório do fonte ou nos diretórios pais;
- funções `Function`, `User Function` e `Static Function` dentro da cobertura do LivrePL;
- variáveis `Local`, `Private`, `Public` e `Static`;
- atribuições simples, `+=` e `-=`;
- valores texto, numérico, lógico, `Nil` e arrays;
- operadores aritméticos, relacionais e lógicos suportados pelo LivrePL;
- estruturas `If/ElseIf/Else`, `For`, `Do While`, `Do Case` e `Begin Sequence`;
- chamadas de função, funções estáticas, acesso a arrays e retorno de valores;
- classes, métodos e code blocks dentro do subconjunto implementado pelo LivrePL;
- builtins básicos do LivrePL, como `Len`, `AllTrim`, `Upper`, `Lower`, `AAdd`, `Empty`, `ValType` e `cValToChar`;
- builtins Protheus adicionados pelo TestLab: `GetMV`, `StrTran` e `Chr`;
- leitura e validação das coleções `parametros`, `tabelas`, `funcoes` e `consultas` do fixture;
- `GetMV(cParam)` em modo estrito e `GetMV(cParam, lHelp, uDefault)` com valor padrão;
- execução integral dos casos isolados `U_SolMailCfg()` e `TextoHtml()` usados nos testes.

### Parcialmente implementado

O caso `TRNSOL02.prw` usa um adaptador headless especializado para o padrão `FWExecStatement` + `FWBrowse`:

- o arquivo `.prw` é aberto e sua primeira `User Function` é descoberta;
- a presença de `FWExecStatement():New()` e `FWBrowse():New()` seleciona o adaptador;
- `SetDescription()` e `AddColumn()` são lidos do texto do fonte;
- os registros são obtidos de `consultas -> Z04CON -> registros` no fixture;
- a grade do `FWBrowse` é representada como tabela no terminal;
- respostas configuradas em `funcoes`, como `FASKFILTROS`, podem controlar o adaptador.

Nesse caminho, o corpo completo de `Z04CON()` **não** é interpretado linha por linha. O teste confirma a integração entre fonte, função de entrada, fixture e saída headless, mas não valida integralmente a regra de negócio da rotina.

### Ainda não implementado para o TRNSOL02.prw

- montagem e execução real da consulta SQL;
- aplicação dos filtros preenchidos em `fAskFiltros()`;
- parâmetros por referência, como `@dDe` e `@cNum`;
- aliases dinâmicos e expressões como `(cAlias)->Z04_CODIGO`;
- navegação completa com `DbGoTop()`, `DbSkip()`, `Eof()` e `DbCloseArea()`;
- objetos genéricos de `FWExecStatement` e `FWBrowse` com todos os métodos;
- macros visuais `Define MSDialog`, `@ ... SAY`, `GET`, `BUTTON` e `ACTIVATE DIALOG`;
- execução de `MsgAlert`, `MsgInfo` e `MsgYesNo` com semântica de interface Protheus;
- geração do arquivo Excel por `FCreate`, `FWrite` e `FClose`;
- pós-incremento, como `nCnt++`, nesse fluxo;
- execução arbitrária de qualquer `.prw` ou de qualquer API Protheus.

### Garantias do fixture

- O fixture é somente entrada; a execução não altera o JSON no disco.
- Nomes de parâmetros, tabelas, funções e consultas são normalizados sem diferenciar maiúsculas e minúsculas.
- APIs ou sintaxes fora da cobertura devem ser implementadas incrementalmente com um caso real e teste automatizado.

## Documentacao

- `docs/AI_RULES.md`: regras obrigatorias do agente.
- `docs/CONTEXT.md`: arquitetura e estado consolidado.
- `docs/TODO.md`: roadmap e pendencias.
- `docs/DECISIONS.md`: decisoes de arquitetura.
- `docs/PROMPT.md`: objetivo mestre e bootstrap de sessao.
- `docs/fase-0-levantamento.md` e `docs/fase-1-getmv.md`: entregas tecnicas por fase.
- `docs/fase-1b-casos-reais.md`: primeiros casos extraidos de fontes funcionais.
- `docs/corpus-desafio1-context-map.md`: inventario e priorizacao do corpus real.

## Decisao de erro do GetMV

Quando o parametro nao existe, o harness gera `AdvPLRuntimeError`. Retornar `NIL` esconderia fixtures incompletos e poderia produzir falso positivo em testes de regra de negocio.
