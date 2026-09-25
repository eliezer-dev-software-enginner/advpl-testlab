# Fase — Depuracao inicial de PRW no VS Code

## Objetivo

Iniciar uma sessao de debug sobre o mesmo interpretador e fixture usados por `advpl-testlab -run`, com breakpoints de linha, navegacao passo a passo e inspecao de estado.

## Desenho

- `compile_sources` associa cada declaracao ao caminho do `.prw` que a produziu. As linhas dos nos do parser continuam no mesmo lugar apos `prepare_source`.
- `DebugFixtureInterpreter` instrumenta `exec_stmt` sem alterar o LivrePL. O `DebugController` coordena a thread de execucao e as pausas.
- `debug_adapter.py` fala DAP por `stdin`/`stdout` em um processo separado. O protocolo usa a saida binaria original; `print` do AdvPL vai para eventos `output`.
- `vscode-extension` registra o tipo de debug `advpl-testlab` e inicia `python -u -m debug_adapter` no Python configurado.
- `testlab.jsonc`, `//usePrw`, `entry`, `args`, `mvcCase` e `state.json` opcional seguem a descoberta/convencoes da CLI.

## Verificacao

- `tests/test_debug_adapter.py` testa breakpoint em um `.prw` carregado por `//usePrw`, mapeamento de arquivo/linha, pilha, locais, `next`, `stepIn`, `stepOut` e mensagens DAP reais por `stdio`.
- `node --check vscode-extension/extension.js` e a leitura JSON de `package.json` validam a extensao.
- `python -m unittest discover -s tests -q` e a suite de integracao de `desafios-aprendizado` passaram apos a primeira implementacao.
- `python -m debug_adapter` foi importado a partir do projeto EX1 depois de `python -m pip install -e .`.

## Fora do escopo deste primeiro corte

- Compilacao e depuracao no AppServer/DBAccess real.
- Pacote VSIX e instalacao permanente da extensao.
- Breakpoints condicionais, logpoints, avaliacao de expressoes, escrita de variaveis, pausa na excecao e debug reverso.
- Ponto de parada em toda linha sintaticamente valida: nos sem coordenada propria (como `Local` sem expressao) e controles UI adaptados ainda precisam de instrumentacao adicional.
