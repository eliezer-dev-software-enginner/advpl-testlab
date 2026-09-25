# CONTEXT.md — Contexto do AdvPL TestLab

> Memoria central do projeto. Em uma nova sessao, ler junto com `AI_RULES.md`, `TODO.md`, `DECISIONS.md` e `PROMPT.md`.

---

## Indice de documentacao

| Arquivo | Funcao |
|---|---|
| `docs/AI_RULES.md` | Regras obrigatorias de trabalho |
| `docs/CONTEXT.md` | Arquitetura, arquivos, execucao e estado atual |
| `docs/TODO.md` | Roadmap e pendencias por fase |
| `docs/DECISIONS.md` | Decisoes de arquitetura em formato ADR |
| `docs/PROMPT.md` | Objetivo mestre e roteiro de bootstrap |
| `docs/fase-0-levantamento.md` | Levantamento e desenho inicial |
| `docs/fase-1-getmv.md` | Implementacao e evidencia do `GetMV` |
| `docs/fase-1b-casos-reais.md` | Casos reais `U_SolMailCfg` e `TextoHtml` |
| `docs/corpus-desafio1-context-map.md` | Mapa dos fontes funcionais usados como corpus |
| `docs/fase-ui-headless.md` | Mensagens, dialogos sem UI e respostas deterministicas |
| `docs/fase-trnsol02-integral.md` | Validacao e execucao integral do primeiro fonte real |
| `docs/fix-private-semantics.md` | Escopo dinamico de `PRIVATE` e localizacao de erros semanticos |
| `docs/fase-mvc-validacao.md` | Validacao de acoes de menu e chaves primarias MVC |
| `docs/fase-debug-vscode.md` | Depuracao DAP inicial de fontes PRW no VS Code |

## O que e o projeto

O AdvPL TestLab executa codigo AdvPL com um ambiente Protheus simulado por fixtures JSON. Ele permite testar logica de negocio isolada sem AppServer, licenca, banco de dados ou interface do Protheus.

O projeto nao e um fork do LivrePL. Ele vive em repositorio proprio e usa o LivrePL como dependencia local, mantendo os dois diretorios como irmaos:

```text
protheus/
|-- livrePL/
`-- advpl-testlab/
```

## Arquitetura

```text
arquivo .prw
    |
    v
executor (descoberta de entrada e fixture)
    |
    v
preparo de sintaxe Protheus suportada
    |
    v
parser + FixtureInterpreter do LivrePL
    |-- objetos, aliases e arquivos virtuais
    `-- integracoes Protheus simuladas
             |
             v
          Fixture JSON
```

`FixtureInterpreter` herda de `Interpreter` e estende `_build_builtins()`. A decisao evita mudancas no lexer, parser e runtime central quando o recurso pode ser expresso como funcao de framework.

A depuracao inicial usa `DebugFixtureInterpreter` sobre `FixtureInterpreter` e um adaptador DAP em processo separado. A extensao VS Code em `vscode-extension/` inicia esse processo no Python com o TestLab instalado. Breakpoints/stack usam o caminho da declaracao carregada por `compile_sources`, inclusive dependencias `//usePrw`; o escopo e headless e ainda nao cobre toda linha, expressao Watch ou excecao pausavel.

O adaptador de comandos suporta `PREPARE ENVIRONMENT EMPRESA ... FILIAL ...` e `RESET ENVIRONMENT` com estado local ao runtime. No EX1 de banco, `Date()` consulta `DDATABASE` deterministico e `xFilial()` pode usar a area corrente. `--persist` carrega e salva os registros em `state.json`, separado do fixture imutavel `testlab.jsonc`; inclui escritas por `RecLock` e MVC1. Sem a opcao, tudo continua somente em memoria (ADR-032).

Na validacao semantica, nomes `PRIVATE` declarados nos fontes carregados sao considerados potencialmente visiveis entre funcoes; `LOCAL` continua restrito a sua funcao. A disponibilidade efetiva de `PRIVATE` e resolvida no runtime pela pilha dinamica. Erros de identificador usam a linha da AST para apontar a leitura que falhou.

