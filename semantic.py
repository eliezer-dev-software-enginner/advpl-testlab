import re

from naming import NamePolicy
from parser import (
    ArrayLiteral, Assign, BlockLiteral, Call, ForLoop, Identifier, Literal,
    MethodCall, SequenceStmt, VarDecl,
)


class SemanticError(Exception):
    diagnostic_label = "SemanticError"

    def __init__(self, message, line=None, column=None):
        self.line = line
        self.column = column
        super().__init__(message)


_DEFAULT_GLOBALS = {"CRLF", "CUSERLOCAL", "SELF"}


def _walk(node):
    if node is None or isinstance(node, (str, int, float, bool)):
        return
    if isinstance(node, (list, tuple)):
        for item in node:
            yield from _walk(item)
        return
    yield node
    for value in vars(node).values():
        yield from _walk(value)


def _declared_names(callable_decl, policy):
    names = {policy.key(name) for name in callable_decl.params}
    for node in _walk(callable_decl.body):
        if isinstance(node, VarDecl):
            names.add(policy.key(node.name))
        elif isinstance(node, ForLoop):
            names.add(policy.key(node.var))
        elif isinstance(node, SequenceStmt) and node.recover_var:
            names.add(policy.key(node.recover_var))
        elif isinstance(node, BlockLiteral):
            names.update(policy.key(name) for name in node.params)
        elif isinstance(node, Assign) and isinstance(node.target, Identifier):
            # AdvPL/Clipper cria PRIVATE implicitamente em uma atribuicao.
            names.add(policy.key(node.target.name))
    return names


def _public_names(program, policy):
    names = set()
    for node in _walk(program):
        if isinstance(node, VarDecl) and node.kind.upper() == "PUBLIC":
            names.add(policy.key(node.name))
    return names


def private_names(program):
    return {
        node.name for node in _walk(program)
        if isinstance(node, VarDecl) and node.kind.upper() == "PRIVATE"
    }


def mvc_field_names(fixture):
    names = set()
    for table in fixture.tabelas.values():
        if isinstance(table, dict):
            if "campos" in table:
                names.update(
                    str(field["nome"]).upper()
                    for field in table["campos"]
                    if isinstance(field, dict) and "nome" in field
                )
                continue
            records = table.get("registros", [])
        else:
            records = table
        for record in records:
            if isinstance(record, dict):
                names.update(str(name).upper() for name in record)
    return names


def _source_location(source, name, line_hint=None):
    pattern = re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE)
    source_lines = source.splitlines()
    if line_hint is not None and 1 <= line_hint <= len(source_lines):
        match = pattern.search(source_lines[line_hint - 1])
        if match:
            return line_hint, match.start() + 1
    for line_number, line in enumerate(source_lines, start=1):
        match = pattern.search(line)
        if match:
            return line_number, match.start() + 1
    return None, None


def _validate_declaration_order(callable_decl, source):
    rank = {"LOCAL": 0, "STATIC": 0, "PRIVATE": 1, "PUBLIC": 2}
    current_rank = 0
    executable_started = False
    for statement in callable_decl.body:
        declarations = statement if isinstance(statement, list) else [statement]
        if not declarations or not all(isinstance(item, VarDecl) for item in declarations):
            executable_started = True
            for node in _walk(statement):
                if isinstance(node, VarDecl):
                    line, column = _source_location(source, node.kind, node.line)
                    raise SemanticError(
                        f"Declaração {node.kind} deve ficar no início da função, "
                        "antes dos comandos executáveis",
                        line=line, column=column,
                    )
            continue
        for declaration in declarations:
            line, column = _source_location(
                source, declaration.kind, declaration.line
            )
            if executable_started:
                raise SemanticError(
                    f"Declaração {declaration.kind} deve ficar no início da função, "
                    "antes dos comandos executáveis",
                    line=line, column=column,
                )
            if rank[declaration.kind] < current_rank:
                raise SemanticError(
                    f"Declaração {declaration.kind} fora de ordem: use "
                    "LOCAL/STATIC, depois PRIVATE, depois PUBLIC",
                    line=line, column=column,
                )
            current_rank = rank[declaration.kind]


