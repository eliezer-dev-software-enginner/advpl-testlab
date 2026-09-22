import re
from pathlib import Path

from fixture_runtime import Fixture, FixtureError, run_source


_USER_FUNCTION = re.compile(
    r"(?im)^\s*user\s+function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("
)
_BROWSE_DESCRIPTION = re.compile(
    r"(?i):SetDescription\s*\(\s*(['\"])(.*?)\1\s*\)"
)
_BROWSE_COLUMN = re.compile(
    r"(?i):AddColumn\s*\(\s*(['\"])(.*?)\1\s*,\s*(['\"])(.*?)\3"
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


def _print_browse(source, records):
    description_match = _BROWSE_DESCRIPTION.search(source)
    description = (
        description_match.group(2) if description_match else "Resultado AdvPL"
    )
    columns = [
        (match.group(2), match.group(4))
        for match in _BROWSE_COLUMN.finditer(source)
    ]
    if not columns and records:
        columns = [(name, name) for name in records[0]]

    print(description)
    if not records:
        print("Nenhum registro encontrado.")
        return

    widths = []
    for field, title in columns:
        widths.append(
            max(len(title), *(len(str(row.get(field, ""))) for row in records))
        )

    print(" | ".join(title.ljust(width) for (_, title), width in zip(columns, widths)))
    print("-+-".join("-" * width for width in widths))
    for row in records:
        print(
            " | ".join(
                str(row.get(field, "")).ljust(width)
                for (field, _), width in zip(columns, widths)
            )
        )


def execute_source(source, fixture, entry=None):
    entry = entry or discover_entry(source)

    # Adaptador headless para fontes Protheus que abrem consulta e FWBrowse.
    # A estrutura (entrada, descricao e colunas) continua sendo lida do .prw;
    # apenas SQL/UI externos sao substituidos pelos dados determinísticos.
    if re.search(r"(?i)FWExecStatement\s*\(\s*\)\s*:\s*New", source) and re.search(
        r"(?i)FWBrowse\s*\(\s*\)\s*:\s*New", source
    ):
        if fixture.get_function_result("FASKFILTROS", default=True) is False:
            return None
        records = fixture.get_query_records(entry)
        _print_browse(source, records)
        return None

    # Fontes que usam somente a linguagem coberta pelo LivrePL seguem pelo
    # interpretador completo já existente.
    return run_source(source, fixture=fixture, entry=entry)


def execute_file(source_path, fixture_path=None, entry=None):
    source_path = Path(source_path).resolve()
    if not source_path.is_file():
        raise FixtureError(f"Fonte PRW nao encontrado: '{source_path}'")
    fixture_path = Path(fixture_path).resolve() if fixture_path else discover_fixture(source_path)
    with source_path.open(encoding="utf-8", errors="replace") as source_file:
        source = source_file.read()
    fixture = Fixture.from_file(fixture_path)
    return execute_source(source, fixture=fixture, entry=entry)
