import re

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


def _declared_names(callable_decl):
    names = {name.upper() for name in callable_decl.params}
    for node in _walk(callable_decl.body):
        if isinstance(node, VarDecl):
            names.add(node.name.upper())
        elif isinstance(node, ForLoop):
            names.add(node.var.upper())
        elif isinstance(node, SequenceStmt) and node.recover_var:
            names.add(node.recover_var.upper())
        elif isinstance(node, BlockLiteral):
            names.update(name.upper() for name in node.params)
        elif isinstance(node, Assign) and isinstance(node.target, Identifier):
            # AdvPL/Clipper cria PRIVATE implicitamente em uma atribuicao.
            names.add(node.target.name.upper())
    return names


def _public_names(program):
    names = set()
    for node in _walk(program):
        if isinstance(node, VarDecl) and node.kind.upper() == "PUBLIC":
            names.add(node.name.upper())
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
):
    globals_ = set(_DEFAULT_GLOBALS)
    globals_.update(_public_names(program))
    globals_.update(name.upper() for name in (allowed_globals or ()))
    functions = {function.name.upper() for function in program.functions}
    functions.update(class_.name.upper() for class_ in program.classes)
    functions.update(name.upper() for name in (allowed_functions or ()))

    callables = list(program.functions) + list(program.methods)
    for callable_decl in callables:
        declared = _declared_names(callable_decl) | globals_
        for node in _walk(callable_decl.body):
            if isinstance(node, Identifier):
                if node.name.upper() in declared:
                    continue
                line, column = _source_location(source, node.name)
                raise SemanticError(
                    f"Variável '{node.name}' não declarada",
                    line=line,
                    column=column,
                )
            if isinstance(node, Call) and node.name.upper() not in functions:
                line, column = _source_location(source, node.name)
                raise SemanticError(
                    f"Função '{node.name}' não encontrada",
                    line=line,
                    column=column,
                )
