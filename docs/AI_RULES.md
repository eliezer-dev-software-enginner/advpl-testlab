# AI_RULES.md — Regras Obrigatorias do Agente

> Referencia de conduta do AdvPL TestLab. Leia este arquivo no inicio de toda nova sessao, antes de alterar o projeto.
> Ordem de precedencia: `AI_RULES.md` > `CONTEXT.md` > `TODO.md` > `DECISIONS.md` > `PROMPT.md`.

---

## 1. Bootstrap da sessao

Antes de iniciar qualquer trabalho:

1. Ler `docs/AI_RULES.md`.
2. Ler `docs/CONTEXT.md`.
3. Ler `docs/TODO.md`.
4. Ler `docs/DECISIONS.md`.
5. Ler `docs/PROMPT.md` quando for necessario recuperar o objetivo completo.
6. Verificar `git status` e preservar alteracoes do usuario.

Depois da leitura, informar em poucas linhas o estado atual e a proxima acao.

## 2. Limites do projeto

- O AdvPL TestLab e um projeto separado que depende do LivrePL local.
- Nao alterar o repositorio `livrePL` durante tarefas deste projeto sem autorizacao explicita.
- Nao tentar reimplementar todo o Protheus.
- Banco real, AppServer, licenca, SmartClient, MVC completo, REST e engenharia reversa de binarios TOTVS permanecem fora do escopo.
- Implementar recursos de framework apenas quando houver caso de teste concreto.
- Alterar lexer/parser somente quando uma sintaxe real exigir; builtins e runtime simulado devem permanecer na camada do TestLab sempre que possivel.

## 3. Regras de compatibilidade

- Preservar escopo dinamico de `PRIVATE`, isolamento de `LOCAL` e persistencia de `STATIC` herdados do LivrePL.
- Nomes AdvPL, parametros e aliases sao case-insensitive.
- Fixtures simples existentes nao podem deixar de funcionar quando o formato evoluir.
- Ausencia de dado obrigatorio deve produzir erro claro, evitando falso positivo em testes.
- A simulacao nao persiste alteracoes no fixture original, salvo decisao futura registrada em ADR.
- Ao criar ou editar um fixture versionado de um projeto AdvPL, nao omitir nenhuma secao de primeiro nivel: `parametros`, `tabelas`, `funcoes`, `ambiente`, `dialogos`, `especificidadesPrw` e `consultas`. Usar `[]` para secoes vazias. A leitura de fixtures minimos legados permanece aceita para compatibilidade.

## 4. Padroes de codigo

- Python sem dependencias externas enquanto a biblioteca padrao for suficiente.
- Manter responsabilidades separadas: carregamento/validacao em `Fixture`, comportamento AdvPL em `FixtureInterpreter` e CLI em `main.py`.
- Builtins novos devem seguir o registro case-insensitive do LivrePL.
- Nao adicionar comentarios redundantes nem abstracoes sem uso imediato.
- Mensagens de erro devem identificar a funcao, o dado procurado e a causa.
- Arquivos `.prw` de exemplo devem permanecer compativeis com a sintaxe real do AdvPL.

## 5. Testes e validacao

Para toda mudanca de comportamento:

1. Adicionar ou atualizar teste automatizado em `tests/`.
2. Rodar `python -m unittest discover -s tests -v`.
3. Rodar o exemplo afetado pela CLI.
4. Quando houver impacto potencial no interpretador, executar a regressao basica do LivrePL:
   - `python main.py exemplos/ola.prw`
   - `python main.py exemplos/todas-etapas.prw`
   - `python interpreter.py`
5. Registrar evidencias relevantes em `docs/DECISIONS.md` e atualizar `docs/TODO.md`.

## 6. Documentacao

- Cada fase deve ter documento proprio com objetivo, desenho, codigo relevante, saida real verificada e fora de escopo.
- `CONTEXT.md` guarda o estado consolidado e a arquitetura atual.
- `TODO.md` e a fonte de verdade das proximas entregas.
- `DECISIONS.md` registra decisoes de arquitetura em formato ADR; decisoes aceitas nao devem ser refeitas sem justificativa.
- `PROMPT.md` preserva o objetivo original e o roteiro de retomada.

## 7. Git

- Nunca executar `git push` sem autorizacao explicita do usuario.
- Fazer commit somente quando solicitado.
- Antes do commit, revisar `git status`, `git diff` e, quando existir historico, `git log --oneline -10`.
- Adicionar apenas arquivos pertencentes ao escopo.
- Nao commitar segredos, credenciais, ambientes virtuais ou caches.
- Usar Conventional Commits com descricao em ingles ou portugues de forma consistente no repositorio. Exemplos:
  - `feat: inicia AdvPL TestLab com fixtures JSON`
  - `test: cobre consulta de parametros com GetMV`
  - `docs: atualiza contexto da fase de aliases`

---

*Ultima atualizacao: 21/09/2026*