O TestLab valida uma convencao estrita de declaracoes por funcao/metodo: `LOCAL`/`STATIC`, `PRIVATE`, `PUBLIC`, sempre antes de comandos executaveis. O LivrePL apenas anota a linha de `VarDecl`; a restricao nao altera a gramatica base, pois a documentacao TOTVS permite declaracoes fora do inicio.

Fontes MVC recebem verificacao adicional: `ADD OPTION` com `VIEWDEF.<modulo>` literal deve apontar para uma `User Function` carregada, e `SetPrimaryKey` literal deve usar campos da fixture. O runtime tambem verifica chaves calculadas dinamicamente quando o metodo e chamado.

IDs literais de `GetValue('SUBMODELO', 'CAMPO')` tambem sao comparados aos IDs declarados por `AddFields`/`AddGrid` no mesmo fonte, antes da execucao. Isso detecta typos no `bPost` mesmo quando o browse nao aciona um cenario MVC. IDs dinamicos continuam sujeitos a verificacao runtime. Ver ADR-029.

## Arquivos do projeto

| Caminho | Responsabilidade |
|---|---|
| `fixture_runtime.py` | Carrega/valida fixtures, integra o LivrePL e registra builtins simulados |
| `semantic.py` | Valida identificadores e chamadas contra simbolos e funcoes conhecidas |
| `executor.py` | Descobre entrada/fixture, valida e executa pelo interpretador |
| `main.py` | CLI `advpl-testlab -run` e `-validate` |
| `pyproject.toml` | Empacotamento e comando instalavel |
| `debug_runtime.py` | Ganchos de pausa, breakpoints e estados da pilha sem modificar o LivrePL |
| `debug_adapter.py` | Protocolo DAP por stdio para o VS Code |
| `vscode-extension/` | Extensao local em desenvolvimento para iniciar o adaptador |
| `examples/getmv.prw` | Exemplo de codigo AdvPL real usando `GetMV` |
| `examples/ui-headless.prw` | Exemplo executavel de dialogo e mensagens sem UI |
| `examples/real-cases/sol_mail_cfg.prw` | Funcoes isoladas de `NOTIFSOL.prw` |
| `fixtures/getmv.json` | Fixture de exemplo com parametros e tabelas |
| `fixtures/sol_mail_cfg.json` | Parametros SMTP para o primeiro caso real |
| `tests/test_getmv.py` | Testes unitarios e ponta a ponta da Fase 1 |
| `desafios-aprendizado/tests/test_real_cases.py` | Testes de integracao do desafio1-solicitacao-compra, fora da suite propria do TestLab |
| `docs/` | Memoria permanente e documentos de fase |

