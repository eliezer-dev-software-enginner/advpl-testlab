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

    def get_parameter(self, name, default=_MISSING):
        key = str(name).upper()
        if key not in self.parametros:
            if default is not _MISSING:
                return default
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
