# Validacao semantica de metadados MVC

## Objetivo

Detectar no `ZA1MVC.prw` dois erros que antes passavam pelo `-run`: acao `VIEWDEF.ZA1ABC` sem modulo carregado e campo `ZA1_CODIGB` ausente na fixture de `ZA1`.

## Desenho

O preparo headless converte `ADD OPTION` em `AAdd` preservando a linha. A analise semantica reconhece essas chamadas originadas do comando e verifica o modulo literal de `VIEWDEF` nas `User Function` carregadas, inclusive nas dependencias `usePrw`. Metodos `SetPrimaryKey` com array literal sao verificados contra `campos` das tabelas da fixture; tabelas legadas sem `campos` usam as chaves dos registros. O metodo simulado repete a verificacao quando recebe um array construido dinamicamente.

## Verificacao

- `advpl-testlab -run ZA1MVC.prw` no diretorio `caminho-protheus/Fontes/mvc/desafio1` agora falha com `SemanticError` em `VIEWDEF.ZA1ABC` na linha 17.
- Testes locais independentes do projeto de exercicios cobrem modulo valido/invalido, campo valido/invalido, `-run` com funcoes MVC nao visitadas e chave dinamica em runtime.
- `python -m unittest discover -s tests -q`: 47 testes aprovados.

## Fora de escopo

`-validate` nao resolve acao de menu ou lista de chaves construida dinamicamente. O TestLab nao simula interacao real com menus, AppServer, DBAccess ou SmartClient.
