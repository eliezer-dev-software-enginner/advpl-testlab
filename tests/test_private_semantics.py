import unittest

from fixture_runtime import compile_source, compile_sources, run_source, run_sources
from interpreter import AdvPLRuntimeError
from semantic import SemanticError


class PrivateSemanticTests(unittest.TestCase):
    def test_private_is_visible_to_called_function(self):
        source = (
            "User Function Main()\nPrivate cCadastro := 'Livros'\nReturn ModelDef()\n"
            "Static Function ModelDef()\nReturn cCadastro\n"
        )
        self.assertEqual("Livros", run_source(source, entry="Main"))

    def test_private_name_can_be_declared_in_other_source(self):
        sources = [
            ("main.prw", "User Function Main()\nPrivate cCadastro := 'Livros'\nReturn U_ModelDef()\n"),
            ("model.prw", "User Function ModelDef()\nReturn cCadastro\n"),
        ]
        self.assertEqual("Livros", run_sources(sources, entry="Main"))

    def test_private_still_requires_active_runtime_scope(self):
        source = (
            "User Function Main()\nPrivate cCadastro := 'Livros'\nReturn NIL\n"
            "Static Function ModelDef()\nReturn cCadastro\n"
        )
        compile_source(source)
        with self.assertRaisesRegex(AdvPLRuntimeError, "cCadastro"):
            run_source(source, entry="ModelDef")

    def test_local_from_other_function_is_not_visible(self):
        source = (
            "User Function Main()\nLocal cCadastro := 'Livros'\nReturn ModelDef()\n"
            "Static Function ModelDef()\nReturn cCadastro\n"
        )
        with self.assertRaises(SemanticError) as captured:
            compile_source(source)
        self.assertEqual(5, captured.exception.line)
        self.assertEqual(8, captured.exception.column)

    def test_undeclared_use_points_to_use_not_earlier_mention(self):
        source = (
            "User Function Main()\n"
            "// cCadastro aparece aqui mas nao foi declarado\n"
            "Return cCadastro\n"
        )
        with self.assertRaises(SemanticError) as captured:
            compile_source(source)
        self.assertEqual(3, captured.exception.line)
        self.assertEqual(8, captured.exception.column)


if __name__ == "__main__":
    unittest.main()
