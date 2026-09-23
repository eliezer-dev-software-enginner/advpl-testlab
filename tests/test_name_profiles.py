import contextlib
import io
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from executor import validate_file
from fixture_runtime import Fixture, run_source
from main import main
from naming import NameCollisionError


SOURCE = Path(__file__).parent / "fixtures" / "naming" / "collision.prw"


class TestLabNameProfileTests(unittest.TestCase):
    def test_modern_default_accepts_distinct_long_names(self):
        self.assertEqual(2, validate_file(SOURCE))

    def test_legacy_validation_rejects_colliding_names(self):
        with self.assertRaises(NameCollisionError):
            validate_file(SOURCE, name_profile="legacy10")

    def test_legacy_semantic_validation_resolves_truncated_variable(self):
        source = (
            "Function Main()\n"
            "Local nTotalGeralAnual := 3\n"
            "Return nTotalGeralMensal\n"
        )
        self.assertEqual(3, run_source(source, fixture=Fixture(), name_profile="legacy10"))

    def test_legacy_fixture_function_uses_same_name_policy(self):
        fixture = Fixture.from_dict({"funcoes": [{"RetornoLongo": 4}]})
        source = "Function Main()\nReturn RetornoLonga()\n"
        self.assertEqual(4, run_source(source, fixture=fixture, name_profile="legacy10"))

    def test_cli_reports_collision_in_legacy_profile(self):
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            code = main(["-validate", str(SOURCE), "--name-profile", "legacy10"])
        self.assertEqual(1, code)
        self.assertIn("colidem", error.getvalue())


if __name__ == "__main__":
    unittest.main()
