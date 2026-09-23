# Fase MVC — cenarios de inclusao

Objetivo: exercitar a pos-validacao de `MPFormModel` em inclusoes deterministicas, sem UI ou persistencia.

## Desenho

O JSONC define `cenariosMvc` com `nome`, `operacao: "incluir"`, `dados` por identificador de `AddFields` e `esperado.salvou` (obrigatorio), `esperado.totalRegistros` e `esperado.registro` (opcionais). A CLI seleciona um cenario com `--mvc-case NOME`. A entrada AdvPL continua sendo executada; em `FWBrowse:Activate`, o runtime chama `ModelDef` enquanto as `PRIVATE` da entrada ainda estao no escopo, aplica o registro candidato ao submodelo, invoca o bloco `bPost`, acrescenta o registro apenas se o retorno for `.T.` e confere a expectativa.

As tabelas sao copiadas da fixture para o runtime. Cada processo comeca do estado original; nem os objetos da fixture nem o arquivo JSONC sao alterados. Campo desconhecido, tipo incorreto, modelo ausente, `bPost` ausente e expectativa divergente causam erro.

## Saida real verificada

Em `caminho-protheus/Fontes/mvc/desafio1`:

```text
advpl-testlab -run ZA1MVC.prw --mvc-case incluir-preco-negativo
[ALERTA] Erros na solicitacao: Preço não pode ser negativo
[MVC] incluir-preco-negativo: salvou=false, totalRegistros=1

advpl-testlab -run ZA1MVC.prw --mvc-case incluir-livro-valido
[MVC] incluir-livro-valido: salvou=true, totalRegistros=2
```

A suite propria do TestLab passou com 55 testes, incluindo rejeicao, inclusao, falha de expectativa, campo ausente e imutabilidade da fixture.

## Fora de escopo desta fase

Menus interativos, `ViewDef`, grid, multiplos submodelos, alteracao/exclusao, gravacao Protheus e persistencia no JSONC. `-validate` continua independente de `--mvc-case`.
