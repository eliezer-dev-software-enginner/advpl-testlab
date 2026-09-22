import contextlib
import io
import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from executor import discover_entry, execute_file, validate_file
from fixture_runtime import Fixture, FixtureError, build_interpreter, run_source


TRNSOL02 = (
    PROJECT_ROOT.parent
    / "desafios-aprendizado"
    / "desafio1-solicitacao-compra"
    / "TRNSOL02.prw"
)
TARGET_FIXTURE = TRNSOL02.parent / "advpl-testlab.json"
USE_PRW_MAIN = PROJECT_ROOT / "tests" / "fixtures" / "use_prw" / "principal.prw"
USE_PRW_MISSING = PROJECT_ROOT / "tests" / "fixtures" / "use_prw" / "ausente.prw"


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

    @unittest.skipUnless(TRNSOL02.is_file(), "corpus TRNSOL02 nao disponivel")
    def test_validates_every_function_in_original_trnsol02(self):
        self.assertEqual(3, validate_file(TRNSOL02))

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
    def test_interpreter_executes_original_trnsol02_without_executor_adapter(self):
        source = TRNSOL02.read_text(encoding="utf-8", errors="replace")
        fixture = Fixture.from_file(TARGET_FIXTURE)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = run_source(
                source,
                fixture=fixture,
                entry="Z04CON",
                source_name=TRNSOL02,
            )

        self.assertIsNone(result)
        text = output.getvalue()
        self.assertIn("Consulta de Solicitacoes Internas", text)
        self.assertIn("000001", text)
        self.assertIn("350.5", text)

    @unittest.skipUnless(TRNSOL02.is_file(), "corpus TRNSOL02 nao disponivel")
    def test_trnsol02_builds_query_and_binds_branch_parameter(self):
        source = TRNSOL02.read_text(encoding="utf-8", errors="replace")
        fixture = Fixture.from_file(TARGET_FIXTURE)
        interpreter = build_interpreter(
            source,
            fixture=fixture,
            entry="Z04CON",
            source_name=TRNSOL02,
        )
        with contextlib.redirect_stdout(io.StringIO()):
            interpreter.run("Z04CON")

        self.assertEqual(1, len(interpreter.statements))
        statement = interpreter.statements[0]
        self.assertIn("SELECT Z04.Z04_CODIGO", statement["query"])
        self.assertIn("LEFT JOIN Z05", statement["query"])
        self.assertIn("GROUP BY Z04.Z04_CODIGO", statement["query"])
        self.assertIn("ORDER BY Z04.Z04_DATA DESC", statement["query"])
        self.assertEqual({1: "01"}, statement["parameters"])

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
        self.assertTrue({"Z04", "Z05", "Z06"}.issubset(tables))
        z05_fields = {field["nome"]: field for field in tables["Z05"]["campos"]}
        self.assertIn("Z05_PRODUT", z05_fields)
        self.assertEqual("Z05_PRODUTO", z05_fields["Z05_PRODUT"]["nome_informado"])
        for table in tables.values():
            for field in table["campos"]:
                self.assertNotIn("decimais", field)
                self.assertNotIn("tamanho", field)
                self.assertNotIn("obrigatorio", field)
                self.assertNotIn("descricao", field)
                self.assertIsInstance(field["titulo"], str)
        self.assertEqual("Quantidade", z05_fields["Z05_QUANT"]["titulo"])
        specificity = next(
            item for item in data["especificidadesPrw"]
            if item["fonte"] == "TRNSOL02.prw"
        )
        self.assertEqual("TRNSOL02.prw", specificity["fonte"])
        self.assertEqual("MSGYESNO", specificity["funcoes"][0]["nome"])
        self.assertFalse(specificity["funcoes"][0]["retorno"])

    @unittest.skipUnless(TRNSOL02.is_file(), "corpus TRNSOL02 nao disponivel")
    def test_trnsol02_true_confirmation_executes_virtual_export_branch(self):
        source = TRNSOL02.read_text(encoding="utf-8", errors="replace")
        fixture = Fixture.from_dict(
            {
                "funcoes": [],
                "dialogos": [
                    {
                        "fonte": "TRNSOL02.prw",
                        "titulo": "Consulta de Solicitacoes - Filtros",
                        "variaveis": [{"LRET": True}],
                    }
                ],
                "ambiente": [
                    {"CUSERLOCAL": "C:\\testlab"},
                    {"TIME": "12:34:56"},
                ],
                "consultas": [
                    {
                        "Z04CON": {
                            "registros": [
                                {
                                    "Z04_CODIGO": "000001",
                                    "Z04_DATA": "2026-09-18",
                                    "Z04_USER": "001",
                                    "Z04_CCUSTO": "CC001",
                                    "Z04_STATUS": "3",
                                    "QT_ITENS": 2,
                                    "VL_TOTAL": 350.5,
                                }
                            ]
                        }
                    }
                ],
                "especificidadesPrw": [
                    {
                        "fonte": "TRNSOL02.prw",
                        "funcoes": [
                            {
                                "nome": "MSGYESNO",
                                "conteudo": "'Gerar arquivo Excel com o resultado da consulta?', 'Consulta'",
                                "retorno": True,
                            }
                        ],
                    }
                ],
            }
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            interpreter = build_interpreter(
                source,
                fixture=fixture,
                entry="Z04CON",
                source_name="TRNSOL02.prw",
            )
            result = interpreter.run("Z04CON")

        self.assertIsNone(result)
        self.assertIn("Arquivo gerado com 1 registro(s)", output.getvalue())
        self.assertIn("TRNSOL_Consulta_123456.xls", output.getvalue())
        self.assertEqual(1, len(interpreter.virtual_files))
        exported_html = next(iter(interpreter.virtual_files.values()))
        self.assertIn("<th>Solicitacao</th>", exported_html)
        self.assertIn("<td>000001</td>", exported_html)
        self.assertTrue(exported_html.endswith("</table>"))

    @unittest.skipUnless(TRNSOL02.is_file(), "corpus TRNSOL02 nao disponivel")
    def test_executes_original_filter_dialog_function(self):
        source = TRNSOL02.read_text(encoding="utf-8", errors="replace")
        fixture = Fixture.from_file(TARGET_FIXTURE)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = run_source(
                source,
                fixture=fixture,
                entry="fAskFiltros",
                args=[None, None, "", "", "", "", ""],
                source_name=TRNSOL02,
            )

        self.assertTrue(result)
        self.assertIn(
            "[MSDIALOG] Consulta de Solicitacoes - Filtros",
            output.getvalue(),
        )

    @unittest.skipUnless(TRNSOL02.is_file(), "corpus TRNSOL02 nao disponivel")
    def test_trnsol02_stops_when_filter_dialog_is_cancelled(self):
        source = TRNSOL02.read_text(encoding="utf-8", errors="replace")
        fixture = Fixture.from_dict(
            {
                "dialogos": [
                    {
                        "fonte": "TRNSOL02.prw",
                        "titulo": "Consulta de Solicitacoes - Filtros",
                        "variaveis": [{"LRET": False}],
                    }
                ]
            }
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = run_source(
                source,
                fixture=fixture,
                entry="Z04CON",
                source_name=TRNSOL02,
            )

        self.assertIsNone(result)
        self.assertEqual(
            "[MSDIALOG] Consulta de Solicitacoes - Filtros\n",
            output.getvalue(),
        )

    @unittest.skipUnless(TRNSOL02.is_file(), "corpus TRNSOL02 nao disponivel")
    def test_trnsol02_reports_empty_query_result(self):
        source = TRNSOL02.read_text(encoding="utf-8", errors="replace")
        fixture = Fixture.from_dict(
            {
                "dialogos": [
                    {
                        "fonte": "TRNSOL02.prw",
                        "titulo": "Consulta de Solicitacoes - Filtros",
                        "variaveis": [{"LRET": True}],
                    }
                ],
                "consultas": [{"Z04CON": {"registros": []}}],
            }
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = run_source(
                source,
                fixture=fixture,
                entry="Z04CON",
                source_name=TRNSOL02,
            )

        self.assertIsNone(result)
        self.assertIn(
            "[ALERTA] Atencao: Nenhuma solicitacao encontrada",
            output.getvalue(),
        )


if __name__ == "__main__":
    unittest.main()
