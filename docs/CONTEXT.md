# CONTEXT.md — Contexto do AdvPL TestLab

> Memoria central do projeto. Em uma nova sessao, ler junto com `AI_RULES.md`, `TODO.md`, `DECISIONS.md` e `PROMPT.md`.

---

## Indice de documentacao

| Arquivo | Funcao |
|---|---|
| `docs/AI_RULES.md` | Regras obrigatorias de trabalho |
| `docs/CONTEXT.md` | Arquitetura, arquivos, execucao e estado atual |
| `docs/TODO.md` | Roadmap e pendencias por fase |
| `docs/DECISIONS.md` | Decisoes de arquitetura em formato ADR |
| `docs/PROMPT.md` | Objetivo mestre e roteiro de bootstrap |
| `docs/fase-0-levantamento.md` | Levantamento e desenho inicial |
| `docs/fase-1-getmv.md` | Implementacao e evidencia do `GetMV` |

## O que e o projeto

O AdvPL TestLab executa codigo AdvPL com um ambiente Protheus simulado por fixtures JSON. Ele permite testar logica de negocio isolada sem AppServer, licenca, banco de dados ou interface do Protheus.

O projeto nao e um fork do LivrePL. Ele vive em repositorio proprio e usa o LivrePL como dependencia local, mantendo os dois diretorios como irmaos:

```text
protheus/
|-- livrePL/
`-- advpl-testlab/
```

## Arquitetura

```text
arquivo .prw
    |
    v
preprocessador + parser do LivrePL
    |
    v
FixtureInterpreter
    |-- builtins da linguagem herdados do LivrePL
    `-- builtins Protheus simulados pelo TestLab
             |
             v
          Fixture JSON
```

`FixtureInterpreter` herda de `Interpreter` e estende `_build_builtins()`. A decisao evita mudancas no lexer, parser e runtime central quando o recurso pode ser expresso como funcao de framework.

## Arquivos do projeto

| Caminho | Responsabilidade |
|---|---|
| `fixture_runtime.py` | Carrega/valida fixtures, integra o LivrePL e registra builtins simulados |
| `main.py` | CLI para executar `.prw` com fixture e funcao de entrada |
| `examples/getmv.prw` | Exemplo de codigo AdvPL real usando `GetMV` |
| `fixtures/getmv.json` | Fixture de exemplo com parametros e tabelas |
| `tests/test_getmv.py` | Testes unitarios e ponta a ponta da Fase 1 |
| `docs/` | Memoria permanente e documentos de fase |

## Formato atual do fixture

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

- `parametros`: objeto chave/valor consultado por `GetMV`.
- `tabelas`: alias para lista de registros; tambem aceita objeto reservado para futura inclusao de `registros` e `metadados`.
- Chaves de parametros e aliases sao normalizadas para maiusculas.

## Funcionalidade entregue

### Fase 0 — Levantamento

- Mapeamento incremental de `GetMV`, aliases, navegacao, escrita e efeitos de interface.
- Arquitetura por camada externa e heranca definida.

### Fase 1 — GetMV

- Leitura de fixture JSON.
- `GetMV(cParam)` registrado como builtin.
- Erro explicito para parametro ausente ou argumento invalido.
- CLI e exemplo ponta a ponta.
- Cinco testes automatizados aprovados.

## Como executar

```powershell
python main.py examples/getmv.prw fixtures/getmv.json ex
```

Saida esperada e verificada:

```text
000007
```

Testes:

```powershell
python -m unittest discover -s tests -v
```

## Estado atual

- Fases 0 e 1 concluidas.
- Proxima entrega recomendada: Fase 2, com runtime basico de aliases e leitura do primeiro registro.
- Nao ha dependencias Python externas.
- O repositorio Git foi inicializado na branch `main`.

## Fora do escopo

- Banco de dados real ou DBAccess.
- AppServer, licenciamento e SmartClient.
- MVC completo, REST e telas do framework.
- Persistencia de escrita no fixture nesta fase.
- Engenharia reversa de componentes TOTVS.

---

*Ultima atualizacao: 21/09/2026*
