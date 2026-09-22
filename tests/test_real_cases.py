import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fixture_runtime import AdvPLRuntimeError, Fixture, run_file, run_source


class RealUseCaseTests(unittest.TestCase):
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
        fixture = Fixture.from_dict({"parametros": {"MV_EXISTE": "configurado"}})
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
