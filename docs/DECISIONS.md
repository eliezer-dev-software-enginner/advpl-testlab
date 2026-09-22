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
- **Estado:** Substituida pela ADR-008
- **Contexto:** A forma inicial usa uma lista de registros, mas fases futuras podem precisar de metadados de campos, indices e ordem.
- **Decisao:** Aceitar tanto lista simples quanto objeto JSON por alias, preservando o formato inicial.
- **Consequencias:** Fixtures atuais nao precisam ser migrados. A semantica do objeto com metadados sera definida na Fase 2.

## ADR-005 — Nome AdvPL TestLab

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** O nome provisorio `livrepl-fixture-harness` era tecnico e pouco memoravel.
- **Decisao:** Adotar **AdvPL TestLab**, com diretorio e repositorio `advpl-testlab`.
- **Consequencias:** Codigo e documentacao usam o novo nome; o vinculo tecnico com o LivrePL continua descrito no README e no CONTEXT.

## ADR-006 — Fontes funcionais do desafio1 como corpus de evolucao

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** Exemplos artificiais confirmam infraestrutura, mas nao revelam todas as assinaturas, sintaxes e combinacoes usadas em customizacoes Protheus reais.
- **Decisao:** Usar `DGB/desafios-pedro-torres/desafio1-solicitacao-compra` como corpus de referencia, isolando primeiro funcoes puras e depois avancando para aliases, navegacao e escrita.
- **Consequencias:** Cada builtin novo precisa estar ligado a um caso concreto. O corpus de origem nao e copiado integralmente nem alterado; trechos portaveis ficam em `examples/real-cases/` com origem documentada.

## ADR-007 — GetMV com default preserva modo estrito

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** `U_SolMailCfg()` usa a assinatura real `GetMV(cParam, lHelp, uDefault)`, enquanto a Fase 1 suportava somente um argumento e gerava erro para chaves ausentes.
- **Decisao:** Aceitar de um a tres argumentos. O terceiro argumento e retornado apenas quando o parametro nao existe; sem terceiro argumento, a ausencia continua gerando `AdvPLRuntimeError`. `lHelp` e aceito sem efeito de interface.
- **Consequencias:** Fixtures incompletos continuam falhando no modo estrito e fontes reais podem declarar defaults de texto, numero, logico ou valor calculado.

## ADR-008 — Colecoes JSON como listas de objetos nomeados

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** O formato inicial representava `parametros` e `tabelas` como objetos. Foi definido que ambas as colecoes devem ser listas e que cada tabela deve possuir um objeto proprio para registros e futuros metadados.
- **Decisao:** Novos fixtures usam `parametros: [{"NOME": valor}]` e `tabelas: [{"ALIAS": {"registros": []}}]`. Cada item declara exatamente um nome; duplicidades case-insensitive sao rejeitadas.
- **Consequencias:** A ordem declarada fica explicita e o objeto da tabela pode evoluir sem mudar a colecao. O carregador normaliza internamente para dicionarios e continua aceitando o formato antigo apenas para compatibilidade.

## Evidencias da entrega inicial

## ADR-009 — Executor hibrido para fontes reais

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** `TRNSOL02.prw` combina linguagem AdvPL, SQL via `FWExecStatement`, alias dinamico e interface `FWBrowse`, recursos ainda nao compreendidos integralmente pelo LivrePL.
- **Decisao:** A CLI descobre a primeira `User Function` e usa o LivrePL para fontes dentro da cobertura atual. Quando encontra o padrao de consulta com `FWExecStatement` e `FWBrowse`, usa um adaptador headless guiado pelo proprio fonte e por `consultas` do fixture.
- **Consequencias:** O fonte original executa sem alteracao e sem Protheus. O adaptador nao representa ainda semantica arbitraria de todas as APIs; sua cobertura sera substituida incrementalmente por objetos, aliases e builtins genericos.

## ADR-010 — Fixture localizado junto ao projeto alvo

- **Data:** 21/09/2026
- **Estado:** Aceita
- **Contexto:** O comando deve funcionar no diretorio do `.prw`, sem exigir caminhos relativos ao repositorio do TestLab.
- **Decisao:** Procurar `advpl-testlab.json` no diretorio do fonte e, em seguida, nos diretorios pais. `--fixture` continua disponivel para sobrescrita explicita.
- **Consequencias:** Cada projeto AdvPL pode versionar sua propria simulacao. O fixture de `desafios-pedro-torres` contem Z04, Z05, Z06 e a consulta de aceite de `Z04CON`.

## ADR-011 — Confirmacoes identificadas por fonte e conteudo

- **Data:** 22/09/2026
- **Estado:** Aceita
- **Contexto:** `MsgYesNo` pode aparecer varias vezes no mesmo fonte e em fontes diferentes. Um unico retorno global nao identifica qual decisao esta sendo simulada e pode esconder cenarios incompletos.
- **Decisao:** Configurar confirmacoes em `especificidadesPrw`, usando `fonte`, `nome`, `conteudo` e `retorno`. O conteudo corresponde aos argumentos ja avaliados e formatados como chamada AdvPL. `MsgYesNo` exige retorno logico e nao produz texto.
- **Consequencias:** Cada decisao fica explicita e deterministica. Regras ausentes falham cedo. O retorno global anterior em `funcoes` permanece como fallback de compatibilidade.

## ADR-012 — Interface Protheus representada como efeito textual

- **Data:** 22/09/2026
- **Estado:** Aceita
- **Contexto:** Testes headless precisam observar mensagens e atravessar fontes com declaracoes de dialogo sem depender de SmartClient.
- **Decisao:** Representar `Define MSDialog`, `MsgAlert` e `MsgInfo` por linhas no terminal. Controles `@` e `Activate Dialog` sao no-op. Nenhuma janela e criada e nenhuma acao de botao e executada.
- **Consequencias:** Mensagens tornam-se verificaveis em testes. Fluxos que dependem de preenchimento ou clique em controles ainda precisam de simulacao propria.

- Teste de aceite da CLI: saida `000007`.
- Cinco testes automatizados executados e aprovados.
- Nove testes automatizados executados e aprovados apos incorporar os primeiros casos reais.
- Treze testes automatizados executados e aprovados apos migrar o schema JSON.
- Dezesseis testes automatizados executados e aprovados com o executor de `TRNSOL02.prw`.
- Vinte e sete testes automatizados executados e aprovados com UI headless e `MsgYesNo` por fonte/chamada/ocorrencia.
- Regressao do LivrePL aprovada com `exemplos/ola.prw`, `exemplos/todas-etapas.prw` e `interpreter.py`.

---

*Ultima atualizacao: 22/09/2026*
