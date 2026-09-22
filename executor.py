import re
from pathlib import Path

from diagnostics import SourceValidationError
from fixture_runtime import (
    Fixture,
    FixtureError,
    SourceUnitError,
    compile_sources,
    run_source,
    run_sources,
)
from lexer import LexError
from parser import ParseError
from semantic import SemanticError


_USER_FUNCTION = re.compile(
    r"(?im)^\s*user\s+function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("
)
_USE_PRW = re.compile(
    r"(?im)^\s*//\s*usePrw\s*\(\s*(['\"])([^'\"]+)\1\s*\)\s*$"
)


def _read_source(source_path):
    raw = Path(source_path).read_bytes()
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252")


def discover_source_units(source_path):
    root_source = Path(source_path).resolve()
    root_directory = root_source.parent
    units = []
    visited = set()

    def visit(current_path):
        resolved = Path(current_path).resolve()
        if resolved in visited:
            return
        if not resolved.is_file():
            raise FixtureError(f"Fonte PRW nao encontrado: '{resolved}'")
        visited.add(resolved)
        source = _read_source(resolved)
        units.append((resolved, source))

        for match in _USE_PRW.finditer(source):
            reference = match.group(2)
            dependency = (resolved.parent / reference).resolve()
            if dependency.suffix.lower() != ".prw":
                raise FixtureError(
                    f"usePrw em '{resolved.name}' deve referenciar um arquivo .prw: "
                    f"'{reference}'"
                )
            if not dependency.is_relative_to(root_directory):
                raise FixtureError(
                    f"usePrw em '{resolved.name}' deve permanecer no diretorio "
                    f"do fonte principal: '{reference}'"
                )
            if not dependency.is_file():
                raise FixtureError(
                    f"usePrw em '{resolved.name}': fonte nao encontrado "
                    f"'{reference}'"
                )
            visit(dependency)

    visit(root_source)
    return units


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


def execute_file(source_path, fixture_path=None, entry=None, args=None):
    source_path = Path(source_path).resolve()
    if not source_path.is_file():
        raise FixtureError(f"Fonte PRW nao encontrado: '{source_path}'")
    fixture_path = Path(fixture_path).resolve() if fixture_path else discover_fixture(source_path)
    source_units = discover_source_units(source_path)
    source = source_units[0][1]
    fixture = Fixture.from_file(fixture_path)
    try:
        entry = entry or discover_entry(source)
        return run_sources(
            source_units,
            fixture=fixture,
            entry=entry,
            args=args,
            source_name=source_path,
        )
    except SourceUnitError as exc:
        raise SourceValidationError(
            exc.source_name,
            exc.source,
            exc.original,
        ) from exc
    except (ParseError, LexError, SemanticError) as exc:
        raise SourceValidationError(source_path, source, exc) from exc


def validate_file(source_path, fixture_path=None):
    source_path = Path(source_path).resolve()
    if not source_path.is_file():
        raise FixtureError(f"Fonte PRW nao encontrado: '{source_path}'")
    if fixture_path:
        fixture = Fixture.from_file(Path(fixture_path).resolve())
    else:
        try:
            discovered_fixture = discover_fixture(source_path)
        except FixtureError:
            fixture = Fixture()
        else:
            fixture = Fixture.from_file(discovered_fixture)
    source_units = discover_source_units(source_path)
    source = source_units[0][1]
    try:
        program = compile_sources(source_units, fixture=fixture)
    except SourceUnitError as exc:
        raise SourceValidationError(
            exc.source_name,
            exc.source,
            exc.original,
        ) from exc
    except (ParseError, LexError, SemanticError) as exc:
        raise SourceValidationError(source_path, source, exc) from exc
    return len(program.functions)
