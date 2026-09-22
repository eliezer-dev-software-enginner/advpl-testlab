import unittest
from pathlib import Path

from diagnostics import SourceValidationError, format_diagnostic
from executor import validate_file


class DiagnosticTests(unittest.TestCase):
    FIXTURE = Path(__file__).parent / "fixtures" / "invalid_assignment.prw"
    UNDEFINED_FIXTURE = (
        Path(__file__).parent / "fixtures" / "undefined_identifier.prw"
    )

    def test_validation_preserves_original_line_and_points_to_incomplete_assignment(self):
        with self.assertRaises(SourceValidationError) as captured:
            validate_file(self.FIXTURE)

        error = captured.exception
        self.assertEqual(3, error.line)
        self.assertEqual("    Local nI :=", error.source_line)
        diagnostic = format_diagnostic(error, color=False)
        self.assertIn("SyntaxError:", diagnostic)
        self.assertIn("invalid_assignment.prw:3:", diagnostic)
        self.assertIn("3 |     Local nI :=", diagnostic)
        self.assertIn("^", diagnostic)

    def test_diagnostic_supports_red_ansi_output(self):
        with self.assertRaises(SourceValidationError) as captured:
            validate_file(self.FIXTURE)

        diagnostic = format_diagnostic(captured.exception, color=True)
        self.assertIn("\033[31;1m", diagnostic)
        self.assertIn("\033[0m", diagnostic)

    def test_validation_rejects_undefined_identifier(self):
        with self.assertRaises(SourceValidationError) as captured:
            validate_file(self.UNDEFINED_FIXTURE)

        error = captured.exception
        self.assertEqual("SemanticError", error.diagnostic_label)
        self.assertEqual(3, error.line)
        self.assertEqual(20, error.column)
        diagnostic = format_diagnostic(error, color=False)
        self.assertIn("SemanticError: Variável 'Nilo' não declarada", diagnostic)
        self.assertIn("3 |     Local oStmt := Nilo", diagnostic)
        self.assertIn("undefined_identifier.prw:3:20", diagnostic)


if __name__ == "__main__":
    unittest.main()
