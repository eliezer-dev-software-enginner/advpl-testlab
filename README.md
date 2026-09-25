# AdvPL TestLab

Ambiente de simulacao e testes para executar arquivos AdvPL reais com dados de fixtures JSON ou JSONC, sem AppServer, licenca ou banco de dados.

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
- Validacao semantica rejeita variaveis nao declaradas e funcoes inexistentes antes da execucao.
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
|-- tests/test_jsonc.py
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
- Um arquivo `testlab.jsonc` (recomendado) ou `testlab.json` no projeto testado, ou seu caminho informado por `--fixture`.

Estrutura esperada:

```text
protheus/
|-- livrePL/
|-- advpl-testlab/
`-- meu-projeto-advpl/
    |-- testlab.jsonc
    `-- rotina.prw
```

Não são necessários AppServer, SmartClient, licença Protheus ou banco de dados para os casos simulados.

## Instalar a CLI

```powershell
cd advpl-testlab
python -m pip install -e .
```

Se a CLI ja estava instalada antes da adicao de `--persist`, rode esse comando novamente no mesmo ambiente Python para incluir o modulo de estado.

A instalação editável precisa ser feita apenas uma vez por ambiente Python. No Windows, se o `pip` avisar que a pasta `Scripts` do usuário não está no `PATH`, adicione a pasta indicada e abra um terminal novo. Para descobrir a base do usuário:

```powershell
python -m site --user-base
```

Normalmente o executável fica em uma subpasta como `Python314\Scripts` dentro dessa base.

Depois, a partir do diretorio de qualquer fonte:

```powershell
advpl-testlab -run TRNSOL02.prw
```

O executor procura `testlab.jsonc` ou `testlab.json` no diretorio do `.prw` e nos diretorios pais. O fixture do diretorio mais proximo prevalece; no mesmo diretorio, `testlab.jsonc` tem prioridade, depois `testlab.json`. Os nomes antigos `advpl-testlab.jsonc` e `advpl-testlab.json` continuam aceitos como fallback. Tambem e possivel usar `--fixture caminho.jsonc`, `--entry NomeDaFuncao` e `--args-json '[...]'`.

### Depuracao inicial no VS Code (extensao em desenvolvimento)

Esta primeira versao permite breakpoints em instrucoes `.prw`, continuar, entrar/sair/avancar passos, ver pilha e inspecionar variaveis locais, privadas e globais. Ela depura o codigo AdvPL simulado, nao o Python do TestLab nem um AppServer real.

1. No Python que o VS Code usara, execute `python -m pip install -e .` na pasta `advpl-testlab`.
2. Abra a pasta `advpl-testlab/vscode-extension` no VS Code e pressione `F5` para iniciar o **Extension Development Host**. Ainda nao ha VSIX publicada ou instalada permanentemente.
3. Na nova janela, abra a pasta que contem seu `.prw` e crie `.vscode/launch.json`:

```jsonc
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "advpl-testlab",
      "request": "launch",
      "name": "Depurar PRW (TestLab)",
      "program": "${file}",
      "entry": "EX1",
      "stopOnEntry": true,
      "persist": false,
      "pythonPath": "python"
    }
  ]
}
```

Selecione o `.prw`, marque um breakpoint em uma linha executavel e inicie `Depurar PRW (TestLab)`. Se o TestLab foi instalado em outro ambiente Python, ajuste `pythonPath` para o `python.exe` desse ambiente. `fixture` e opcional (a descoberta e a mesma da CLI); tambem sao aceitos `args` (array JSON), `mvcCase`, `nameProfile` e `persist`. Com `persist: true`, o estado so e salvo apos execucao bem-sucedida; encerrar a depuracao durante uma pausa nao grava.

Limitacoes do MVP: breakpoints so sao confirmados em instrucoes que o parser associa a uma linha executavel. Linhas de controles de UI adaptadas, breakpoints condicionais, avaliacao de expressoes no console/Watch, edicao de variaveis e pausa na excecao ainda nao estao implementados. `//usePrw` e suportado: a pilha e o breakpoint apontam para o arquivo dependente correto. Ver [fase-debug-vscode](docs/fase-debug-vscode.md).

