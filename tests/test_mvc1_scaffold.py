import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from executor import execute_file, validate_file
from fixture_runtime import Fixture

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import main
from scaffold import create_mvc1


class Mvc1ScaffoldTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        previous = Path.cwd()
        self.addCleanup(os.chdir, previous)
        os.chdir(directory.name)

    def invoke(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main(list(args))

    def test_custom_table_validates_and_includes_with_persistence(self):
        self.assertEqual(0, self.invoke('--mvc1', '--table', 'za4'))
        source = Path('Fontes/ZA4MVC.prw')
        config = Path('mock.json')
        original = config.read_bytes()
        self.assertIn("cenariosMvc", json.loads(original))
        fixture = Fixture.from_file(config)
        self.assertIn('ZA4', fixture.tabelas)
        self.assertEqual(4, validate_file(source))
        with contextlib.redirect_stdout(io.StringIO()):
            execute_file(source)
            result = execute_file(source, mvc_case='incluir-registro', persist=True)
        self.assertTrue(result['salvou'])
        self.assertEqual('000001', result['registros'][0]['ZA4_COD'])
        self.assertTrue(Path('state.json').is_file())
        self.assertEqual(original, config.read_bytes())
        self.assertIn("Static Function ViewDef()", source.read_text())

    def test_default_table(self):
        self.assertEqual(0, self.invoke('--mvc1'))
        self.assertTrue(Path('Fontes/ZA1MVC.prw').exists())

    def test_existing_files_are_preserved_without_partial_output(self):
        for name, other in [('Fontes/ZA4MVC.prw', 'mock.json'),
                            ('mock.json', 'Fontes/ZA4MVC.prw')]:
            with self.subTest(name=name):
                path = Path(name)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('conteudo existente')
                self.assertEqual(1, self.invoke('--mvc1', '--table', 'ZA4'))
                self.assertEqual('conteudo existente', path.read_text())
                self.assertFalse(Path(other).exists())
                path.unlink()

    def test_invalid_alias_and_unrelated_flags_create_nothing(self):
        for args in [('--mvc1', '--table', '../ZA4'), ('--mvc1', '--table', ''),
                     ('--mvc1', '--table', 'TOOLONG'), ('--mvc1', '--persist'),
                     ('--init', '--table', 'ZA4')]:
            with self.subTest(args=args):
                self.assertEqual(1, self.invoke(*args))
                self.assertEqual([], list(Path.cwd().iterdir()))

    def test_write_failure_removes_only_new_files(self):
        original = Path.open
        def fail_fixture(path, *args, **kwargs):
            if path.name == 'mock.json':
                raise PermissionError('falha simulada')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', fail_fixture):
            with self.assertRaises(PermissionError):
                create_mvc1('ZA4')
        self.assertEqual([], list(Path.cwd().iterdir()))

    def test_existing_fontes_directory_and_files_are_preserved(self):
        Path('Fontes').mkdir()
        existing = Path('Fontes/outro.prw')
        existing.write_text('fonte existente')
        self.assertEqual(0, self.invoke('--mvc1', '--table', 'ZA4'))
        self.assertEqual('fonte existente', existing.read_text())
        self.assertTrue(Path('Fontes/ZA4MVC.prw').is_file())

    def test_fontes_as_file_fails_without_creating_mock(self):
        Path('Fontes').write_text('arquivo existente')
        self.assertEqual(1, self.invoke('--mvc1'))
        self.assertFalse(Path('mock.json').exists())
        self.assertEqual('arquivo existente', Path('Fontes').read_text())
