import json
import uuid
import unittest
from pathlib import Path

from fixture_runtime import Fixture, build_interpreter, run_sources
from interpreter import Interpreter


class CoreUtilitiesTests(unittest.TestCase):
    def test_pure_utilities_are_inherited_without_override(self):
        runtime = build_interpreter('Function Main()\nReturn Nil\n', fixture=Fixture())
        core = Interpreter._build_builtins(runtime)
        names = {'STRTRAN', 'CHR', 'AT', 'LEFT', 'ACLONE', 'ASCAN', 'TYPE',
                 'CTOD', 'DTOC', 'TRANSFORM', 'ENCODEUTF8', 'FREEOBJ',
                 'ERRORBLOCK', 'BREAK', 'CONOUT'}
        self.assertTrue(names <= core.keys())
        for name in names:
            self.assertEqual(core[name].__code__, runtime.builtins[name].__code__)

    def test_fixture_clock_and_date_fields_have_date_type(self):
        fixture = Fixture.from_dict({
            'ambiente': [{'DDATABASE': '2024-02-29'}, {'TIME': '12:34:56'}],
            'tabelas': [{'T01': {'campos': [{'nome': 'T01_DATA', 'tipo': 'D'}],
                                'registros': [{'T01_DATA': '2024-02-28'}]}}],
        })
        runtime = build_interpreter("""Function Main()
Return {ValType(Date()), DToC(Date()), Time(), Date() - T01->T01_DATA}
""", fixture=fixture)
        self.assertEqual(['D', '29/02/2024', '12:34:56', 1], runtime.run())

    def test_typed_dates_survive_state_roundtrip(self):
        fixture = Fixture.from_dict({'ambiente': [{'DDATABASE': '2024-02-29'}],
            'tabelas': [{'T01': {'campos': [{'nome': 'T01_DATA', 'tipo': 'D'}],
                                'registros': []}}]})
        source = """Function Main()
DbSelectArea('T01')
RecLock('T01', .T.)
T01_DATA := Date()
MsUnlock()
Return Nil
"""
        path = Path(__file__).parent / 'fixtures' / 'state' / ('state-' + uuid.uuid4().hex + '.json')
        self.addCleanup(path.unlink, missing_ok=True)
        run_sources([('teste.prw', source)], fixture=fixture, state_path=path)
        self.assertEqual('2024-02-29', json.loads(path.read_text())['tabelas']['T01'][0]['T01_DATA'])
        result = run_sources([('teste.prw', "Function Main()\nReturn ValType(T01->T01_DATA)\n")],
                             fixture=fixture, state_path=path)
        self.assertEqual('D', result)
