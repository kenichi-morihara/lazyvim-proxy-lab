"""Optional live Pi integration: EDITOR_PI_TEST_PREFIX=/path/to/prefix python3 tests/pi_test.py."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest

PREFIX = os.environ.get('EDITOR_PI_TEST_PREFIX')


@unittest.skipUnless(PREFIX, 'set EDITOR_PI_TEST_PREFIX after make setup-pi')
class PiTests(unittest.TestCase):
    def test_internal_provider_tool_roundtrip_without_external_traffic(self):
        requests = []
        external = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_CONNECT(self):
                external.append(self.path)
                self.send_error(502)

            def do_GET(self):
                external.append(self.path)
                self.send_error(502)

            def do_POST(self):
                if self.path != '/v1/chat/completions':
                    external.append(self.path)
                    return self.send_error(502)
                data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append((dict(self.headers), data))
                if len(requests) == 1:
                    delta = {'role': 'assistant', 'tool_calls': [{'index': 0, 'id': 'call_read', 'type': 'function',
                             'function': {'name': 'read', 'arguments': '{"path":"sample.txt"}'}}]}
                    reason = 'tool_calls'
                else:
                    delta = {'role': 'assistant', 'content': 'internal mock OK'}
                    reason = 'stop'
                chunks = [
                    {'id': 'mock', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'dummy-model',
                     'choices': [{'index': 0, 'delta': delta, 'finish_reason': None}]},
                    {'id': 'mock', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'dummy-model',
                     'choices': [{'index': 0, 'delta': {}, 'finish_reason': reason}]},
                ]
                payload = ''.join('data: ' + json.dumps(chunk) + '\n\n' for chunk in chunks) + 'data: [DONE]\n\n'
                encoded = payload.encode()
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Content-Length', str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with tempfile.TemporaryDirectory(prefix='pi-check-') as directory:
            root = Path(directory)
            (root / 'sample.txt').write_text('local-tool-fixture\n')
            origin = 'http://127.0.0.1:' + str(server.server_port)
            env = dict(os.environ, HOME=directory, XDG_STATE_HOME=str(root / 'state'),
                       INTERNAL_AI_BASE_URL=origin + '/v1', INTERNAL_AI_MODEL='dummy-model',
                       INTERNAL_AI_API_KEY='dummy-private-key')
            for name in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy'):
                env[name] = origin
            for name in ('NO_PROXY', 'no_proxy'):
                env[name] = '127.0.0.1,localhost'
            for header in ('Authorization', 'api-key'):
                requests.clear()
                env['INTERNAL_AI_AUTH_HEADER'] = header
                result = subprocess.run([str(Path(PREFIX) / 'bin/pi'), '-p', '--no-session', 'Read sample.txt'],
                                        cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, timeout=40)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('internal mock OK', result.stdout)
                self.assertEqual(len(requests), 2)
                headers, first = requests[0]
                headers = {key.lower(): value for key, value in headers.items()}
                self.assertEqual(headers.get(header.lower()), 'Bearer dummy-private-key' if header == 'Authorization' else 'dummy-private-key')
                self.assertEqual(first['model'], 'dummy-model')
                self.assertTrue(first['stream'])
                self.assertIn('read', [tool['function']['name'] for tool in first['tools']])
                self.assertTrue(any(message.get('role') == 'tool' and 'local-tool-fixture' in str(message.get('content'))
                                    for message in requests[1][1]['messages']))
                self.assertEqual(list((root / 'state/editor-pi').glob('runtime-*')), [])
            self.assertEqual(external, [], 'Pi attempted external management/provider traffic')


if __name__ == '__main__':
    unittest.main()
