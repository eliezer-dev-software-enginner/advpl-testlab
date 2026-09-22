import argparse
import sys

from executor import execute_file, validate_file
from fixture_runtime import FixtureError
from interpreter import AdvPLRuntimeError
from lexer import LexError
from parser import ParseError


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="advpl-testlab",
        description="Executa fontes AdvPL com fixtures JSON, sem Protheus.",
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("-run", "--run", dest="source", metavar="ARQUIVO.PRW")
    action.add_argument(
        "-validate",
        "--validate",
        dest="validate_source",
        metavar="ARQUIVO.PRW",
        help="valida todo o fonte sem executar a funcao de entrada",
    )
    parser.add_argument("--fixture", help="fixture JSON (padrao: advpl-testlab.json)")
    parser.add_argument("--entry", help="User Function de entrada")
    args = parser.parse_args(argv)
    try:
        if args.validate_source:
            function_count = validate_file(args.validate_source)
            print(
                f"[OK] Sintaxe valida: {args.validate_source} "
                f"({function_count} funcao(oes))"
            )
        else:
            execute_file(args.source, fixture_path=args.fixture, entry=args.entry)
    except (FixtureError, ParseError, LexError, AdvPLRuntimeError, OSError) as exc:
        print(f"[ERRO] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