#### FAQ: como rodar em debug?

**Preciso instalar alguma extensao?** Por enquanto, use **Arquivo > Abrir Pasta** para abrir exatamente `advpl-testlab/vscode-extension` no VS Code (nao a raiz `advpl-testlab`). Em **Executar e Depurar**, selecione `Executar extensão de debug` e pressione `F5`. Isso abre uma segunda janela, o **Extension Development Host**, com a extensao temporariamente ativa. A configuracao de desenvolvimento da extensao esta versionada em `vscode-extension/.vscode/launch.json`; nao ha VSIX publicada.

**O que preparo antes de apertar F5?** Na raiz de `advpl-testlab`, rode `python -m pip install -e .` no mesmo Python que sera usado para depurar. No projeto alvo, mantenha o `testlab.jsonc` acessivel ao `.prw` (ou informe `fixture` no `launch.json`). A partir da pasta alvo, `python -c "import debug_adapter; print(debug_adapter.__file__)"` deve localizar o modulo instalado.

**Onde crio o `launch.json` da rotina?** Na *segunda* janela, abra a pasta do projeto que contem os fontes, crie `.vscode/launch.json` com o exemplo acima e ajuste `entry` para a funcao de entrada do seu arquivo. Se ja existir um `launch.json` com `TOTVS Language Debug`, acrescente a configuracao `advpl-testlab` ao array `configurations` e selecione `Depurar PRW (TestLab)` no menu de **Executar e Depurar**; nao precisa apagar a configuracao TOTVS. `program: "${file}"` usa o `.prw` aberto na guia ativa; para depurar sempre o mesmo fonte, use o caminho absoluto dele. Se `python` nao for o Python em que o TestLab foi instalado, use o caminho absoluto do respectivo `python.exe` em `pythonPath`.

**Como paro e examino o codigo?** Abra o `.prw` na segunda janela, clique a esquerda do numero de uma linha executavel para criar um breakpoint, escolha `Depurar PRW (TestLab)` em **Executar e Depurar** e pressione `F5`. `stopOnEntry: true` para na primeira instrucao mesmo sem breakpoint. Use `F10` para avancar sem entrar na chamada, `F11` para entrar, `Shift+F11` para sair e `F5` para continuar. As abas **Variaveis**, **Pilha de Chamadas** e **Console de Depuracao** mostram o estado simulado.

**Como passo argumentos ou testo MVC?** Inclua `"args": ["ENVIO"]` para argumentos da entrada. Para um cenario declarado em `cenariosMvc` no fixture, use `"mvcCase": "nome-do-cenario"`. `"persist": true` carrega e salva `state.json` apos sucesso; deixe `false` para uma depuracao repetivel que nao altera o estado.

**Por que o breakpoint nao para ou a sessao falha ao iniciar?** Confira se o `.prw` aberto e o `program` sao o mesmo arquivo, se a linha possui instrucao executavel, se `entry` existe, se o fixture foi encontrado e se `pythonPath` aponta para o Python com `debug_adapter` instalado. Se o arquivo falhar em `advpl-testlab -validate arquivo.prw`, corrija primeiro o diagnostico: o depurador valida o fonte antes de iniciar. Breakpoints em arquivos `//usePrw` funcionam quando eles sao carregados pela entrada.

**Por que `F5` abre o depurador da TOTVS?** Voce esta na janela/pasta errada ou a configuracao selecionada ainda e `TOTVS Language Debug`. Na primeira janela, abra somente `advpl-testlab/vscode-extension` e selecione `Executar extensão de debug`; na segunda janela, abra o projeto dos `.prw` e selecione `Depurar PRW (TestLab)`. O `launch.json` da raiz `advpl-testlab` pode conter a configuracao TOTVS e nao e usado para iniciar esta extensao.

