# Validacao semantica de metadados MVC

## Objetivo

Detectar no `ZA1MVC.prw` erros que antes passavam pelo `-run`: acao `VIEWDEF.ZA1ABC` sem modulo carregado, campo `ZA1_CODIGB` ausente na fixture e ID `ZA1MASTE` inexistente em `GetValue`.

## Desenho

O preparo headless converte `ADD OPTION` em `AAdd` preservando a linha. A analise semantica reconhece essas chamadas originadas do comando e verifica o modulo literal de `VIEWDEF` nas `User Function` carregadas, inclusive nas dependencias `usePrw`. Metodos `SetPrimaryKey` com array literal sao verificados contra `campos` das tabelas da fixture; tabelas legadas sem `campos` usam as chaves dos registros. O metodo simulado repete a verificacao quando recebe um array construido dinamicamente.

IDs literais do primeiro argumento de `GetValue` com dois argumentos sao comparados com os IDs literais de `AddFields`/`AddGrid` no mesmo fonte. Se algum ID de submodelo for construido dinamicamente, a comparacao estatica e omitida; a chamada efetiva continua verificada em runtime. A checagem nao depende de `ModelDef` ou `bPost` serem chamados pela entrada.

## Verificacao

- `advpl-testlab -run ZA1MVC.prw` no diretorio `caminho-protheus/Fontes/mvc/desafio1` agora falha com `SemanticError` em `VIEWDEF.ZA1ABC` na linha 17.
- Testes locais independentes do projeto de exercicios cobrem modulo valido/invalido, campo valido/invalido, `-run` com funcoes MVC nao visitadas e chave dinamica em runtime.
- `python -m unittest discover -s tests -q`: 47 testes aprovados.
- Em 24/09/2026, o fonte real com `GetValue('ZA1MASTE', 'ZA1_PRECO')` falhou na linha 55 com `SemanticError` em `-validate`, `-run` e `-run --mvc-case`. A suite propria passou com 59 testes.

## Fora de escopo

`-validate` nao resolve acao de menu, lista de chaves ou ID de submodelo construido dinamicamente. O TestLab nao simula interacao real com menus, AppServer, DBAccess ou SmartClient.
