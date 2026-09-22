import argparse
import sys

from executor import execute_file
from fixture_runtime import FixtureError
from interpreter import AdvPLRuntimeError
from lexer import LexError
from parser import ParseError


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="advpl-testlab",
        description="Executa fontes AdvPL com fixtures JSON, sem Protheus.",
    )
    parser.add_argument("-run", "--run", dest="source", metavar="ARQUIVO.PRW")
    parser.add_argument("--fixture", help="fixture JSON (padrao: advpl-testlab.json)")
    parser.add_argument("--entry", help="User Function de entrada")
    args = parser.parse_args(argv)
    if not args.source:
        parser.print_help()
        return 2

    try:
        execute_file(args.source, fixture_path=args.fixture, entry=args.entry)
    except (FixtureError, ParseError, LexError, AdvPLRuntimeError, OSError) as exc:
        print(f"[ERRO] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