`PREPARE ENVIRONMENT EMPRESA ... FILIAL ...` e `RESET ENVIRONMENT` sao simulados sem abrir AppServer. O corte atual aceita valores literais ou variaveis para empresa/filial; `Date()` usa `DDATABASE` de `ambiente` (formato `AAAA-MM-DD`), `xFilial()` sem argumento usa o alias corrente, e `Alert()` escreve no terminal. Sem `--persist`, a escrita via `RecLock` continua apenas em memoria; veja [fase-ex1-ambiente](docs/fase-ex1-ambiente.md).

### `ambiente`: bloco pronto para `testlab.jsonc`

Copie a propriedade abaixo para a raiz do seu fixture e ajuste os valores. Este bloco reune todas as chaves de ambiente com significado proprio no runtime atual; as de e-mail so afetam fontes que usam `TMailManager`/`TMailMessage`. `0` significa sucesso simulado nesses resultados.

```jsonc
"ambiente": [
  {"DDATABASE": "2026-09-25"},
  {"TIME": "12:34:56"},
  {"CUSERLOCAL": "C:\\testlab"},
  {"MODEL_OPERATION": 2},
  {"MAIL_INIT_RESULT": 0},
  {"MAIL_TIMEOUT_RESULT": 0},
  {"MAIL_CONNECT_RESULT": 0},
  {"MAIL_AUTH_RESULT": 0},
  {"MAIL_SEND_RESULT": 0},
  // Opcionais por fonte: descomente e ajuste antes de usar.
  // {"RECLOCK_ZA2": false},
  // {"PARAMIXB": []},
  // {"AHEADER": []},
  // {"ACOLS": []},
  {"MAIL_ERROR_MESSAGE": "Falha SMTP simulada"}
]
```

`DDATABASE` alimenta `Date()`/`dDataBase`; `TIME` alimenta `Time()`; `CUSERLOCAL` e um caminho simulado, nao um diretorio criado pelo TestLab. `MODEL_OPERATION` controla `GetOperation()` fora de `--mvc-case` (padrao `2`; durante um cenario de inclusao, o TestLab usa `3`). Altere um resultado `MAIL_*_RESULT` para um numero diferente de zero para simular falha; `MAIL_ERROR_MESSAGE` e usado quando o fonte chama `GetErrorString()`.

Ha ainda entradas que dependem do fonte, sem valor universal para copiar: `RECLOCK_<ALIAS>` (por exemplo, `{"RECLOCK_ZA2": false}`) faz `RecLock`/`DbRLock` falhar nesse alias; sem a entrada, o bloqueio e permitido. `PARAMIXB`, `AHEADER` e `ACOLS` podem ser declarados como valores/arrays globais, mas precisam ter a estrutura e os indices esperados pelo `.prw` testado. Outros nomes em `ambiente` tambem viram globais do interpretador; isso nao cria automaticamente uma funcao ou uma integracao Protheus. Parametros lidos por `GetMV` pertencem a `parametros`, nao a `ambiente`.

```text
-run ARQUIVO.PRW       fonte AdvPL alvo da execução ou simulação
--fixture ARQUIVO.JSONC fixture específico; aceita também .json
--entry FUNCAO         entrada; opcional, usa a primeira User Function
--args-json ARRAY       argumentos da entrada como array JSON
--name-profile PERFIL    modern (padrao) ou legacy10 (10 caracteres historicos)
--mvc-case NOME          executa cenario MVC de inclusao definido no fixture
--persist                carrega e salva registros no state.json ao lado da fixture
```

### Persistencia opcional em `state.json`

```powershell
advpl-testlab -run EX1.prw --persist
advpl-testlab -run EX1.prw --persist
```

