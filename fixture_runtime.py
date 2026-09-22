import json
import sys
from pathlib import Path


_MISSING = object()


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
    def __init__(self, parametros=None, tabelas=None, funcoes=None, consultas=None):
        self.parametros = self._normalize_parameters(
            [] if parametros is None else parametros
        )
        self.tabelas = self._validate_tables([] if tabelas is None else tabelas)
        self.funcoes = self._normalize_named_values(
            "funcoes", [] if funcoes is None else funcoes
        )
        self.consultas = self._normalize_named_values(
            "consultas", [] if consultas is None else consultas
        )

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise FixtureError("A raiz do fixture deve ser um objeto JSON")
        return cls(
            parametros=data.get("parametros", []),
            tabelas=data.get("tabelas", []),
            funcoes=data.get("funcoes", []),
            consultas=data.get("consultas", []),
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
        if isinstance(parameters, dict):
            entries = parameters.items()
        elif isinstance(parameters, list):
            entries = []
            for item in parameters:
                if not isinstance(item, dict) or len(item) != 1:
                    raise FixtureError(
                        "Cada item de 'parametros' deve conter exatamente um parametro"
                    )
                entries.extend(item.items())
        else:
            raise FixtureError("'parametros' deve ser uma lista JSON")

        normalized = {}
        for name, value in entries:
            key = str(name).upper()
            if key in normalized:
                raise FixtureError(f"Parametro duplicado: '{key}'")
            normalized[key] = value
        return normalized

    @staticmethod
    def _validate_tables(tables):
        canonical = isinstance(tables, list)
        if isinstance(tables, dict):
            entries = tables.items()
        elif canonical:
            entries = []
            for item in tables:
                if not isinstance(item, dict) or len(item) != 1:
                    raise FixtureError(
                        "Cada item de 'tabelas' deve conter exatamente um alias"
                    )
                entries.extend(item.items())
        else:
            raise FixtureError("'tabelas' deve ser uma lista JSON")

        normalized = {}
        for alias, table in entries:
            key = str(alias).upper()
            if key in normalized:
                raise FixtureError(f"Tabela duplicada: '{key}'")
            if canonical:
                if not isinstance(table, dict) or not isinstance(
                    table.get("registros"), list
                ):
                    raise FixtureError(
                        f"Tabela '{alias}' deve possuir 'registros' como lista"
                    )
            elif not isinstance(table, (list, dict)):
                raise FixtureError(
                    f"Tabela '{alias}' deve ser uma lista ou um objeto com metadados"
                )
            normalized[key] = table
        return normalized

    @staticmethod
    def _normalize_named_values(section, values):
        if isinstance(values, dict):
            entries = values.items()
        elif isinstance(values, list):
            entries = []
            for item in values:
                if not isinstance(item, dict) or len(item) != 1:
                    raise FixtureError(
                        f"Cada item de '{section}' deve conter exatamente um nome"
                    )
                entries.extend(item.items())
        else:
            raise FixtureError(f"'{section}' deve ser uma lista JSON")

        normalized = {}
        for name, value in entries:
            key = str(name).upper()
            if key in normalized:
                raise FixtureError(f"Nome duplicado em '{section}': '{key}'")
            normalized[key] = value
        return normalized

    def get_parameter(self, name, default=_MISSING):
        key = str(name).upper()
        if key not in self.parametros:
            if default is not _MISSING:
                return default
            raise AdvPLRuntimeError(
                f"GetMV: parametro '{name}' nao encontrado no fixture"
            )
        return self.parametros[key]

    def get_function_result(self, name, default=_MISSING):
        key = str(name).upper()
        if key in self.funcoes:
            return self.funcoes[key]
        if default is not _MISSING:
            return default
        raise FixtureError(f"Funcao '{name}' nao configurada no fixture")

    def get_query_records(self, name):
        query = self.consultas.get(str(name).upper())
        if query is None:
            raise FixtureError(f"Consulta '{name}' nao configurada no fixture")
        if not isinstance(query, dict) or not isinstance(query.get("registros"), list):
            raise FixtureError(
                f"Consulta '{name}' deve possuir 'registros' como lista"
            )
        return query["registros"]


class FixtureInterpreter(Interpreter):
    def __init__(self, program, fixture=None):
        self.fixture = fixture or Fixture()
        super().__init__(program)

    def _build_builtins(self):
        builtins = super()._build_builtins()

        def b_getmv(args):
            if not 1 <= len(args) <= 3:
                raise AdvPLRuntimeError("GetMV espera de 1 a 3 argumentos")
            if not isinstance(args[0], str):
                raise AdvPLRuntimeError("GetMV espera o nome do parametro como texto")
            default = args[2] if len(args) == 3 else _MISSING
            return self.fixture.get_parameter(args[0], default=default)

        def b_strtran(args):
            if len(args) != 3 or not all(isinstance(value, str) for value in args):
                raise AdvPLRuntimeError("StrTran espera 3 argumentos de texto")
            return args[0].replace(args[1], args[2])

        def b_chr(args):
            if len(args) != 1 or not isinstance(args[0], (int, float)):
                raise AdvPLRuntimeError("Chr espera 1 argumento numerico")
            try:
                return chr(int(args[0]))
            except ValueError as exc:
                raise AdvPLRuntimeError("Chr recebeu um codigo invalido") from exc

        builtins["GETMV"] = b_getmv
        builtins["STRTRAN"] = b_strtran
        builtins["CHR"] = b_chr
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
