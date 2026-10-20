"""Real Pi Responses integration against a local fake service; no paid API calls."""
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
class ResponsesPiTests(unittest.TestCase):
    def test_user_header_read_edit_and_tool_result_roundtrip(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append((self.path, dict(self.headers), body))
                index = len(requests)
                probe = next((t for t in body['tools'] if t.get('name') == 'diagnostic_echo'), None)
                if probe:
                    item = {'type': 'function_call', 'id': 'fc_probe', 'call_id': 'call_probe', 'name': 'diagnostic_echo',
                            'arguments': json.dumps({'nonce': probe['parameters']['properties']['nonce']['const']}), 'status': 'completed'}
                elif index < 3:
                    arguments = {'path': 'sample.txt'} if index == 1 else {
                        'path': 'sample.txt', 'edits': [{'oldText': 'before', 'newText': 'after'}]}
                    # Follow the installed Pi tool schema, including older single-edit variants.
                    edit = next((t for t in body['tools'] if t.get('name') == 'edit'), {})
                    if index == 2 and 'edits' not in edit.get('parameters', {}).get('properties', {}):
                        arguments = {'path': 'sample.txt', 'oldText': 'before', 'newText': 'after'}
                    item = {'type': 'function_call', 'id': 'fc_' + str(index), 'call_id': 'call_' + str(index),
                            'name': 'read' if index == 1 else 'edit', 'arguments': json.dumps(arguments), 'status': 'completed'}
                else:
                    item = {'type': 'message', 'id': 'msg_final', 'role': 'assistant', 'status': 'completed',
                            'content': [{'type': 'output_text', 'text': 'Responses 日本語 OK', 'annotations': []}]}
                response = {'id': 'resp_' + str(index), 'object': 'response', 'created_at': 1,
                            'status': 'completed', 'model': 'test-responses', 'output': [item],
                            'usage': {'input_tokens': 10, 'output_tokens': 5, 'total_tokens': 15}}
                events = [
                    {'type': 'response.created', 'response': dict(response, status='in_progress', output=[])},
                    {'type': 'response.output_item.added', 'output_index': 0, 'item': dict(item, arguments='') if item['type'] == 'function_call' else dict(item, content=[])},
                    {'type': 'response.output_item.done', 'output_index': 0, 'item': item},
                    {'type': 'response.completed', 'response': response},
                ]
                payload = ''.join('event: ' + e['type'] + '\ndata: ' + json.dumps(e) + '\n\n' for e in events).encode()
                self.send_response(200)
                if not body['stream']:
                    payload = json.dumps(response).encode()
                self.send_header('Content-Type', 'text/event-stream' if body['stream'] else 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = {k: v for k, v in os.environ.items() if not k.startswith('INTERNAL_AI_')}
            env.update(HOME=directory, XDG_STATE_HOME=str(root / 'state'), INTERNAL_AI_TRANSPORT='openai',
                       INTERNAL_AI_BASE_URL=f'http://127.0.0.1:{server.server_port}/v1',
                       INTERNAL_AI_MODEL='test-responses', INTERNAL_AI_USER_HEADER='X-Company-User',
                       INTERNAL_AI_USER='private-test-user', NO_PROXY='127.0.0.1,localhost', no_proxy='127.0.0.1,localhost')
            for api_key, api, streaming in (('', None, True), ('private-test-key', None, True), ('private-test-key', 'openai-responses', True), ('private-test-key', None, False)):
                with self.subTest(api_key_present=bool(api_key), api=api, streaming=streaming):
                    env['INTERNAL_AI_STREAM'] = str(streaming).lower()
                    if api:
                        env['INTERNAL_AI_API'] = api
                    else:
                        env.pop('INTERNAL_AI_API', None)
                    requests.clear()
                    env['INTERNAL_AI_API_KEY'] = api_key
                    (root / 'sample.txt').write_text('before\n')
                    run_env = dict(env)
                    if api_key and api is None:
                        settings = root / '.config/editor-pi/connection.json'
                        settings.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                        settings.write_text(json.dumps({k: v for k, v in env.items() if k.startswith('INTERNAL_AI_')}))
                        settings.chmod(0o600)
                        run_env = {k: v for k, v in env.items() if not k.startswith('INTERNAL_AI_')}
                    result = subprocess.run([str(Path(PREFIX) / 'bin/pi'), '-p', '--no-session', '--tools', 'read,edit',
                                             'Read sample.txt, replace before with after, then report completion.'],
                                            cwd=root, env=run_env, capture_output=True, text=True, timeout=40)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn('Responses 日本語 OK', result.stdout)
                    self.assertEqual((root / 'sample.txt').read_text(), 'after\n')
                    self.assertEqual(len(requests), 3)
                    for path, headers, body in requests:
                        headers = {k.lower(): v for k, v in headers.items()}
                        self.assertEqual(path, '/v1/responses')
                        self.assertEqual(headers['x-company-user'], 'private-test-user')
                        self.assertEqual(headers.get('authorization', ''), 'Bearer ' + api_key if api_key else '')
                        self.assertEqual(body['model'], 'test-responses')
                        self.assertEqual(body['stream'], streaming)
                        self.assertIn('input', body)
                        self.assertNotIn('messages', body)
                        self.assertTrue(all('status' not in item for item in body['input'] if isinstance(item, dict)))
                    self.assertTrue(any(i.get('type') == 'function_call_output' and 'before' in str(i.get('output'))
                                        for i in requests[1][2]['input']))
                    self.assertEqual(list((root / 'state/editor-pi').glob('runtime-*')), [])
                    self.assertNotIn('private-test-user', result.stdout + result.stderr)
                    self.assertNotIn('private-test-key', result.stdout + result.stderr)
            requests.clear()
            env.pop('INTERNAL_AI_API', None)
            env['PI_DOCTOR_PROBE'] = '1'
            result = subprocess.run([str(Path(PREFIX) / 'bin/pi'), '--doctor'], cwd=root, env=env,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('no tool executed', result.stdout)
            self.assertEqual(len(requests), 1)
            env.pop('PI_DOCTOR_PROBE')
            requests.clear()
            for header, value in [('Authorization', 'private-test-user'), ('X-User', 'bad\r\nInjected: value')]:
                env.update(INTERNAL_AI_USER_HEADER=header, INTERNAL_AI_USER=value)
                result = subprocess.run([str(Path(PREFIX) / 'bin/pi'), '-p', '--no-session', 'hello'],
                                        cwd=root, env=env, capture_output=True, text=True, timeout=15)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(value, result.stdout + result.stderr)
            self.assertEqual(requests, [])


if __name__ == '__main__':
    unittest.main()
