# Context Map — desafio1-solicitacao-compra

## Objetivo

Usar os fontes funcionais de `DGB/desafios-pedro-torres/desafio1-solicitacao-compra` como corpus real para orientar a evolucao incremental do AdvPL TestLab.

## Fontes analisados

| Fonte | Funcoes principais | Oportunidade de teste | Bloqueadores atuais |
|---|---|---|---|
| `NOTIFSOL.prw` | `U_SolMailCfg`, `U_NotificarSolicitacao`, `TabelaItensEmail`, `TextoHtml` | Parametros SMTP, escape HTML, montagem de tabela e navegacao Z02/Z03 | `GetMV` com default, `StrTran`, `Chr`, aliases, navegacao |
| `ENVEMAIL.prw` | `U_EnviarEmailSolicitacao` | Validacao de assunto e configuracao SMTP antes da conexao | `At`, `Left` e classes externas apenas nos caminhos de envio |
| `TRNSOL01.prw` | Fluxos Z04/Z05/Z06, validacoes, processamento e notificacao | Regras de aprovacao, validacao de itens, status e escrita simulada | Alias `->`, cursor, `RecLock`, MVC, macros de interface e transacoes |
| `TRNSOL02.prw` | Consulta, filtros e exportacao | Filtros, cursor de alias dinamico e geracao tabular | SQL/framework, alias dinamico, datas e arquivo |

## Context Map

### Arquivos a modificar nesta entrega

| Arquivo | Finalidade | Mudanca necessaria |
|---|---|---|
| `fixture_runtime.py` | Runtime do TestLab | Aceitar `GetMV(cParam, lHelp, uDefault)` e devolver o default quando o parametro nao existir |
| `tests/test_real_cases.py` | Regressao do corpus real | Executar a funcao real `U_SolMailCfg()` com parametros presentes e ausentes |
| `examples/real-cases/sol_mail_cfg.prw` | Caso AdvPL portavel | Preservar a funcao isolada extraida de `NOTIFSOL.prw` |
| `fixtures/sol_mail_cfg.json` | Ambiente simulado | Fornecer parte dos parametros SMTP e exercitar defaults reais |

### Dependencias

| Arquivo | Relacao |
|---|---|
| `livrePL/interpreter.py` | Fornece `Interpreter`, `AdvPLRuntimeError`, `AllTrim` e arrays; nao sera alterado |
| `livrePL/parser.py` | Ja aceita a sintaxe usada por `U_SolMailCfg`; nao sera alterado |
| `tests/test_getmv.py` | Garante compatibilidade do comportamento estrito existente com um argumento |

### Testes

| Teste | Cobertura |
|---|---|
| `test_sol_mail_cfg_runs_real_advpl_case` | Executa a funcao real e compara o array SMTP completo |
| `test_getmv_uses_default_only_when_parameter_is_missing` | Distingue valor configurado de valor default |
| `test_getmv_without_default_keeps_clear_missing_parameter_error` | Preserva o contrato estrito da Fase 1 |

### Padroes de referencia

| Fonte | Padrao aproveitado |
|---|---|
| `NOTIFSOL.prw:18-31` | `GetMV` com tres argumentos, defaults de texto, numero e logico, e default derivado de variavel local |
| `ENVEMAIL.prw:40-58` | Retornos antecipados permitem testar validacoes antes de dependencias externas de SMTP |
| `NOTIFSOL.prw:143-179` | Caso futuro para `DbSetOrder`, `DbSeek`, `Eof`, `Deleted` e `DbSkip` |
| `TRNSOL01.prw:463-510` | Caso futuro para validar regras reais sobre Z04/Z05 |

## Priorizacao do corpus

1. `U_SolMailCfg`: apenas extensao compativel de `GetMV`; entrega atual.
2. `TextoHtml`: adicionar `StrTran` e `Chr`, sem banco ou interface.
3. Validacoes iniciais de `U_EnviarEmailSolicitacao`: adicionar `At` e `Left`; nao simular SMTP.
4. `TabelaItensEmail`: inaugurar runtime de aliases, indices e navegacao.
5. Fluxos de `TRNSOL01`: escrita em memoria, locks e efeitos capturados.
6. `TRNSOL02`: aliases dinamicos, datas, SQL e exportacao simulada.

## Avaliacao de risco

- [x] API publica preservada: `GetMV` com um argumento continua valido.
- [x] Sem alteracao no LivrePL.
- [x] Sem banco, migracao ou configuracao externa.
- [x] Fixture antigo permanece compativel.
- [ ] Suporte de alias ainda necessario para executar rotinas completas.
- [ ] Framework MVC, SMTP e SQL permanecem fora do runtime atual.
