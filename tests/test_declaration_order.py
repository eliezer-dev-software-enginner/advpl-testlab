import unittest

from fixture_runtime import compile_source, run_source
from semantic import SemanticError


class DeclarationOrderTests(unittest.TestCase):
    def test_ordered_declarations_run(self):
        source = (
            "User Function Main()\n"
            "Local nLocal := 1\n"
            "Static nStatic := 2\n"
            "Private nPrivate := 3\n"
            "Public nPublic := 4\n"
            "Return nLocal + nStatic + nPrivate + nPublic\n"
        )
        self.assertEqual(10, run_source(source, entry="Main"))

    def test_local_after_private_is_rejected_at_declaration(self):
        source = "User Function Main()\nPrivate nP := 1\nLocal nL := 2\nReturn nP\n"
        with self.assertRaises(SemanticError) as captured:
            compile_source(source)
        self.assertEqual((3, 1), (captured.exception.line, captured.exception.column))
        self.assertIn("fora de ordem", str(captured.exception))

    def test_private_after_public_is_rejected(self):
        source = "User Function Main()\nPublic nG := 1\nPrivate nP := 2\nReturn nG\n"
        with self.assertRaises(SemanticError) as captured:
            compile_source(source)
        self.assertEqual(3, captured.exception.line)

    def test_declaration_after_statement_is_rejected(self):
        source = "User Function Main()\nLocal nA := 1\nnA += 1\nLocal nB := 2\nReturn nA\n"
        with self.assertRaises(SemanticError) as captured:
            compile_source(source)
        self.assertEqual(4, captured.exception.line)
        self.assertIn("antes dos comandos", str(captured.exception))

    def test_declaration_inside_branch_is_rejected(self):
        source = "User Function Main()\nIf .T.\nLocal nA := 1\nEndIf\nReturn Nil\n"
        with self.assertRaises(SemanticError) as captured:
            compile_source(source)
        self.assertEqual(3, captured.exception.line)

    def test_multiple_declarations_on_one_line_remain_valid(self):
        source = "User Function Main()\nLocal nA := 1, nB := 2\nReturn nA + nB\n"
        self.assertEqual(3, run_source(source, entry="Main"))


if __name__ == "__main__":
    unittest.main()
