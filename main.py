import argparse
import json
import sys

from diagnostics import SourceValidationError, print_diagnostic
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
    parser.add_argument("--fixture", help="fixture JSON/JSONC (padrao: advpl-testlab.jsonc ou .json)")
    parser.add_argument("--entry", help="User Function de entrada")
    parser.add_argument(
        "--args-json",
        help='argumentos da entrada como array JSON, por exemplo: ["ENVIO"]',
    )
    args = parser.parse_args(argv)
    try:
        if args.validate_source:
            function_count = validate_file(
                args.validate_source,
                fixture_path=args.fixture,
            )
            print(
                f"[OK] Sintaxe valida: {args.validate_source} "
                f"({function_count} funcao(oes))"
            )
        else:
            entry_args = []
            if args.args_json is not None:
                try:
                    entry_args = json.loads(args.args_json)
                except json.JSONDecodeError as exc:
                    raise FixtureError(
                        f"--args-json invalido: {exc.msg}"
                    ) from exc
                if not isinstance(entry_args, list):
                    raise FixtureError("--args-json deve ser um array JSON")
            execute_file(
                args.source,
                fixture_path=args.fixture,
                entry=args.entry,
                args=entry_args,
            )
    except (
        FixtureError,
        SourceValidationError,
        ParseError,
        LexError,
        AdvPLRuntimeError,
        OSError,
    ) as exc:
        print_diagnostic(exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