O primeiro comando parte dos `registros` de `testlab.jsonc` se ainda nao houver `state.json`. Cada execucao seguinte com `--persist` carrega o estado anterior; apos uma execucao bem-sucedida que alterou registros, o TestLab substitui `state.json` por um snapshot JSON. O arquivo fica no mesmo diretorio da fixture descoberta (ou informada por `--fixture`) e e ignorado pelo Git nos projetos deste workspace. O JSONC nunca e reescrito. Sem `--persist`, a execucao ignora `state.json` e usa apenas a fixture. Estado invalido ou alias nao declarado causa erro sem sobrescrita; erro de execucao ou divergencia de expectativa MVC tambem nao grava. Nao execute duas gravacoes simultaneas no mesmo `state.json`: bloqueio de concorrencia ainda nao esta implementado.

Para MVC1, use `advpl-testlab -run ZA1MVC.prw --mvc-case incluir-livro-valido --persist`. Uma inclusao aprovada fica disponivel para o proximo `-run ... --persist`; uma inclusao rejeitada nao cria nem altera o estado. Expectativas absolutas como `totalRegistros: 2` continuam sendo verificadas contra o estado carregado, portanto repetir o mesmo caso de inclusao pode falhar por ja existir um registro anterior. Para voltar ao ponto inicial, guarde ou remova conscientemente o `state.json`; isso nao altera o JSONC.

Para `GetSXENum(cAlias, cCampo)`, declare a regra na tabela do fixture: `"numeracao": {"ZA2_COD": {"digitos": 6, "inicio": 1}}`. O runtime verifica que o campo existe, calcula o maior codigo numerico dos registros carregados e reserva o proximo valor preenchido com zeros. Chamadas repetidas na mesma execucao nao repetem numero; com `--persist`, os registros de `state.json` entram no calculo da execucao seguinte. Registros sem codigo sao ignorados; valores nao numericos, estouro de largura e ausencia da regra geram erro explicito. Isto simula o caso de dois argumentos, nao o servico SXE/SXF/License Server nem a semantica completa de `ConfirmSX8`/`RollbackSX8`.

### Cenarios de inclusao MVC

Defina `cenariosMvc` no `testlab.jsonc` e selecione um cenario por nome:

```jsonc
"cenariosMvc": [
  {
    "nome": "incluir-preco-negativo",
    "operacao": "incluir",
    "dados": {"ZA1MASTER": {"ZA1_COD": "000002", "ZA1_PRECO": -10}},
    "esperado": {"salvou": false, "totalRegistros": 1}
  }
]
```

```powershell
advpl-testlab -run ZA1MVC.prw --mvc-case incluir-preco-negativo
```

O `Activate()` do browse chama `ModelDef` no escopo ativo da entrada, preenche o modelo com `dados`, executa o bloco de pos-validacao (`bPost`) e compara `salvou` e, se declarados, `totalRegistros` e `registro` (ultimo registro completo). Uma inclusao aprovada acrescenta o registro ao runtime e, com `--persist`, ao `state.json`; o JSONC nao e alterado. Erro de expectativa retorna codigo `1`. A primeira versao aceita um unico `AddFields`/alias no `MPFormModel`, com campos `C` e `N` declarados na fixture; nao simula a UI, `ViewDef`, persistencia Protheus ou outras operacoes MVC. Sem `--mvc-case`, `-run` conserva o browse headless anterior.

O perfil de nomes e passado ao LivrePL na validacao e na execucao. Use, por exemplo, `advpl-testlab -validate rotina.prw --name-profile legacy10` para detectar colisoes de nomes historicos; o padrao `modern` mantem nomes completos. O perfil legado tambem considera `U_` mais oito caracteres para `User Function`.

### Dependencias locais com `usePrw`

Um fonte pode declarar dependencias locais pela convencao:

```advpl
//usePrw('ENVEMAIL.prw')
//usePrw('NOTIFSOL.prw')
```

Cada declaracao deve ocupar sua propria linha. O caminho e relativo ao arquivo que contem o comentario, deve terminar em `.prw` e permanecer dentro do diretorio do fonte principal. O TestLab carrega as dependencias recursivamente, evita duplicacao/ciclos e gera erro claro quando o arquivo nao existe.

