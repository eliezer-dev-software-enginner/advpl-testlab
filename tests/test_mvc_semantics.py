import unittest

from fixture_runtime import Fixture, compile_source, run_source
from interpreter import AdvPLRuntimeError
from semantic import SemanticError


def mvc_fixture():
    return Fixture.from_dict({
        "tabelas": [{"ZA1": {"campos": [
            {"nome": "ZA1_FILIAL", "tipo": "C"},
            {"nome": "ZA1_COD", "tipo": "C"},
        ], "registros": []}}],
    })


class MvcSemanticTests(unittest.TestCase):
    def test_menu_rejects_unknown_viewdef_module(self):
        source = (
            "User Function ZA1MVC()\nLocal aRotina := {}\n"
            "ADD OPTION aRotina TITLE 'Visualizar' ACTION 'VIEWDEF.ZA1ABC' "
            "OPERATION 2 ACCESS 0\nReturn aRotina\n"
            "Static Function ViewDef()\nReturn NIL\n"
        )
        with self.assertRaises(SemanticError) as captured:
            compile_source(source, fixture=mvc_fixture())
        self.assertIn("ZA1ABC", str(captured.exception))
        self.assertEqual(3, captured.exception.line)

    def test_menu_accepts_loaded_viewdef_module(self):
        source = (
            "User Function ZA1MVC()\nLocal aRotina := {}\n"
            "ADD OPTION aRotina TITLE 'Visualizar' ACTION 'VIEWDEF.ZA1MVC' "
            "OPERATION 2 ACCESS 0\nReturn aRotina\n"
            "Static Function ViewDef()\nReturn NIL\n"
        )
        compile_source(source, fixture=mvc_fixture())

    def test_run_rejects_invalid_menu_in_unvisited_function(self):
        source = (
            "User Function ZA1MVC()\nReturn NIL\n"
            "Static Function MenuDef()\nLocal aRotina := {}\n"
            "ADD OPTION aRotina TITLE 'Visualizar' ACTION 'VIEWDEF.ZA1ABC' "
            "OPERATION 2 ACCESS 0\nReturn aRotina\n"
        )
        with self.assertRaisesRegex(SemanticError, "VIEWDEF.ZA1ABC"):
            run_source(source, fixture=mvc_fixture(), entry="ZA1MVC")

    def test_primary_key_rejects_unknown_fixture_field(self):
        source = (
            "User Function ZA1MVC()\n"
            "Local oModel := MPFormModel():New('ZA1')\n"
            'oModel:SetPrimaryKey({ "ZA1_FILIAL", "ZA1_CODIGB" })\n'
            "Return NIL\n"
        )
        with self.assertRaises(SemanticError) as captured:
            compile_source(source, fixture=mvc_fixture())
        self.assertIn("ZA1_CODIGB", str(captured.exception))
        self.assertEqual(3, captured.exception.line)

    def test_primary_key_accepts_fixture_fields(self):
        source = (
            "User Function ZA1MVC()\n"
            "Local oModel := MPFormModel():New('ZA1')\n"
            'oModel:SetPrimaryKey({ "ZA1_FILIAL", "ZA1_COD" })\n'
            "Return NIL\n"
        )
        compile_source(source, fixture=mvc_fixture())

    def test_run_rejects_invalid_key_in_unvisited_function(self):
        source = (
            "User Function ZA1MVC()\nReturn NIL\n"
            "Static Function ModelDef()\n"
            "Local oModel := MPFormModel():New('ZA1')\n"
            'oModel:SetPrimaryKey({ "ZA1_CODIGB" })\n'
            "Return oModel\n"
        )
        with self.assertRaisesRegex(SemanticError, "ZA1_CODIGB"):
            run_source(source, fixture=mvc_fixture(), entry="ZA1MVC")

    def test_dynamic_primary_key_checked_at_runtime(self):
        source = (
            "User Function ZA1MVC()\n"
            "Local oModel := MPFormModel():New('ZA1')\n"
            'Local aChave := { "ZA1_CODIGB" }\n'
            "oModel:SetPrimaryKey(aChave)\nReturn NIL\n"
        )
        with self.assertRaisesRegex(AdvPLRuntimeError, "ZA1_CODIGB"):
            run_source(source, fixture=mvc_fixture(), entry="ZA1MVC")


if __name__ == "__main__":
    unittest.main()
