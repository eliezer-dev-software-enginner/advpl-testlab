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
| `docs/fase-1b-casos-reais.md` | Casos reais `U_SolMailCfg` e `TextoHtml` |
| `docs/corpus-desafio1-context-map.md` | Mapa dos fontes funcionais usados como corpus |

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
executor (descoberta de entrada e fixture)
    |
    |-- linguagem coberta -> parser + FixtureInterpreter do LivrePL
    `-- integracoes Protheus -> adaptador headless
             |
             v
          Fixture JSON
```

`FixtureInterpreter` herda de `Interpreter` e estende `_build_builtins()`. A decisao evita mudancas no lexer, parser e runtime central quando o recurso pode ser expresso como funcao de framework.

## Arquivos do projeto

| Caminho | Responsabilidade |
|---|---|
| `fixture_runtime.py` | Carrega/valida fixtures, integra o LivrePL e registra builtins simulados |
| `executor.py` | Descobre entrada/fixture e executa via LivrePL ou adaptador headless |
| `main.py` | CLI `advpl-testlab -run` |
| `pyproject.toml` | Empacotamento e comando instalavel |
| `examples/getmv.prw` | Exemplo de codigo AdvPL real usando `GetMV` |
| `examples/real-cases/sol_mail_cfg.prw` | Funcoes isoladas de `NOTIFSOL.prw` |
| `fixtures/getmv.json` | Fixture de exemplo com parametros e tabelas |
| `fixtures/sol_mail_cfg.json` | Parametros SMTP para o primeiro caso real |
| `tests/test_getmv.py` | Testes unitarios e ponta a ponta da Fase 1 |
| `tests/test_real_cases.py` | Testes extraidos do desafio1-solicitacao-compra |
| `docs/` | Memoria permanente e documentos de fase |

## Formato atual do fixture

```json
{
  "parametros": [
    {
      "MV_ADMIN": "000007"
    }
  ],
  "tabelas": [
    {
      "SB1": {
        "registros": []
      }
    }
  ]
}
```

- `parametros`: lista em que cada objeto declara exatamente um parametro consultado por `GetMV`.
- `tabelas`: lista em que cada objeto declara exatamente um alias; o valor do alias possui `registros` e pode receber metadados.
- `funcoes`: respostas configuradas para chamadas externas em modo headless.
- `consultas`: conjuntos de registros devolvidos por consultas simuladas, indexados pela funcao de entrada.
- Chaves de parametros e aliases sao normalizadas para maiusculas.
- O formato legado baseado em objetos continua aceito apenas para compatibilidade de leitura.

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

### Fase 1b — Casos reais do desafio1

- `GetMV(cParam, lHelp, uDefault)` com fallback tipado.
- `StrTran` e `Chr` registrados na camada do TestLab.
- `U_SolMailCfg()` executado com configuracoes presentes e defaults ausentes.
- `TextoHtml()` executado com escape HTML e quebra de linha.
- Corpus real mapeado para orientar as fases seguintes.
- Suite ampliada para treze testes automatizados apos a migracao do schema JSON.

### Executor de `.prw` e TRNSOL02

- CLI instalavel com `advpl-testlab -run arquivo.prw`.
- Descoberta automatica da primeira `User Function` e de `advpl-testlab.json` nos diretorios pais.
- Caminho nativo pelo LivrePL para a linguagem ja suportada.
- Adaptador headless inicial para `FWExecStatement` e `FWBrowse`.
- Fixture real no projeto `DGB/desafios-pedro-torres`, com metadados e registros de Z04, Z05 e Z06.
- Dezesseis testes automatizados aprovados.

## Como executar

```powershell
python main.py -run examples/getmv.prw --fixture fixtures/getmv.json --entry ex
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

- Fases 0, 1 e 1b concluidas.
- O `TRNSOL02.prw` ja executa em modo headless; a proxima entrega e substituir gradualmente o adaptador por runtime generico de aliases e objetos Protheus.
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
