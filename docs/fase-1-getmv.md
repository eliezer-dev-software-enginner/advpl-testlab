# Fase 1 - GetMV lendo fixture JSON

> Registro historico da primeira implementacao. A assinatura foi ampliada de forma compativel na Fase 1b; consulte `fase-1b-casos-reais.md` para o comportamento atual com `lHelp` e `uDefault`.

## Decisoes

- Chaves de `parametros` sao normalizadas para maiusculas, seguindo o comportamento case-insensitive do AdvPL.
- `GetMV` aceita exatamente um argumento textual.
- Parametro ausente gera `AdvPLRuntimeError` com o nome procurado. Essa escolha torna fixture incompleto uma falha visivel.
- A CLI recebe o `.prw`, o fixture e, opcionalmente, a funcao de entrada.

## Codigo-fonte completo da extensao

`fixture_runtime.py`:

```python
import json
import sys
from pathlib import Path


class FixtureError(ValueError):
    pass


def _load_livrepl():
    default_path = Path(__file__).resolve().parent.parent / "livrePL"
    source_path = default_path.resolve()
    if not source_path.is_dir():
        raise FixtureError(
            f"LivrePL nao encontrado em '{source_path}'. "
            "Mantenha livrePL e advpl-testlab como diretorios irmaos."
        )
    source_text = str(source_path)
    if source_text not in sys.path:
        sys.path.insert(0, source_text)


_load_livrepl()

from interpreter import AdvPLRuntimeError, Interpreter
from parser import parse_source
from preprocessor import preprocess


class Fixture:
    def __init__(self, parametros=None, tabelas=None):
        self.parametros = self._normalize_parameters(
            {} if parametros is None else parametros
        )
        self.tabelas = self._validate_tables({} if tabelas is None else tabelas)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise FixtureError("A raiz do fixture deve ser um objeto JSON")
        return cls(
            parametros=data.get("parametros", {}),
            tabelas=data.get("tabelas", {}),
        )

    @classmethod
    def from_file(cls, path):
        fixture_path = Path(path)
        try:
            with fixture_path.open(encoding="utf-8") as fixture_file:
                data = json.load(fixture_file)
        except FileNotFoundError as exc:
            raise FixtureError(f"Fixture nao encontrado: '{fixture_path}'") from exc
        except json.JSONDecodeError as exc:
            raise FixtureError(
                f"JSON invalido em '{fixture_path}', linha {exc.lineno}: {exc.msg}"
            ) from exc
        return cls.from_dict(data)

    @staticmethod
    def _normalize_parameters(parameters):
        if not isinstance(parameters, dict):
            raise FixtureError("'parametros' deve ser um objeto JSON")
        return {str(name).upper(): value for name, value in parameters.items()}

    @staticmethod
    def _validate_tables(tables):
        if not isinstance(tables, dict):
            raise FixtureError("'tabelas' deve ser um objeto JSON")
        normalized = {}
        for alias, table in tables.items():
            if not isinstance(table, (list, dict)):
                raise FixtureError(
                    f"Tabela '{alias}' deve ser uma lista ou um objeto com metadados"
                )
            normalized[str(alias).upper()] = table
        return normalized

    def get_parameter(self, name):
        key = str(name).upper()
        if key not in self.parametros:
            raise AdvPLRuntimeError(
                f"GetMV: parametro '{name}' nao encontrado no fixture"
            )
        return self.parametros[key]


class FixtureInterpreter(Interpreter):
    def __init__(self, program, fixture=None):
        self.fixture = fixture or Fixture()
        super().__init__(program)

    def _build_builtins(self):
        builtins = super()._build_builtins()

        def b_getmv(args):
            if len(args) != 1:
                raise AdvPLRuntimeError("GetMV espera exatamente 1 argumento")
            if not isinstance(args[0], str):
                raise AdvPLRuntimeError("GetMV espera o nome do parametro como texto")
            return self.fixture.get_parameter(args[0])

        builtins["GETMV"] = b_getmv
        return builtins


def run_source(source, fixture=None, entry="MAIN", args=None):
    program = parse_source(preprocess(source))
    interpreter = FixtureInterpreter(program, fixture=fixture)
    return interpreter.run(entry, args)


def run_file(source_path, fixture_path, entry="MAIN", args=None):
    source_file = Path(source_path)
    with source_file.open(encoding="utf-8", errors="replace") as advpl_file:
        source = advpl_file.read()
    fixture = Fixture.from_file(fixture_path)
    return run_source(source, fixture=fixture, entry=entry, args=args)
```

`main.py`:

```python
import sys

from fixture_runtime import FixtureError, run_file
from interpreter import AdvPLRuntimeError
from lexer import LexError
from parser import ParseError


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]
    if len(args) < 2:
        print("Uso: python main.py arquivo.prw fixture.json [FuncaoDeEntrada]")
        print("Ex.: python main.py examples/getmv.prw fixtures/getmv.json ex")
        return 2

    source_path = args[0]
    fixture_path = args[1]
    entry = args[2] if len(args) > 2 else "MAIN"

    try:
        run_file(source_path, fixture_path, entry=entry)
    except (FixtureError, ParseError, LexError, AdvPLRuntimeError, OSError) as exc:
        print(f"[ERRO] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## Teste de aceite

Fonte AdvPL:

```advpl
User Function ex()
    Local cUserId := GetMV("MV_ADMIN")
    ? cUserId
Return NIL
```

Fixture:

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

Comando:

```powershell
python main.py examples/getmv.prw fixtures/getmv.json ex
```

Saida real verificada:

```text
000007
```

## Testes automatizados

O modulo `tests/test_getmv.py` cobre:

- execucao ponta a ponta e comparacao exata da saida;
- nome de parametro case-insensitive;
- erro claro para parametro ausente;
- rejeicao de `parametros` com formato invalido;
- compatibilidade do formato simples de tabelas com um futuro objeto de metadados.

Comando e saida real verificada:

```text
> python -m unittest discover -s tests -v
test_example_runs_end_to_end ... ok
test_fixture_rejects_invalid_parameters_shape ... ok
test_missing_parameter_has_clear_error ... ok
test_parameter_name_is_case_insensitive ... ok
test_table_can_be_list_or_future_metadata_object ... ok

Ran 5 tests

OK
```

A regressao do LivrePL original tambem foi executada com sucesso:

```powershell
python main.py exemplos/ola.prw
python main.py exemplos/todas-etapas.prw
python interpreter.py
```

## Fora do escopo desta fase

- Valor default ou argumentos adicionais de `GetMV`.
- Conversao automatica da string `".T."` para tipo logico.
- Qualquer operacao sobre `tabelas`.