def validate_program(
    program,
    source,
    allowed_globals=None,
    allowed_functions=None,
    allowed_privates=None,
    name_profile="modern",
):
    policy = NamePolicy(name_profile)
    globals_ = {policy.key(name) for name in _DEFAULT_GLOBALS}
    globals_.update(_public_names(program, policy))
    globals_.update(policy.key(name) for name in private_names(program))
    globals_.update(policy.key(name) for name in (allowed_privates or ()))
    globals_.update(policy.key(name) for name in (allowed_globals or ()))
    functions = {policy.key(function.name) for function in program.functions}
    functions.update(policy.key(class_.name) for class_ in program.classes)
    functions.update(policy.key(name) for name in (allowed_functions or ()))

    callables = list(program.functions) + list(program.methods)
    for callable_decl in callables:
        _validate_declaration_order(callable_decl, source)
        declared = _declared_names(callable_decl, policy) | globals_
        for node in _walk(callable_decl.body):
            if isinstance(node, Identifier):
                if policy.key(node.name) in declared:
                    continue
                line, column = _source_location(source, node.name, getattr(node, "line", None))
                raise SemanticError(
                    f"Variável '{node.name}' não declarada",
                    line=line,
                    column=column,
                )
            if isinstance(node, Call) and policy.key(node.name) not in functions:
                line, column = _source_location(source, node.name, getattr(node, "line", None))
                raise SemanticError(
                    f"Função '{node.name}' não encontrada",
                    line=line,
                    column=column,
                )


def validate_mvc_metadata(program, source, fixture, user_functions,
                          name_profile="modern"):
    policy = NamePolicy(name_profile)
    modules = {policy.key(name) for name in user_functions}
    user_actions = {policy.user_symbol(name) for name in user_functions}
    user_actions.update(policy.key(name) for name in fixture.funcoes)
    fields = mvc_field_names(fixture)
    lines = source.splitlines()
    model_ids = set()
    has_dynamic_model_id = False
    for node in _walk(program):
        if not isinstance(node, MethodCall) or node.name.upper() not in ("ADDFIELDS", "ADDGRID"):
            continue
        if node.args and isinstance(node.args[0], Literal) and isinstance(node.args[0].value, str):
            model_ids.add(node.args[0].value.upper())
        else:
            has_dynamic_model_id = True
    for callable_decl in (*program.functions, *program.methods):
        for node in _walk(callable_decl.body):
            line_number = getattr(node, "line", None)
            if isinstance(node, Call) and node.name.upper() == "AADD":
                if not (line_number and line_number <= len(lines)
                        and lines[line_number - 1].lstrip().upper().startswith("ADD OPTION")):
                    continue
                if len(node.args) < 2 or not isinstance(node.args[1], ArrayLiteral):
                    continue
                items = node.args[1].elements
                if len(items) < 2 or not isinstance(items[1], Literal):
                    continue
                action = items[1].value
                if not isinstance(action, str):
                    continue
                if action.upper().startswith("VIEWDEF."):
                    module = action.split(".", 1)[1]
                    if policy.key(module) in modules:
                        continue
                    line, column = _source_location(source, action, line_number)
                    raise SemanticError(
                        f"Ação MVC '{action}' referencia User Function '{module}' inexistente",
                        line=line, column=column,
                    )
                user_action = re.fullmatch(
                    r"(U_[A-Za-z_][A-Za-z_0-9]*)(?:\(\))?", action.strip(), re.IGNORECASE
                )
                if user_action and policy.key(user_action.group(1)) not in user_actions:
                    line, column = _source_location(source, user_action.group(1), line_number)
                    raise SemanticError(
                        f"Acao de menu '{action}' referencia User Function "
                        f"'{user_action.group(1)[2:]}' inexistente",
                        line=line, column=column,
                    )
            if isinstance(node, MethodCall) and node.name.upper() == "SETPRIMARYKEY":
                if not node.args or not isinstance(node.args[0], ArrayLiteral):
                    continue
                for item in node.args[0].elements:
                    if not isinstance(item, Literal) or not isinstance(item.value, str):
                        continue
                    if item.value.upper() not in fields:
                        line, column = _source_location(
                            source, item.value, getattr(item, "line", line_number)
                        )
                        raise SemanticError(
                            f"Campo '{item.value}' de SetPrimaryKey não existe na fixture",
                            line=line, column=column,
                        )
            if (isinstance(node, MethodCall) and node.name.upper() == "GETVALUE"
                    and model_ids and not has_dynamic_model_id
                    and len(node.args) == 2 and isinstance(node.args[0], Literal)
                    and isinstance(node.args[0].value, str)):
                model_id = node.args[0].value
                if model_id.upper() not in model_ids:
                    line, column = _source_location(
                        source, model_id, getattr(node.args[0], "line", line_number)
                    )
                    raise SemanticError(
                        f"GetValue referencia submodelo '{model_id}' nao declarado por AddFields/AddGrid",
                        line=line, column=column,
                    )
