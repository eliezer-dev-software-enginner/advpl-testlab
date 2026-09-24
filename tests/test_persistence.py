import contextlib
import io
import json
import unittest
import uuid
from pathlib import Path

from fixture_runtime import Fixture, FixtureError, run_sources
from state_store import StateError
from test_mvc_cases import SOURCE as MVC_SOURCE, make_fixture as mvc_fixture


SOURCE = """User Function Insert()
DbSelectArea('ZA2')
RecLock('ZA2', .T.)
ZA2_NOME := 'Paulo'
MsUnlock()
Return NIL
"""


class PersistenceTests(unittest.TestCase):
    def fixture(self):
        return Fixture.from_dict({"tabelas": [{"ZA2": {
            "campos": [{"nome": "ZA2_NOME", "tipo": "C"}], "registros": [],
        }}]})

    def state_path(self):
        path = Path(__file__).parent / "fixtures" / "state" / f"state-{uuid.uuid4().hex}.json"
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def test_reclock_state_survives_new_runtime_without_changing_fixture(self):
        fixture = self.fixture()
        path = self.state_path()
        for count in (1, 2):
            run_sources([("insert.prw", SOURCE)], fixture=fixture,
                        entry="Insert", state_path=path)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(count, len(data["tabelas"]["ZA2"]))
        self.assertEqual([], fixture.tabelas["ZA2"]["registros"])

    def test_mvc_inclusion_persists_and_next_browse_loads_it(self):
        fixture = mvc_fixture()
        path = self.state_path()
        result = run_sources([("demo.prw", MVC_SOURCE)], fixture=fixture,
                             entry="DemoMvc", mvc_case="valido", state_path=path)
        self.assertTrue(result["salvou"])
        self.assertEqual(2, len(json.loads(path.read_text(encoding="utf-8"))["tabelas"]["ZA1"]))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            run_sources([("demo.prw", MVC_SOURCE)], fixture=fixture,
                        entry="DemoMvc", state_path=path)
        self.assertIn("002", output.getvalue())
        self.assertEqual(1, len(fixture.tabelas["ZA1"]["registros"]))

    def test_failed_mvc_expectation_does_not_write_state(self):
        fixture = mvc_fixture()
        fixture.cenarios_mvc["valido"]["esperado"]["totalRegistros"] = 99
        path = self.state_path()
        with self.assertRaisesRegex(FixtureError, "totalRegistros"):
            run_sources([("demo.prw", MVC_SOURCE)], fixture=fixture,
                        entry="DemoMvc", mvc_case="valido", state_path=path)
        self.assertFalse(path.exists())

    def test_rejected_mvc_inclusion_does_not_create_state(self):
        path = self.state_path()
        with contextlib.redirect_stdout(io.StringIO()):
            result = run_sources([("demo.prw", MVC_SOURCE)], fixture=mvc_fixture(),
                                 entry="DemoMvc", mvc_case="bloqueado", state_path=path)
        self.assertFalse(result["salvou"])
        self.assertFalse(path.exists())

    def test_failed_mvc_expectation_preserves_existing_state(self):
        path = self.state_path()
        fixture = mvc_fixture()
        with contextlib.redirect_stdout(io.StringIO()):
            run_sources([("demo.prw", MVC_SOURCE)], fixture=fixture,
                        entry="DemoMvc", mvc_case="valido", state_path=path)
        original = path.read_bytes()
        fixture.cenarios_mvc["valido"]["esperado"]["totalRegistros"] = 99
        with self.assertRaisesRegex(FixtureError, "totalRegistros"):
            run_sources([("demo.prw", MVC_SOURCE)], fixture=fixture,
                        entry="DemoMvc", mvc_case="valido", state_path=path)
        self.assertEqual(original, path.read_bytes())

    def test_read_only_browse_does_not_create_state(self):
        path = self.state_path()
        with contextlib.redirect_stdout(io.StringIO()):
            run_sources([("demo.prw", MVC_SOURCE)], fixture=mvc_fixture(),
                        entry="DemoMvc", state_path=path)
        self.assertFalse(path.exists())

    def test_corrupted_state_is_rejected_without_overwriting(self):
        path = self.state_path()
        path.write_text("{bad", encoding="utf-8")
        with self.assertRaisesRegex(StateError, "state.json invalido"):
            run_sources([("insert.prw", SOURCE)], fixture=self.fixture(),
                        entry="Insert", state_path=path)
        self.assertEqual("{bad", path.read_text(encoding="utf-8"))

    def test_unknown_alias_in_state_is_rejected(self):
        path = self.state_path()
        path.write_text('{"versao":1,"tabelas":{"XYZ":[]}}', encoding="utf-8")
        with self.assertRaisesRegex(StateError, "XYZ"):
            run_sources([("insert.prw", SOURCE)], fixture=self.fixture(),
                        entry="Insert", state_path=path)


if __name__ == "__main__":
    unittest.main()