## Formato atual do fixture

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
        "registros": []
      }
    }
  ]
}
```

- `parametros`: lista em que cada objeto declara exatamente um parametro consultado por `GetMV`.
- `tabelas`: lista em que cada objeto declara exatamente um alias; o valor do alias possui `registros` e pode receber metadados.
- `funcoes`: respostas configuradas para chamadas externas em modo headless.
- `consultas`: conjuntos de registros devolvidos por consultas simuladas, indexados pela funcao de entrada.
- `especificidadesPrw`: respostas de funcoes identificadas por fonte, nome e conteudo da chamada.
- `dialogos`: estado final de variaveis aplicado por dialogos headless.
- `ambiente`: valores deterministas como `CUSERLOCAL` e `TIME`.
- Chaves de parametros e aliases sao normalizadas para maiusculas.
- O formato legado baseado em objetos continua aceito apenas para compatibilidade de leitura.

## Funcionalidade entregue

### Fase 0 — Levantamento

- Mapeamento incremental de `GetMV`, aliases, navegacao, escrita e efeitos de interface.
- Arquitetura por camada externa e heranca definida.

### Fase 1 — GetMV

- Leitura de fixture JSON.
- `GetMV(cParam)` registrado como builtin.
- Erro explicito para parametro ausente ou argumento invalido.
- CLI e exemplo ponta a ponta.
- Cinco testes automatizados aprovados.

### Fase 1b — Casos reais do desafio1

- `GetMV(cParam, lHelp, uDefault)` com fallback tipado.
- `StrTran` e `Chr` registrados na camada do TestLab.
- `U_SolMailCfg()` executado com configuracoes presentes e defaults ausentes.
- `TextoHtml()` executado com escape HTML e quebra de linha.
- Corpus real mapeado para orientar as fases seguintes.
- Suite ampliada para treze testes automatizados apos a migracao do schema JSON.

### Executor integral do TRNSOL02

- CLI instalavel com `advpl-testlab -run arquivo.prw`.
- Descoberta automatica da primeira `User Function` e de `testlab.jsonc`/`testlab.json` nos diretorios pais, com fallback para o nome antigo.
- `--name-profile modern|legacy10` seleciona a politica de nomes do LivrePL tanto em `-validate` quanto em `-run`; `modern` e o padrao.
- Validacao das tres funcoes do fonte por `-validate`.
- Execucao de `Z04CON`, `fAskFiltros` e `fGerarExcel` pelo interpretador.
- Runtime de `FWExecStatement`, alias dinamico, navegacao e `FWBrowse`.
- Exportacao HTML simulada em arquivo virtual.
- Cenarios de cancelamento, consulta vazia, browse e exportacao confirmada.
- Fixture real em `desafios-aprendizado/desafio1-solicitacao-compra/testlab.jsonc`, com metadados e registros de Z02 a Z06. Cada desafio mantem seu fixture ao lado dos fontes.
- Trinta e tres testes automatizados aprovados.

### UI headless e confirmacoes deterministicas

- `Define MSDialog` produz uma linha `[MSDIALOG]` com o titulo; controles `@` e `Activate Dialog` nao abrem interface.
- `MsgAlert` e `MsgInfo` produzem texto no terminal e retornam `NIL`.
- `MsgYesNo` nao produz texto e resolve `true` ou `false` por `fonte` + `nome` + `conteudo` em `especificidadesPrw`.
- Ausencia de resposta deterministica para `MsgYesNo` gera erro explicito.
- O retorno global legado em `funcoes` permanece aceito como fallback.
- A entrega inicial de UI headless foi incorporada à suíte atual de trinta e três testes automatizados.

### Diagnosticos de sintaxe

- Diretivas removidas pelo pre-processador preservam sua posicao por meio de linhas vazias.
- Um `NEWLINE` inesperado apos expressao incompleta aponta a linha da instrucao, nao a linha vazia seguinte.
- A CLI exibe trecho, marcador, caminho, linha e coluna; em terminal interativo, o erro aparece em vermelho.
- `NO_COLOR` desativa ANSI e saidas sem TTY permanecem em texto puro.
- Cinco testes dedicados cobrem sintaxe, coordenadas, cor, identificadores e funcoes inexistentes, alem de funcoes simuladas; a suite possui trinta e oito casos. Se o corpus externo `TRNSOL02.prw` estiver propositalmente invalido, os nove testes de integracao que dependem dele falham como esperado ate o fonte ser corrigido.
- `Local oStmt := Nilo` falha como `SemanticError`, enquanto `Nil` permanece um literal valido.
- `GetAreaTESTE()` falha antes da execucao; funcoes declaradas em `funcoes` no fixture continuam permitidas.

### Dependencias `usePrw` e ENVEMAIL

- `//usePrw('arquivo.prw')` declara uma dependencia local relativa ao fonte atual.
- O executor carrega o grafo recursivamente, rejeita arquivo ausente/fora da raiz e disponibiliza as funcoes para validacao e execucao, incluindo chamadas `U_Nome()`.
- O `ENVEMAIL.prw` real passa por lexer, parser, validacao semantica e execucao automatizada de suas validacoes de entrada.
- `TMailManager`/`TMailMessage` sao simulados em memoria; `Send()` nunca acessa a rede e os dados nao sensiveis do envio ficam em `sent_emails`.
- Resultados SMTP podem ser controlados por `MAIL_INIT_RESULT`, `MAIL_TIMEOUT_RESULT`, `MAIL_CONNECT_RESULT`, `MAIL_AUTH_RESULT`, `MAIL_SEND_RESULT` e `MAIL_ERROR_MESSAGE` em `ambiente`.
- Seis testes adicionais cobrem dependencias locais, referencia ausente, validacoes do `ENVEMAIL`, sucesso headless e erro de envio; a suite passa a ter quarenta e quatro casos.

