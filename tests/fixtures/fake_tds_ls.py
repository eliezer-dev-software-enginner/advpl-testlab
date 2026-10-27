import json
import sys


def send(message):
    body = json.dumps({'jsonrpc': '2.0', **message}, ensure_ascii=False).encode('utf-8')
    sys.stdout.buffer.write(f'Content-Length: {len(body)}\r\n\r\n'.encode() + body)
    sys.stdout.buffer.flush()


while True:
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            sys.exit(0)
        if line == b'\r\n':
            break
        key, value = line.decode().split(':', 1)
        headers[key.lower()] = value.strip()
    message = json.loads(sys.stdin.buffer.read(int(headers['content-length'])))
    method = message.get('method')
    if 'id' not in message or not method:
        continue
    if method == 'initialize':
        send({'id': 'config', 'method': 'workspace/configuration', 'params': {'items': [{}]}})
        send({'method': 'window/logMessage', 'params': {'message': 'Simulação local'}})
        result = {'capabilities': {}}
    elif method == '$totvsserver/reconnect':
        result = {'connectionToken': 'FAKE_RENEWED', 'environment': 'dev', 'user': 'tester'}
    elif method == '$totvsserver/compilation':
        info = message['params']['compilationInfo']
        valid = (info['connectionToken'] == 'FAKE_RENEWED' and
                 info['environment'] == 'dev' and len(info['fileUris']) == 1)
        result = {'returnCode': 0 if valid else 1, 'compileInfos': []}
    elif method == 'neverReply':
        continue
    else:
        result = None
    send({'id': message['id'], 'result': result})
