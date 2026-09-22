import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) in sys.path:
    sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from main import main
from executor import discover_source_units, validate_file
from fixture_runtime import (
    AdvPLRuntimeError,
    Fixture,
    FixtureError,
    build_interpreter,
    build_interpreter_sources,
    run_file,
    run_source,
)


ENVEMAIL = (
    PROJECT_ROOT.parent
    / "desafios-aprendizado"
    / "desafio1-solicitacao-compra"
    / "ENVEMAIL.prw"
)
NOTIFSOL = ENVEMAIL.with_name("NOTIFSOL.prw")
TRNSOL01 = ENVEMAIL.with_name("TRNSOL01.prw")
TARGET_FIXTURE = ENVEMAIL.parent / "advpl-testlab.json"


class RealUseCaseTests(unittest.TestCase):
    @unittest.skipUnless(TRNSOL01.is_file(), "corpus TRNSOL01 nao disponivel")
    def test_trnsol01_real_source_is_semantically_valid(self):
        self.assertGreaterEqual(validate_file(TRNSOL01), 20)

    @unittest.skipUnless(TRNSOL01.is_file(), "corpus TRNSOL01 nao disponivel")
    def test_trnsol01_approval_updates_record_and_sends_email(self):
        data = json.loads(TARGET_FIXTURE.read_text(encoding="utf-8"))
        data["tabelas"][2]["Z04"]["registros"][0]["Z04_STATUS"] = "2"
        interpreter = build_interpreter_sources(
            discover_source_units(TRNSOL01),
            fixture=Fixture.from_dict(data),
            entry="Z04APR",
            source_name=TRNSOL01,
        )

        self.assertIsNone(interpreter.run("Z04APR"))
        self.assertEqual("3", interpreter._aliases["Z04"].records[0]["Z04_STATUS"])
        self.assertEqual(1, len(interpreter.sent_emails))
        self.assertIn("aprovada", interpreter.sent_emails[0]["subject"])

    @unittest.skipUnless(TRNSOL01.is_file(), "corpus TRNSOL01 nao disponivel")
    def test_trnsol01_send_for_approval_updates_record_and_sends_email(self):
        data = json.loads(TARGET_FIXTURE.read_text(encoding="utf-8"))
        data["tabelas"][2]["Z04"]["registros"][0]["Z04_STATUS"] = "1"
        interpreter = build_interpreter_sources(
            discover_source_units(TRNSOL01),
            fixture=Fixture.from_dict(data),
            entry="Z04ENV",
            source_name=TRNSOL01,
        )

        self.assertIsNone(interpreter.run("Z04ENV"))
        self.assertEqual("2", interpreter._aliases["Z04"].records[0]["Z04_STATUS"])
        self.assertEqual("aprovador@example.com", interpreter.sent_emails[0]["to"])

    @unittest.skipUnless(TRNSOL01.is_file(), "corpus TRNSOL01 nao disponivel")
    def test_trnsol01_rejection_uses_dialog_fixture(self):
        data = json.loads(TARGET_FIXTURE.read_text(encoding="utf-8"))
        data["tabelas"][2]["Z04"]["registros"][0]["Z04_STATUS"] = "2"
        interpreter = build_interpreter_sources(
            discover_source_units(TRNSOL01),
            fixture=Fixture.from_dict(data),
            entry="Z04REJ",
            source_name=TRNSOL01,
        )

        self.assertIsNone(interpreter.run("Z04REJ"))
        record = interpreter._aliases["Z04"].records[0]
        self.assertEqual("4", record["Z04_STATUS"])
        self.assertEqual("Orcamento indisponivel", record["Z04_MOTIVO"])
        self.assertIn("rejeitada", interpreter.sent_emails[0]["subject"])

    @unittest.skipUnless(TRNSOL01.is_file(), "corpus TRNSOL01 nao disponivel")
    def test_trnsol01_processing_updates_items_and_results(self):
        data = json.loads(TARGET_FIXTURE.read_text(encoding="utf-8"))
        interpreter = build_interpreter_sources(
            discover_source_units(TRNSOL01),
            fixture=Fixture.from_dict(data),
            entry="Z04PROC",
            source_name=TRNSOL01,
        )

        self.assertIsNone(interpreter.run("Z04PROC"))
        self.assertEqual("5", interpreter._aliases["Z04"].records[0]["Z04_STATUS"])
        self.assertEqual(
            ["5", "5"],
            [record["Z05_STATUS"] for record in interpreter._aliases["Z05"].records[:2]],
        )
        self.assertEqual(3, len(interpreter._aliases["Z06"].records))
        self.assertIn("Resultado do processamento", interpreter.sent_emails[0]["subject"])

    @unittest.skipUnless(TRNSOL01.is_file(), "corpus TRNSOL01 nao disponivel")
    def test_trnsol01_processing_reports_item_error(self):
        data = json.loads(TARGET_FIXTURE.read_text(encoding="utf-8"))
        data["tabelas"][3]["Z05"]["registros"][0]["Z05_QUANT"] = 101
        interpreter = build_interpreter_sources(
            discover_source_units(TRNSOL01),
            fixture=Fixture.from_dict(data),
            entry="Z04PROC",
            source_name=TRNSOL01,
        )

        interpreter.run("Z04PROC")
        self.assertEqual("7", interpreter._aliases["Z04"].records[0]["Z04_STATUS"])
        self.assertEqual("7", interpreter._aliases["Z05"].records[0]["Z05_STATUS"])
        self.assertIn("acima do limite", interpreter._aliases["Z05"].records[0]["Z05_ERRO"])

    @unittest.skipUnless(TRNSOL01.is_file(), "corpus TRNSOL01 nao disponivel")
    def test_trnsol01_processing_rolls_back_failed_lock(self):
        data = json.loads(TARGET_FIXTURE.read_text(encoding="utf-8"))
        data["ambiente"].append({"RECLOCK_Z06": False})
        interpreter = build_interpreter_sources(
            discover_source_units(TRNSOL01),
            fixture=Fixture.from_dict(data),
            entry="Z04PROC",
            source_name=TRNSOL01,
        )

        interpreter.run("Z04PROC")
        self.assertEqual("3", interpreter._aliases["Z04"].records[0]["Z04_STATUS"])
        self.assertEqual("3", interpreter._aliases["Z05"].records[0]["Z05_STATUS"])
        self.assertEqual(1, len(interpreter._aliases["Z06"].records))
        self.assertIn("Falha no processamento", interpreter.sent_emails[0]["subject"])

    @unittest.skipUnless(TRNSOL01.is_file(), "corpus TRNSOL01 nao disponivel")
    def test_trnsol01_browse_menu_model_and_view_execute(self):
        interpreter = build_interpreter_sources(
            discover_source_units(TRNSOL01),
            fixture=Fixture.from_file(TARGET_FIXTURE),
            entry="TRNSOL01",
            source_name=TRNSOL01,
        )

        self.assertIsNone(interpreter.run("TRNSOL01"))
        self.assertEqual(9, len(interpreter.run("MenuDef")))
        self.assertIsNone(interpreter.run("Z04LEG"))
        model = interpreter.run("ModelDef")
        self.assertTrue(interpreter.run("fVldSalvar", [model]))
        self.assertIsNotNone(interpreter.run("ViewDef"))

    @unittest.skipUnless(TRNSOL01.is_file(), "corpus TRNSOL01 nao disponivel")
    def test_trnsol01_model_grid_only_validates_current_request_items(self):
        data = json.loads(TARGET_FIXTURE.read_text(encoding="utf-8"))
        data["tabelas"][3]["Z05"]["registros"][2]["Z05_QUANT"] = -1
        interpreter = build_interpreter_sources(
            discover_source_units(TRNSOL01),
            fixture=Fixture.from_dict(data),
            entry="ModelDef",
            source_name=TRNSOL01,
        )

        model = interpreter.run("ModelDef")
        self.assertTrue(interpreter.run("fVldSalvar", [model]))

    @unittest.skipUnless(TRNSOL01.is_file(), "corpus TRNSOL01 nao disponivel")
    def test_trnsol01_grid_rejects_processed_item(self):
        interpreter = build_interpreter_sources(
            discover_source_units(TRNSOL01),
            fixture=Fixture.from_file(TARGET_FIXTURE),
            entry="ModelDef",
            source_name=TRNSOL01,
        )
        model = interpreter.run("ModelDef")
        grid = interpreter.call_method(model, "GetModel", ["Z05DETAIL"])
        self.assertTrue(interpreter.run("fVldLinha", [grid]))
        interpreter._aliases["Z05"].records[0]["Z05_STATUS"] = "5"
        self.assertFalse(interpreter.run("fVldLinha", [grid]))

    def test_dbsetorder_uses_fixture_index_for_seek_and_skip(self):
        fixture = Fixture.from_dict(
            {
                "tabelas": [
                    {
                        "ZX1": {
                            "campos": [
                                {"nome": "ZX1_FILIAL", "tipo": "C"},
                                {"nome": "ZX1_CODIGO", "tipo": "C"},
                                {"nome": "ZX1_ITEM", "tipo": "C"},
                            ],
                            "indices": {"1": ["ZX1_FILIAL", "ZX1_CODIGO", "ZX1_ITEM"]},
                            "registros": [
                                {"ZX1_ITEM": "0002", "ZX1_CODIGO": "000001", "ZX1_FILIAL": "01"},
                                {"ZX1_ITEM": "0001", "ZX1_CODIGO": "000001", "ZX1_FILIAL": "01"},
                            ],
                        }
                    }
                ]
            }
        )
        result = run_source(
            """
Function Main()
    DbSelectArea('ZX1')
    DbSetOrder(1)
    DbSeek('01000001')
    Local cFirst := ZX1_ITEM
    DbSkip()
Return {cFirst, ZX1_ITEM}
""",
            fixture=fixture,
        )
        self.assertEqual(["0001", "0002"], result)

    def test_fixture_rejects_index_with_undeclared_field(self):
        with self.assertRaisesRegex(FixtureError, "campos declarados"):
            Fixture.from_dict({
                "tabelas": [{"ZX1": {
                    "campos": [{"nome": "ZX1_CODIGO", "tipo": "C"}],
                    "indices": {"1": ["ZX1_INEXISTENTE"]},
                    "registros": [],
                }}]
            })

    @unittest.skipUnless(TRNSOL01.is_file(), "corpus TRNSOL01 nao disponivel")
    def test_trnsol01_cancel_updates_record_after_confirmation(self):
        data = json.loads(TARGET_FIXTURE.read_text(encoding="utf-8"))
        data["tabelas"][2]["Z04"]["registros"][0]["Z04_STATUS"] = "1"
        interpreter = build_interpreter_sources(
            discover_source_units(TRNSOL01),
            fixture=Fixture.from_dict(data),
            entry="Z04CAN",
            source_name=TRNSOL01,
        )

        self.assertIsNone(interpreter.run("Z04CAN"))
        self.assertEqual("6", interpreter._aliases["Z04"].records[0]["Z04_STATUS"])

    @unittest.skipUnless(NOTIFSOL.is_file(), "corpus NOTIFSOL nao disponivel")
    def test_notifsol_real_source_is_semantically_valid(self):
        self.assertEqual(5, validate_file(NOTIFSOL))

    @unittest.skipUnless(NOTIFSOL.is_file(), "corpus NOTIFSOL nao disponivel")
    def test_notifsol_executes_complete_envio_flow(self):
        fixture = Fixture.from_file(TARGET_FIXTURE)
        interpreter = build_interpreter_sources(
            discover_source_units(NOTIFSOL),
            fixture=fixture,
            entry="NotificarSolicitacao",
            source_name=NOTIFSOL,
        )

        result = interpreter.run("NotificarSolicitacao", ["ENVIO"])

        self.assertTrue(result)
        self.assertEqual(1, len(interpreter.sent_emails))
        self.assertIn("000001", interpreter.sent_emails[0]["subject"])
        self.assertIn("Material de escritorio", interpreter.sent_emails[0]["body"])

    @unittest.skipUnless(NOTIFSOL.is_file(), "corpus NOTIFSOL nao disponivel")
    def test_notifsol_executes_every_event_branch(self):
        fixture = Fixture.from_file(TARGET_FIXTURE)
        cases = {
            "ENVIO": "Quantidade de itens",
            "APROVACAO": "Aprovada",
            "REJEICAO": "Motivo da rejei",
            "PROCESSAMENTO": "Itens com sucesso",
        }

        for event, expected_body in cases.items():
            with self.subTest(event=event):
                interpreter = build_interpreter_sources(
                    discover_source_units(NOTIFSOL),
                    fixture=fixture,
                    entry="NotificarSolicitacao",
                    source_name=NOTIFSOL,
                )
                self.assertTrue(
                    interpreter.run("NotificarSolicitacao", [event])
                )
                self.assertIn(expected_body, interpreter.sent_emails[0]["body"])

        interpreter = build_interpreter_sources(
            discover_source_units(NOTIFSOL),
            fixture=fixture,
            entry="NotificarSolicitacao",
            source_name=NOTIFSOL,
        )
        self.assertFalse(interpreter.run("NotificarSolicitacao", ["INVALIDO"]))
        self.assertEqual([], interpreter.sent_emails)

    @unittest.skipUnless(NOTIFSOL.is_file(), "corpus NOTIFSOL nao disponivel")
    def test_cli_accepts_json_arguments_for_notifsol_entry(self):
        self.assertEqual(
            0,
            main(
                [
                    "-run",
                    str(NOTIFSOL),
                    "--fixture",
                    str(TARGET_FIXTURE),
                    "--entry",
                    "NotificarSolicitacao",
                    "--args-json",
                    '["ENVIO"]',
                ]
            ),
        )

    @unittest.skipUnless(ENVEMAIL.is_file(), "corpus ENVEMAIL nao disponivel")
    def test_envemail_real_source_is_semantically_valid(self):
        self.assertEqual(1, validate_file(ENVEMAIL))

    @unittest.skipUnless(ENVEMAIL.is_file(), "corpus ENVEMAIL nao disponivel")
    def test_envemail_runs_all_input_validations_without_network(self):
        source = ENVEMAIL.read_text(encoding="cp1252")
        cases = [
            (
                ["destino@teste.com", None, "<p>Oi</p>", []],
                "Assunto do e-mail nao informado.",
            ),
            (
                ["destino@teste.com", "   ", "<p>Oi</p>", []],
                "Assunto do e-mail nao informado.",
            ),
            (
                ["destino@teste.com", "Assunto", "<p>Oi</p>", None],
                "Configuracao SMTP nao informada.",
            ),
            (
                ["destino@teste.com", "Assunto", "<p>Oi</p>", []],
                "Configuracao SMTP deve conter oito valores.",
            ),
            (
                [
                    "destino@teste.com",
                    "Assunto",
                    "<p>Oi</p>",
                    ["smtp", "conta", "senha", "origem", "587", True, False, False],
                ],
                "Configuracao SMTP possui tipos invalidos.",
            ),
        ]

        for args, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(
                    expected,
                    run_source(
                        source,
                        fixture=Fixture(),
                        entry="EnviarEmailSolicitacao",
                        args=args,
                        source_name=ENVEMAIL,
                    ),
                )

    @unittest.skipUnless(ENVEMAIL.is_file(), "corpus ENVEMAIL nao disponivel")
    def test_envemail_send_is_headless_and_captured_in_memory(self):
        source = ENVEMAIL.read_text(encoding="cp1252")
        interpreter = build_interpreter(
            source,
            fixture=Fixture(),
            entry="EnviarEmailSolicitacao",
            source_name=ENVEMAIL,
        )

        result = interpreter.run(
            "EnviarEmailSolicitacao",
            [
                "destino@teste.com",
                "Assunto de teste",
                "<p>Mensagem</p>",
                ["smtp.teste:587", "conta", "senha", "", 25, True, True, False],
            ],
        )

        self.assertEqual("", result)
        self.assertEqual(
            [
                {
                    "from": "conta",
                    "to": "destino@teste.com",
                    "subject": "Assunto de teste",
                    "body_type": "text/html",
                    "body": "<p>Mensagem</p>",
                }
            ],
            interpreter.sent_emails,
        )

    @unittest.skipUnless(ENVEMAIL.is_file(), "corpus ENVEMAIL nao disponivel")
    def test_envemail_returns_configured_headless_send_error(self):
        source = ENVEMAIL.read_text(encoding="cp1252")
        fixture = Fixture.from_dict(
            {
                "ambiente": [
                    {"MAIL_SEND_RESULT": 42},
                    {"MAIL_ERROR_MESSAGE": "Falha SMTP simulada"},
                ]
            }
        )

        result = run_source(
            source,
            fixture=fixture,
            entry="EnviarEmailSolicitacao",
            args=[
                "destino@teste.com",
                "Assunto",
                "<p>Mensagem</p>",
                ["smtp.teste", "conta", "senha", "origem", 587, False, False, True],
            ],
            source_name=ENVEMAIL,
        )

        self.assertEqual("Falha SMTP simulada", result)

    def test_sol_mail_cfg_runs_real_advpl_case(self):
        result = run_file(
            PROJECT_ROOT / "examples" / "real-cases" / "sol_mail_cfg.prw",
            PROJECT_ROOT / "fixtures" / "sol_mail_cfg.json",
            entry="SolMailCfg",
        )
        self.assertEqual(
            [
                "smtp.exemplo.local:587",
                "conta.smtp",
                "senha-teste",
                "conta.smtp",
                587,
                True,
                False,
                False,
            ],
            result,
        )

    def test_getmv_uses_default_only_when_parameter_is_missing(self):
        fixture = Fixture.from_dict(
            {"parametros": [{"MV_EXISTE": "configurado"}]}
        )
        result = run_source(
            """
Function Main()
    Local aValores := { ;
        GetMV("MV_EXISTE", .F., "default"), ;
        GetMV("MV_AUSENTE", .F., "default") }
Return aValores
""",
            fixture=fixture,
        )
        self.assertEqual(["configurado", "default"], result)

    def test_getmv_without_default_keeps_clear_missing_parameter_error(self):
        with self.assertRaisesRegex(
            AdvPLRuntimeError,
            "GetMV: parametro 'MV_AUSENTE' nao encontrado no fixture",
        ):
            run_source(
                'Function Main()\nReturn GetMV("MV_AUSENTE")',
                fixture=Fixture(),
            )

    def test_texto_html_escapes_content_and_preserves_line_breaks(self):
        result = run_file(
            PROJECT_ROOT / "examples" / "real-cases" / "sol_mail_cfg.prw",
            PROJECT_ROOT / "fixtures" / "sol_mail_cfg.json",
            entry="TextoHtml",
            args=['  A&B<>"\'\r\nLinha 2  '],
        )
        self.assertEqual("A&amp;B&lt;&gt;&quot;&#39;<br>Linha 2", result)


if __name__ == "__main__":
    unittest.main()
