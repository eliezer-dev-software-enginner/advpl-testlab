import json
import unittest
from pathlib import Path

from executor import discover_source_units, validate_file
from fixture_runtime import Fixture, build_interpreter_sources


FAT006 = Path(__file__).resolve().parents[2] / "desafios-aprendizado" / "desafio0-Fat006"


@unittest.skipUnless(FAT006.is_dir(), "corpus FAT006 nao disponivel")
class Fat006Tests(unittest.TestCase):
    def test_project_fixtures_declare_all_sections(self):
        required = {
            "parametros", "tabelas", "funcoes", "consultas",
            "especificidadesPrw", "ambiente", "dialogos",
        }
        fixtures = [
            FAT006 / "advpl-testlab.json",
            FAT006.parent / "desafio1-solicitacao-compra" / "advpl-testlab.json",
        ]
        for path in fixtures:
            with self.subTest(path=path):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertTrue(required <= data.keys(), required - data.keys())

    def interpreter(self, filename, entry, fixture=None):
        source = FAT006 / filename
        return build_interpreter_sources(
            discover_source_units(source),
            fixture=fixture or Fixture(),
            entry=entry,
            source_name=source,
        )

    def test_msgdanfe_consolidates_lines_without_duplicates(self):
        source = FAT006 / "U_MSGDANFE.prw"
        self.assertEqual(3, validate_file(source))
        interpreter = self.interpreter(source.name, "MSGDANFE")
        self.assertEqual(
            "Portal\r\nFiscal\r\nOutra",
            interpreter.run("MSGDANFE", ["Portal\r\nFiscal", "portal\nOutra"]),
        )
        self.assertIsNone(interpreter.run("MSGDANFE", [None, "Fiscal"]))

    def test_a410cons_is_semantically_valid(self):
        self.assertEqual(2, validate_file(FAT006 / "A410CONS.prw"))
        interpreter = self.interpreter(
            "A410CONS.prw", "A410CONS", Fixture.from_file(FAT006 / "advpl-testlab.json")
        )
        self.assertEqual(1, len(interpreter.run("A410CONS")))
        interpreter.run("UONGEXIB")

    def test_pe01nfesefaz_is_semantically_valid(self):
        self.assertEqual(2, validate_file(FAT006 / "PE01NFESEFAZ.prw"))

    def test_pe01nfesefaz_merges_order_message(self):
        interpreter = self.interpreter(
            "PE01NFESEFAZ.prw", "PE01NFESEFAZ",
            Fixture.from_file(FAT006 / "advpl-testlab.json"),
        )
        result = interpreter.run("PE01NFESEFAZ")
        self.assertEqual("Mensagem padrao\r\nMensagem fiscal", result[1])

    def test_pe01nfesefaz_leaves_incoming_note_unchanged(self):
        fixture = Fixture.from_file(FAT006 / "advpl-testlab.json")
        fixture.ambiente["PARAMIXB"][4][3] = "0"
        interpreter = self.interpreter("PE01NFESEFAZ.prw", "PE01NFESEFAZ", fixture)
        self.assertEqual("Mensagem padrao", interpreter.run("PE01NFESEFAZ")[1])

    def test_ufate003_uses_msgdanfe_and_updates_order(self):
        source = FAT006 / "UFATE003.prw"
        self.assertEqual(5, validate_file(source))
        interpreter = self.interpreter(
            source.name, "UFATE003", Fixture.from_file(FAT006 / "advpl-testlab.json")
        )
        self.assertTrue(interpreter.run("UFATE003"))
        self.assertEqual(
            "Mensagem do portal\r\nMensagem fiscal",
            interpreter._aliases["SC5"].records[0]["C5_MENNOT"],
        )
        self.assertTrue(interpreter.run("M410PVNF"))

    def test_ufate003_does_not_change_order_when_lock_fails(self):
        fixture = Fixture.from_file(FAT006 / "advpl-testlab.json")
        fixture.ambiente["RECLOCK_SC5"] = False
        interpreter = self.interpreter("UFATE003.prw", "UFATE003", fixture)
        self.assertFalse(interpreter.run("UFATE003"))
        self.assertEqual("Mensagem fiscal", interpreter._aliases["SC5"].records[0]["C5_MENNOT"])
