import os
import re
import shutil
import subprocess
import tempfile
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


def discover_source_units(source_path, dependencies_first=False):
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
        if not dependencies_first:
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

        if dependencies_first:
            units.append((resolved, source))

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
        for name in (
            "mock.json",
            "testlab.jsonc", "testlab.json",
            "advpl-testlab.jsonc", "advpl-testlab.json",
        ):
            candidate = directory / name
            if candidate.is_file():
                return candidate
    raise FixtureError(
        "Fixture nao encontrado. Crie 'mock.json' no diretorio do fonte "
        "ou em um diretorio pai, ou informe --fixture."
    )


def execute_source(source, fixture, entry=None, source_name="<memoria>",
                   name_profile="modern"):
    entry = entry or discover_entry(source)
    return run_source(
        source,
        fixture=fixture,
        entry=entry,
        source_name=source_name,
        name_profile=name_profile,
    )


def execute_file(source_path, fixture_path=None, entry=None, args=None,
                 name_profile="modern", mvc_case=None, persist=False):
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
            name_profile=name_profile,
            mvc_case=mvc_case,
            state_path=fixture_path.parent / "state.json" if persist else None,
        )
    except SourceUnitError as exc:
        raise SourceValidationError(
            exc.source_name,
            exc.source,
            exc.original,
        ) from exc
    except (ParseError, LexError, SemanticError) as exc:
        raise SourceValidationError(source_path, source, exc) from exc


def validate_file(source_path, fixture_path=None, name_profile="modern"):
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
        program = compile_sources(
            source_units, fixture=fixture, name_profile=name_profile
        )
    except SourceUnitError as exc:
        raise SourceValidationError(
            exc.source_name,
            exc.source,
            exc.original,
        ) from exc
    except (ParseError, LexError, SemanticError) as exc:
        raise SourceValidationError(source_path, source, exc) from exc
    return len(program.functions)


class CompileError(Exception):
    pass


def ordered_sources(source_path, compile_order=None):
    source_path = Path(source_path).resolve()
    units = discover_source_units(source_path, dependencies_first=True)
    paths = [path for path, _ in units]
    if compile_order is None:
        return paths

    root_directory = source_path.parent
    by_relative_name = {
        path.relative_to(root_directory).as_posix().casefold(): path
        for path in paths
    }
    names = [name.strip().replace("\\", "/").casefold()
             for name in compile_order.split(",")]
    if not names or any(not name for name in names):
        raise CompileError("--compile-order deve listar todos os arquivos .prw")
    if len(names) != len(set(names)) or set(names) != set(by_relative_name):
        raise CompileError(
            "--compile-order deve listar cada fonte do grafo usePrw "
            "exatamente uma vez: " + ", ".join(by_relative_name)
        )
    return [by_relative_name[name] for name in names]


def find_tds_cli(explicit_path=None):
    if explicit_path:
        candidate = Path(explicit_path).resolve()
        if not candidate.is_file():
            raise CompileError(f"TDS-CLI nao encontrado: '{candidate}'")
        return candidate

    executable = "advpls.exe" if os.name == "nt" else "advpls"
    on_path = shutil.which(executable)
    if on_path:
        return Path(on_path).resolve()

    extension_roots = (
        Path.home() / ".vscode" / "extensions",
        Path.home() / ".vscode-insiders" / "extensions",
    )
    candidates = []
    for extension_root in extension_roots:
        if extension_root.is_dir():
            candidates.extend(extension_root.glob(
                f"totvs.tds-vscode-*/node_modules/@totvs/tds-ls/bin/windows/{executable}"
            ))
    if candidates:
        return sorted(candidates)[-1].resolve()
    raise CompileError(
        "TDS-CLI nao encontrado. Informe --tds-cli com o caminho do advpls.exe."
    )


def _read_authentication(config_path):
    path = Path(config_path).resolve()
    if not path.is_file():
        raise CompileError(f"Configuracao TDS-CLI nao encontrada: '{path}'")
    content = path.read_text(encoding="cp1252")
    sections = re.findall(r"(?im)^\s*\[([^]]+)\]\s*$", content)
    section_names = [section.casefold() for section in sections]
    if "authentication" not in section_names:
        raise CompileError("--tds-config precisa conter [authentication]")
    if any(section not in {"user", "authentication", "authorization"}
           for section in section_names):
        raise CompileError(
            "--tds-config aceita somente [user], [authentication] e [authorization]"
        )
    actions = re.findall(r"(?im)^\s*action\s*=\s*(\S+)\s*$", content)
    if any(action.casefold() not in {"authentication", "authorization"}
           for action in actions):
        raise CompileError("--tds-config contem uma acao nao permitida")
    if not re.search(r"(?im)^\s*action\s*=\s*authentication\s*$", content):
        raise CompileError("--tds-config precisa definir action=authentication")
    return content.rstrip() + "\r\n"


def compile_source_tree(source_path, *, config_path, includes, cli_path=None,
                        compile_order=None):
    paths = ordered_sources(source_path, compile_order)
    include_paths = [Path(item).resolve() for item in includes]
    if not include_paths:
        raise CompileError("Informe ao menos um diretorio com --include")
    for include_path in include_paths:
        if not include_path.is_dir():
            raise CompileError(f"Diretorio de includes nao encontrado: '{include_path}'")
        if ";" in str(include_path) or "\n" in str(include_path):
            raise CompileError(f"Caminho de include invalido: '{include_path}'")

    cli = find_tds_cli(cli_path)
    authentication = _read_authentication(config_path)
    with tempfile.TemporaryDirectory(prefix="advpl-testlab-compile-") as temp_dir:
        directory = Path(temp_dir)
        program_list = directory / "programs.txt"
        script = directory / "compile.ini"
        program_list.write_bytes(
            ("\r\n".join(path.as_posix() for path in paths) + "\r\n").encode("cp1252")
        )
        script_text = (
            "showConsoleOutput=true\r\n" + authentication
            + "\r\n[compile]\r\n"
            + "action=compile\r\n"
            + f"programList={program_list.as_posix()}\r\n"
            + "recompile=T\r\n"
            + "includes=" + ";".join(path.as_posix() for path in include_paths) + "\r\n"
        )
        script.write_bytes(script_text.encode("cp1252"))
        result = subprocess.run([str(cli), "cli", str(script)], check=False)
    if result.returncode:
        raise CompileError(f"TDS-CLI falhou (codigo {result.returncode})")
    return paths
