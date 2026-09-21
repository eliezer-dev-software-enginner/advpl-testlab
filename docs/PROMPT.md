# PROMPT.md — Objetivo Mestre e Bootstrap de Sessao

> Use este documento para iniciar uma nova sessao sem perder o contexto do AdvPL TestLab.

---

## Prompt de inicializacao

```text
Retome o desenvolvimento do AdvPL TestLab.

Antes de agir:
1. Leia docs/AI_RULES.md.
2. Leia docs/CONTEXT.md.
3. Leia docs/TODO.md.
4. Leia docs/DECISIONS.md.
5. Consulte o documento da fase relacionada ao pedido.
6. Verifique git status e preserve alteracoes existentes.

Resuma em ate tres linhas o estado atual, a proxima tarefa do TODO e a validacao que sera executada. Depois implemente somente o escopo solicitado.

Ao concluir:
- rode python -m unittest discover -s tests -v;
- execute o exemplo afetado pela CLI;
- rode a regressao do LivrePL quando houver risco de impacto;
- atualize TODO.md, CONTEXT.md e DECISIONS.md conforme necessario;
- nao faca push sem autorizacao explicita.

MEU PEDIDO:
<descreva aqui a proxima tarefa>
```

## Objetivo original

Construir um harness de testes AdvPL sobre o LivrePL capaz de executar um arquivo `.prw` real com dados hidratados por fixture JSON, sem depender de Protheus real, AppServer, licenca, banco de dados ou interface.

Exemplo minimo:

```advpl
User Function ex()
    Local cUserId := GetMV("MV_ADMIN")
    ? cUserId
Return NIL
```

Fixture:

```json
{
  "parametros": {
    "MV_ADMIN": "000007"
  },
  "tabelas": {
    "SB1": []
  }
}
```

Saida esperada:

```text
000007
```

## Plano incremental

1. Fase 0: mapear funcoes necessarias e definir a arquitetura.
2. Fase 1: implementar `GetMV` lendo `parametros` do JSON.
3. Fase 2: abrir alias e ler o primeiro registro de uma tabela.
4. Fase 3: implementar busca, navegacao, `Eof()` e `Bof()`.
5. Fase 4: simular escrita e efeitos como `RecLock`, `MsgAlert` e `ConOut`.
6. Fase 5: definir casos declarativos com entrada e resultado esperado.

## Regras permanentes

- O projeto parte do LivrePL; nao recriar lexer, parser ou interpretador do zero.
- Preservar `PRIVATE`, `LOCAL` e `STATIC` como implementados no LivrePL.
- Builtins Protheus devem ser adicionados na camada do TestLab.
- Sintaxe nova so deve alterar lexer/parser quando houver caso real que nao possa ser atendido por builtin.
- Fixtures antigos devem continuar validos quando o formato evoluir.
- Cada fase deve ter teste automatizado, saida real e documentacao propria.

## Fora do escopo permanente

- Banco de dados real.
- MVC completo (`FWMBrowse`, `ModelDef`).
- REST (`WSRESTFUL`).
- SmartClient e multi-thread.
- Engenharia reversa de binarios TOTVS.

---

*Ultima atualizacao: 21/09/2026*
