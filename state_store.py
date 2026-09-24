import json
import os
import tempfile
from pathlib import Path


class StateError(ValueError):
    pass


def load_state(path, aliases):
    path = Path(path)
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as handle:
            state = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StateError(f"state.json invalido em '{path}': {exc}") from exc
    if not isinstance(state, dict) or state.get("versao") != 1:
        raise StateError(f"state.json em '{path}' deve ter versao 1")
    tables = state.get("tabelas")
    if not isinstance(tables, dict):
        raise StateError(f"state.json em '{path}': 'tabelas' deve ser um objeto")
    for alias, records in tables.items():
        if alias not in aliases:
            raise StateError(f"state.json em '{path}': alias '{alias}' nao existe na fixture")
        if not isinstance(records, list) or not all(
            isinstance(record, dict)
            and all(isinstance(field, str) for field in record)
            for record in records
        ):
            raise StateError(f"state.json em '{path}': registros de '{alias}' invalidos")
    return tables


def save_state(path, tables):
    path = Path(path)
    try:
        encoded = json.dumps(
            {"versao": 1, "tabelas": tables}, ensure_ascii=False, indent=2
        ) + "\n"
    except (TypeError, ValueError) as exc:
        raise StateError(f"state.json nao pode serializar registros: {exc}") from exc
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", suffix=".tmp",
            prefix=".state-", dir=path.parent, delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise StateError(f"Nao foi possivel gravar state.json em '{path}': {exc}") from exc
    finally:
        if temporary is not None and temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass
