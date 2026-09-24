import copy
import json
import re
import sys
from pathlib import Path


_MISSING = object()


class FixtureError(ValueError):
    pass


def _jsonc_to_json(source):
    """Remove comentarios e virgulas finais sem alterar as posicoes de linha."""
    chars = list(source)
    index = 0
    in_string = False
    escaped = False

    while index < len(chars):
        char = chars[index]
        next_char = chars[index + 1] if index + 1 < len(chars) else ""
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            index += 1
            continue
        if char == "/" and next_char == "/":
            while index < len(chars) and chars[index] not in "\r\n":
                chars[index] = " "
                index += 1
            continue
        if char == "/" and next_char == "*":
            start = index
            chars[index] = chars[index + 1] = " "
            index += 2
            while index + 1 < len(chars) and chars[index:index + 2] != ["*", "/"]:
                if chars[index] not in "\r\n":
                    chars[index] = " "
                index += 1
            if index + 1 >= len(chars):
                line = source.count("\n", 0, start) + 1
                raise FixtureError(f"Comentario de bloco nao terminado na linha {line}")
            chars[index] = chars[index + 1] = " "
            index += 2
            continue
        index += 1

    in_string = False
    escaped = False
    for index, char in enumerate(chars):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char != ",":
            continue
        next_index = index + 1
        while next_index < len(chars) and chars[next_index].isspace():
            next_index += 1
        if next_index < len(chars) and chars[next_index] in "]}":
            chars[index] = " "
    return "".join(chars)


class SourceUnitError(Exception):
    def __init__(self, source_name, source, original):
        self.source_name = source_name
        self.source = source
        self.original = original
        super().__init__(str(original))


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