As funcoes dos arquivos carregados participam da validacao semantica e da execucao. Uma `User Function EnviarEmailSolicitacao()` pode ser chamada por outro fonte como `U_EnviarEmailSolicitacao()`, conforme a convencao do AdvPL. O comentario continua inofensivo para o compilador Protheus e tambem serve como mapa direto para pessoas e agentes localizarem o codigo relacionado.

Para validar todas as funções do arquivo sem executar nenhuma delas:

```powershell
advpl-testlab -validate TRNSOL02.prw
```

O comando falha com erro de lexer, parser ou semântica quando encontra sintaxe inválida, construção sem suporte, variável não declarada ou função inexistente. O diagnóstico preserva a numeração do `.prw` original, inclusive quando existem diretivas `#include`, mostra a linha e aponta a coluna aproximada:

```text
SyntaxError: Token inesperado TokenType.NEWLINE (None)
  31 |     Local nI :=
     |                 ^
  --> C:\projeto\TRNSOL02.prw:31:13
```

Em um terminal interativo, o erro é exibido em vermelho e o processo termina com código `1`. Defina a variável de ambiente `NO_COLOR` para desativar cores. Saídas redirecionadas e ferramentas sem TTY recebem texto puro automaticamente.

Por exemplo, `Local oStmt := Nilo` produz `SemanticError: Variável 'Nilo' não declarada`. `Nil` continua sendo reconhecido normalmente como o literal AdvPL. A atribuição direta a um nome ainda segue a semântica Clipper/AdvPL já adotada pelo LivrePL: `x := 1` pode criar uma variável `PRIVATE` implícita.

Uma `PRIVATE` declarada no fonte pode ser acessada por outra funcao enquanto seu escopo dinamico estiver ativo. Por isso, `-validate` aceita o nome em funcoes auxiliares; `-run` ainda gera erro se a funcao for executada sem a `PRIVATE` ativa. Variaveis `LOCAL` continuam restritas a funcao que as declarou. O diagnostico de nome ausente aponta para a linha da leitura, nao para uma mencao anterior em comentario ou declaracao.

