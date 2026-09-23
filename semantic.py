import re

from naming import NamePolicy
from parser import Assign, BlockLiteral, Call, ForLoop, Identifier, SequenceStmt, VarDecl


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


def _source_location(source, name):
    pattern = re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE)
    for line_number, line in enumerate(source.splitlines(), start=1):
        match = pattern.search(line)
        if match:
            return line_number, match.start() + 1
    return None, None


def validate_program(
    program,
    source,
    allowed_globals=None,
    allowed_functions=None,
    name_profile="modern",
):
    policy = NamePolicy(name_profile)
    globals_ = {policy.key(name) for name in _DEFAULT_GLOBALS}
    globals_.update(_public_names(program, policy))
    globals_.update(policy.key(name) for name in (allowed_globals or ()))
    functions = {policy.key(function.name) for function in program.functions}
    functions.update(policy.key(class_.name) for class_ in program.classes)
    functions.update(policy.key(name) for name in (allowed_functions or ()))

    callables = list(program.functions) + list(program.methods)
    for callable_decl in callables:
        declared = _declared_names(callable_decl, policy) | globals_
        for node in _walk(callable_decl.body):
            if isinstance(node, Identifier):
                if policy.key(node.name) in declared:
                    continue
                line, column = _source_location(source, node.name)
                raise SemanticError(
                    f"Variável '{node.name}' não declarada",
                    line=line,
                    column=column,
                )
            if isinstance(node, Call) and policy.key(node.name) not in functions:
                line, column = _source_location(source, node.name)
                raise SemanticError(
                    f"Função '{node.name}' não encontrada",
                    line=line,
                    column=column,
                )