from interpreter import AdvPLBlock, AdvPLObject, AdvPLRuntimeError, Interpreter
from lexer import LexError
from naming import NameCollisionError
from parser import Call, ParseError, Program, parse_source
from preprocessor import preprocess
from semantic import (
    SemanticError, mvc_field_names, private_names, validate_mvc_metadata,
    validate_program,
)
from state_store import load_state, save_state


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
        cenarios_mvc=None,
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
        self.cenarios_mvc = self._validate_mvc_cases(
            [] if cenarios_mvc is None else cenarios_mvc
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
            ambiente=data.get("ambiente", []),
            dialogos=data.get("dialogos", []),
            cenarios_mvc=data.get("cenariosMvc", []),
        )

    @staticmethod
    def _validate_mvc_cases(cases):
        if not isinstance(cases, list):
            raise FixtureError("'cenariosMvc' deve ser uma lista JSON")
        normalized = {}
        for case in cases:
            if not isinstance(case, dict):
                raise FixtureError("Cada cenario MVC deve ser um objeto")
            name = case.get("nome")
            if not isinstance(name, str) or not name.strip():
                raise FixtureError("Cenario MVC deve ter 'nome' nao vazio")
            if name in normalized:
                raise FixtureError(f"Cenario MVC duplicado: '{name}'")
            if str(case.get("operacao", "")).lower() != "incluir":
                raise FixtureError(f"Cenario MVC '{name}': operacao deve ser 'incluir'")
            data = case.get("dados")
            if not isinstance(data, dict) or not data or not all(
                isinstance(key, str) and isinstance(value, dict)
                for key, value in data.items()
            ):
                raise FixtureError(f"Cenario MVC '{name}': 'dados' deve mapear modelos para campos")
            expected = case.get("esperado")
            if not isinstance(expected, dict) or type(expected.get("salvou")) is not bool:
                raise FixtureError(f"Cenario MVC '{name}': 'esperado.salvou' deve ser booleano")
            if "totalRegistros" in expected and (
                type(expected["totalRegistros"]) is not int
                or expected["totalRegistros"] < 0
            ):
                raise FixtureError(
                    f"Cenario MVC '{name}': 'esperado.totalRegistros' deve ser inteiro nao negativo"
                )
            if "registro" in expected and not isinstance(expected["registro"], dict):
                raise FixtureError(f"Cenario MVC '{name}': 'esperado.registro' deve ser objeto")
            normalized[name] = case
        return normalized

    @classmethod
    def read_data(cls, path):
        fixture_path = Path(path)
        try:
            with fixture_path.open(encoding="utf-8") as fixture_file:
                source = fixture_file.read()
            if fixture_path.suffix.lower() == ".jsonc":
                source = _jsonc_to_json(source)
            return json.loads(source)
        except FileNotFoundError as exc:
            raise FixtureError(f"Fixture nao encontrado: '{fixture_path}'") from exc
        except json.JSONDecodeError as exc:
            raise FixtureError(
                f"JSON invalido em '{fixture_path}', linha {exc.lineno}: {exc.msg}"
            ) from exc

    @classmethod
    def from_file(cls, path):
        return cls.from_dict(cls.read_data(path))

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
            if isinstance(table, dict) and "indices" in table:
                indices = table["indices"]
                if not isinstance(indices, dict):
                    raise FixtureError(f"Indices de '{alias}' devem ser um objeto")
                fields = {
                    str(field.get("nome", "")).upper()
                    for field in table.get("campos", [])
                    if isinstance(field, dict)
                }
                for order, names in indices.items():
                    if not str(order).isdigit() or int(order) < 1:
                        raise FixtureError(f"Ordem de indice invalida em '{alias}': {order}")
                    if not isinstance(names, list) or not names or not all(
                        isinstance(name, str) and name.upper() in fields
                        for name in names
                    ):
                        raise FixtureError(
                            f"Indice {order} de '{alias}' deve listar campos declarados"
                        )
            if isinstance(table, dict) and "apelidosIndices" in table:
                nicknames = table["apelidosIndices"]
                indices = table.get("indices", {})
                if not isinstance(nicknames, dict) or any(
                    not isinstance(nickname, str) or not nickname
                    or str(order) not in indices
                    for nickname, order in nicknames.items()
                ):
                    raise FixtureError(
                        f"Apelidos de indices de '{alias}' devem apontar para ordens declaradas"
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
    def __init__(self, records, indices=None, nicknames=None):
        self.records = [
            {str(field).upper(): value for field, value in record.items()}
            for record in records
        ]
        self.indices = {
            int(order): tuple(str(field).upper() for field in fields)
            for order, fields in (indices or {}).items()
        }
        self.nicknames = {
            str(nickname).upper(): int(order)
            for nickname, order in (nicknames or {}).items()
        }
        self.order = None
        self.position = 0
        self.closed = False
        self.filter_block = None

    def set_order(self, order):
        number = int(order)
        if self.indices and number != 0 and number not in self.indices:
            raise AdvPLRuntimeError(f"Indice {number} nao definido no fixture")
        current = self.records[self.position] if not self.eof() else None
        self.order = number
        if number in self.indices:
            fields = self.indices[number]
            self.records.sort(
                key=lambda record: "".join(str(record.get(field, "")) for field in fields)
            )
            if current is not None:
                self.position = next(
                    index for index, record in enumerate(self.records) if record is current
                )

    def go_top(self):
        self.position = 0

    def eof(self):
        return self.closed or self.position >= len(self.records)

    def skip(self):
        self.position += 1

    def go_bottom(self):
        self.position = len(self.records) - 1 if self.records else 0

    def go_to(self, recno):
        if isinstance(recno, bool) or not isinstance(recno, int) or recno < 1:
            raise AdvPLRuntimeError("DbGoTo espera numero de registro positivo")
        self.position = min(recno - 1, len(self.records))

    def seek(self, key):
        sought = str(key)
        fields = self.indices.get(self.order)
        for position, record in enumerate(self.records):
            record_key = (
                "".join(str(record.get(field, "")) for field in fields)
                if fields is not None
                else "".join(
                    str(value) for field, value in record.items()
                    if field != "D_E_L_E_T_"
                )
            )
            if record_key.startswith(sought):
                self.position = position
                return True
        self.position = len(self.records)
        return False

    def deleted(self):
        if self.eof():
            return False
        return str(self.records[self.position].get("D_E_L_E_T_", " ")) == "*"

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


class _MvcRuntime(AdvPLObject):
    def __init__(self, name):
        super().__init__(name)
        self.models = {}
        self.alias = None
        self.position = 0
        self.post_block = None
        self.draft = None


class _MailManagerRuntime(AdvPLObject):
    def __init__(self):
        super().__init__("TMAILMANAGER")
        self.connected = False


class _MailMessageRuntime(AdvPLObject):
    def __init__(self):
        super().__init__("TMAILMESSAGE")


class FixtureInterpreter(Interpreter):
    def __init__(
        self,
        program,
        fixture=None,
        source_name="<memoria>",
        entry_name="MAIN",
        name_profile="modern",
    ):
        self.fixture = fixture or Fixture()
        self.source_name = source_name
        self.entry_name = entry_name
        self._prw_function_calls = {}
        self._aliases = {
            alias: _AliasRuntime(
                table.get("registros", []) if isinstance(table, dict) else table,
                table.get("indices", {}) if isinstance(table, dict) else None,
                table.get("apelidosIndices", {}) if isinstance(table, dict) else None,
            )
            for alias, table in self.fixture.tabelas.items()
        }
        self._alias_sequence = 0
        self._virtual_files = {}
        self._file_handles = {}
        self._file_sequence = 0
        self._current_dialog_title = None
        self._statements = []
        self._sent_emails = []
        self._transaction_snapshot = None
        self._error_block = None
        self._current_alias = next(iter(self._aliases), None)
        self._locked_alias = None
        self._record_locks = {}
        self._prepared_company = None
        self._prepared_branch = None
        self.mvc_case = None
        self.mvc_result = None
        super().__init__(program, name_profile=name_profile)
        self._fixture_function_symbols = {}
        for name in self.fixture.funcoes:
            key = self.name_policy.key(name)
            previous = self._fixture_function_symbols.get(key)
            if previous is not None:
                raise NameCollisionError(
                    f"Funcoes de fixture '{previous}' e '{name}' "
                    f"colidem no simbolo '{key}' ({name_profile})"
                )
            self._fixture_function_symbols[key] = name
        self.globals["CUSERLOCAL"] = self.fixture.get_environment(
            "CUSERLOCAL", default="."
        )
        self.globals["DDATABASE"] = self.fixture.get_environment(
            "DDATABASE", default="2026-09-22"
        )
        self.globals[self.name_policy.key("MODEL_OPERATION_INSERT")] = 3
        self.globals.update({
            self.name_policy.key(name): value
            for name, value in self.fixture.ambiente.items()
        })

    def _field_alias(self, name):
        key = name.upper()
        for alias_name, table in self.fixture.tabelas.items():
            if not isinstance(table, dict):
                continue
            if any(field.get("nome", "").upper() == key for field in table.get("campos", [])):
                return alias_name
        return None

    def _mvc_grid_positions(self, obj):
        items = self._get_alias(obj.alias).records
        master = self._get_alias("Z04")
        if master.eof():
            return []
        request = master.records[master.position]
        return [
            index for index, item in enumerate(items)
            if item.get("Z05_FILIAL") == request.get("Z04_FILIAL")
            and item.get("Z05_CODIGO") == request.get("Z04_CODIGO")
        ]

    def lookup(self, name):
        if self._field_alias(name):
            if not self._current_alias:
                raise AdvPLRuntimeError(f"Campo '{name}' sem alias selecionado")
            return self._get_alias(self._current_alias).field(name)
        return super().lookup(name)

    def assign_existing(self, name, value):
        if self._field_alias(name):
            alias = self._get_alias(self._current_alias)
            if alias.position + 1 not in self._record_locks.get(self._current_alias, set()):
                raise AdvPLRuntimeError(
                    f"Campo '{name}' requer RecLock no alias '{self._current_alias}'"
                )
            if alias.eof():
                raise AdvPLRuntimeError(f"Alias '{self._current_alias}' sem registro corrente")
            alias.records[alias.position][name.upper()] = value
            return
        return super().assign_existing(name, value)

    def assign_target(self, target, value):
        if isinstance(target, Call) and target.name.upper() == "TESTLABALIASFIELD":
            if len(target.args) != 2:
                raise AdvPLRuntimeError("Atribuicao de campo espera alias e nome")
            alias_name = str(self.eval(target.args[0])).upper()
            field_name = str(self.eval(target.args[1])).upper()
            alias = self._get_alias(alias_name)
            if alias.eof() or alias.position + 1 not in self._record_locks.get(alias_name, set()):
                raise AdvPLRuntimeError(f"Campo '{field_name}' requer RecLock em '{alias_name}'")
            alias.records[alias.position][field_name] = value
            return
        return super().assign_target(target, value)

    @property
    def virtual_files(self):
        return dict(self._virtual_files)

    @property
    def statements(self):
        return [
            {"query": statement.query, "parameters": dict(statement.parameters)}
            for statement in self._statements
        ]

    @property
    def sent_emails(self):
        return [dict(message) for message in self._sent_emails]

    def call_function(self, name, args):
        upper = name.upper()
        configured = self._fixture_function_symbols.get(self.name_policy.key(name))
        if configured is not None and upper not in self.builtins:
            return self.fixture.get_function_result(configured)
        if (upper.startswith("U_")
                and self.name_policy.key(upper) not in self.user_functions
                and self.name_policy.key(upper[2:]) in self.functions):
            upper = upper[2:]
        return super().call_function(upper, args)

    def apply_binop(self, op, left, right):
        if op == "!=":
            op = "<>"
        return super().apply_binop(op, left, right)

    def call_method(self, obj, method_name, args):
        method = method_name.upper()
        if isinstance(obj, _MailManagerRuntime):
            if method == "NEW":
                return obj
            if method in ("SETUSESSL", "SETUSETLS"):
                if len(args) != 1 or not isinstance(args[0], bool):
                    raise AdvPLRuntimeError(
                        f"TMailManager:{method_name} espera um argumento logico"
                    )
                obj.attrs[method] = args[0]
                return None
            if method == "INIT":
                if len(args) != 6:
                    raise AdvPLRuntimeError("TMailManager:Init espera 6 argumentos")
                obj.attrs["SERVER"] = args[1]
                obj.attrs["ACCOUNT"] = args[2]
                obj.attrs["PORT"] = args[5]
                return self._mail_result("MAIL_INIT_RESULT")
            if method == "SETSMTPTIMEOUT":
                if len(args) != 1:
                    raise AdvPLRuntimeError(
                        "TMailManager:SetSMTPTimeout espera 1 argumento"
                    )
                obj.attrs["TIMEOUT"] = args[0]
                return self._mail_result("MAIL_TIMEOUT_RESULT")
            if method == "SMTPCONNECT":
                if args:
                    raise AdvPLRuntimeError(
                        "TMailManager:SMTPConnect nao espera argumentos"
                    )
                result = self._mail_result("MAIL_CONNECT_RESULT")
                obj.connected = result == 0
                return result
            if method == "SMTPAUTH":
                if len(args) != 2:
                    raise AdvPLRuntimeError("TMailManager:SMTPAuth espera 2 argumentos")
                return self._mail_result("MAIL_AUTH_RESULT")
            if method == "GETERRORSTRING":
                if len(args) != 1:
                    raise AdvPLRuntimeError(
                        "TMailManager:GetErrorString espera 1 argumento"
                    )
                return self.fixture.get_environment(
                    "MAIL_ERROR_MESSAGE",
                    default=f"Erro SMTP simulado ({args[0]})",
                )
            if method == "SMTPDISCONNECT":
                if args:
                    raise AdvPLRuntimeError(
                        "TMailManager:SMTPDisconnect nao espera argumentos"
                    )
                obj.connected = False
                return 0
            raise AdvPLRuntimeError(
                f"Metodo TMailManager:{method_name} nao suportado"
            )

        if isinstance(obj, _MailMessageRuntime):
            if method == "NEW":
                return obj
            if method == "CLEAR":
                if args:
                    raise AdvPLRuntimeError("TMailMessage:Clear nao espera argumentos")
                obj.attrs.clear()
                return None
            if method == "MSGBODYTYPE":
                if len(args) != 1 or not isinstance(args[0], str):
                    raise AdvPLRuntimeError(
                        "TMailMessage:MsgBodyType espera um argumento de texto"
                    )
                obj.attrs["BODY_TYPE"] = args[0]
                return None
            if method == "SEND":
                if len(args) != 1 or not isinstance(args[0], _MailManagerRuntime):
                    raise AdvPLRuntimeError(
                        "TMailMessage:Send espera um TMailManager"
                    )
                result = self._mail_result("MAIL_SEND_RESULT")
                if result == 0:
                    self._sent_emails.append(
                        {
                            "from": obj.attrs.get("CFROM", ""),
                            "to": obj.attrs.get("CTO", ""),
                            "subject": obj.attrs.get("CSUBJECT", ""),
                            "body_type": obj.attrs.get("BODY_TYPE", ""),
                            "body": obj.attrs.get("CBODY", ""),
                        }
                    )
                return result
            raise AdvPLRuntimeError(
                f"Metodo TMailMessage:{method_name} nao suportado"
            )

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
            if method in ("SETMENUDEF", "SETCACHEVIEW"):
                obj.attrs = getattr(obj, "attrs", {})
                obj.attrs[method] = args[0]
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

        if isinstance(obj, _MvcRuntime):
            if method == "NEW":
                if obj.class_name == "MPFORMMODEL" and len(args) > 2:
                    obj.post_block = args[2]
                return obj
            if method == "SETPRIMARYKEY":
                if len(args) != 1 or not isinstance(args[0], list):
                    raise AdvPLRuntimeError("SetPrimaryKey espera array de campos")
                fields = mvc_field_names(self.fixture)
                for field in args[0]:
                    if not isinstance(field, str) or field.upper() not in fields:
                        raise AdvPLRuntimeError(
                            f"Campo '{field}' de SetPrimaryKey nao existe na fixture"
                        )
                return None
            if method == "GETMODEL":
                if len(args) != 1:
                    raise AdvPLRuntimeError("GetModel espera identificador")
                key = str(args[0]).upper()
                if key not in obj.models:
                    raise AdvPLRuntimeError(f"Modelo '{key}' nao encontrado")
                return obj.models[key]
            if method in ("ADDFIELDS", "ADDGRID") and obj.class_name == "MPFORMMODEL":
                if not args:
                    raise AdvPLRuntimeError(f"{method_name} espera identificador")
                child = _MvcRuntime("MVCGRID" if method == "ADDGRID" else "MVCFIELDS")
                child.alias = (
                    args[2].alias if len(args) > 2 and isinstance(args[2], _MvcRuntime)
                    and args[2].alias else ("Z05" if method == "ADDGRID" else "Z04")
                )
                child.models = obj.models
                obj.models[str(args[0]).upper()] = child
                return None
            if method == "GETOPERATION":
                if self.mvc_case is not None:
                    return 3
                return self.fixture.get_environment("MODEL_OPERATION", default=2)
            if method == "GETVALUE":
                if obj.class_name == "MPFORMMODEL":
                    if len(args) != 2:
                        raise AdvPLRuntimeError("GetValue espera modelo e campo")
                    child = obj.models.get(str(args[0]).upper())
                    if child is None:
                        raise AdvPLRuntimeError(f"GetValue: modelo '{args[0]}' nao encontrado")
                    return self.call_method(child, "GetValue", [args[1]])
                if len(args) != 1:
                    raise AdvPLRuntimeError("GetValue espera campo")
                if obj.draft is not None:
                    key = str(args[0]).upper()
                    if key not in obj.draft:
                        raise AdvPLRuntimeError(f"GetValue: campo '{key}' ausente nos dados do cenario MVC")
                    return obj.draft[key]
                alias = self._get_alias(obj.alias)
                if obj.class_name == "MVCGRID":
                    alias.position = self._mvc_grid_positions(obj)[obj.position]
                return alias.field(args[0])
            if method == "LENGTH":
                if obj.class_name == "MVCGRID":
                    return len(self._mvc_grid_positions(obj))
                return len(self._get_alias(obj.alias).records)
            if method == "GOLINE":
                length = self.call_method(obj, "Length", [])
                if len(args) != 1 or not 1 <= int(args[0]) <= length:
                    raise AdvPLRuntimeError("GoLine: linha fora do grid")
                obj.position = int(args[0]) - 1
                return None
            if method == "ISDELETED":
                alias = self._get_alias(obj.alias)
                alias.position = self._mvc_grid_positions(obj)[obj.position]
                return alias.deleted()
            if method in (
                "SETRELATION", "SETUNIQUELINE", "SETDESCRIPTION",
                "REMOVEFIELD", "SETMODEL", "ADDFIELD", "ADDGRID", "CREATEHORIZONTALBOX",
                "SETOWNERVIEW", "ENABLETITLEVIEW", "ADDINCREMENTFIELD",
            ):
                return None
            raise AdvPLRuntimeError(f"Metodo MVC '{method_name}' nao suportado")

        return super().call_method(obj, method_name, args)

    def _mail_result(self, name):
        result = self.fixture.get_environment(name, default=0)
        if isinstance(result, bool) or not isinstance(result, (int, float)):
            raise AdvPLRuntimeError(f"Ambiente {name} deve ser numerico")
        return result

    def _get_alias(self, name):
        key = str(name).upper()
        alias = self._aliases.get(key)
        if alias is None or alias.closed:
            raise AdvPLRuntimeError(f"Alias '{name}' nao esta aberto")
        return alias

    def _activate_browse(self, browse):
        if self.mvc_case is not None:
            self._run_mvc_case(browse)
            return
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

    def _run_mvc_case(self, browse):
        case = self.mvc_case
        if self.mvc_result is not None:
            raise FixtureError(f"Cenario MVC '{case['nome']}' acionou mais de um browse")
        model = self.call_function("ModelDef", [])
        if not isinstance(model, _MvcRuntime) or model.class_name != "MPFORMMODEL":
            raise FixtureError(f"Cenario MVC '{case['nome']}': ModelDef nao retornou MPFormModel")
        if not isinstance(model.post_block, AdvPLBlock):
            raise FixtureError(f"Cenario MVC '{case['nome']}': MPFormModel nao possui bPost")
        if len(case["dados"]) != 1:
            raise FixtureError(f"Cenario MVC '{case['nome']}': inclusao suporta um modelo de campos")
        model_name, fields = next(iter(case["dados"].items()))
        child = model.models.get(model_name.upper())
        if child is None or child.class_name != "MVCFIELDS":
            raise FixtureError(f"Cenario MVC '{case['nome']}': modelo '{model_name}' nao encontrado")
        if child.alias != browse.alias:
            raise FixtureError(
                f"Cenario MVC '{case['nome']}': modelo '{model_name}' usa '{child.alias}', "
                f"mas browse usa '{browse.alias}'"
            )
        table = self.fixture.tabelas.get(child.alias)
        if not isinstance(table, dict) or not isinstance(table.get("campos"), list):
            raise FixtureError(f"Cenario MVC '{case['nome']}': tabela '{child.alias}' sem metadados de campos")
        declared = {field["nome"].upper(): field.get("tipo", "").upper()
                    for field in table["campos"]}
        draft = {}
        for name, value in fields.items():
            key = str(name).upper()
            if key not in declared:
                raise FixtureError(f"Cenario MVC '{case['nome']}': campo '{name}' nao existe em '{child.alias}'")
            kind = declared[key]
            if kind == "N" and (isinstance(value, bool) or not isinstance(value, (int, float))):
                raise FixtureError(f"Cenario MVC '{case['nome']}': campo '{name}' deve ser numerico")
            if kind == "C" and not isinstance(value, str):
                raise FixtureError(f"Cenario MVC '{case['nome']}': campo '{name}' deve ser texto")
            draft[key] = value
        child.draft = draft
        saved = self.invoke_block(model.post_block, [model])
        if type(saved) is not bool:
            raise FixtureError(f"Cenario MVC '{case['nome']}': bPost deve retornar logico")
        alias = self._get_alias(child.alias)
        if saved:
            alias.records.append(copy.deepcopy(draft))
        self.mvc_result = {"salvou": saved, "totalRegistros": len(alias.records),
                           "registros": copy.deepcopy(alias.records)}
        expected = case["esperado"]
        if saved != expected["salvou"]:
            raise FixtureError(
                f"Cenario MVC '{case['nome']}': esperado salvou={expected['salvou']}, "
                f"obtido salvou={saved}"
            )
        if "totalRegistros" in expected and len(alias.records) != expected["totalRegistros"]:
            raise FixtureError(
                f"Cenario MVC '{case['nome']}': esperado totalRegistros="
                f"{expected['totalRegistros']}, obtido {len(alias.records)}"
            )
        if "registro" in expected:
            expected_record = {str(key).upper(): value
                               for key, value in expected["registro"].items()}
            if not saved or alias.records[-1] != expected_record:
                raise FixtureError(
                    f"Cenario MVC '{case['nome']}': ultimo registro difere de 'esperado.registro'"
                )
        print(f"[MVC] {case['nome']}: salvou={str(saved).lower()}, "
              f"totalRegistros={len(alias.records)}")

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

        def b_at(args):
            if len(args) != 2 or not all(isinstance(value, str) for value in args):
                raise AdvPLRuntimeError("At espera 2 argumentos de texto")
            position = args[1].find(args[0])
            return position + 1 if position >= 0 else 0

        def b_type(args):
            require_count("Type", args, 1)
            if not isinstance(args[0], str):
                raise AdvPLRuntimeError("Type espera nome de variavel como texto")
            return builtins["VALTYPE"]([self.globals.get(args[0].upper())])

        def b_aclone(args):
            require_count("AClone", args, 1)
            if not isinstance(args[0], list):
                raise AdvPLRuntimeError("AClone espera array")
            return list(args[0])

        def b_chkfile(args):
            require_count("ChkFile", args, 1)
            return str(args[0]).upper() in self._aliases

        def b_errorblock(args):
            require_count("ErrorBlock", args, 1)
            previous = self._error_block
            self._error_block = args[0]
            return previous

        def b_break(args):
            if len(args) > 1:
                raise AdvPLRuntimeError("Break espera no maximo 1 argumento")
            return builtins["THROW"](args)

        def b_left(args):
            if (
                len(args) != 2
                or not isinstance(args[0], str)
                or isinstance(args[1], bool)
                or not isinstance(args[1], (int, float))
            ):
                raise AdvPLRuntimeError("Left espera texto e tamanho numerico")
            return args[0][: max(0, int(args[1]))]

        def b_encode_utf8(args):
            if not 1 <= len(args) <= 2 or not isinstance(args[0], str):
                raise AdvPLRuntimeError(
                    "EncodeUTF8 espera texto e encoding de origem opcional"
                )
            if len(args) == 2 and not isinstance(args[1], str):
                raise AdvPLRuntimeError("EncodeUTF8 espera encoding como texto")
            return args[0]

        def b_free_obj(args):
            if len(args) != 1:
                raise AdvPLRuntimeError("FreeObj espera 1 argumento")
            return None

        def b_transform(args):
            if len(args) != 2 or not isinstance(args[1], str):
                raise AdvPLRuntimeError("Transform espera valor e mascara")
            value = args[0]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return str(value)
            decimals = len(args[1].rsplit(".", 1)[1]) if "." in args[1] else 0
            return f"{value:,.{decimals}f}"

        def b_dtoc(args):
            if len(args) != 1:
                raise AdvPLRuntimeError("DToC espera 1 argumento")
            value = args[0]
            if value is None:
                return ""
            if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                year, month, day = value.split("-")
                return f"{day}/{month}/{year}"
            return str(value)

        def b_contains(args):
            if len(args) != 2 or not all(isinstance(value, str) for value in args):
                raise AdvPLRuntimeError("Operador $ espera dois textos")
            return args[0] in args[1]

        def b_tmail_manager(args):
            if args:
                raise AdvPLRuntimeError("TMailManager nao espera argumentos")
            return _MailManagerRuntime()

        def b_tmail_message(args):
            if args:
                raise AdvPLRuntimeError("TMailMessage nao espera argumentos")
            return _MailMessageRuntime()

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

        def b_msgstop(args):
            message, title = message_args("MsgStop", args)
            prefix = f"{title}: " if title else ""
            print(f"[ERRO] {prefix}{message}")
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
            position = None
            if self._current_alias in self._aliases:
                position = self._aliases[self._current_alias].position
            return [self._current_alias, position]

        def b_restarea(args):
            require_count("RestArea", args, 1)
            area = args[0]
            if not isinstance(area, list) or len(area) != 2:
                raise AdvPLRuntimeError("RestArea espera area salva por GetArea")
            self._current_alias = area[0]
            if area[0] in self._aliases and area[1] is not None:
                self._aliases[area[0]].position = area[1]
            return None

        def b_select(args):
            if len(args) > 1:
                raise AdvPLRuntimeError("Select espera zero ou um alias")
            name = str(args[0]).upper() if args else self._current_alias
            if name not in self._aliases or self._aliases[name].closed:
                return 0
            return list(self._aliases).index(name) + 1

        def b_dbselectarea(args):
            require_count("DbSelectArea", args, 1)
            name = args[0]
            if isinstance(name, int) and not isinstance(name, bool):
                names = list(self._aliases)
                name = names[name - 1] if 1 <= name <= len(names) else name
            name = str(name).upper()
            self._get_alias(name)
            self._current_alias = name
            return None

        def b_dbsetorder(args):
            require_count("DbSetOrder", args, 1)
            self._get_alias(self._current_alias).set_order(args[0])
            return None

        def b_dbseek(args):
            if not 1 <= len(args) <= 2 or (len(args) == 2 and not isinstance(args[1], bool)):
                raise AdvPLRuntimeError("DbSeek espera chave e lSoft opcional")
            alias = self._get_alias(self._current_alias)
            sought = str(args[0])
            fields = alias.indices.get(alias.order)
            soft_position = None
            for index, record in enumerate(alias.records):
                key = ("".join(str(record.get(field, "")) for field in fields)
                       if fields else "".join(str(value) for field, value in record.items()
                                              if field != "D_E_L_E_T_"))
                alias.position = index
                if not visible(alias):
                    continue
                if key.startswith(sought):
                    return True
                if len(args) == 2 and args[1] and soft_position is None and key >= sought:
                    soft_position = index
            alias.position = soft_position if soft_position is not None else len(alias.records)
            return False

        def visible(alias):
            if alias.eof() or alias.deleted():
                return False
            if alias.filter_block is None:
                return True
            result = self.invoke_block(alias.filter_block, [])
            if not isinstance(result, bool):
                raise AdvPLRuntimeError("DbSetFilter: bloco deve retornar logico")
            return result

        def advance(alias, direction):
            alias.position += direction
            while 0 <= alias.position < len(alias.records) and not visible(alias):
                alias.position += direction
            if alias.position < 0:
                alias.position = 0

        def b_eof(args):
            require_count("Eof", args, 0)
            return self._get_alias(self._current_alias).eof()

        def b_dbskip(args):
            if len(args) > 1 or (args and (isinstance(args[0], bool) or not isinstance(args[0], int))):
                raise AdvPLRuntimeError("DbSkip espera deslocamento inteiro opcional")
            alias = self._get_alias(self._current_alias)
            count = args[0] if args else 1
            for _ in range(abs(count)):
                advance(alias, 1 if count >= 0 else -1)
            return None

        def b_reclock(args):
            if len(args) != 2 or not isinstance(args[1], bool):
                raise AdvPLRuntimeError("RecLock espera alias e indicador de inclusao")
            name = str(args[0]).upper()
            alias = self._get_alias(name)
            self._current_alias = name
            permitted = self.fixture.get_environment(f"RECLOCK_{name}", default=True)
            if not isinstance(permitted, bool):
                raise AdvPLRuntimeError(f"Ambiente RECLOCK_{name} deve ser logico")
            if not permitted:
                return False
            if args[1]:
                alias.records.append({})
                alias.position = len(alias.records) - 1
            elif alias.eof():
                return False
            self._locked_alias = name
            self._record_locks.setdefault(name, set()).add(alias.position + 1)
            return True

        def b_msunlock(args):
            require_count("MsUnlock", args, 0)
            if self._locked_alias is not None:
                self._record_locks.pop(self._locked_alias, None)
            self._locked_alias = None
            return None

        def b_dbgoto(args):
            require_count("DbGoTo", args, 1)
            self._get_alias(self._current_alias).go_to(args[0])
            return None

        def b_dbgotop(args):
            require_count("DbGoTop", args, 0)
            alias = self._get_alias(self._current_alias)
            alias.go_top()
            while not alias.eof() and not visible(alias):
                alias.position += 1
            return None

        def b_dbgobottom(args):
            require_count("DbGoBottom", args, 0)
            alias = self._get_alias(self._current_alias)
            alias.go_bottom()
            while alias.records and not visible(alias) and alias.position > 0:
                alias.position -= 1
            if alias.records and not visible(alias):
                alias.position = len(alias.records)
            return None

        def b_dbclosearea(args):
            require_count("DbCloseArea", args, 0)
            alias = self._get_alias(self._current_alias)
            alias.closed = True
            self._record_locks.pop(self._current_alias, None)
            if self._locked_alias == self._current_alias:
                self._locked_alias = None
            self._current_alias = None
            return None

        def b_dbcommit(args):
            require_count("DbCommit", args, 0)
            self._get_alias(self._current_alias)
            return None

        def b_dbcommitall(args):
            require_count("DbCommitAll", args, 0)
            return None

        def b_dbdelete(args):
            require_count("DbDelete", args, 0)
            alias = self._get_alias(self._current_alias)
            if alias.eof():
                raise AdvPLRuntimeError("DbDelete sem registro corrente")
            if alias.position + 1 not in self._record_locks.get(self._current_alias, set()):
                raise AdvPLRuntimeError("DbDelete requer bloqueio do registro corrente")
            alias.records[alias.position]["D_E_L_E_T_"] = "*"
            return None

        def b_dbrlock(args):
            if len(args) > 1:
                raise AdvPLRuntimeError("DbRLock espera recno opcional")
            alias = self._get_alias(self._current_alias)
            recno = args[0] if args else alias.position + 1
            if isinstance(recno, bool) or not isinstance(recno, int):
                raise AdvPLRuntimeError("DbRLock espera recno inteiro")
            if not 1 <= recno <= len(alias.records):
                return False
            permitted = self.fixture.get_environment(f"RECLOCK_{self._current_alias}", default=True)
            if not isinstance(permitted, bool):
                raise AdvPLRuntimeError(f"Ambiente RECLOCK_{self._current_alias} deve ser logico")
            if not permitted:
                return False
            self._record_locks.setdefault(self._current_alias, set()).add(recno)
            self._locked_alias = self._current_alias
            return True

        def b_dbrlocklist(args):
            require_count("DbRLockList", args, 0)
            self._get_alias(self._current_alias)
            return sorted(self._record_locks.get(self._current_alias, set()))

        def b_dbunlock(args):
            require_count("DbUnlock", args, 0)
            self._get_alias(self._current_alias)
            self._record_locks.pop(self._current_alias, None)
            if self._locked_alias == self._current_alias:
                self._locked_alias = None
            return None

        def b_dbunlockall(args):
            require_count("DbUnlockAll", args, 0)
            self._record_locks.clear()
            self._locked_alias = None
            return None

        def b_dbsetfilter(args):
            if len(args) > 2 or (args and args[0] is not None and not isinstance(args[0], AdvPLBlock)):
                raise AdvPLRuntimeError("DbSetFilter espera bloco e expressao textual opcional")
            if len(args) == 2 and not isinstance(args[1], str):
                raise AdvPLRuntimeError("DbSetFilter: expressao deve ser texto")
            self._get_alias(self._current_alias).filter_block = args[0] if args else None
            return None

        def b_dbordernickname(args):
            require_count("DbOrderNickname", args, 1)
            alias = self._get_alias(self._current_alias)
            nickname = str(args[0]).upper()
            if nickname not in alias.nicknames:
                raise AdvPLRuntimeError(
                    f"DbOrderNickname: apelido '{args[0]}' nao configurado no fixture"
                )
            alias.set_order(alias.nicknames[nickname])
            return None

        def b_softlock(args):
            require_count("SoftLock", args, 1)
            name = str(args[0]).upper()
            alias = self._get_alias(name)
            if alias.eof():
                return False
            previous = self._current_alias
            self._current_alias = name
            try:
                return b_dbrlock([])
            finally:
                self._current_alias = previous

        def b_dbusearea(args):
            if not 3 <= len(args) <= 6:
                raise AdvPLRuntimeError("DbUseArea espera lNew, cDriver, cName, cAlias e opcoes")
            name = args[3] if len(args) >= 4 and args[3] else args[2]
            if not isinstance(name, str) or not name:
                raise AdvPLRuntimeError("DbUseArea espera alias textual")
            name = name.upper()
            if name not in self._aliases:
                raise AdvPLRuntimeError(f"DbUseArea: alias '{name}' nao configurado no fixture")
            if not isinstance(args[0], bool):
                raise AdvPLRuntimeError("DbUseArea espera lNew logico")
            alias = self._aliases[name]
            if not args[0] and self._current_alias in self._aliases and self._current_alias != name:
                b_dbclosearea([])
            alias.closed = False
            alias.go_top()
            self._current_alias = name
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
            if len(args) > 1:
                raise AdvPLRuntimeError("xFilial espera zero ou um alias")
            alias = str(args[0]).upper() if args else self._current_alias
            if not alias:
                raise AdvPLRuntimeError("xFilial sem alias e sem area corrente")
            table = self.fixture.tabelas.get(alias, {})
            records = table.get("registros", []) if isinstance(table, dict) else table
            field = f"{alias}_FILIAL"
            if records and field in records[0]:
                return records[0][field]
            return self._prepared_branch or "01"

        def b_prepare_environment(args):
            if len(args) != 2 or not all(isinstance(value, str) and value for value in args):
                raise AdvPLRuntimeError("PREPARE ENVIRONMENT espera EMPRESA e FILIAL como texto nao vazio")
            self._prepared_company, self._prepared_branch = args
            return None

        def b_reset_environment(args):
            require_count("RESET ENVIRONMENT", args, 0)
            self._prepared_company = None
            self._prepared_branch = None
            return None

        def b_alert(args):
            if len(args) != 1 or not isinstance(args[0], str):
                raise AdvPLRuntimeError("Alert espera uma mensagem de texto")
            print(f"[ALERTA] {args[0]}")
            return None

        def b_date(args):
            require_count("Date", args, 0)
            value = self.globals["DDATABASE"]
            if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise AdvPLRuntimeError("DDATABASE deve estar em formato AAAA-MM-DD")
            return value

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

        def b_mvc_object(name, args):
            if name != "FWFORMSTRUCT" and args:
                raise AdvPLRuntimeError(f"{name} nao espera argumentos")
            result = _MvcRuntime(name)
            if name == "FWFORMSTRUCT" and len(args) > 1 and isinstance(args[1], str):
                result.alias = args[1].upper()
            return result

        def b_fwloadmodel(args):
            require_count("FWLoadModel", args, 1)
            return self.call_function("ModelDef", [])

        def b_fwmsgrun(args):
            if len(args) != 4 or not isinstance(args[1], AdvPLBlock):
                raise AdvPLRuntimeError("FWMsgRun espera componente, bloco, titulo e mensagem")
            print(f"[PROGRESSO] {args[2]}: {args[3]}")
            return self.invoke_block(args[1], [])

        def b_ascan(args):
            if len(args) != 2 or not isinstance(args[0], list):
                raise AdvPLRuntimeError("AScan espera array e valor")
            if isinstance(args[1], AdvPLBlock):
                for index, value in enumerate(args[0], start=1):
                    if self.invoke_block(args[1], [value]):
                        return index
                return 0
            try:
                return args[0].index(args[1]) + 1
            except ValueError:
                return 0

        def b_indexkey(args):
            require_count("IndexKey", args, 1)
            return f"INDEX_{args[0]}"

        def b_brwlegenda(args):
            if len(args) != 3:
                raise AdvPLRuntimeError("BrwLegenda espera titulo, subtitulo e legendas")
            print(f"[LEGENDA] {args[0]}: {args[1]}")

        def b_alias_call(args):
            require_count("TestLabAliasCall", args, 2)
            name = str(args[0]).upper()
            self._get_alias(name)
            method = str(args[1]).upper()
            if method in builtins:
                previous = self._current_alias
                self._current_alias = name
                try:
                    return builtins[method]([])
                finally:
                    if method != "DBCLOSEAREA" or previous != name:
                        self._current_alias = previous
            raise AdvPLRuntimeError(f"Metodo de alias '{args[1]}' nao suportado")

        def b_alias_field(args):
            require_count("TestLabAliasField", args, 2)
            return self._get_alias(args[0]).field(args[1])

        def b_static_alias_call(args):
            if len(args) < 2:
                raise AdvPLRuntimeError(
                    "TestLabStaticAliasCall espera alias e metodo"
                )
            alias = self._get_alias(args[0])
            method = str(args[1]).upper()
            method_args = args[2:]
            if method in {"DBGOTO", "DBGOTOP", "DBGOBOTTOM", "DBGOBOTTON",
                          "DBSEEK", "MSSEEK", "DBSKIP", "DBSETORDER", "DBSETFILTER",
                          "DBDELETE", "DBRLOCK", "DBRLOCKLIST", "DBUNLOCK",
                          "DBCOMMIT", "DBORDERNICKNAME", "DBCLOSEAREA", "EOF"}:
                previous = self._current_alias
                self._current_alias = str(args[0]).upper()
                try:
                    return builtins[method](method_args)
                finally:
                    if method != "DBCLOSEAREA" or previous != str(args[0]).upper():
                        self._current_alias = previous
            table = self.fixture.tabelas.get(str(args[0]).upper(), {})
            fields = table.get("campos", []) if isinstance(table, dict) else []
            if method == "FIELDPOS":
                require_count("FieldPos", method_args, 1)
                return next(
                    (index for index, field in enumerate(fields, start=1)
                     if field.get("nome", "").upper() == str(method_args[0]).upper()),
                    0,
                )
            if method == "FIELDGET":
                require_count("FieldGet", method_args, 1)
                index = int(method_args[0]) - 1
                if not 0 <= index < len(fields):
                    raise AdvPLRuntimeError("FieldGet: campo fora da estrutura")
                return alias.field(fields[index]["nome"])
            if method == "DBSTRUCT":
                require_count("DbStruct", method_args, 0)
                return [
                    [field["nome"], field["tipo"], field.get("tamanho", 0), 0]
                    for field in fields
                ]
            if method == "GETAREA":
                require_count("GetArea", method_args, 0)
                return [str(args[0]).upper(), alias.position]
            if method == "DBSETORDER":
                require_count("DbSetOrder", method_args, 1)
                alias.set_order(method_args[0])
                return None
            if method == "INDEXKEY":
                require_count("IndexKey", method_args, 1)
                return f"INDEX_{method_args[0]}"
            if method == "DBSEEK":
                require_count("DbSeek", method_args, 1)
                return alias.seek(method_args[0])
            if method == "EOF":
                require_count("Eof", method_args, 0)
                return alias.eof()
            if method == "DELETED":
                require_count("Deleted", method_args, 0)
                return alias.deleted()
            if method == "DBSKIP":
                require_count("DbSkip", method_args, 0)
                alias.skip()
                return None
            if method == "MSUNLOCK":
                require_count("MsUnlock", method_args, 0)
                self._locked_alias = None
                return None
            raise AdvPLRuntimeError(
                f"Metodo de alias estatico '{args[1]}' nao suportado"
            )

        def b_begin_transaction(args):
            require_count("Begin Transaction", args, 0)
            if self._transaction_snapshot is not None:
                raise AdvPLRuntimeError("Transacao aninhada nao suportada")
            self._transaction_snapshot = copy.deepcopy(self._aliases)

        def b_disarm_transaction(args):
            require_count("DisarmTransaction", args, 0)
            if self._transaction_snapshot is None:
                raise AdvPLRuntimeError("DisarmTransaction sem transacao")
            self._aliases = self._transaction_snapshot
            self._transaction_snapshot = None

        def b_end_transaction(args):
            require_count("End Transaction", args, 0)
            self._transaction_snapshot = None

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
        builtins["AT"] = b_at
        builtins["TYPE"] = b_type
        builtins["ACLONE"] = b_aclone
        builtins["CHKFILE"] = b_chkfile
        builtins["ERRORBLOCK"] = b_errorblock
        builtins["BREAK"] = b_break
        builtins["LEFT"] = b_left
        builtins["ENCODEUTF8"] = b_encode_utf8
        builtins["FREEOBJ"] = b_free_obj
        builtins["TRANSFORM"] = b_transform
        builtins["DTOC"] = b_dtoc
        builtins["TESTLABCONTAINS"] = b_contains
        builtins["TMAILMANAGER"] = b_tmail_manager
        builtins["TMAILMESSAGE"] = b_tmail_message
        builtins["MSGALERT"] = b_msgalert
        builtins["MSGINFO"] = b_msginfo
        builtins["MSGSTOP"] = b_msgstop
        builtins["MSGYESNO"] = b_msgyesno
        builtins["TESTLABMSDIALOG"] = b_testlab_msdialog
        builtins["TESTLABNOOP"] = b_testlab_noop
        builtins["TESTLABACTIVATEDIALOG"] = b_testlab_activate_dialog
        builtins["GETAREA"] = b_getarea
        builtins["RESTAREA"] = b_restarea
        builtins["SELECT"] = b_select
        builtins["DBSELECTAREA"] = b_dbselectarea
        builtins["DBSETORDER"] = b_dbsetorder
        builtins["DBSEEK"] = b_dbseek
        builtins["MSSEEK"] = b_dbseek
        builtins["EOF"] = b_eof
        builtins["DBSKIP"] = b_dbskip
        builtins["DBGOTO"] = b_dbgoto
        builtins["DBGOTOP"] = b_dbgotop
        builtins["DBGOBOTTOM"] = b_dbgobottom
        builtins["DBGOBOTTON"] = b_dbgobottom
        builtins["DBCLOSEAREA"] = b_dbclosearea
        builtins["DBCOMMIT"] = b_dbcommit
        builtins["DBCOMMITALL"] = b_dbcommitall
        builtins["DBDELETE"] = b_dbdelete
        builtins["DBRLOCK"] = b_dbrlock
        builtins["RLOCK"] = b_dbrlock
        builtins["SOFTLOCK"] = b_softlock
        builtins["DBRLOCKLIST"] = b_dbrlocklist
        builtins["DBUNLOCK"] = b_dbunlock
        builtins["UNLOCK"] = b_dbunlock
        builtins["DBUNLOCKALL"] = b_dbunlockall
        builtins["DBSETFILTER"] = b_dbsetfilter
        builtins["DBORDERNICKNAME"] = b_dbordernickname
        builtins["DBUSEAREA"] = b_dbusearea
        builtins["RECLOCK"] = b_reclock
        builtins["MSUNLOCK"] = b_msunlock
        builtins["CTOD"] = b_ctod
        builtins["RETSQLNAME"] = b_retsqlname
        builtins["XFILIAL"] = b_xfilial
        builtins["TESTLABPREPAREENVIRONMENT"] = b_prepare_environment
        builtins["TESTLABRESETENVIRONMENT"] = b_reset_environment
        builtins["ALERT"] = b_alert
        builtins["DATE"] = b_date
        builtins["CHANGEQUERY"] = b_changequery
        builtins["GETNEXTALIAS"] = b_getnextalias
        builtins["FWEXECSTATEMENT"] = b_fwexecstatement
        builtins["FWBROWSE"] = b_fwbrowse
        builtins["FWMBROWSE"] = b_fwbrowse
        builtins["FWFORMSTRUCT"] = lambda args: b_mvc_object("FWFORMSTRUCT", args)
        builtins["MPFORMMODEL"] = lambda args: b_mvc_object("MPFORMMODEL", args)
        builtins["FWFORMVIEW"] = lambda args: b_mvc_object("FWFORMVIEW", args)
        builtins["FWLOADMODEL"] = b_fwloadmodel
        builtins["FWMSGRUN"] = b_fwmsgrun
        builtins["ASCAN"] = b_ascan
        builtins["INDEXKEY"] = b_indexkey
        builtins["BRWLEGENDA"] = b_brwlegenda
        builtins["TESTLABALIASCALL"] = b_alias_call
        builtins["TESTLABALIASFIELD"] = b_alias_field
        builtins["TESTLABSTATICALIASCALL"] = b_static_alias_call
        builtins["TESTLABBEGINTRANSACTION"] = b_begin_transaction
        builtins["DISARMTRANSACTION"] = b_disarm_transaction
        builtins["TESTLABENDTRANSACTION"] = b_end_transaction
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
_ACTIVATE_MSDIALOG = re.compile(r"^\s*ACTIVATE\s+MSDIALOG\b", re.IGNORECASE)
_TMULTIGET_ASSIGN = re.compile(
    r"^(?P<indent>\s*)(?P<target>\w+)\s*:=\s*TMultiGet\(\):New\(",
    re.IGNORECASE,
)
_BEGIN_TRANSACTION = re.compile(r"^\s*BEGIN\s+TRANSACTION\s*$", re.IGNORECASE)
_END_TRANSACTION = re.compile(r"^\s*END\s+TRANSACTION\s*$", re.IGNORECASE)
_PREPARE_ENVIRONMENT = re.compile(
    r"^(?P<indent>\s*)PREPARE\s+ENVIRONMENT\s+EMPRESA\s+"
    r"(?P<company>'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"|[A-Za-z_]\w*)\s+"
    r"FILIAL\s+(?P<branch>'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"|[A-Za-z_]\w*)\s*$",
    re.IGNORECASE,
)
_RESET_ENVIRONMENT = re.compile(r"^\s*RESET\s+ENVIRONMENT\s*$", re.IGNORECASE)
_ADD_OPTION = re.compile(
    r"^(?P<indent>\s*)ADD\s+OPTION\s+(?P<menu>\w+)\s+"
    r"TITLE\s+(?P<title>'(?:[^']|'')*')\s+"
    r"ACTION\s+(?P<action>'(?:[^']|'')*')\s+"
    r"OPERATION\s+(?P<operation>\d+)\s+ACCESS\s+(?P<access>\d+)\s*$",
    re.IGNORECASE,
)
_ALIAS_CALL = re.compile(
    r"\(\s*(?P<alias>[A-Za-z_]\w*)\s*\)\s*->\s*"
    r"\(\s*(?P<method>[A-Za-z_]\w*)\s*\(\s*\)\s*\)"
)
_ALIAS_FIELD = re.compile(
    r"\(\s*(?P<alias>[A-Za-z_]\w*)\s*\)\s*->\s*(?P<field>[A-Za-z_]\w*)"
)
_STATIC_ALIAS_CALL = re.compile(
    r"\b(?P<alias>[A-Za-z_]\w*)\s*->\s*\(\s*"
    r"(?P<method>[A-Za-z_]\w*)\s*\((?P<args>.*?)\)\s*\)"
)
_STATIC_ALIAS_FIELD = re.compile(
    r"\b(?P<alias>[A-Za-z_]\w*)\s*->\s*(?P<field>[A-Za-z_]\w*)"
)
_POST_INCREMENT = re.compile(r"\b(?P<name>[A-Za-z_]\w*)\s*\+\+")
_CONTAINS = re.compile(
    r"\b(?P<left>[A-Za-z_]\w*)\s+\$\s+"
    r"(?P<right>'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\")"
)
_MULTI_INDEX = re.compile(
    r"\b(?P<array>[A-Za-z_]\w*)\[\s*(?P<first>[A-Za-z_]\w*|\d+)\s*,\s*"
    r"(?P<second>[A-Za-z_]\w*|\d+)\s*\]"
)


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
    while re.search(r",\s*,", line):
        line = re.sub(r",\s*,", ", NIL,", line)
    line = re.sub(r"\bIf\s*\(", "IIf(", line, flags=re.IGNORECASE)
    line = _MULTI_INDEX.sub(
        lambda match: (
            f"{match.group('array')}[{match.group('first')}]"
            f"[{match.group('second')}]"
        ),
        line,
    )
    line = _CONTAINS.sub(
        lambda match: (
            f"TestLabContains({match.group('left')}, {match.group('right')})"
        ),
        line,
    )
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
    line = _STATIC_ALIAS_CALL.sub(
        lambda match: (
            f"TestLabStaticAliasCall('{match.group('alias')}', "
            f"'{match.group('method')}'"
            + (f", {match.group('args')}" if match.group("args").strip() else "")
            + ")"
        ),
        line,
    )
    line = _STATIC_ALIAS_FIELD.sub(
        lambda match: (
            f"TestLabAliasField('{match.group('alias')}', "
            f"'{match.group('field')}')"
        ),
        line,
    )
    line = _POST_INCREMENT.sub(r"\g<name> += 1", line)
    return _replace_advpl_operators(line)


