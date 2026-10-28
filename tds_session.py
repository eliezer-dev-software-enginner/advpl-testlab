import json
import os
import queue
import signal
import subprocess
import threading
import tempfile
from pathlib import Path


class TdsSessionError(ValueError):
    pass


def read_connected_server(path=None):
    path = Path(path) if path else Path.home() / '.totvsls' / 'servers.json'
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        raise TdsSessionError('Nao foi possivel ler ~/.totvsls/servers.json; conecte pelo VS Code.') from None
    server = data.get('connectedServer') if isinstance(data, dict) else None
    if not isinstance(server, dict) or server.get('type') != 'totvs_server_protheus':
        raise TdsSessionError('Nao foi encontrada uma conexao Protheus valida na sessao salva do VS Code. Se houver uma sessao ativa no Protheus impedindo a compilacao, encerre-a. Depois, conecte ou reconecte o servidor pelo VS Code e tente novamente.')
    environment = server.get('environment')
    if not isinstance(environment, str) or not environment:
        raise TdsSessionError('Ambiente conectado ausente; reconecte pelo VS Code.')
    token = None
    saved_tokens = data.get('savedTokens') or []
    if not isinstance(saved_tokens, list):
        raise TdsSessionError('Lista de tokens invalida; reconecte pelo VS Code.')
    for item in saved_tokens:
        if (isinstance(item, list) and len(item) == 2 and
                item[0] == f"{server.get('id')}:{environment}" and isinstance(item[1], dict)):
            token = item[1].get('token')
            break
    token = token or server.get('token')
    if not isinstance(token, str) or not token:
        raise TdsSessionError('Token de sessao ausente; reconecte pelo VS Code.')
    includes = server.get('includes') or data.get('includes') or []
    if not isinstance(includes, list) or any(not isinstance(item, str) for item in includes):
        raise TdsSessionError('Includes invalidos em servers.json; ajuste no VS Code ou use --include.')
    authorization = ''
    if str(server.get('buildVersion', '')) > '7.00.191205P':
        rpo = data.get('rpoToken') or {}
        if isinstance(rpo, dict) and rpo.get('enabled', True):
            authorization = rpo.get('token', '')
    else:
        permissions = data.get('permissions') or {}
        if isinstance(permissions, dict):
            authorization = permissions.get('authorizationToken', permissions.get('authorizationtoken', ''))
    if not isinstance(authorization, str):
        raise TdsSessionError('Token de autorizacao invalido; ajuste no VS Code.')
    return server, token, includes, authorization


class LanguageServer:
    def __init__(self, executable, root, timeout=60):
        self.root = Path(root).resolve()
        self.timeout = timeout
        self.sequence = 0
        self.messages = queue.Queue()
        self.directory = tempfile.TemporaryDirectory(prefix='advplab-lsp-')
        try:
            self.process = subprocess.Popen(
                [str(executable), 'language-server'], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                start_new_session=(os.name != 'nt'), cwd=self.directory.name,
            )
        except OSError:
            self.directory.cleanup()
            raise
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        try:
            while True:
                headers = {}
                while True:
                    line = self.process.stdout.readline()
                    if not line:
                        raise EOFError()
                    if line in (b'\r\n', b'\n'):
                        break
                    name, value = line.decode('ascii').split(':', 1)
                    headers[name.lower()] = value.strip()
                length = int(headers['content-length'])
                if not 0 < length <= 16 * 1024 * 1024:
                    raise ValueError()
                chunks = bytearray()
                while len(chunks) < length:
                    chunk = self.process.stdout.read(length - len(chunks))
                    if not chunk:
                        raise EOFError()
                    chunks.extend(chunk)
                message = json.loads(chunks)
                if not isinstance(message, dict):
                    raise ValueError()
                self.messages.put(message)
        except (OSError, ValueError, KeyError, EOFError):
            self.messages.put(None)

    def send(self, message):
        body = json.dumps({'jsonrpc': '2.0', **message}, ensure_ascii=False).encode('utf-8')
        try:
            self.process.stdin.write(f'Content-Length: {len(body)}\r\n\r\n'.encode('ascii') + body)
            self.process.stdin.flush()
        except (OSError, ValueError):
            raise TdsSessionError('Language Server encerrou a comunicacao.') from None

    def request(self, method, params, timeout=None):
        import time
        self.sequence += 1
        request_id = self.sequence
        self.send({'id': request_id, 'method': method, 'params': params})
        deadline = time.monotonic() + (timeout or self.timeout)
        while True:
            try:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise queue.Empty()
                message = self.messages.get(timeout=remaining)
            except queue.Empty:
                raise TdsSessionError(f'Tempo esgotado aguardando {method}.') from None
            if message is None:
                raise TdsSessionError('Language Server encerrou antes de responder.')
            if 'method' in message and 'id' in message:
                if message['method'] == 'workspace/configuration':
                    result = [{} for _ in message.get('params', {}).get('items', [])]
                elif message['method'] == 'workspace/workspaceFolders':
                    result = [{'uri': self.root.as_uri(), 'name': self.root.name}]
                elif message['method'] in ('client/registerCapability', 'window/workDoneProgress/create'):
                    result = None
                else:
                    self.send({'id': message['id'], 'error': {'code': -32601, 'message': 'Unsupported method'}})
                    continue
                self.send({'id': message['id'], 'result': result})
            elif message.get('id') == request_id:
                if 'error' in message:
                    code = message['error'].get('code')
                    raise TdsSessionError(f'Falha em {method} (codigo {code}); reconecte pelo VS Code.')
                return message.get('result')

    def close(self):
        def stop(force=False):
            if os.name != 'nt':
                try:
                    os.killpg(self.process.pid, signal.SIGKILL if force else signal.SIGTERM)
                except ProcessLookupError:
                    pass
            elif self.process.poll() is None:
                self.process.kill() if force else self.process.terminate()
        stop()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            stop(force=True)
            self.process.wait(timeout=5)
        stop(force=True)
        self.process.stdin.close()
        self.reader.join(timeout=2)
        if not self.reader.is_alive():
            self.process.stdout.close()
        self.directory.cleanup()


