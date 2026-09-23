# Correcao da validacao de PRIVATE

## Objetivo

Aceitar fontes que declaram uma `PRIVATE` na funcao de entrada e a leem em uma funcao auxiliar, sem permitir que uma `LOCAL` de outra funcao passe pela validacao.

## Desenho

`compile_sources()` coleta os nomes `PRIVATE` em todos os fontes carregados e os informa ao validador semantico de cada unidade. A validacao estatica trata esses nomes como potencialmente visiveis; o interpretador do LivrePL continua responsavel por exigir que o escopo dinamico esteja ativo na execucao. Para um nome realmente ausente, a linha do no `Identifier` ou `Call` da AST direciona a localizacao do diagnostico.

## Verificacao

- `python -m unittest discover -s tests -q`: 40 testes aprovados, incluindo `PRIVATE` no mesmo arquivo e em arquivo dependente, acesso a `LOCAL` rejeitado, escopo ausente em runtime e linha correta de erro.
- `advpl-testlab -run ZA1MVC.prw` no diretorio `caminho-protheus/Fontes/mvc/desafio1`: exibiu o browse simulado `Gerenciamento de livros` com o registro `Livro A`.

## Fora de escopo

A analise estatica nao prova que toda rota de execucao inicializou a `PRIVATE`; chamadas sem escopo ativo continuam falhando em runtime. Nao ha simulacao de AppServer, SmartClient ou MVC completo.
