# Fase — `ConOut` headless

## Objetivo

Permitir que fontes AdvPL emitam logs simples durante a validacao e execucao pelo TestLab, sem AppServer ou SmartClient.

## Desenho

`ConOut(valor)` e um builtin da camada `FixtureInterpreter`. Ele exige exatamente um argumento, converte o valor para texto, escreve uma linha no terminal e retorna `NIL`.

## Saida verificada

```advpl
ConOut('Apagou')
```

```text
Apagou
```

## Fora do escopo

- console remoto do AppServer;
- arquivo de log;
- categorias, niveis ou configuracoes de rastreamento do Protheus.

## Verificacao

```powershell
python -m unittest discover -s tests -v
advpl-testlab -validate EX2.prw
advpl-testlab -run EX2.prw
```