def compile_connected(paths, includes, executable, server, token, authorization=''):
    client = LanguageServer(executable, Path.cwd())
    try:
        client.request('initialize', {
            'processId': os.getpid(), 'rootPath': str(Path.cwd()), 'rootUri': Path.cwd().as_uri(),
            'capabilities': {'workspace': {'configuration': True, 'workspaceFolders': True}}, 'initializationOptions': {},
            'workspaceFolders': [{'uri': Path.cwd().as_uri(), 'name': Path.cwd().name}],
        })
        client.send({'method': 'initialized', 'params': {}})
        reconnect = client.request('$totvsserver/reconnect', {'reconnectInfo': {
            'connectionToken': token, 'serverName': server.get('name', ''), 'connType': 3,
        }})
        if not isinstance(reconnect, dict) or not reconnect.get('connectionToken'):
            raise TdsSessionError('Token recusado ou expirado; reconecte pelo VS Code.')
        if reconnect.get('environment') != server['environment']:
            raise TdsSessionError('Ambiente da sessao difere do servidor conectado; reconecte pelo VS Code.')
        result = client.request('$totvsserver/compilation', {'compilationInfo': {
            'connectionToken': reconnect['connectionToken'], 'authorizationToken': authorization,
            'environment': server['environment'],
            'includeUris': [path.as_uri() for path in includes],
            'fileUris': [path.as_uri() for path in paths],
            'compileOptions': {
                'recompile': True, 'syntaxOnly': False, 'debugAphInfo': True,
                'gradualSending': True, 'generatePpoFile': False, 'showPreCompiler': False,
                'priorVelocity': True, 'returnPpo': False, 'commitWithErrorOrWarning': False,
            }, 'includeUrisRequired': True, 'syntaxOnly': False,
        }}, timeout=600)
        if not isinstance(result, dict) or 'returnCode' not in result:
            raise TdsSessionError('Resposta de compilacao invalida; sucesso nao confirmado.')
        infos = result.get('compileInfos', [])
        if (not isinstance(infos, list) or any(not isinstance(info, dict) for info in infos) or
                not isinstance(result['returnCode'], int)):
            raise TdsSessionError('Resposta de compilacao invalida; sucesso nao confirmado.')
        failures = [info for info in infos if info.get('status') in ('FATAL', 'ERROR')]
        if result['returnCode'] != 0 or failures:
            messages = []
            for info in failures:
                message = str(info.get('message', 'Erro de compilacao'))
                for secret in (token, reconnect['connectionToken'], authorization):
                    if secret:
                        message = message.replace(secret, '[token omitido]')
                messages.append(message)
            detail = '\n'.join(messages)
            raise TdsSessionError(f"Compilacao falhou (codigo {result['returnCode']}, {len(failures)} erro(s))." +
                                  ('\n' + detail if detail else ''))
    finally:
        client.close()