def adapt_headless_ui(source):
    lines = []
    source_lines = source.splitlines()
    index = 0
    while index < len(source_lines):
        line = source_lines[index]
        dialog = _DEFINE_MSDIALOG.match(line)
        option = _ADD_OPTION.match(line)
        multiget = _TMULTIGET_ASSIGN.match(line)
        if re.match(r"^\s*DEFINE\s+MSDIALOG\b", line, re.IGNORECASE):
            title_line = line
            if line.rstrip().endswith(";") and index + 1 < len(source_lines):
                title_line = line.rstrip()[:-1] + " " + source_lines[index + 1]
            dialog = _DEFINE_MSDIALOG.match(title_line)
        if dialog:
            lines.append(
                f"{dialog.group('indent')}TestLabMSDialog("
                f"{_adapt_advpl_line(dialog.group('title'))})"
            )
            if title_line != line:
                lines.append("")
                index += 1
        elif option:
            lines.append(
                f"{option.group('indent')}AAdd({option.group('menu')}, "
                f"{{{option.group('title')}, {option.group('action')}, "
                f"{option.group('operation')}, {option.group('access')}}})"
            )
        elif _UI_CONTROL.match(line):
            indent = line[: len(line) - len(line.lstrip())]
            lines.append(f"{indent}TestLabNoOp()")
            while line.rstrip().endswith(";") and index + 1 < len(source_lines):
                index += 1
                line = source_lines[index]
                lines.append("")
        elif multiget:
            lines.append(
                f"{multiget.group('indent')}{multiget.group('target')} := TestLabNoOp()"
            )
            while line.rstrip().endswith(";") and index + 1 < len(source_lines):
                index += 1
                line = source_lines[index]
                lines.append("")
        elif _ACTIVATE_DIALOG.match(line) or _ACTIVATE_MSDIALOG.match(line):
            indent = line[: len(line) - len(line.lstrip())]
            lines.append(f"{indent}TestLabActivateDialog()")
        elif _BEGIN_TRANSACTION.match(line):
            lines.append(f"{line[:len(line) - len(line.lstrip())]}TestLabBeginTransaction()")
        elif _END_TRANSACTION.match(line):
            lines.append(f"{line[:len(line) - len(line.lstrip())]}TestLabEndTransaction()")
        elif environment := _PREPARE_ENVIRONMENT.match(line):
            lines.append(
                f"{environment.group('indent')}TestLabPrepareEnvironment("
                f"{environment.group('company')}, {environment.group('branch')})"
            )
        elif _RESET_ENVIRONMENT.match(line):
            lines.append(f"{line[:len(line) - len(line.lstrip())]}TestLabResetEnvironment()")
        else:
            lines.append(_adapt_advpl_line(line))
        index += 1
    return "\n".join(lines)


