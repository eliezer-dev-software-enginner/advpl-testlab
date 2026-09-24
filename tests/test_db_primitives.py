import unittest

from fixture_runtime import Fixture, build_interpreter
from interpreter import AdvPLRuntimeError


def fixture():
    return Fixture.from_dict({"tabelas": [{"T01": {
        "campos": [{"nome": "T01_COD", "tipo": "C"}],
        "indices": {"1": ["T01_COD"]},
        "apelidosIndices": {"CODIGO": 1},
        "registros": [{"T01_COD": "A"}, {"T01_COD": "B"}, {"T01_COD": "C"}],
    }}]})


def run(body, data=None):
    source = f"User Function Teste()\n{body}\nReturn Nil\n"
    runtime = build_interpreter(source, fixture=data or fixture(), entry="Teste")
    runtime.run("Teste")
    return runtime


class DbPrimitiveTests(unittest.TestCase):
    def test_all_requested_functions_are_registered(self):
        runtime = build_interpreter("User Function Teste()\nReturn Nil\n",
                                    fixture=fixture(), entry="Teste")
        names = {
            "DBSELECTAREA", "DBSETORDER", "DBRLOCK", "DBCLOSEAREA",
            "DBCOMMIT", "DBCOMMITALL", "DBDELETE", "DBGOTO", "DBGOTOP",
            "DBGOBOTTOM", "DBGOBOTTON", "DBRLOCKLIST", "DBSEEK", "MSSEEK",
            "DBSKIP", "DBSETFILTER", "DBORDERNICKNAME", "DBUNLOCK",
            "DBUNLOCKALL", "DBUSEAREA", "MSUNLOCK", "RECLOCK", "RLOCK",
            "SELECT", "SOFTLOCK", "UNLOCK",
        }
        self.assertFalse(names - set(runtime.builtins))

    def test_select_does_not_change_area_and_accepts_number(self):
        data = fixture()
        data.tabelas["T02"] = {"campos": [], "registros": []}
        runtime = run("""
    DbSelectArea(1)
    DbOrderNickname('CODIGO')
""", data=data)
        self.assertEqual("T01", runtime._current_alias)
        self.assertEqual(1, runtime.call_function("Select", ["T01"]))
        self.assertEqual(1, runtime.call_function("Select", []))
        self.assertEqual(2, runtime.call_function("Select", ["T02"]))
        self.assertEqual("T01", runtime._current_alias)
        self.assertEqual(1, runtime._aliases["T01"].order)

    def test_filter_skips_hidden_record_and_delete_is_logical(self):
        runtime = run("""
    DbSelectArea('T01')
    DbSetFilter({|| T01_COD != 'B'})
    DbGoTop()
    DbSkip()
""")
        self.assertEqual(2, runtime._aliases["T01"].position)
        runtime = run("""
    DbSelectArea('T01')
    DbGoTo(2)
    DbRLock()
    DbDelete()
    DbGoTop()
    DbSkip()
""")
        self.assertEqual(3, len(runtime._aliases["T01"].records))
        self.assertEqual(2, runtime._aliases["T01"].position)

    def test_navigation_seek_filter_and_soft_seek(self):
        runtime = run("""
    DbSelectArea('T01')
    DbSetOrder(1)
    DbSetFilter({|| T01_COD != 'B'}, 'T01_COD != B')
    DbGoTop()
    DbSkip()
    DbGoBottom()
    DbGoTo(1)
    DbSeek('C')
    MsSeek('C')
    DbSetFilter()
    DbGoTop()
    DbSkip(2)
    DbSkip(-1)
    DbGoBotton()
""")
        self.assertEqual(2, runtime._aliases["T01"].position)

    def test_locks_delete_commit_and_unlock(self):
        runtime = run("""
    DbSelectArea('T01')
    DbGoTo(2)
    DbRLock()
    RLock(1)
    DbRLock(3)
    SoftLock('T01')
    DbDelete()
    DbCommit()
    DbCommitAll()
    DbUnlock()
    DbRLock()
    Unlock()
    DbRLock()
    DbUnlockAll()
""")
        self.assertEqual("*", runtime._aliases["T01"].records[1]["D_E_L_E_T_"])
        self.assertEqual({}, runtime._record_locks)

    def test_reclock_msunlock_and_reopen(self):
        runtime = run("""
    DbSelectArea('T01')
    RecLock('T01', .T.)
    T01_COD := 'D'
    MsUnlock()
    DbCloseArea()
    DbUseArea(.T., 'TOPCONN', 'T01', 'T01', .T., .F.)
    DbGoTop()
""")
        self.assertEqual("D", runtime._aliases["T01"].records[-1]["T01_COD"])
        self.assertFalse(runtime._aliases["T01"].closed)

    def test_invalid_operations_fail_explicitly(self):
        for body, message in [
            ("DbUseArea(.T., 'TOPCONN', 'T99', 'T99')", "nao configurado"),
            ("DbGoTo(0)", "positivo"),
            ("DbSetFilter('not a block')", "bloco"),
            ("DbDelete()", "bloqueio"),
            ("DbOrderNickname('DESCONHECIDO')", "nao configurado"),
        ]:
            with self.subTest(body=body):
                with self.assertRaisesRegex(AdvPLRuntimeError, message):
                    run(body)


if __name__ == "__main__":
    unittest.main()
