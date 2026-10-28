import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from executor import execute_file
from fixture_runtime import Fixture, FixtureError, run_sources, build_interpreter
from interpreter import AdvPLRuntimeError
from browse_preview import render_browse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from main import main

SOURCE = (ROOT / 'examples/preview-browse.prw').read_text()


class BrowsePreviewTests(unittest.TestCase):
    def preview(self, fixture=None, source=SOURCE):
        fixture = fixture or Fixture.from_file(ROOT / 'fixtures/preview-browse.jsonc')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = run_sources([('preview.prw', source)], fixture=fixture, entry='Preview', preview=True)
        return output.getvalue(), result

    def test_title_actions_dates_and_values_match_mock(self):
        output, result = self.preview()
        self.assertIn('PREVIEW DO BROWSE | Cadastro de patrimonio', output)
        self.assertEqual(['Incluir', 'Alterar', 'Visualizar', 'Excluir'], result['acoes'])
        for value in ['Codigo', 'PROD1', '28/10/2026', '20,00', '600,00', 'Disponivel', 'Em uso']:
            self.assertIn(value, output)

    def test_headers_are_truncated_without_changing_data_or_metadata(self):
        columns = ['Situação do patrimônio']
        rows = [['Descrição completa do bem']]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            render_browse('Cadastro de patrimônio', 'ZA4', columns, rows, [], width=120)
        self.assertIn('| Situação do ', output.getvalue())
        self.assertNotIn('Situação do patrimônio', output.getvalue())
        self.assertIn('Descrição completa do bem', output.getvalue())
        self.assertIn('Cadastro de patrimônio', output.getvalue())
        self.assertEqual(['Situação do patrimônio'], columns)
        self.assertEqual([['Descrição completa do bem']], rows)

    def test_diagnostics_appear_above_browse_without_interrupting_tables(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            render_browse('Cadastro', 'ZA4', ['Coluna A', 'Coluna B'],
                          [['a' * 28, 'b' * 28]], [], width=40, total=30)
        diagnostics, browse = output.getvalue().split('=' * 40, 1)
        for label in ['Alias: ZA4', 'Simulacao local', 'Colunas divididas em 2 blocos',
                      'Mostrando os primeiros 1 de 30 registros.']:
            self.assertIn(label, diagnostics)
            self.assertNotIn(label, browse)
        self.assertIn('PREVIEW DO BROWSE | Cadastro', browse)
        self.assertIn('Coluna A', browse)
        self.assertIn('Coluna B', browse)
        self.assertNotIn('Colunas 1/2', browse)
        self.assertNotIn('Colunas 2/2', browse)

    def test_empty_table_still_renders_metadata(self):
        fixture = Fixture.from_file(ROOT / 'fixtures/preview-browse.jsonc')
        fixture.tabelas['T01']['registros'] = []
        output, result = self.preview(fixture)
        self.assertIn('Codigo', output)
        self.assertIn('Nenhum registro encontrado', output)
        self.assertEqual([], result['registros'])

    def test_preview_stops_at_browse_without_running_actions_or_later_code(self):
        source = SOURCE.replace('    oBrowse:Activate()\nReturn NIL', '    oBrowse:Activate()\n    UserException("NAO EXECUTAR")\nReturn NIL')
        output, _ = self.preview(source=source)
        self.assertIn('PREVIEW', output)
        self.assertNotIn('NAO EXECUTAR', output)

    def test_cli_discovers_parent_mock_and_does_not_change_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Fontes').mkdir()
            source = root / 'Fontes/preview.prw'
            source.write_text(SOURCE)
            fixture = root / 'mock.jsonc'
            fixture.write_bytes((ROOT / 'fixtures/preview-browse.jsonc').read_bytes())
            before = fixture.read_bytes()
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, main(['--preview', str(source)]))
            self.assertEqual(before, fixture.read_bytes())
            self.assertFalse((root / 'state.json').exists())

    def test_preview_rejects_persistence_and_mvc_case(self):
        for flag in [['--persist'], ['--mvc-case', 'qualquer']]:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(1, main(['--preview', str(ROOT / 'examples/preview-browse.prw'), *flag]))

    def test_source_without_browse_reports_error(self):
        with self.assertRaisesRegex(FixtureError, 'nao ativou um browse'):
            self.preview(source='User Function Preview()\nReturn Nil\n')

    def test_explicit_columns_and_calculated_values_are_evaluated_per_row(self):
        source = SOURCE.replace("    oBrowse:Activate()", "    oBrowse:AddColumn('T01_COD', 'Meu codigo')\n    oBrowse:SetFields({{'Produto calculado', {|| T01->T01_PROD}}})\n    oBrowse:Activate()")
        _, result = self.preview(source=source)
        self.assertEqual(['Meu codigo', 'Produto calculado'], result['colunas'])
        self.assertEqual([['000001', 'PROD1'], ['000002', 'MON1']], result['registros'])

    def test_width_and_control_characters_do_not_break_the_table(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            render_browse('Titulo', 'T01', ['Coluna A', 'Coluna B'],
                          [['a' * 50, '\x1b[31m\nvalor']], [], width=40)
        value = output.getvalue()
        self.assertIn('Colunas divididas em 2 blocos', value)
        self.assertNotIn('\x1b', value)
        self.assertIn('...', value)
        self.assertTrue(all(len(line) <= 40 for line in value.splitlines() if line.startswith('| ')))

    def test_menu_from_private_arotina_and_visible_fields(self):
        source = SOURCE.replace('    Local oBrowse :=', "    Local oBrowse :=").replace("    oBrowse:SetAlias", "    Private aRotina := {{'Acao customizada', 'VIEWDEF.Preview', 0, 2, 0}}\n    oBrowse:SetAlias")
        fixture = Fixture.from_file(ROOT / 'fixtures/preview-browse.jsonc')
        fixture.tabelas['T01']['campos'][0]['visivel'] = False
        _, result = self.preview(fixture=fixture, source=source)
        self.assertEqual(['Acao customizada'], result['acoes'])
        self.assertNotIn('Codigo', result['colunas'])

    def test_callback_failure_restores_alias_and_record_position(self):
        source = SOURCE.replace("    oBrowse:Activate()", "    oBrowse:SetFields({{'Erro', {|| 1 / 0}}})\n    oBrowse:Activate()")
        runtime = build_interpreter(source, fixture=Fixture.from_file(ROOT / 'fixtures/preview-browse.jsonc'), entry='Preview')
        runtime.preview = True
        runtime._aliases['T01'].position = 1
        previous_alias = runtime._current_alias
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(AdvPLRuntimeError):
            runtime.run('Preview')
        self.assertEqual(1, runtime._aliases['T01'].position)
        self.assertEqual(previous_alias, runtime._current_alias)
