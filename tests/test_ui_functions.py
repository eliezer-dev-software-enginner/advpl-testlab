import contextlib
import io
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fixture_runtime import (
    AdvPLRuntimeError,
    Fixture,
    FixtureError,
    run_file,
    run_source,
)


class UiFunctionTests(unittest.TestCase):
    def test_ui_headless_example_runs_end_to_end(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = run_file(
                PROJECT_ROOT / "examples" / "ui-headless.prw",
                PROJECT_ROOT / "fixtures" / "ui-headless.json",
                entry="UiHeadless",
            )

        self.assertIsNone(result)
        self.assertEqual(
            "[MSDIALOG] Cadastro sem UI\n"
            "[ALERTA] Atencao: Falha simulada\n"
            "[INFO] Resultado: Operacao concluida\n"
            "[INFO] MsgYesNo: Resposta configurada: nao\n",
            output.getvalue(),
        )

    def test_dialog_alert_and_info_are_rendered_as_text(self):
        source = """
User Function Tela()
    Local oDlg := Nil
    Define MSDialog oDlg TITLE 'Cadastro sem UI' FROM 0,0 TO 100,200
    @ 010, 010 SAY oSay PROMPT 'Nome:' SIZE 040, 010 OF oDlg
    ACTIVATE DIALOG oDlg CENTER
    MsgAlert('Falha simulada', 'Atencao')
    MsgInfo('Operacao concluida', 'Resultado')
Return Nil
"""
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            run_source(source, fixture=Fixture(), entry="Tela", source_name="TELA.PRW")

        self.assertEqual(
            "[MSDIALOG] Cadastro sem UI\n"
            "[ALERTA] Atencao: Falha simulada\n"
            "[INFO] Resultado: Operacao concluida\n",
            output.getvalue(),
        )

    def test_msgyesno_uses_source_and_content_to_select_result(self):
        source = """
User Function Confirma()
    If MsgYesNo('Continuar?', 'Teste')
        Return 'SIM'
    EndIf
Return 'NAO'
"""
        fixture = Fixture.from_dict(
            {
                "especificidadesPrw": [
                    {
                        "fonte": "OUTRO.PRW",
                        "funcoes": [
                            {
                                "nome": "MSGYESNO",
                                "conteudo": "'Continuar?', 'Teste'",
                                "retorno": False,
                            }
                        ],
                    },
                    {
                        "fonte": "CONFIRMA.PRW",
                        "funcoes": [
                            {
                                "nome": "MSGYESNO",
                                "conteudo": "'Continuar?', 'Teste'",
                                "retorno": True,
                            }
                        ],
                    },
                ]
            }
        )

        result = run_source(
            source,
            fixture=fixture,
            entry="Confirma",
            source_name="c:/fontes/confirma.prw",
        )

        self.assertEqual("SIM", result)

    def test_msgyesno_does_not_print_text(self):
        source = """
User Function Confirma()
Return MsgYesNo('Continuar?')
"""
        fixture = Fixture.from_dict(
            {
                "especificidadesPrw": [
                    {
                        "fonte": "CONFIRMA.PRW",
                        "funcoes": [
                            {
                                "nome": "MSGYESNO",
                                "conteudo": "'Continuar?'",
                                "retorno": False,
                            }
                        ],
                    }
                ]
            }
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = run_source(
                source,
                fixture=fixture,
                entry="Confirma",
                source_name="CONFIRMA.PRW",
            )

        self.assertFalse(result)
        self.assertEqual("", output.getvalue())

    def test_multiple_msgyesno_calls_in_same_source_have_independent_results(self):
        source = """
User Function Confirma()
    Local lPrimeira := MsgYesNo('Processar?', 'Teste')
    Local lSegunda := MsgYesNo('Cancelar?', 'Teste')
Return {lPrimeira, lSegunda}
"""
        fixture = Fixture.from_dict(
            {
                "especificidadesPrw": [
                    {
                        "fonte": "CONFIRMA.PRW",
                        "funcoes": [
                            {
                                "nome": "MSGYESNO",
                                "conteudo": "'Processar?', 'Teste'",
                                "retorno": True,
                            },
                            {
                                "nome": "MSGYESNO",
                                "conteudo": "'Cancelar?', 'Teste'",
                                "retorno": False,
                            },
                        ],
                    }
                ]
            }
        )

        result = run_source(
            source,
            fixture=fixture,
            entry="Confirma",
            source_name="CONFIRMA.PRW",
        )

        self.assertEqual([True, False], result)

    def test_identical_msgyesno_calls_can_differ_by_occurrence(self):
        source = """
User Function Confirma()
    Local lPrimeira := MsgYesNo('Repetir?')
    Local lSegunda := MsgYesNo('Repetir?')
Return {lPrimeira, lSegunda}
"""
        fixture = Fixture.from_dict(
            {
                "especificidadesPrw": [
                    {
                        "fonte": "CONFIRMA.PRW",
                        "funcoes": [
                            {
                                "nome": "MSGYESNO",
                                "conteudo": "'Repetir?'",
                                "ocorrencia": 1,
                                "retorno": True,
                            },
                            {
                                "nome": "MSGYESNO",
                                "conteudo": "'Repetir?'",
                                "ocorrencia": 2,
                                "retorno": False,
                            },
                        ],
                    }
                ]
            }
        )

        result = run_source(
            source,
            fixture=fixture,
            entry="Confirma",
            source_name="CONFIRMA.PRW",
        )

        self.assertEqual([True, False], result)

    def test_msgyesno_without_deterministic_result_fails(self):
        source = """
User Function Confirma()
Return MsgYesNo('Continuar?')
"""
        with self.assertRaisesRegex(
            AdvPLRuntimeError,
            "MsgYesNo.*CONFIRMA.PRW.*'Continuar\\?'",
        ):
            run_source(
                source,
                fixture=Fixture(),
                entry="Confirma",
                source_name="CONFIRMA.PRW",
            )

    def test_msgyesno_keeps_legacy_global_result(self):
        source = """
User Function Confirma()
Return MsgYesNo('Continuar?')
"""
        fixture = Fixture.from_dict({"funcoes": [{"MSGYESNO": True}]})
        self.assertTrue(
            run_source(
                source,
                fixture=fixture,
                entry="Confirma",
                source_name="CONFIRMA.PRW",
            )
        )

    def test_msgyesno_requires_boolean_result(self):
        with self.assertRaisesRegex(FixtureError, "MSGYESNO.*logico"):
            Fixture.from_dict(
                {
                    "especificidadesPrw": [
                        {
                            "fonte": "CONFIRMA.PRW",
                            "funcoes": [
                                {
                                    "nome": "MSGYESNO",
                                    "conteudo": "'Continuar?'",
                                    "retorno": "sim",
                                }
                            ],
                        }
                    ]
                }
            )


if __name__ == "__main__":
    unittest.main()
