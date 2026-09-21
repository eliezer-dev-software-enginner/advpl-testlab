# Fase 0 - Levantamento e desenho

## Objetivo

Definir a menor extensao possivel sobre o LivrePL para simular APIs do Protheus usando fixtures JSON, sem alterar as regras da linguagem.

## Mapeamento incremental

| Prioridade | Recurso | Motivo | Impacto esperado |
|---|---|---|---|
| 1 | `GetMV` | Primeiro caso real e nao exige sintaxe nova | Builtin com acesso ao fixture |
| 2 | `DBUseArea` e leitura do registro corrente | Habilita regras que consultam cadastros | Runtime de aliases e `FieldGet` |
| 3 | `DBSeek`, `DbSkip`, `Eof`, `Bof` | Habilita busca e varredura | Cursor em listas do fixture |
| 4 | `(alias)->campo` | Sintaxe comum em fontes reais | Alteracao pontual no lexer/parser |
| 5 | `RecLock`, atribuicao e `MsUnlock` | Habilita fluxo de escrita simulada | Mutacao somente em memoria |
| 6 | `MsgAlert` e `ConOut` | Evita quebra em efeitos de interface/log | Captura ou no-op configuravel |

## Arquitetura escolhida

O projeto e uma camada separada. `FixtureInterpreter` herda de `Interpreter` e sobrescreve apenas `_build_builtins()`. O construtor recebe um `Fixture`, guarda esse ambiente e chama o construtor original.

```text
fixture JSON -> Fixture -> FixtureInterpreter -> LivrePL Interpreter
                                  |
                                  `-> GETMV adicional
```

O metodo original `_build_builtins()` continua sendo a fonte de todas as funcoes nativas da linguagem. A camada chama `super()`, acrescenta `GETMV` e devolve o dicionario estendido.

## Assinatura

```python
class FixtureInterpreter(Interpreter):
    def __init__(self, program, fixture=None):
        self.fixture = fixture or Fixture()
        super().__init__(program)
```

Nao foi necessario mudar a assinatura do `Interpreter` original. Isso reduz risco de regressao e mantem o novo projeto isolado.

## Formato evolutivo das tabelas

O formato simples continua valido:

```json
"SB1": []
```

O carregador tambem aceita um objeto para uma evolucao futura sem quebrar fixtures existentes:

```json
"SB1": {
  "registros": [],
  "metadados": {}
}
```

A semantica desse objeto sera definida quando a Fase 2 implementar aliases. Nesta fase ele e apenas preservado e validado como estrutura JSON.

## Fora do escopo desta fase

- Alterar lexer ou parser.
- Implementar alias, cursor ou acesso a campos.
- Persistir alteracoes do fixture no disco.
- Simular SQL, MVC, REST ou SmartClient.
