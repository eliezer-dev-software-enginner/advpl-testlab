import argparse
import json
import sys

from diagnostics import SourceValidationError, print_diagnostic
from executor import (
    CompileError, compile_source_tree, execute_file, ordered_sources, validate_file,
)
from fixture_runtime import FixtureError
from interpreter import AdvPLRuntimeError
from lexer import LexError
from naming import NameCollisionError
from parser import ParseError
from state_store import StateError


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
    action.add_argument(
        "-compile", "--compile", dest="compile_source", metavar="ARQUIVO.PRW",
        help="recompila recursivamente no RPO via TDS-CLI oficial",
    )
    parser.add_argument("--fixture", help="fixture JSON/JSONC (padrao: testlab.jsonc ou .json)")
    parser.add_argument("--tds-config", help="INI privado com autenticacao do TDS-CLI (somente -compile)")
    parser.add_argument("--tds-cli", help="caminho do advpls.exe (deteccao automatica por padrao)")
    parser.add_argument("--include", action="append", default=[], help="diretorio de includes; pode repetir")
    parser.add_argument("--compile-order", help="ordem explicita, separada por virgulas, de todos os PRW do grafo")
    parser.add_argument("--dry-run", action="store_true", help="mostra a ordem de compilacao sem acessar o RPO")
    parser.add_argument("--entry", help="User Function de entrada")
    parser.add_argument("--mvc-case", help="cenario MVC nomeado na fixture JSONC (somente -run)")
    parser.add_argument("--persist", action="store_true",
                        help="carrega e salva registros em state.json junto da fixture (somente -run)")
    parser.add_argument(
        "--name-profile", choices=("modern", "legacy10"), default="modern",
        help="regras de identificadores (padrao: modern)",
    )
    parser.add_argument(
        "--args-json",
        help='argumentos da entrada como array JSON, por exemplo: ["ENVIO"]',
    )
    args = parser.parse_args(argv)
    try:
        if args.compile_source:
            if args.fixture or args.entry or args.mvc_case or args.persist or args.args_json:
                raise CompileError("-compile nao aceita opcoes de fixture ou execucao")
            paths = ordered_sources(args.compile_source, args.compile_order)
            for index, path in enumerate(paths, start=1):
                print(f"{index}. {path}")
            if not args.dry_run:
                if not args.tds_config:
                    raise CompileError("-compile requer --tds-config; use --dry-run para ver o plano")
                compile_source_tree(
                    args.compile_source,
                    config_path=args.tds_config,
                    includes=args.include,
                    cli_path=args.tds_cli,
                    compile_order=args.compile_order,
                )
                print(f"[OK] {len(paths)} fonte(s) recompilado(s) no RPO")
        elif args.validate_source:
            if args.tds_config or args.tds_cli or args.include or args.compile_order or args.dry_run:
                raise FixtureError("opcoes de compilacao requerem -compile")
            if args.mvc_case:
                raise FixtureError("--mvc-case requer -run")
            if args.persist:
                raise FixtureError("--persist requer -run")
            function_count = validate_file(
                args.validate_source,
                fixture_path=args.fixture,
                name_profile=args.name_profile,
            )
            print(
                f"[OK] Sintaxe valida: {args.validate_source} "
                f"({function_count} funcao(oes))"
            )
        else:
            if args.tds_config or args.tds_cli or args.include or args.compile_order or args.dry_run:
                raise FixtureError("opcoes de compilacao requerem -compile")
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
                name_profile=args.name_profile,
                mvc_case=args.mvc_case,
                persist=args.persist,
            )
    except (
        FixtureError,
        StateError,
        SourceValidationError,
        ParseError,
        LexError,
        AdvPLRuntimeError,
        NameCollisionError,
        CompileError,
        OSError,
    ) as exc:
        print_diagnostic(exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
