# DECISIONS.md — Registro de Decisoes de Arquitetura

> Formato ADR: estado, contexto, decisao e consequencias. Novas decisoes estruturais devem ser registradas antes da implementacao.

---

## ADR-001 — Projeto separado do LivrePL

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** O harness precisa evoluir com simulacoes do framework Protheus sem aumentar o escopo do interpretador de linguagem pura.
- **Decisao:** Manter o AdvPL TestLab em repositorio e diretorio proprios, usando o LivrePL como dependencia local em diretorio irmao.
- **Consequencias:** O LivrePL original permanece intacto. A estrutura atual exige que `livrePL/` e `advpl-testlab/` tenham o mesmo diretorio pai.

## ADR-002 — Extensao por heranca e registro de builtins

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** Funcoes como `GetMV` pertencem ao framework Protheus, nao a sintaxe central do AdvPL.
- **Decisao:** Criar `FixtureInterpreter(Interpreter)` e estender `_build_builtins()` chamando primeiro `super()`.
- **Consequencias:** Lexer, parser, escopos e builtins originais sao reutilizados sem duplicacao. Sintaxe nova so sera introduzida quando um caso real exigir.

## ADR-003 — Parametro ausente em GetMV gera erro

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** Retornar `NIL` para parametro ausente pode esconder fixture incompleto e produzir falso positivo na regra de negocio.
- **Decisao:** `GetMV` gera `AdvPLRuntimeError` contendo o nome do parametro quando a chave nao existe.
- **Consequencias:** Testes falham cedo e com mensagem clara. Um valor default podera ser proposto futuramente como extensao explicita da assinatura.

## ADR-004 — Formato evolutivo de tabelas no fixture

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** A forma inicial usa uma lista de registros, mas fases futuras podem precisar de metadados de campos, indices e ordem.
- **Decisao:** Aceitar tanto lista simples quanto objeto JSON por alias, preservando o formato inicial.
- **Consequencias:** Fixtures atuais nao precisam ser migrados. A semantica do objeto com metadados sera definida na Fase 2.

## ADR-005 — Nome AdvPL TestLab

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** O nome provisorio `livrepl-fixture-harness` era tecnico e pouco memoravel.
- **Decisao:** Adotar **AdvPL TestLab**, com diretorio e repositorio `advpl-testlab`.
- **Consequencias:** Codigo e documentacao usam o novo nome; o vinculo tecnico com o LivrePL continua descrito no README e no CONTEXT.

## Evidencias da entrega inicial

- Teste de aceite da CLI: saida `000007`.
- Cinco testes automatizados executados e aprovados.
- Regressao do LivrePL aprovada com `exemplos/ola.prw`, `exemplos/todas-etapas.prw` e `interpreter.py`.

---

*Ultima atualizacao: 21/09/2026*
