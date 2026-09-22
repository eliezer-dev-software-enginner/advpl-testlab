import contextlib
import io
import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from executor import discover_entry, execute_file


TRNSOL02 = (
    PROJECT_ROOT.parent
    / "DGB"
    / "desafios-pedro-torres"
    / "desafio1-solicitacao-compra"
    / "TRNSOL02.prw"
)
TARGET_FIXTURE = TRNSOL02.parents[1] / "advpl-testlab.json"


class ExecutorTests(unittest.TestCase):
    def test_discovers_first_user_function_as_entry(self):
        source = """
Static Function Auxiliar()
Return NIL

User Function MinhaRotina()
Return NIL
"""
        self.assertEqual("MinhaRotina", discover_entry(source))

    @unittest.skipUnless(TRNSOL02.is_file(), "corpus TRNSOL02 nao disponivel")
    def test_executes_original_trnsol02_headless(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = execute_file(
                TRNSOL02,
                fixture_path=TARGET_FIXTURE,
            )
        self.assertIsNone(result)
        text = output.getvalue()
        self.assertIn("Consulta de Solicitacoes Internas", text)
        self.assertIn("000001", text)
        self.assertIn("350.5", text)
        self.assertIn("000002", text)

    @unittest.skipUnless(TRNSOL02.is_file(), "corpus TRNSOL02 nao disponivel")
    def test_discovers_fixture_in_target_project(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            execute_file(TRNSOL02)
        self.assertIn("000001", output.getvalue())

    @unittest.skipUnless(TARGET_FIXTURE.is_file(), "fixture alvo nao disponivel")
    def test_target_fixture_declares_z04_z05_and_z06(self):
        data = json.loads(TARGET_FIXTURE.read_text(encoding="utf-8"))
        tables = {name: value for item in data["tabelas"] for name, value in item.items()}
        self.assertEqual({"Z04", "Z05", "Z06"}, set(tables))
        z05_fields = {field["nome"]: field for field in tables["Z05"]["campos"]}
        self.assertIn("Z05_PRODUT", z05_fields)
        self.assertEqual("Z05_PRODUTO", z05_fields["Z05_PRODUT"]["nome_informado"])
        for table in tables.values():
            for field in table["campos"]:
                self.assertNotIn("decimais", field)
                self.assertIsInstance(field["titulo"], str)
                self.assertIsInstance(field["descricao"], str)
        self.assertEqual("Quantidade", z05_fields["Z05_QUANT"]["titulo"])


if __name__ == "__main__":
    unittest.main()
