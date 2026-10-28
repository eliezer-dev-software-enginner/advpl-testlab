# Preview do browse no terminal

## Uso

`advplab --preview Fontes/ZA4MVC.prw` descobre o mock junto do fonte ou nos pais. Aceita --fixture, --entry, --args-json e --name-profile. --preview e mutuamente exclusivo com run, validate, compile, init e mvc1; persistencia e cenarios MVC sao rejeitados.

O fonte e validado e executado no runtime simulado ate o primeiro browse ativado. PreviewComplete interrompe a entrada depois da renderizacao, evitando os comandos posteriores ao Activate. Comandos anteriores ao browse ainda sao executados em memoria no simulador; o preview nao e analise estatica de codigo arbitrario. Nao inicia LS, nao conecta ao Protheus e nao salva state.json. O arquivo de mock nao e alterado. Sem browse ativado, retorna erro claro.

## Conteudo

- Titulo de SetDescription e alias de SetAlias.
- Acoes declaradas no array aRotina, em SetMenuDef com array ou no MenuDef acessivel no fonte, nessa prioridade. Sao exibidas, sem invocar suas actions.
- Colunas explicitas de AddColumn e colunas calculadas de SetFields. Sem AddColumn, campos do mock usam titulo, descricao ou nome; visivel false omite um campo automatico.
- Cabecalhos das colunas truncados nos primeiros 12 caracteres, sem reticencias; descricoes completas permanecem no mock. O titulo do browse e os dados nao recebem esse limite.
- Ate 20 registros do mock, sem inventar dados. Datas D em DD/MM/AAAA e numeros N usando decimais do campo, separador decimal virgula e milhar ponto. Codigos de status permanecem como declarados no mock: nao se infere o significado do SX3.
- Tabela vazia continua exibindo as colunas declaradas. Sem metadados e sem registros, informa a falta de colunas.
- Largura obtida do terminal, colunas divididas em grupos com os mesmos registros e celulas limitadas a 28 caracteres. Valores completos permanecem no mock. Caracteres de controle sao substituidos por espacos. Legendas exibem suas descricoes, sem cores ou avaliacao de condicoes.

O modulo browse_preview.py formata a saida; FixtureInterpreter coleta os valores respeitando o alias/posicao corrente e restaura esse contexto inclusive em falhas de code blocks. -run conserva sua saida anterior.

## Exemplo incluido

```bash
advplab --preview examples/preview-browse.prw --fixture fixtures/preview-browse.jsonc
```

O exemplo mostra dois registros ficticios, datas 28/10/2026 e valores 20,00/600,00, com acoes Incluir, Alterar, Visualizar e Excluir.

## Limites

E uma aproximacao textual do browse, nao um SmartClient/WebApp nem um preview de ViewDef/formulario. Layout, cores, selecao, filtros interativos, mascaras SX3, menus de permissao e operacoes reais do banco nao sao reproduzidos. O mock precisa conter os dados e metadados desejados; os registros visiveis na tela real nao sao importados automaticamente. Somente o primeiro browse e mostrado.

## Evidencias

Testes proprios cobrem titulo/acoes/datas/valores, tabela vazia, parada no primeiro browse, descoberta no pai sem escrita, opcoes invalidas, ausencia de browse, colunas calculadas, largura/controle, aRotina e preservacao de alias/posicao em falhas. O fonte real de controle-patrimonio foi executado pela CLI e mostrou ZA4 vazia conforme seu mock, sem modificar esse projeto. Os tres exemplos basicos de regressao do LivrePL passaram.