### NOTIFSOL integral

- O corpus real fica em `desafios-aprendizado/desafio1-solicitacao-compra/NOTIFSOL.prw`.
- Aliases estaticos Z02/Z03, `While`, `DbSeek`, `DbSkip`, `Eof`, `Deleted`, `Transform`, `DToC` e `MsgStop` possuem runtime headless.
- Os eventos ENVIO, APROVACAO, REJEICAO e PROCESSAMENTO montam o HTML original e capturam o e-mail em memoria; evento desconhecido retorna falso.
- A CLI aceita argumentos da entrada por `--args-json`, por exemplo `["ENVIO"]`.
- Os testes do corpus real pertencem agora a `desafios-aprendizado/tests`; a suite propria do TestLab nao precisa de fontes desse outro projeto. Os testes legados de `TRNSOL02.prw`, ausente no corpus atual, foram retirados da descoberta automatica.

### TRNSOL01 headless

- O mesmo corpus contem `TRNSOL01.prw`; `//usePrw` carrega `NOTIFSOL` e `ENVEMAIL`.
- Fluxos de menu, aprovacao, rejeicao, processamento e cancelamento sao interpretados com Z04/Z05/Z06 em memoria.
- `indices` no fixture definem a ordenacao/chave de `DbSetOrder`/`DbSeek`; transacoes copiam o estado das tabelas para rollback.
- MVC e dialogos sao adaptadores headless; callbacks de controles `@` nao sao validados internamente. Nenhuma integracao real com AppServer, DBAccess ou SMTP ocorre.

### desafio0-Fat006 headless

- O fixture local `desafios-aprendizado/desafio0-Fat006/testlab.jsonc` fornece SC5, area M, `PARAMIXB`, `aHeader` e `aCols`.
- `UFATE003.prw` declara dependencia direta de `U_MSGDANFE.prw`; `A410CONS` e `PE01NFESEFAZ` sao independentes.
- O runtime suporta busca `AScan` com bloco, indice bidimensional adaptado, metadados de alias e escrita com RecLock em memoria. `ErrorBlock` e simplificado e nao representa AppServer.

## Como executar

```powershell
python main.py -run examples/getmv.prw --fixture fixtures/getmv.json --entry ex
```

Saida esperada e verificada:

```text
000007
```

Testes:

```powershell
python -m unittest discover -s tests -v
```

## Estado atual

- `cenariosMvc` em JSONC e `--mvc-case` permitem exercitar inclusao simples de `MPFormModel`, incluindo `bPost` e comparacao de `salvou`/`totalRegistros`, sem persistir no fixture. Os dois cenarios reais de `ZA1MVC.prw` foram executados: preco negativo rejeitado (1 registro) e valido aprovado (2 registros em memoria). Ver `fase-mvc-cenarios.md` e ADR-028.

- Fases 0, 1 e 1b concluidas.
- O `TRNSOL02.prw` e validado integralmente e executado pelo interpretador com fronteiras Protheus simuladas.
- A proxima entrega e generalizar a cobertura adquirida para os demais fontes do corpus.
- Nao ha dependencias Python externas.
- O repositorio Git foi inicializado na branch `main`.

## Fora do escopo

- Banco de dados real ou DBAccess.
- AppServer, licenciamento e SmartClient.
- MVC completo, REST e telas do framework.
- Persistencia de escrita no fixture nesta fase.
- Engenharia reversa de componentes TOTVS.

---

*Ultima atualizacao: 22/09/2026*