def prepare_source(source):
    lines_with_placeholders = []
    for line in source.splitlines():
        lines_with_placeholders.append(line)
        if line.lstrip().startswith("#"):
            lines_with_placeholders.append("")
    preprocessed = preprocess("\n".join(lines_with_placeholders))
    return adapt_headless_ui(preprocessed)


def compile_sources(source_units, fixture=None, name_profile="modern"):
    fixture = fixture or Fixture()
    parsed_units = []
    for source_name, source in source_units:
        try:
            program = parse_source(prepare_source(source))
        except (ParseError, LexError) as exc:
            raise SourceUnitError(source_name, source, exc) from exc
        parsed_units.append((source_name, source, program))

    combined = Program(
        [function for _, _, program in parsed_units for function in program.functions],
        [class_ for _, _, program in parsed_units for class_ in program.classes],
        [method for _, _, program in parsed_units for method in program.methods],
    )
    supported_runtime = FixtureInterpreter(
        combined, fixture=fixture, name_profile=name_profile
    )
    allowed_functions = set(supported_runtime.builtins) | set(fixture.funcoes)
    allowed_functions.update(
        function.name.upper() for function in combined.functions
    )
    allowed_functions.update(
        f"U_{function.name.upper()}" for function in combined.functions
    )
    allowed_functions.update(class_.name.upper() for class_ in combined.classes)
    allowed_globals = set(supported_runtime.globals)
    for alias_name, table in fixture.tabelas.items():
        if isinstance(table, dict):
            allowed_globals.update(
                field["nome"].upper() for field in table.get("campos", [])
                if "nome" in field
            )
    declared_privates = private_names(combined)
    user_functions = {
        function.name for function in combined.functions
        if function.kind == "USER"
    }
    for source_name, source, program in parsed_units:
        try:
            validate_program(
                program,
                source,
                allowed_globals=allowed_globals,
                allowed_functions=allowed_functions,
                allowed_privates=declared_privates,
                name_profile=name_profile,
            )
            validate_mvc_metadata(
                program, source, fixture, user_functions,
                name_profile=name_profile,
            )
        except SemanticError as exc:
            raise SourceUnitError(source_name, source, exc) from exc
    return combined


