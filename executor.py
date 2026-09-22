import re
from pathlib import Path

from diagnostics import SourceValidationError
from fixture_runtime import Fixture, FixtureError, compile_source, run_source
from lexer import LexError
from parser import ParseError
from semantic import SemanticError


_USER_FUNCTION = re.compile(
    r"(?im)^\s*user\s+function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("
)
def discover_entry(source):
    match = _USER_FUNCTION.search(source)
    if not match:
        raise FixtureError("Nenhuma 'User Function' foi encontrada no fonte")
    return match.group(1)


def discover_fixture(source_path):
    source_path = Path(source_path).resolve()
    for directory in (source_path.parent, *source_path.parents):
        candidate = directory / "advpl-testlab.json"
        if candidate.is_file():
            return candidate
    raise FixtureError(
        "Fixture nao encontrado. Crie 'advpl-testlab.json' no diretorio do fonte "
        "ou em um diretorio pai, ou informe --fixture."
    )


def execute_source(source, fixture, entry=None, source_name="<memoria>"):
    entry = entry or discover_entry(source)
    return run_source(
        source,
        fixture=fixture,
        entry=entry,
        source_name=source_name,
    )


def execute_file(source_path, fixture_path=None, entry=None):
    source_path = Path(source_path).resolve()
    if not source_path.is_file():
        raise FixtureError(f"Fonte PRW nao encontrado: '{source_path}'")
    fixture_path = Path(fixture_path).resolve() if fixture_path else discover_fixture(source_path)
    with source_path.open(encoding="utf-8", errors="replace") as source_file:
        source = source_file.read()
    fixture = Fixture.from_file(fixture_path)
    try:
        return execute_source(
            source,
            fixture=fixture,
            entry=entry,
            source_name=source_path,
        )
    except (ParseError, LexError, SemanticError) as exc:
        raise SourceValidationError(source_path, source, exc) from exc


def validate_file(source_path):
    source_path = Path(source_path).resolve()
    if not source_path.is_file():
        raise FixtureError(f"Fonte PRW nao encontrado: '{source_path}'")
    with source_path.open(encoding="utf-8", errors="replace") as source_file:
        source = source_file.read()
    try:
        program = compile_source(source)
    except (ParseError, LexError, SemanticError) as exc:
        raise SourceValidationError(source_path, source, exc) from exc
    return len(program.functions)
