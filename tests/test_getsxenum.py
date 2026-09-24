import json
import unittest
import uuid
from pathlib import Path

from fixture_runtime import Fixture, FixtureError, build_interpreter, run_sources
from interpreter import AdvPLRuntimeError


SOURCE = """User Function Insert()
    DbSelectArea('ZA2')
    RecLock('ZA2', .T.)
    ZA2_COD := GetSXENum('ZA2', 'ZA2_COD')
    MsUnlock()
Return Nil
"""


def fixture(records=None, width=6):
    return Fixture.from_dict({"tabelas": [{"ZA2": {
        "campos": [{"nome": "ZA2_COD", "tipo": "C"}],
        "numeracao": {"ZA2_COD": {"digitos": width, "inicio": 1}},
        "registros": records or [],
    }}]})


class GetSxeNumTests(unittest.TestCase):
    def test_number_is_zero_padded_and_reservations_are_unique(self):
        runtime = build_interpreter(SOURCE, fixture=fixture(), entry="Insert")
        self.assertEqual("000001", runtime.call_function("GetSXENum", ["ZA2", "ZA2_COD"]))
        self.assertEqual("000002", runtime.call_function("GetSXENum", ["ZA2", "ZA2_COD"]))

    def test_existing_records_define_next_number(self):
        runtime = build_interpreter(
            SOURCE, fixture=fixture([{"ZA2_COD": "000009"}]), entry="Insert")
        runtime.run("Insert")
        self.assertEqual("000010", runtime._aliases["ZA2"].records[-1]["ZA2_COD"])

    def test_persistence_keeps_sequence_between_runs(self):
        path = Path(__file__).parent / "fixtures" / "state" / f"state-{uuid.uuid4().hex}.json"
        self.addCleanup(path.unlink, missing_ok=True)
        data = fixture()
        for expected in ("000001", "000002"):
            run_sources([("insert.prw", SOURCE)], fixture=data,
                        entry="Insert", state_path=path)
            state = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(expected, state["tabelas"]["ZA2"][-1]["ZA2_COD"])
        self.assertEqual([], data.tabelas["ZA2"]["registros"])

    def test_missing_config_and_invalid_existing_code_fail(self):
        data = fixture()
        del data.tabelas["ZA2"]["numeracao"]
        runtime = build_interpreter(SOURCE, fixture=data, entry="Insert")
        with self.assertRaisesRegex(AdvPLRuntimeError, "configure numeracao"):
            runtime.run("Insert")
        runtime = build_interpreter(
            SOURCE, fixture=fixture([{"ZA2_COD": "ABC"}]), entry="Insert")
        with self.assertRaisesRegex(AdvPLRuntimeError, "nao numerico"):
            runtime.run("Insert")

    def test_invalid_config_and_overflow_fail(self):
        with self.assertRaisesRegex(FixtureError, "digitos positivos"):
            fixture(width=0)
        runtime = build_interpreter(
            SOURCE, fixture=fixture([{"ZA2_COD": "9"}], width=1), entry="Insert")
        with self.assertRaisesRegex(AdvPLRuntimeError, "excede"):
            runtime.run("Insert")


if __name__ == "__main__":
    unittest.main()