def compile_source(source, fixture=None, name_profile="modern"):
    try:
        return compile_sources(
            [("<memoria>", source)], fixture=fixture, name_profile=name_profile
        )
    except SourceUnitError as exc:
        raise exc.original from exc


def build_interpreter(
    source,
    fixture=None,
    entry="MAIN",
    source_name="<memoria>",
    name_profile="modern",
):
    fixture = fixture or Fixture()
    program = compile_source(source, fixture=fixture, name_profile=name_profile)
    return FixtureInterpreter(
        program,
        fixture=fixture,
        source_name=source_name,
        entry_name=entry,
        name_profile=name_profile,
    )


def build_interpreter_sources(
    source_units,
    fixture=None,
    entry="MAIN",
    source_name="<memoria>",
    name_profile="modern",
):
    fixture = fixture or Fixture()
    program = compile_sources(
        source_units, fixture=fixture, name_profile=name_profile
    )
    return FixtureInterpreter(
        program,
        fixture=fixture,
        source_name=source_name,
        entry_name=entry,
        name_profile=name_profile,
    )


def run_source(source, fixture=None, entry="MAIN", args=None,
               source_name="<memoria>", name_profile="modern"):
    interpreter = build_interpreter(
        source,
        fixture=fixture,
        entry=entry,
        source_name=source_name,
        name_profile=name_profile,
    )
    return interpreter.run(entry, args)


