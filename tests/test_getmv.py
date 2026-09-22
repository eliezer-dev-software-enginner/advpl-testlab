import contextlib
import io
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fixture_runtime import (
    AdvPLRuntimeError,
    Fixture,
    FixtureError,
    run_file,
    run_source,
)


class GetMVTests(unittest.TestCase):
    def test_example_runs_end_to_end(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = run_file(
                PROJECT_ROOT / "examples" / "getmv.prw",
                PROJECT_ROOT / "fixtures" / "getmv.json",
                entry="ex",
            )
        self.assertIsNone(result)
        self.assertEqual("000007\n", output.getvalue())

    def test_parameter_name_is_case_insensitive(self):
        fixture = Fixture.from_dict(
            {"parametros": [{"mv_admin": "000007"}]}
        )
        result = run_source(
            'Function Main()\nReturn GetMV("MV_ADMIN")',
            fixture=fixture,
        )
        self.assertEqual("000007", result)

    def test_missing_parameter_has_clear_error(self):
        with self.assertRaisesRegex(
            AdvPLRuntimeError,
            "GetMV: parametro 'MV_INEXISTENTE' nao encontrado no fixture",
        ):
            run_source(
                'Function Main()\nReturn GetMV("MV_INEXISTENTE")',
                fixture=Fixture(),
            )

    def test_parameters_use_canonical_list_format(self):
        fixture = Fixture.from_dict(
            {
                "parametros": [
                    {"MV_ADMIN": "000007"},
                    {"MV_ATIVO": True},
                ]
            }
        )
        self.assertEqual("000007", fixture.parametros["MV_ADMIN"])
        self.assertIs(True, fixture.parametros["MV_ATIVO"])

    def test_tables_use_canonical_list_with_alias_objects(self):
        fixture = Fixture.from_dict(
            {
                "tabelas": [
                    {
                        "SB1": {
                            "registros": [
                                {"B1_COD": "000001", "B1_DESC": "Produto"}
                            ]
                        }
                    },
                    {"SA1": {"registros": [], "metadados": {}}},
                ]
            }
        )
        self.assertEqual("000001", fixture.tabelas["SB1"]["registros"][0]["B1_COD"])
        self.assertEqual([], fixture.tabelas["SA1"]["registros"])

    def test_fixture_rejects_invalid_parameter_list_entry(self):
        with self.assertRaisesRegex(
            FixtureError,
            "Cada item de 'parametros' deve conter exatamente um parametro",
        ):
            Fixture.from_dict({"parametros": [{"MV_A": 1, "MV_B": 2}]})

    def test_fixture_rejects_duplicate_parameter(self):
        with self.assertRaisesRegex(FixtureError, "Parametro duplicado: 'MV_ADMIN'"):
            Fixture.from_dict(
                {"parametros": [{"MV_ADMIN": "1"}, {"mv_admin": "2"}]}
            )

    def test_fixture_rejects_table_without_records_list(self):
        with self.assertRaisesRegex(
            FixtureError,
            "Tabela 'SB1' deve possuir 'registros' como lista",
        ):
            Fixture.from_dict({"tabelas": [{"SB1": {"registros": {}}}]})

    def test_legacy_object_format_remains_compatible(self):
        fixture = Fixture.from_dict(
            {
                "parametros": {"MV_ADMIN": "000007"},
                "tabelas": {"SB1": []},
            }
        )
        self.assertEqual("000007", fixture.parametros["MV_ADMIN"])
        self.assertEqual([], fixture.tabelas["SB1"])


if __name__ == "__main__":
    unittest.main()
