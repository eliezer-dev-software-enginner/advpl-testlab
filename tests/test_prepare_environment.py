import contextlib
import io
import unittest

from fixture_runtime import Fixture, build_interpreter, compile_source
from interpreter import AdvPLRuntimeError
from parser import ParseError


SOURCE = """User Function Ex1()
    PREPARE ENVIRONMENT EMPRESA "01" FILIAL "02"
    DbSelectArea('ZA2')
    DbSetOrder(1)
    RecLock('ZA2', .T.)
    ZA2_FILIAL := xFilial()
    ZA2_NOME := 'Paulo'
    ZA2_DTCRIA := Date()
    MsUnlock()
    Alert('Inseriu!')
    RESET ENVIRONMENT
Return Nil
"""


def fixture():
    return Fixture.from_dict({
        "tabelas": [{"ZA2": {"campos": [
            {"nome": "ZA2_FILIAL", "tipo": "C"},
            {"nome": "ZA2_NOME", "tipo": "C"},
            {"nome": "ZA2_DTCRIA", "tipo": "D"},
        ], "registros": []}}],
        "ambiente": [{"DDATABASE": "2026-09-24"}],
    })


class PrepareEnvironmentTests(unittest.TestCase):
    def test_ex1_inserts_only_in_memory(self):
        data = fixture()
        compile_source(SOURCE, fixture=data)
        runtime = build_interpreter(SOURCE, fixture=data, entry="Ex1")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            runtime.run("Ex1")
        self.assertEqual("[ALERTA] Inseriu!", output.getvalue().strip())
        self.assertEqual([{"ZA2_FILIAL": "02", "ZA2_NOME": "Paulo",
                           "ZA2_DTCRIA": "2026-09-24"}], runtime._aliases["ZA2"].records)
        self.assertEqual([], data.tabelas["ZA2"]["registros"])
        self.assertIsNone(runtime._prepared_company)
        self.assertIsNone(runtime._prepared_branch)

    def test_prepare_accepts_variable_values(self):
        source = SOURCE.replace(
            '    PREPARE ENVIRONMENT EMPRESA "01" FILIAL "02"',
            "    Local cEmpresa := '03'\n    Local cFilial := '04'\n"
            "    PREPARE ENVIRONMENT EMPRESA cEmpresa FILIAL cFilial",
        )
        runtime = build_interpreter(source, fixture=fixture(), entry="Ex1")
        with contextlib.redirect_stdout(io.StringIO()):
            runtime.run("Ex1")
        self.assertEqual("04", runtime._aliases["ZA2"].records[0]["ZA2_FILIAL"])

    def test_invalid_environment_values_fail_explicitly(self):
        source = SOURCE.replace('FILIAL "02"', 'FILIAL ""')
        runtime = build_interpreter(source, fixture=fixture(), entry="Ex1")
        with self.assertRaisesRegex(AdvPLRuntimeError, "FILIAL como texto nao vazio"):
            runtime.run("Ex1")

    def test_incomplete_prepare_is_not_silently_ignored(self):
        source = SOURCE.replace(' FILIAL "02"', '')
        with self.assertRaises(ParseError):
            compile_source(source, fixture=fixture())


if __name__ == "__main__":
    unittest.main()