def run_sources(
    source_units,
    fixture=None,
    entry="MAIN",
    args=None,
    source_name="<memoria>",
    name_profile="modern",
    mvc_case=None,
    state_path=None,
):
    interpreter = build_interpreter_sources(
        source_units,
        fixture=fixture,
        entry=entry,
        source_name=source_name,
        name_profile=name_profile,
    )
    if state_path is not None:
        for alias, records in load_state(state_path, interpreter.fixture.tabelas).items():
            interpreter._aliases[alias].records = copy.deepcopy(records)
            interpreter._aliases[alias].position = 0
        initial_records = {
            alias: copy.deepcopy(interpreter._aliases[alias].records)
            for alias in interpreter.fixture.tabelas
        }
    if mvc_case is not None:
        if mvc_case not in interpreter.fixture.cenarios_mvc:
            raise FixtureError(f"Cenario MVC '{mvc_case}' nao encontrado na fixture")
        interpreter.mvc_case = interpreter.fixture.cenarios_mvc[mvc_case]
    result = interpreter.run(entry, args)
    if mvc_case is not None:
        if interpreter.mvc_result is None:
            raise FixtureError(f"Cenario MVC '{mvc_case}' nao foi executado: entrada nao ativou browse")
        result = interpreter.mvc_result
    if state_path is not None:
        final_records = {
            alias: interpreter._aliases[alias].records
            for alias in interpreter.fixture.tabelas
        }
        if final_records != initial_records:
            save_state(state_path, final_records)
    return result


def run_file(source_path, fixture_path, entry="MAIN", args=None,
             name_profile="modern"):
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
        name_profile=name_profile,
    )
