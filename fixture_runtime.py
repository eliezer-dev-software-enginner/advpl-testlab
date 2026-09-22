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
from semantic import validate_program


class Fixture:
    def __init__(
        self,
        parametros=None,
        tabelas=None,
        funcoes=None,
        consultas=None,
        especificidades_prw=None,
        ambiente=None,
        dialogos=None,
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
        self.ambiente = self._normalize_parameters(
            [] if ambiente is None else ambiente
        )
        self.dialogos = self._validate_dialogs([] if dialogos is None else dialogos)

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
            ambiente=data.get("ambiente", []),
            dialogos=data.get("dialogos", []),
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

    @staticmethod
    def _validate_dialogs(dialogs):
        if not isinstance(dialogs, list):
            raise FixtureError("'dialogos' deve ser uma lista JSON")
        normalized = {}
        for dialog in dialogs:
            if not isinstance(dialog, dict):
                raise FixtureError("Cada item de 'dialogos' deve ser um objeto")
            source = dialog.get("fonte")
            title = dialog.get("titulo")
            variables = dialog.get("variaveis", [])
            if not isinstance(source, str) or not source.strip():
                raise FixtureError("Dialogo deve possuir 'fonte' como texto")
            if not isinstance(title, str) or not title:
                raise FixtureError("Dialogo deve possuir 'titulo' como texto")
            values = Fixture._normalize_parameters(variables)
            key = (Path(source.replace("\\", "/")).name.upper(), title)
            if key in normalized:
                raise FixtureError(
                    f"Dialogo duplicado para '{source}' com titulo '{title}'"
                )
            normalized[key] = values
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

    def get_environment(self, name, default=_MISSING):
        key = str(name).upper()
        if key in self.ambiente:
            return self.ambiente[key]
        if default is not _MISSING:
            return default
        raise AdvPLRuntimeError(
            f"Ambiente: valor '{name}' nao encontrado no fixture"
        )

    def get_dialog_variables(self, source_name, title):
        source_key = Path(str(source_name).replace("\\", "/")).name.upper()
        return self.dialogos.get((source_key, title), {})

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


class _AliasRuntime:
    def __init__(self, records):
        self.records = [
            {str(field).upper(): value for field, value in record.items()}
            for record in records
        ]
        self.position = 0
        self.closed = False

    def go_top(self):
        self.position = 0

    def eof(self):
        return self.closed or self.position >= len(self.records)

    def skip(self):
        self.position += 1

    def field(self, name):
        if self.eof():
            raise AdvPLRuntimeError(
                f"Alias sem registro corrente para ler o campo '{name}'"
            )
        return self.records[self.position].get(str(name).upper())


class _StatementRuntime:
    def __init__(self):
        self.query = ""
        self.parameters = {}


class _BrowseRuntime:
    def __init__(self):
        self.alias = ""
        self.description = "Resultado AdvPL"
        self.columns = []
        self.legends = []


class FixtureInterpreter(Interpreter):
    def __init__(
        self,
        program,
        fixture=None,
        source_name="<memoria>",
        entry_name="MAIN",
    ):
        self.fixture = fixture or Fixture()
        self.source_name = source_name
        self.entry_name = entry_name
        self._prw_function_calls = {}
        self._aliases = {}
        self._alias_sequence = 0
        self._virtual_files = {}
        self._file_handles = {}
        self._file_sequence = 0
        self._current_dialog_title = None
        self._statements = []
        super().__init__(program)
        self.globals["CUSERLOCAL"] = self.fixture.get_environment(
            "CUSERLOCAL", default="."
        )

    @property
    def virtual_files(self):
        return dict(self._virtual_files)

    @property
    def statements(self):
        return [
            {"query": statement.query, "parameters": dict(statement.parameters)}
            for statement in self._statements
        ]

    def call_function(self, name, args):
        upper = name.upper()
        if upper in self.fixture.funcoes and upper not in self.builtins:
            return self.fixture.get_function_result(upper)
        return super().call_function(name, args)

    def call_method(self, obj, method_name, args):
        method = method_name.upper()
        if isinstance(obj, _StatementRuntime):
            if method == "NEW":
                obj.query = args[0] if args else ""
                return obj
            if method in ("SETSTRING", "SETDATE"):
                if len(args) != 2:
                    raise AdvPLRuntimeError(
                        f"FWExecStatement:{method_name} espera indice e valor"
                    )
                obj.parameters[int(args[0])] = args[1]
                return None
            if method == "OPENALIAS":
                if len(args) != 1 or not isinstance(args[0], str):
                    raise AdvPLRuntimeError(
                        "FWExecStatement:OpenAlias espera um alias como texto"
                    )
                alias = args[0].upper()
                records = self.fixture.get_query_records(self.entry_name)
                self._aliases[alias] = _AliasRuntime(records)
                return args[0]
            if method == "DESTROY":
                return None
            raise AdvPLRuntimeError(
                f"Metodo FWExecStatement:{method_name} nao suportado"
            )

        if isinstance(obj, _BrowseRuntime):
            if method == "NEW":
                return obj
            if method == "SETALIAS":
                obj.alias = str(args[0]).upper()
                return None
            if method == "SETDESCRIPTION":
                obj.description = str(args[0])
                return None
            if method == "ADDCOLUMN":
                if len(args) < 2:
                    raise AdvPLRuntimeError(
                        "FWBrowse:AddColumn espera campo e titulo"
                    )
                obj.columns.append((str(args[0]).upper(), str(args[1])))
                return None
            if method == "ADDLEGEND":
                obj.legends.append(tuple(args))
                return None
            if method == "ACTIVATE":
                self._activate_browse(obj)
                return None
            raise AdvPLRuntimeError(f"Metodo FWBrowse:{method_name} nao suportado")

        return super().call_method(obj, method_name, args)

    def _get_alias(self, name):
        key = str(name).upper()
        alias = self._aliases.get(key)
        if alias is None or alias.closed:
            raise AdvPLRuntimeError(f"Alias '{name}' nao esta aberto")
        return alias

    def _activate_browse(self, browse):
        alias = self._get_alias(browse.alias)
        print(browse.description)
        if not alias.records:
            print("Nenhum registro encontrado.")
            return
        columns = browse.columns or [
            (field, field) for field in alias.records[0]
        ]
        widths = [
            max(
                len(title),
                *(len(str(record.get(field, ""))) for record in alias.records),
            )
            for field, title in columns
        ]
        print(
            " | ".join(
                title.ljust(width)
                for (_, title), width in zip(columns, widths)
            )
        )
        print("-+-".join("-" * width for width in widths))
        for record in alias.records:
            print(
                " | ".join(
                    str(record.get(field, "")).ljust(width)
                    for (field, _), width in zip(columns, widths)
                )
            )

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
            self._current_dialog_title = args[0]
            print(f"[MSDIALOG] {args[0]}")
            return None

        def b_testlab_noop(args):
            return None

        def b_testlab_activate_dialog(args):
            require_count("Activate Dialog", args, 0)
            if self._current_dialog_title is None:
                raise AdvPLRuntimeError(
                    "Activate Dialog executado sem Define MSDialog anterior"
                )
            values = self.fixture.get_dialog_variables(
                self.source_name, self._current_dialog_title
            )
            frame = self.call_stack[-1]
            for name, value in values.items():
                if name not in frame.locals:
                    raise AdvPLRuntimeError(
                        f"Dialogo '{self._current_dialog_title}': variavel "
                        f"'{name}' nao existe na funcao atual"
                    )
                frame.locals[name] = value
            return None

        def require_count(name, args, count):
            if len(args) != count:
                raise AdvPLRuntimeError(f"{name} espera {count} argumento(s)")

        def b_getarea(args):
            require_count("GetArea", args, 0)
            return []

        def b_restarea(args):
            require_count("RestArea", args, 1)
            return None

        def b_ctod(args):
            require_count("CToD", args, 1)
            if not isinstance(args[0], str):
                raise AdvPLRuntimeError("CToD espera texto")
            return None if args[0].strip() == "" else args[0]

        def b_retsqlname(args):
            require_count("RetSQLName", args, 1)
            return str(args[0])

        def b_xfilial(args):
            require_count("xFilial", args, 1)
            alias = str(args[0]).upper()
            table = self.fixture.tabelas.get(alias, {})
            records = table.get("registros", []) if isinstance(table, dict) else table
            field = f"{alias}_FILIAL"
            if records and field in records[0]:
                return records[0][field]
            return "01"

        def b_changequery(args):
            require_count("ChangeQuery", args, 1)
            return args[0]

        def b_getnextalias(args):
            require_count("GetNextAlias", args, 0)
            self._alias_sequence += 1
            return f"TL{self._alias_sequence:04d}"

        def b_fwexecstatement(args):
            require_count("FWExecStatement", args, 0)
            statement = _StatementRuntime()
            self._statements.append(statement)
            return statement

        def b_fwbrowse(args):
            require_count("FWBrowse", args, 0)
            return _BrowseRuntime()

        def b_alias_call(args):
            require_count("TestLabAliasCall", args, 2)
            alias = self._get_alias(args[0])
            method = str(args[1]).upper()
            if method == "DBGOTOP":
                alias.go_top()
                return None
            if method == "EOF":
                return alias.eof()
            if method == "DBSKIP":
                alias.skip()
                return None
            if method == "DBCLOSEAREA":
                alias.closed = True
                return None
            raise AdvPLRuntimeError(f"Metodo de alias '{args[1]}' nao suportado")

        def b_alias_field(args):
            require_count("TestLabAliasField", args, 2)
            return self._get_alias(args[0]).field(args[1])

        def b_time(args):
            require_count("Time", args, 0)
            value = self.fixture.get_environment("TIME", default="00:00:00")
            if not isinstance(value, str):
                raise AdvPLRuntimeError("Ambiente TIME deve ser texto")
            return value

        def b_fcreate(args):
            require_count("FCreate", args, 1)
            if not isinstance(args[0], str):
                raise AdvPLRuntimeError("FCreate espera o caminho como texto")
            self._file_sequence += 1
            handle = self._file_sequence
            self._virtual_files[args[0]] = ""
            self._file_handles[handle] = args[0]
            return handle

        def b_fwrite(args):
            require_count("FWrite", args, 2)
            handle = int(args[0])
            path = self._file_handles.get(handle)
            if path is None:
                raise AdvPLRuntimeError(f"FWrite: handle {handle} nao esta aberto")
            text = str(args[1])
            self._virtual_files[path] += text
            return len(text)

        def b_fclose(args):
            require_count("FClose", args, 1)
            handle = int(args[0])
            if handle not in self._file_handles:
                raise AdvPLRuntimeError(f"FClose: handle {handle} nao esta aberto")
            del self._file_handles[handle]
            return 0

        builtins["GETMV"] = b_getmv
        builtins["STRTRAN"] = b_strtran
        builtins["CHR"] = b_chr
        builtins["MSGALERT"] = b_msgalert
        builtins["MSGINFO"] = b_msginfo
        builtins["MSGYESNO"] = b_msgyesno
        builtins["TESTLABMSDIALOG"] = b_testlab_msdialog
        builtins["TESTLABNOOP"] = b_testlab_noop
        builtins["TESTLABACTIVATEDIALOG"] = b_testlab_activate_dialog
        builtins["GETAREA"] = b_getarea
        builtins["RESTAREA"] = b_restarea
        builtins["CTOD"] = b_ctod
        builtins["RETSQLNAME"] = b_retsqlname
        builtins["XFILIAL"] = b_xfilial
        builtins["CHANGEQUERY"] = b_changequery
        builtins["GETNEXTALIAS"] = b_getnextalias
        builtins["FWEXECSTATEMENT"] = b_fwexecstatement
        builtins["FWBROWSE"] = b_fwbrowse
        builtins["TESTLABALIASCALL"] = b_alias_call
        builtins["TESTLABALIASFIELD"] = b_alias_field
        builtins["TIME"] = b_time
        builtins["FCREATE"] = b_fcreate
        builtins["FWRITE"] = b_fwrite
        builtins["FCLOSE"] = b_fclose
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
_ALIAS_CALL = re.compile(
    r"\(\s*(?P<alias>[A-Za-z_]\w*)\s*\)\s*->\s*"
    r"\(\s*(?P<method>[A-Za-z_]\w*)\s*\(\s*\)\s*\)"
)
_ALIAS_FIELD = re.compile(
    r"\(\s*(?P<alias>[A-Za-z_]\w*)\s*\)\s*->\s*(?P<field>[A-Za-z_]\w*)"
)
_POST_INCREMENT = re.compile(r"\b(?P<name>[A-Za-z_]\w*)\s*\+\+")


def _replace_advpl_operators(line):
    result = []
    quote = None
    index = 0
    while index < len(line):
        char = line[index]
        if quote:
            result.append(char)
            if char == quote:
                if index + 1 < len(line) and line[index + 1] == quote:
                    result.append(line[index + 1])
                    index += 1
                else:
                    quote = None
        elif char in ("'", '"'):
            quote = char
            result.append(char)
        elif char == "!" and not (
            index + 1 < len(line) and line[index + 1] == "="
        ):
            result.append(".NOT.")
        elif (
            char == "@"
            and index + 1 < len(line)
            and (line[index + 1].isalpha() or line[index + 1] == "_")
        ):
            pass
        else:
            result.append(char)
        index += 1
    return "".join(result)


def _adapt_advpl_line(line):
    line = _ALIAS_CALL.sub(
        lambda match: (
            f"TestLabAliasCall({match.group('alias')}, "
            f"'{match.group('method')}')"
        ),
        line,
    )
    line = _ALIAS_FIELD.sub(
        lambda match: (
            f"TestLabAliasField({match.group('alias')}, "
            f"'{match.group('field')}')"
        ),
        line,
    )
    line = _POST_INCREMENT.sub(r"\g<name> += 1", line)
    return _replace_advpl_operators(line)


def adapt_headless_ui(source):
    lines = []
    for line in source.splitlines():
        dialog = _DEFINE_MSDIALOG.match(line)
        if dialog:
            lines.append(
                f"{dialog.group('indent')}TestLabMSDialog({dialog.group('title')})"
            )
        elif _UI_CONTROL.match(line):
            indent = line[: len(line) - len(line.lstrip())]
            lines.append(f"{indent}TestLabNoOp()")
        elif _ACTIVATE_DIALOG.match(line):
            indent = line[: len(line) - len(line.lstrip())]
            lines.append(f"{indent}TestLabActivateDialog()")
        else:
            lines.append(_adapt_advpl_line(line))
    return "\n".join(lines)


def prepare_source(source):
    lines_with_placeholders = []
    for line in source.splitlines():
        lines_with_placeholders.append(line)
        if line.lstrip().startswith("#"):
            lines_with_placeholders.append("")
    preprocessed = preprocess("\n".join(lines_with_placeholders))
    return adapt_headless_ui(preprocessed)


def compile_source(source):
    program = parse_source(prepare_source(source))
    validate_program(program, source)
    return program


def build_interpreter(
    source,
    fixture=None,
    entry="MAIN",
    source_name="<memoria>",
):
    program = compile_source(source)
    return FixtureInterpreter(
        program,
        fixture=fixture,
        source_name=source_name,
        entry_name=entry,
    )


def run_source(source, fixture=None, entry="MAIN", args=None, source_name="<memoria>"):
    interpreter = build_interpreter(
        source,
        fixture=fixture,
        entry=entry,
        source_name=source_name,
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
