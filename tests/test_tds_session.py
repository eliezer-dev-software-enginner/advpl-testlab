import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from executor import CompileError, compile_source_tree, find_tds_cli
from tds_session import LanguageServer, TdsSessionError, compile_connected, read_connected_server


class ConnectedSessionTests(unittest.TestCase):
    def data(self):
        return {'includes': ['/global'], 'connectedServer': {
            'id': 's1', 'type': 'totvs_server_protheus', 'name': 'Teste',
            'environment': 'dev', 'token': 'FAKE_CONNECTION', 'buildVersion': '7.00.240223P',
            'includes': [],
        }, 'savedTokens': [['s1:dev', {'token': 'FAKE_SAVED'}]],
            'rpoToken': {'token': 'FAKE_AUTH', 'enabled': True}}

    def read(self, data):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'servers.json'
            path.write_text(json.dumps(data))
            return read_connected_server(path)

    def test_home_discovery_and_saved_token_for_exact_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.totvsls').mkdir()
            (root / '.totvsls/servers.json').write_text(json.dumps(self.data()))
            with patch('tds_session.Path.home', return_value=root):
                server, token, includes, auth = read_connected_server()
            self.assertEqual(('dev', 'FAKE_SAVED', ['/global'], 'FAKE_AUTH'),
                             (server['environment'], token, includes, auth))

    def test_other_environment_token_is_not_used_and_server_includes_win(self):
        data = self.data()
        data['savedTokens'][0][0] = 's1:production'
        data['connectedServer']['includes'] = ['/specific']
        _, token, includes, _ = self.read(data)
        self.assertEqual('FAKE_CONNECTION', token)
        self.assertEqual(['/specific'], includes)

    def test_missing_session_and_missing_token_are_explicit_errors(self):
        for data in [{}, {'connectedServer': []}, {'connectedServer': {'type': 'totvs_server_protheus', 'environment': 'dev'}}]:
            with self.subTest(data=data), self.assertRaises(TdsSessionError):
                self.read(data)

    def test_bad_json_does_not_expose_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'servers.json'
            path.write_text('{"token":"DONT_PRINT"')
            with self.assertRaises(TdsSessionError) as error:
                read_connected_server(path)
            self.assertNotIn('DONT_PRINT', str(error.exception))

    def test_disabled_rpo_token_is_not_sent(self):
        data = self.data()
        data['rpoToken']['enabled'] = False
        self.assertEqual('', self.read(data)[3])

    def test_compile_protocol_uses_reconnected_token_and_ordered_uris(self):
        calls = []
        server, token, _, auth = self.read(self.data())
        class FakeClient:
            def __init__(self, *args): pass
            def request(self, method, params, **kwargs):
                calls.append((method, params))
                if method == '$totvsserver/reconnect':
                    return {'connectionToken': 'FAKE_REFRESHED', 'environment': 'dev', 'user': 'tester'}
                return {'returnCode': 0, 'compileInfos': []}
            def send(self, message): calls.append((message['method'], message.get('params')))
            def close(self): calls.append(('close', None))
        paths = [Path('/tmp/aux.prw'), Path('/tmp/main.prw')]
        with patch('tds_session.LanguageServer', FakeClient):
            compile_connected(paths, [Path('/tmp/includes')], 'advpls', server, token, auth)
        methods = [call[0] for call in calls]
        self.assertEqual(['initialize', 'initialized', '$totvsserver/reconnect', '$totvsserver/compilation', 'close'], methods)
        compilation = calls[3][1]['compilationInfo']
        self.assertEqual('FAKE_REFRESHED', compilation['connectionToken'])
        self.assertEqual('FAKE_AUTH', compilation['authorizationToken'])
        self.assertEqual([p.as_uri() for p in paths], compilation['fileUris'])
        self.assertFalse(compilation['compileOptions']['commitWithErrorOrWarning'])

    def test_rejected_token_wrong_environment_or_compile_error_never_report_success(self):
        server, token, _, auth = self.read(self.data())
        cases = [({}, None), ({'connectionToken': 'secret', 'environment': 'production'}, None),
                 ({'connectionToken': 'secret', 'environment': 'dev'}, {'returnCode': 1, 'compileInfos': []}),
                 ({'connectionToken': 'secret', 'environment': 'dev'}, {'returnCode': 0, 'compileInfos': [{'status': 'ERROR'}]}),
                 ({'connectionToken': 'secret', 'environment': 'dev'}, {})]
        for reconnect, result in cases:
            with self.subTest(reconnect=reconnect, result=result), patch('tds_session.LanguageServer') as cls:
                cls.return_value.request.side_effect = [{}, reconnect, result]
                with self.assertRaises(TdsSessionError) as error:
                    compile_connected([Path('/tmp/main.prw')], [], 'advpls', server, token, auth)
                self.assertNotIn('secret', str(error.exception))
                cls.return_value.close.assert_called_once()
                if result is None:
                    self.assertEqual(2, cls.return_value.request.call_count)

    def test_compile_defaults_to_saved_includes_and_explicit_include_overrides(self):
        root = Path(__file__).parent.resolve()
        source = root / 'fixtures/use_prw/entrada_escopo.prw'
        session = ({'environment': 'dev'}, 'FAKE', [str(root)], '')
        with patch('tds_session.read_connected_server', return_value=session), \
                patch('tds_session.compile_connected') as compile_mock:
            compile_source_tree(source, cli_path=sys.executable)
            self.assertEqual([root], compile_mock.call_args.args[1])
            compile_source_tree(source, cli_path=sys.executable, includes=[str(root / 'fixtures')])
            self.assertEqual([root / 'fixtures'], compile_mock.call_args.args[1])

    def test_cli_compiles_without_ini_and_dry_run_never_reads_session(self):
        from main import main
        source = Path(__file__).parent / 'fixtures/use_prw/entrada_escopo.prw'
        with patch('main.compile_source_tree') as compile_mock, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, main(['-compile', str(source)]))
            self.assertIsNone(compile_mock.call_args.kwargs['config_path'])
        with patch('tds_session.read_connected_server') as session_reader, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, main(['-compile', str(source), '--dry-run']))
            session_reader.assert_not_called()

    def test_linux_binary_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / '.vscode/extensions/totvs.tds-vscode-9.0/node_modules/@totvs/tds-ls/bin/linux/advpls'
            binary.parent.mkdir(parents=True)
            binary.touch()
            with patch('executor.Path.home', return_value=root), patch('executor.shutil.which', return_value=None), patch('executor.sys.platform', 'linux'):
                self.assertEqual(binary, find_tds_cli())