O TestLab aplica uma **convenção estrita de organização**: no início de cada função ou método, declare `LOCAL`/`STATIC`, depois `PRIVATE` e por último `PUBLIC`, antes dos comandos executáveis. Uma declaração fora dessa ordem ou dentro de `If`/`For`/outro bloco gera `SemanticError` na linha da declaração. Exemplo: `Private nP := 1` seguido de `Local nL := 2` falha em `-validate` e `-run`. Esta é uma política de validação do TestLab; a [documentação da TOTVS](https://tdn.totvs.com/pages/viewpage.action?pageId=6063095) não impõe a mesma ordem como regra geral da linguagem AdvPL.

Para fontes MVC, a validacao tambem confere acoes literais `VIEWDEF.<modulo>` e `U_<nome>` (com ou sem `()`) de `ADD OPTION` contra as `User Function` carregadas. Por exemplo, `ACTION 'U_Z04CAN'` exige `User Function Z04CAN()` no fonte atual ou em um `//usePrw` carregado; uma funcao `Static` de mesmo nome nao atende a referencia. Uma resposta explicitamente configurada em `funcoes` do fixture tambem e aceita. Acoes calculadas dinamicamente nao sao verificadas estaticamente. A validacao tambem confere campos literais de `SetPrimaryKey({ ... })` contra a fixture e IDs literais de `GetValue('SUBMODELO', 'CAMPO')` contra `AddFields`/`AddGrid`. Isso ocorre mesmo que as funcoes MVC nao sejam executadas pela entrada headless. Por exemplo, `ZA1MASTE` em vez de `ZA1MASTER` falha tanto em `-validate` quanto em `-run`.

Da mesma forma, `Local aArea := GetAreaTESTE()` produz `SemanticError: Função 'GetAreaTESTE' não encontrada`. São aceitas as funções declaradas no próprio fonte, os built-ins implementados pelo LivrePL/TestLab, construtores de classes e funções simuladas em `funcoes` no JSON. Para validar uma simulação declarada em outro fixture, informe `--fixture arquivo.json` também com `-validate`.

Sem instalar, o mesmo fluxo pode ser executado dentro deste repositorio:

```powershell
python main.py -run examples/getmv.prw --fixture fixtures/getmv.json --entry ex
```

Funcoes de entrada com parametros podem ser chamadas assim:

```powershell
advpl-testlab -run NOTIFSOL.prw --entry NotificarSolicitacao --args-json '["ENVIO"]'
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

### Simulacao headless de e-mail

O `ENVEMAIL.prw` real e validado e executado pela suite. `TMailManager` e `TMailMessage` sao objetos somente em memoria: nenhuma conexao SMTP e aberta e `Send()` nunca envia uma mensagem real. Um envio aceito e armazenado em `FixtureInterpreter.sent_emails` sem senha, permitindo conferir remetente, destinatario, assunto, tipo e corpo.

Os retornos usam valores numericos em `ambiente`; quando ausentes, o padrao e sucesso (`0`). O bloco completo para copiar esta na secao `ambiente` acima.

Para exercitar o tratamento de erro de `Send()`, configure `MAIL_SEND_RESULT` com valor diferente de zero. `MAIL_ERROR_MESSAGE` sera devolvida por `GetErrorString()`. Tambem possuem suporte headless as funcoes `At`, `Left`, `EncodeUTF8` e `FreeObj`; `EncodeUTF8` preserva a string Python porque nao ha transporte de bytes real.

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
            "titulo": "Código"
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

O dicionário usa títulos apenas em português. Os campos precisam somente de `nome`, `tipo` e, quando útil para a saída, `titulo`; metadados como `tamanho`, `descricao`, `obrigatorio` e `decimais` não são necessários para a execução headless.

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

1. Crie `testlab.jsonc` na pasta dos fontes do caso de teste. Para projetos com varios desafios, use um fixture por pasta; a CLI prefere o fixture mais proximo do `.prw`.
   Nos fixtures versionados, mantenha sempre `parametros`, `tabelas`, `funcoes`, `ambiente`, `dialogos`, `especificidadesPrw` e `consultas`, usando `[]` para secoes vazias.
   JSONC aceita comentarios `//` e `/* ... */` e virgulas finais; dentro de strings, esses caracteres sao preservados. Arquivos `.json` continuam aceitos, mas seguem JSON estrito, sem comentarios nem virgulas finais.
2. Cadastre parâmetros, tabelas, funções externas e consultas usadas pelo fonte.
3. Abra um terminal no diretório do `.prw`.
4. Execute `advpl-testlab -run NomeDoFonte.prw`.
5. Para validar o TestLab, execute `python -m unittest discover -s tests -v` neste repositório.

A suite propria do TestLab usa apenas fontes e fixtures deste repositorio; nao depende dos `.prw` de `desafios-aprendizado`. Os testes de integracao dos casos reais ficam em `desafios-aprendizado/tests` e podem ser executados separadamente naquele repositorio.

## Cobertura atual

### Implementado e interpretado

Estes recursos passam pelo parser e pelo interpretador, portanto sua lógica é executada:

- descoberta automática da primeira `User Function` ou seleção explícita por `--entry`;
- descoberta de `testlab.jsonc` ou `testlab.json` no diretório do fonte ou nos diretórios pais, com fallback para os nomes antigos;
- funções `Function`, `User Function` e `Static Function` dentro da cobertura do LivrePL;
- variáveis `Local`, `Private`, `Public` e `Static`;
- atribuições simples, `+=` e `-=`;
- valores texto, numérico, lógico, `Nil` e arrays;
- operadores aritméticos, relacionais e lógicos suportados pelo LivrePL;
- estruturas `If/ElseIf/Else`, `For`, `While`, `Do While`, `Do Case` e `Begin Sequence`;
- chamadas de função, funções estáticas, acesso a arrays e retorno de valores;
- classes, métodos e code blocks dentro do subconjunto implementado pelo LivrePL;
- builtins básicos do LivrePL, como `Len`, `AllTrim`, `Upper`, `Lower`, `AAdd`, `Empty`, `ValType` e `cValToChar`;
- builtins Protheus adicionados pelo TestLab: `GetMV`, `StrTran`, `Chr`, `Transform`, `DToC` e `MsgStop`;
- `MsgAlert` e `MsgInfo` como saída textual `[ALERTA]` e `[INFO]`, sem janela;
- `MsgYesNo` com retorno determinístico por fonte e conteúdo, sem saída textual;
- `Define MSDialog ... TITLE ... FROM ...` como saída textual `[MSDIALOG]`;
- linhas de controles `@ ...` e `Activate Dialog` como operações sem interface;
- leitura e validação das coleções `parametros`, `tabelas`, `funcoes` e `consultas` do fixture;
- validação semântica de identificadores e chamadas contra parâmetros, declarações, globais, built-ins e funções simuladas;
- descoberta e execucao recursiva de dependencias locais declaradas com `//usePrw('arquivo.prw')`;
- simulacao sem rede de `TMailManager`, `TMailMessage` e `Send()`;
- `GetMV(cParam)` em modo estrito e `GetMV(cParam, lHelp, uDefault)` com valor padrão;
- execução integral dos casos isolados `U_SolMailCfg()` e `TextoHtml()` usados nos testes.

### NOTIFSOL.prw interpretado integralmente

O fonte real e sua dependencia `ENVEMAIL.prw` passam juntos por lexer, parser, validacao semantica e interpretacao. A suite executa `ENVIO`, `APROVACAO`, `REJEICAO`, `PROCESSAMENTO` e o evento invalido.

- aliases estaticos `Z02->CAMPO` e `Z03->(...)` leem as tabelas do fixture;
- `DbSetOrder`, `DbSeek`, `Eof`, `Deleted` e `DbSkip` operam somente em memoria;
- `UsrRetMail` e `FwGetUserName` recebem retornos determinísticos de `funcoes`;
- o HTML e montado pela logica original, incluindo totais e resultados por item;
- `U_EnviarEmailSolicitacao()` resolve a dependencia local e captura o envio em memoria, sem SMTP real;
- `--args-json` fornece o `cEvento` da funcao de entrada pela CLI.

### TRNSOL01.prw em modo headless

O fonte real e as dependencias declaradas com `//usePrw` passam por lexer, parser e validacao semantica. A suite executa a entrada `TRNSOL01`, menu, modelo/view e os fluxos de envio, aprovacao, rejeicao, processamento e cancelamento, incluindo erro de item e rollback por falha de bloqueio.

```powershell
advpl-testlab -validate TRNSOL01.prw
advpl-testlab -run TRNSOL01.prw
advpl-testlab -run TRNSOL01.prw --entry Z04PROC
```

- `Z04`, `Z05` e `Z06` sao registros em memoria; `DbSetOrder` usa `indices` do fixture, quando declarados, para ordenar e buscar pela chave configurada;
- `RecLock`, `MsUnlock` e transacoes alteram apenas os registros da execucao atual; `RECLOCK_Z06: false` em `ambiente` simula falha de bloqueio e exercita o rollback;
- `FWBrowse`, `MPFormModel`, `FWFormView`, `MSDialog` e controles de tela usam adaptadores sem UI; `dialogos` fornece os valores finais da rejeicao;
- confirmacoes `MsgYesNo` de processamento e cancelamento usam `especificidadesPrw` e podem ser alteradas entre `true` e `false`;
- as notificacoes passam pelo codigo real de `NOTIFSOL`/`ENVEMAIL`, mas o envio fica somente em memoria, sem SMTP.

`-run` valida todas as funcoes carregadas, mas executa apenas a entrada escolhida e os ramos que ela chamar. As acoes de menu nao sao clicadas automaticamente. Os adaptadores de controles `@` ignoram callbacks de UI, portanto a validacao headless nao comprova a sintaxe interna desses callbacks, nem substitui compilacao e testes no AppServer/DBAccess.

### Primitivas de banco simuladas

O runtime headless reconhece `DbSelectArea`, `DbSetOrder`, `DbRLock`, `DbCloseArea`, `DbCommit`, `DbCommitAll`, `DbDelete`, `DbGoTo`, `DbGoTop`, `DbGoBottom`, `DbRLockList`, `DbSeek`, `MsSeek`, `DbSkip`, `DbSetFilter`, `DbOrderNickname`, `DbUnlock`, `DbUnlockAll`, `DbUseArea`, `MsUnlock`, `RecLock`, `RLock`, `Select`, `SoftLock` e `Unlock`. `DbGoBotton` (grafia da pergunta) tambem e aceito como alias de `DbGoBottom` na simulacao.

- `Select(cAlias)` apenas informa o numero da area; `DbSelectArea(cAlias|nArea)` a seleciona. `DbUseArea` so reabre aliases declarados em `tabelas`; nao acessa um SGBD real.
- `DbSetOrder(n)` usa `indices`. Para `DbOrderNickname(cApelido)`, declare tambem `"apelidosIndices": {"CODIGO": 1}` na tabela, associando o apelido a uma ordem existente.
- `DbSeek`/`MsSeek` pesquisam pela chave do indice atual; `lSoft` opcional posiciona no proximo registro visivel se nao houver correspondencia. `DbSetFilter({|| ...}, cExpressao)` avalia o bloco na navegacao; a expressao textual e apenas descritiva. `DbSetFilter()` limpa o filtro.
- `DbRLock`, `RLock`, `RecLock` e `SoftLock(cAlias)` simulam bloqueios locais ao processo; `DbRLockList` lista recnos bloqueados. `DbDelete` exige bloqueio e marca `D_E_L_E_T_`, sem remover fisicamente o registro. `DbUnlock`/`Unlock`, `DbUnlockAll` e `MsUnlock` liberam os bloqueios simulados.
- `DbCommit` e `DbCommitAll` validam a chamada, mas nao fazem flush intermediario: com `--persist`, o snapshot e gravado apenas ao fim de uma execucao bem-sucedida. Concorrencia, RDD, transacoes do DBAccess e tempos de espera por lock nao sao reproduzidos.

### desafio0-Fat006 em modo headless

Os quatro fontes da pasta `desafios-aprendizado/desafio0-Fat006` usam um fixture proprio. `U_MSGDANFE`, `A410CONS` e `PE01NFESEFAZ` sao independentes; `UFATE003` carrega `U_MSGDANFE` via `usePrw`. A suite `desafios-aprendizado/tests/test_fat006.py` verifica consolidacao sem duplicatas, preview, mensagem da NF-e, gravacao em SC5 e falha de bloqueio.

- `AScan` avalia blocos de busca e a adaptacao aceita `a[linha, coluna]`;
- `PARAMIXB`, `aHeader` e `aCols` sao valores declarados em `ambiente`; `Type`, `AClone`, `ChkFile`, `ErrorBlock` e `Break` possuem adaptadores headless;
- `FieldPos`, `FieldGet`, `DbStruct`, atribuicao `ALIAS->CAMPO` e `ALIAS->(MsUnlock())` usam tabelas em memoria;
- a CLI executa uma entrada por vez e nao imprime automaticamente seu valor de retorno; os testes automatizados verificam os retornos.

Nada e persistido em SC5 real nem enviado ao emissor NF-e. `ErrorBlock` armazena/restaura o bloco no interpretador, mas nao simula toda a semantica de erros do AppServer.

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
- `DbSetOrder` usa os campos de `indices` quando configurados; sem eles, `DbSeek` usa a ordem dos campos do registro como chave de prefixo. Nao interpreta indices SX2/SIX;
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
