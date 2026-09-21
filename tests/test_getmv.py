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
        fixture = Fixture.from_dict({"parametros": {"mv_admin": "000007"}})
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

    def test_fixture_rejects_invalid_parameters_shape(self):
        with self.assertRaisesRegex(FixtureError, "'parametros' deve ser um objeto"):
            Fixture.from_dict({"parametros": []})

    def test_table_can_be_list_or_future_metadata_object(self):
        fixture = Fixture.from_dict(
            {
                "tabelas": {
                    "SB1": [],
                    "SA1": {"registros": [], "metadados": {}},
                }
            }
        )
        self.assertEqual([], fixture.tabelas["SB1"])
        self.assertEqual([], fixture.tabelas["SA1"]["registros"])


if __name__ == "__main__":
    unittest.main()
