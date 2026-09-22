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
- Validacao semantica rejeita leituras de variaveis nao declaradas antes da execucao.
- Primeiro fonte real executado pelo parser e interpretador completos: `TRNSOL02.prw`, incluindo diálogo headless, statement, alias, browse e exportação virtual.

## Estrutura

```text
advpl-testlab/
|-- fixture_runtime.py
|-- semantic.py
|-- executor.py
|-- main.py
|-- pyproject.toml
|-- examples/getmv.prw
|-- examples/ui-headless.prw
|-- examples/real-cases/sol_mail_cfg.prw
|-- fixtures/getmv.json
|-- fixtures/ui-headless.json
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

Para validar todas as funções do arquivo sem executar nenhuma delas:

```powershell
advpl-testlab -validate TRNSOL02.prw
```

O comando falha com erro de lexer, parser ou semântica quando encontra sintaxe inválida, construção sem suporte ou leitura de variável não declarada. O diagnóstico preserva a numeração do `.prw` original, inclusive quando existem diretivas `#include`, mostra a linha e aponta a coluna aproximada:

```text
SyntaxError: Token inesperado TokenType.NEWLINE (None)
  31 |     Local nI :=
     |                 ^
  --> C:\projeto\TRNSOL02.prw:31:13
```

Em um terminal interativo, o erro é exibido em vermelho e o processo termina com código `1`. Defina a variável de ambiente `NO_COLOR` para desativar cores. Saídas redirecionadas e ferramentas sem TTY recebem texto puro automaticamente.

Por exemplo, `Local oStmt := Nilo` produz `SemanticError: Variável 'Nilo' não declarada`. `Nil` continua sendo reconhecido normalmente como o literal AdvPL. A atribuição direta a um nome ainda segue a semântica Clipper/AdvPL já adotada pelo LivrePL: `x := 1` pode criar uma variável `PRIVATE` implícita.

Sem instalar, o mesmo fluxo pode ser executado dentro deste repositorio:

```powershell
python main.py -run examples/getmv.prw --fixture fixtures/getmv.json --entry ex
```

Saida:

```text
000007
```

Exemplo de diálogo e mensagens sem UI:

```powershell
advpl-testlab -run examples/ui-headless.prw --fixture fixtures/ui-headless.json
```

Saída:

```text
[MSDIALOG] Cadastro sem UI
[ALERTA] Atencao: Falha simulada
[INFO] Resultado: Operacao concluida
[INFO] MsgYesNo: Resposta configurada: nao
```

A pergunta `Continuar?` não é impressa; ela apenas seleciona o ramo `false` configurado no fixture.

## Rodar os testes

```powershell
python -m unittest discover -s tests -v
```

A suíte inclui fontes `.prw` propositalmente inválidos em `tests/fixtures` para conferir sintaxe incompleta, identificador não declarado, linha, trecho, marcador e cor do diagnóstico.

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

### Respostas de MsgYesNo por fonte e chamada

Como cada `.prw` pode possuir várias confirmações, configure `MsgYesNo` em `especificidadesPrw`:

```json
{
  "especificidadesPrw": [
    {
      "fonte": "TRNSOL02.prw",
      "funcoes": [
        {
          "nome": "MSGYESNO",
          "conteudo": "'Gerar arquivo Excel com o resultado da consulta?', 'Consulta'",
          "retorno": false
        }
      ]
    }
  ]
}
```

- `fonte` é comparado pelo nome do arquivo, sem diferenciar maiúsculas e minúsculas.
- `conteudo` identifica os argumentos da chamada no formato AdvPL, separados por vírgula e espaço.
- `retorno` de `MSGYESNO` deve ser `true` ou `false`.
- Várias chamadas no mesmo fonte são declaradas como vários itens em `funcoes`, cada uma com seu `conteudo`.
- Se duas chamadas tiverem exatamente o mesmo conteúdo e precisarem de respostas diferentes, adicione `"ocorrencia": 1`, `"ocorrencia": 2` e assim por diante. Sem `ocorrencia`, a regra é o padrão para todas as chamadas com aquele conteúdo.
- Em argumentos calculados, `conteudo` deve representar o valor depois da avaliação. Exemplo: se o código monta `"Confirmar " + cCodigo + "?"`, configure o texto final esperado para aquele cenário.
- `MsgYesNo` não imprime a pergunta; ele apenas devolve o valor configurado.
- Sem regra específica, o carregador ainda aceita `{"MSGYESNO": false}` na coleção global `funcoes` por compatibilidade.
- Sem regra específica nem retorno global, a execução falha com uma mensagem que informa fonte e conteúdo procurados.

### Diálogos e ambiente determinístico

`dialogos` aplica o estado final esperado quando o fonte executa `Activate Dialog`:

```json
{
  "dialogos": [
    {
      "fonte": "TRNSOL02.prw",
      "titulo": "Consulta de Solicitacoes - Filtros",
      "variaveis": [
        {"LRET": true}
      ]
    }
  ],
  "ambiente": [
    {"CUSERLOCAL": "C:\\advpl-testlab"},
    {"TIME": "12:34:56"}
  ]
}
```

