import json
import re
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
    def __init__(
        self,
        parametros=None,
        tabelas=None,
        funcoes=None,
        consultas=None,
        especificidades_prw=None,
    ):
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
        self.especificidades_prw = self._validate_prw_specificities(
            [] if especificidades_prw is None else especificidades_prw
        )

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise FixtureError("A raiz do fixture deve ser um objeto JSON")
        if "especificidadesPrw" in data and "especificicidadesPrw" in data:
            raise FixtureError(
                "Use apenas 'especificidadesPrw'; a grafia alternativa nao pode coexistir"
            )
        especificidades = data.get(
            "especificidadesPrw", data.get("especificicidadesPrw", [])
        )
        return cls(
            parametros=data.get("parametros", []),
            tabelas=data.get("tabelas", []),
            funcoes=data.get("funcoes", []),
            consultas=data.get("consultas", []),
            especificidades_prw=especificidades,
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

    @staticmethod
    def _validate_prw_specificities(specificities):
        if not isinstance(specificities, list):
            raise FixtureError("'especificidadesPrw' deve ser uma lista JSON")

        normalized = {}
        seen = set()
        for specificity in specificities:
            if not isinstance(specificity, dict):
                raise FixtureError(
                    "Cada item de 'especificidadesPrw' deve ser um objeto"
                )
            source = specificity.get("fonte")
            functions = specificity.get("funcoes")
            if not isinstance(source, str) or not source.strip():
                raise FixtureError(
                    "Cada especificidade PRW deve possuir 'fonte' como texto"
                )
            if not isinstance(functions, list):
                raise FixtureError(
                    f"Especificidade de '{source}' deve possuir 'funcoes' como lista"
                )

            source_key = Path(source.replace("\\", "/")).name.upper()
            target = normalized.setdefault(source_key, [])
            for function in functions:
                if not isinstance(function, dict):
                    raise FixtureError(
                        f"Cada funcao especifica de '{source}' deve ser um objeto"
                    )
                name = function.get("nome")
                content = function.get("conteudo")
                if not isinstance(name, str) or not name.strip():
                    raise FixtureError(
                        f"Funcao especifica de '{source}' deve possuir 'nome'"
                    )
                if not isinstance(content, str):
                    raise FixtureError(
                        f"Funcao '{name}' de '{source}' deve possuir 'conteudo' como texto"
                    )
                name_key = name.upper()
                result = function.get("retorno", _MISSING)
                occurrence = function.get("ocorrencia")
                if result is _MISSING:
                    raise FixtureError(
                        f"Funcao '{name}' de '{source}' deve possuir 'retorno'"
                    )
                if name_key == "MSGYESNO" and not isinstance(result, bool):
                    raise FixtureError(
                        f"MSGYESNO de '{source}' deve possuir retorno logico true ou false"
                    )
                if occurrence is not None and (
                    isinstance(occurrence, bool)
                    or not isinstance(occurrence, int)
                    or occurrence < 1
                ):
                    raise FixtureError(
                        f"Funcao '{name}' de '{source}' deve possuir 'ocorrencia' "
                        "como inteiro positivo"
                    )
                rule_key = (source_key, name_key, content.strip(), occurrence)
                if rule_key in seen:
                    raise FixtureError(
                        f"Regra duplicada para {name_key} em '{source}': {content}"
                    )
                seen.add(rule_key)
                target.append(
                    {
                        "nome": name_key,
                        "conteudo": content.strip(),
                        "retorno": result,
                        "ocorrencia": occurrence,
                    }
                )
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

    def get_prw_function_result(self, source_name, name, args, occurrence=None):
        source_key = Path(str(source_name).replace("\\", "/")).name.upper()
        name_key = str(name).upper()
        content = _format_advpl_arguments(args)
        rules = self.especificidades_prw.get(source_key, [])
        for rule in rules:
            if (
                rule["nome"] == name_key
                and rule["conteudo"] == content
                and rule["ocorrencia"] == occurrence
            ):
                return rule["retorno"]
        for rule in rules:
            if (
                rule["nome"] == name_key
                and rule["conteudo"] == content
                and rule["ocorrencia"] is None
            ):
                return rule["retorno"]

        legacy = self.funcoes.get(name_key, _MISSING)
        if legacy is not _MISSING:
            if name_key == "MSGYESNO" and not isinstance(legacy, bool):
                raise AdvPLRuntimeError(
                    "MsgYesNo: retorno global em 'funcoes' deve ser logico"
                )
            return legacy

        raise AdvPLRuntimeError(
            f"{name}: retorno nao configurado para fonte '{source_key}' "
            f"e conteudo {content} na ocorrencia {occurrence or 1}"
        )

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
    def __init__(self, program, fixture=None, source_name="<memoria>"):
        self.fixture = fixture or Fixture()
        self.source_name = source_name
        self._prw_function_calls = {}
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

        def message_args(name, args):
            if not 1 <= len(args) <= 2 or not all(
                isinstance(value, str) for value in args
            ):
                raise AdvPLRuntimeError(
                    f"{name} espera mensagem e titulo opcional como texto"
                )
            return args[0], args[1] if len(args) == 2 else ""

        def b_msgalert(args):
            message, title = message_args("MsgAlert", args)
            prefix = f"{title}: " if title else ""
            print(f"[ALERTA] {prefix}{message}")
            return None

        def b_msginfo(args):
            message, title = message_args("MsgInfo", args)
            prefix = f"{title}: " if title else ""
            print(f"[INFO] {prefix}{message}")
            return None

        def b_msgyesno(args):
            message_args("MsgYesNo", args)
            call_key = ("MSGYESNO", _format_advpl_arguments(args))
            occurrence = self._prw_function_calls.get(call_key, 0) + 1
            self._prw_function_calls[call_key] = occurrence
            return self.fixture.get_prw_function_result(
                self.source_name,
                "MsgYesNo",
                args,
                occurrence=occurrence,
            )

        def b_testlab_msdialog(args):
            if len(args) != 1 or not isinstance(args[0], str):
                raise AdvPLRuntimeError("Define MSDialog espera titulo como texto")
            print(f"[MSDIALOG] {args[0]}")
            return None

        def b_testlab_noop(args):
            return None

        builtins["GETMV"] = b_getmv
        builtins["STRTRAN"] = b_strtran
        builtins["CHR"] = b_chr
        builtins["MSGALERT"] = b_msgalert
        builtins["MSGINFO"] = b_msginfo
        builtins["MSGYESNO"] = b_msgyesno
        builtins["TESTLABMSDIALOG"] = b_testlab_msdialog
        builtins["TESTLABNOOP"] = b_testlab_noop
        return builtins


def _format_advpl_arguments(args):
    def format_value(value):
        if isinstance(value, str):
            return "'" + value.replace("'", "''") + "'"
        if isinstance(value, bool):
            return ".T." if value else ".F."
        if value is None:
            return "NIL"
        return str(value)

    return ", ".join(format_value(value) for value in args)


_DEFINE_MSDIALOG = re.compile(
    r"^(?P<indent>\s*)DEFINE\s+MSDIALOG\s+\w+\s+TITLE\s+"
    r"(?P<title>.+?)\s+FROM\s+.+$",
    re.IGNORECASE,
)
_UI_CONTROL = re.compile(r"^\s*@")
_ACTIVATE_DIALOG = re.compile(r"^\s*ACTIVATE\s+DIALOG\b", re.IGNORECASE)


def adapt_headless_ui(source):
    lines = []
    for line in source.splitlines():
        dialog = _DEFINE_MSDIALOG.match(line)
        if dialog:
            lines.append(
                f"{dialog.group('indent')}TestLabMSDialog({dialog.group('title')})"
            )
        elif _UI_CONTROL.match(line) or _ACTIVATE_DIALOG.match(line):
            indent = line[: len(line) - len(line.lstrip())]
            lines.append(f"{indent}TestLabNoOp()")
        else:
            lines.append(line)
    return "\n".join(lines)


def run_source(source, fixture=None, entry="MAIN", args=None, source_name="<memoria>"):
    program = parse_source(adapt_headless_ui(preprocess(source)))
    interpreter = FixtureInterpreter(
        program, fixture=fixture, source_name=source_name
    )
    return interpreter.run(entry, args)


def run_file(source_path, fixture_path, entry="MAIN", args=None):
    source_file = Path(source_path)
    with source_file.open(encoding="utf-8", errors="replace") as advpl_file:
        source = advpl_file.read()
    fixture = Fixture.from_file(fixture_path)
    return run_source(
        source,
        fixture=fixture,
        entry=entry,
        args=args,
        source_name=source_file,
    )
