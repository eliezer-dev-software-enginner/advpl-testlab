# TODO.md — Roadmap e Status do AdvPL TestLab

> Status: `[ ]` pendente · `[~]` em andamento · `[x]` concluido.
> Atualizar este arquivo ao final de cada tarefa.

---

## Foco atual

### Fase 2 — Leitura basica de tabela

- [ ] Definir o objeto de runtime de alias e registro corrente.
- [ ] Normalizar aliases e campos como case-insensitive.
- [ ] Implementar abertura de alias simulado por `DBUseArea` ou adaptacao minima equivalente.
- [ ] Implementar leitura do primeiro registro por `FieldGet` antes de introduzir sintaxe nova.
- [ ] Definir o comportamento de tabela vazia e alias inexistente.
- [ ] Criar fixture, `.prw` de aceite e testes automatizados.
- [ ] Documentar desenho, codigo, saida real e fora de escopo em `docs/fase-2-*.md`.

Status: `[ ]`

## Concluido

### Fase 0 — Levantamento

- [x] Mapear APIs prioritarias do framework Protheus.
- [x] Escolher camada separada sobre o LivrePL.
- [x] Evitar alteracoes prematuras no lexer/parser.
- [x] Documentar arquitetura inicial.

Status: `[x]` — concluido em 21/09/2026.

### Fase 1 — GetMV lendo JSON

- [x] Criar carregador e validador de fixture.
- [x] Injetar `Fixture` no construtor de `FixtureInterpreter`.
- [x] Registrar `GetMV` como builtin adicional.
- [x] Normalizar nomes de parametros de forma case-insensitive.
- [x] Gerar erro claro para parametro ausente.
- [x] Criar CLI, exemplo e fixture de aceite.
- [x] Executar cinco testes automatizados com sucesso.
- [x] Verificar saida ponta a ponta `000007`.
- [x] Executar regressao basica do LivrePL.

Status: `[x]` — concluido em 21/09/2026.

## Roadmap posterior

### Fase 3 — Navegacao e busca

- [ ] Implementar `DBSeek` sobre registros do fixture.
- [ ] Implementar `DbSkip`/`MoveNext`.
- [ ] Implementar `Eof()` e `Bof()`.
- [ ] Validar `DO WHILE` percorrendo tabela completa.

### Fase 4 — Escrita simulada

- [ ] Implementar `RecLock` e desbloqueio em memoria.
- [ ] Implementar atribuicao de campo no registro corrente.
- [ ] Definir `MsgAlert` e `ConOut` como captura de efeitos ou no-op configuravel.
- [ ] Garantir que o fixture de entrada no disco nao seja alterado involuntariamente.

### Fase 5 — Casos de teste declarativos

- [ ] Definir fixture de entrada e resultado esperado no mesmo caso de teste.
- [ ] Comparar retorno de funcao.
- [ ] Comparar saida capturada.
- [ ] Comparar estado final das tabelas simuladas.
- [ ] Produzir relatorio claro de divergencias.

## Pendencias tecnicas continuas

- [ ] Avaliar empacotamento ou configuracao explicita do caminho do LivrePL sem quebrar o uso atual por diretorios irmaos.
- [ ] Adicionar CI quando houver repositorio remoto configurado.
- [ ] Manter README, CONTEXT e DECISIONS sincronizados com cada fase.

---

*Ultima atualizacao: 21/09/2026*