class ProtocolTransportTests(unittest.TestCase):
    def test_real_subprocess_framing_notifications_and_server_requests(self):
        import subprocess
        real_popen = subprocess.Popen
        script = Path(__file__).parent / 'fixtures/fake_tds_ls.py'
        commands = []
        def spawn(command, **kwargs):
            commands.append(command)
            return real_popen([sys.executable, str(script)], **kwargs)
        output = io.StringIO()
        with patch('tds_session.subprocess.Popen', side_effect=spawn), contextlib.redirect_stdout(output):
            compile_connected([Path('/tmp/ação.prw')], [Path('/tmp/includes')],
                              'fake-advpls', {'environment': 'dev', 'name': 'Teste'}, 'FAKE_SAVED')
        self.assertEqual([['fake-advpls', 'language-server']], commands)
        self.assertNotIn('FAKE_SAVED', output.getvalue())

    def test_timeout_closes_child_process(self):
        import subprocess
        real_popen = subprocess.Popen
        script = Path(__file__).parent / 'fixtures/fake_tds_ls.py'
        with patch('tds_session.subprocess.Popen', side_effect=lambda command, **kwargs:
                   real_popen([sys.executable, str(script)], **kwargs)):
            client = LanguageServer('fake-advpls', Path.cwd(), timeout=0.1)
        try:
            with self.assertRaisesRegex(TdsSessionError, 'Tempo esgotado'):
                client.request('neverReply', {})
        finally:
            client.close()
        self.assertIsNotNone(client.process.poll())
