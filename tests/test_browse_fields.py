import contextlib
import io
import unittest

from fixture_runtime import Fixture, build_interpreter
from interpreter import AdvPLRuntimeError


class BrowseFieldsTests(unittest.TestCase):
    def runtime(self, fields):
        source = """User Function Teste()
Local oBrowse := FWMBrowse():New()
DbSelectArea('T02')
oBrowse:SetAlias('T01')
oBrowse:AddColumn('T01_COD', 'Codigo')
oBrowse:SetFields(%s)
oBrowse:Activate()
Return Nil
""" % fields
        data = Fixture.from_dict({"tabelas": [
            {"T01": {"registros": [{"T01_COD": "A"}, {"T01_COD": "B"}]}},
            {"T02": {"registros": [{"T02_COD": "X"}]}},
        ]})
        runtime = build_interpreter(source, fixture=data, entry="Teste")
        runtime._aliases["T01"].position = 1
        return runtime

    def test_calculated_columns_use_each_record_and_keep_original_columns(self):
        runtime = self.runtime("{{'Nome', {|| 'Nome ' + T01->T01_COD}, 'C', '@!', 1, 60, 0}}")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            runtime.run("Teste")
        lines = output.getvalue().splitlines()
        self.assertEqual(["Codigo", "Nome"], [cell.strip() for cell in lines[1].split('|')])
        self.assertEqual(["A", "Nome A"], [cell.strip() for cell in lines[3].split('|')])
        self.assertEqual(["B", "Nome B"], [cell.strip() for cell in lines[4].split('|')])
        self.assertEqual(1, runtime._aliases["T01"].position)
        self.assertEqual("T02", runtime._current_alias)

    def test_callback_error_restores_record_position_and_current_alias(self):
        runtime = self.runtime("{{'Erro', {|| 1 / 0}}}")
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(AdvPLRuntimeError, "zero"):
                runtime.run("Teste")
        self.assertEqual(1, runtime._aliases["T01"].position)
        self.assertEqual("T02", runtime._current_alias)

    def test_invalid_column_definition_is_rejected(self):
        for fields in ("Nil", "{1}", "{{'Nome'}}", "{{'Nome', 'texto'}}"):
            with self.subTest(fields=fields):
                with self.assertRaisesRegex(AdvPLRuntimeError, "SetFields espera"):
                    self.runtime(fields).run("Teste")
