import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from diagnostics import SourceValidationError
from executor import discover_entry, execute_file, validate_file
from fixture_runtime import FixtureError, compile_sources


USE_PRW_MAIN = PROJECT_ROOT / "tests" / "fixtures" / "use_prw" / "principal.prw"
USE_PRW_MISSING = PROJECT_ROOT / "tests" / "fixtures" / "use_prw" / "ausente.prw"
USE_PRW_SCOPE = PROJECT_ROOT / "tests" / "fixtures" / "use_prw" / "entrada_escopo.prw"


class ExecutorTests(unittest.TestCase):
    def test_use_prw_loads_and_executes_local_dependency(self):
        self.assertEqual(2, validate_file(USE_PRW_MAIN))
        self.assertEqual(
            "dependencia carregada",
            execute_file(
                USE_PRW_MAIN,
                fixture_path=PROJECT_ROOT / "fixtures" / "getmv.json",
            ),
        )

    def test_use_prw_reports_missing_local_dependency(self):
        with self.assertRaisesRegex(
            FixtureError,
            "usePrw.*nao encontrado.*inexistente.prw",
        ):
            validate_file(USE_PRW_MISSING)

    def test_discovers_first_user_function_as_entry(self):
        source = """
Static Function Auxiliar()
Return NIL

User Function MinhaRotina()
Return NIL
"""
        self.assertEqual("MinhaRotina", discover_entry(source))

    def test_recursive_validation_rejects_cross_source_static_call(self):
        with self.assertRaises(SourceValidationError) as captured:
            validate_file(USE_PRW_SCOPE)
        self.assertEqual("modulo_escopo.prw", captured.exception.source_path.name)
        self.assertEqual(3, captured.exception.line)
        self.assertIn("fAuxiliarEscopo", str(captured.exception))
        self.assertIn("STATIC", str(captured.exception))
        self.assertIn("util_escopo.prw", str(captured.exception))

    def test_public_function_remains_visible_between_sources(self):
        sources = [
            ("entrada.prw", "User Function Entrada()\nReturn fPublica()\n"),
            ("util.prw", "Function fPublica()\nReturn NIL\n"),
        ]
        self.assertEqual(2, len(compile_sources(sources).functions))


if __name__ == "__main__":
    unittest.main()
