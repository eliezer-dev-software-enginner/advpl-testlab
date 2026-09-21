import sys

from fixture_runtime import FixtureError, run_file
from interpreter import AdvPLRuntimeError
from lexer import LexError
from parser import ParseError


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]
    if len(args) < 2:
        print("Uso: python main.py arquivo.prw fixture.json [FuncaoDeEntrada]")
        print("Ex.: python main.py examples/getmv.prw fixtures/getmv.json ex")
        return 2

    source_path = args[0]
    fixture_path = args[1]
    entry = args[2] if len(args) > 2 else "MAIN"

    try:
        run_file(source_path, fixture_path, entry=entry)
    except (FixtureError, ParseError, LexError, AdvPLRuntimeError, OSError) as exc:
        print(f"[ERRO] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