No `TRNSOL02`, `LRET: true` representa o botão Consultar e `false` representa Cancelar. `ambiente` torna o caminho e o nome da exportação reproduzíveis; o arquivo continua virtual.

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
- `MsgAlert` e `MsgInfo` como saída textual `[ALERTA]` e `[INFO]`, sem janela;
- `MsgYesNo` com retorno determinístico por fonte e conteúdo, sem saída textual;
- `Define MSDialog ... TITLE ... FROM ...` como saída textual `[MSDIALOG]`;
- linhas de controles `@ ...` e `Activate Dialog` como operações sem interface;
- leitura e validação das coleções `parametros`, `tabelas`, `funcoes` e `consultas` do fixture;
- validação semântica de identificadores contra parâmetros, declarações e globais simuladas;
- `GetMV(cParam)` em modo estrito e `GetMV(cParam, lHelp, uDefault)` com valor padrão;
- execução integral dos casos isolados `U_SolMailCfg()` e `TextoHtml()` usados nos testes.

### TRNSOL02.prw interpretado integralmente

O executor não possui mais um atalho especializado para esse fonte. As três funções são analisadas pelo lexer/parser e os cenários executam seus comandos pelo `FixtureInterpreter`:

- `Z04CON()` executa declarações, montagem do SQL, condições, parâmetros, statement, alias, browse, confirmação e fechamento;
- `fAskFiltros()` executa a declaração do diálogo e seus comandos headless; `dialogos` no fixture aplica os valores simulados durante `Activate Dialog`;
- `fGerarExcel()` executa condição, loop, leitura de campos, `nCnt++`, montagem do HTML e chamadas de arquivo;
- `FWExecStatement():New()`, `SetString()`, `SetDate()`, `OpenAlias()` e `Destroy()` possuem objetos simulados;
- `(cAlias)->(...)` e `(cAlias)->CAMPO` são adaptados para o runtime de alias;
- `DbGoTop()`, `DbSkip()`, `Eof()` e `DbCloseArea()` operam sobre registros em memória;
- `FWBrowse` recebe alias, descrição, colunas e legendas e renderiza os dados no terminal;
- `FCreate`, `FWrite` e `FClose` escrevem em arquivo virtual na memória, sem alterar o disco;
- `Time()` e `cUserLocal` podem ser definidos em `ambiente` para resultados determinísticos;
- os testes cobrem cancelamento do diálogo, consulta vazia, browse com dados e exportação confirmada.

O SQL é montado e seus parâmetros são vinculados pela lógica original, mas não é enviado a um banco. `OpenAlias()` hidrata o alias com `consultas -> Z04CON -> registros` do fixture.

### Limitações que permanecem

- os controles `SAY`, `GET` e `BUTTON` não possuem interação visual; `dialogos` injeta o estado final esperado;
- o marcador `@` de passagem por referência é aceito sintaticamente, mas a propagação genérica de alterações ao chamador ainda não está implementada;
- a exportação é validada em memória e não cria um `.xls` físico;
- `FWExecStatement` não interpreta SQL nem aplica automaticamente os filtros aos registros do fixture;
- a cobertura implementada atende todo o `TRNSOL02.prw`, mas ainda não representa qualquer API Protheus ou qualquer `.prw` arbitrário.

### Garantias do fixture

- O fixture é somente entrada; a execução não altera o JSON no disco.
- Nomes de parâmetros, tabelas, funções e consultas são normalizados sem diferenciar maiúsculas e minúsculas.
- APIs ou sintaxes fora da cobertura devem ser implementadas incrementalmente com um caso real e teste automatizado.
- `-validate` sempre analisa todas as funções; `-run` valida o arquivo inteiro antes de executar a entrada.

## Documentacao

- `docs/AI_RULES.md`: regras obrigatorias do agente.
- `docs/CONTEXT.md`: arquitetura e estado consolidado.
- `docs/TODO.md`: roadmap e pendencias.
- `docs/DECISIONS.md`: decisoes de arquitetura.
- `docs/PROMPT.md`: objetivo mestre e bootstrap de sessao.
- `docs/fase-0-levantamento.md` e `docs/fase-1-getmv.md`: entregas tecnicas por fase.
- `docs/fase-1b-casos-reais.md`: primeiros casos extraidos de fontes funcionais.
- `docs/corpus-desafio1-context-map.md`: inventario e priorizacao do corpus real.
- `docs/fase-ui-headless.md`: mensagens e confirmacoes sem interface.
- `docs/fase-trnsol02-integral.md`: validacao e execucao das tres funcoes do primeiro fonte real.

## Decisao de erro do GetMV

Quando o parametro nao existe, o harness gera `AdvPLRuntimeError`. Retornar `NIL` esconderia fixtures incompletos e poderia produzir falso positivo em testes de regra de negocio.
