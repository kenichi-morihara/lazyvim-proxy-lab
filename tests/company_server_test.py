"""Company API reproduction tests. Upstream is local; no OpenAI account is used."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ai_lab', ROOT / 'lab/ai/server.py')
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


class CompanyServerTests(unittest.TestCase):
    def start(self, server):
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f'http://127.0.0.1:{server.server_port}'

    def post(self, base, payload, cookie='lab-session=demo'):
        request = urllib.request.Request(base + lab.ENDPOINT, data=json.dumps(payload).encode(),
                                         headers={'Content-Type': 'application/json', 'Cookie': cookie})
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as response:
            return response.code, response.read()

    @staticmethod
    def payload():
        return dict(guid='', premium=False, secondary=False, message='hello', fileMessage=[])

    def test_mock_cookie_and_request_validation(self):
        base = self.start(lab.create_server(port=0))
        self.assertEqual(self.post(base, self.payload(), cookie='expired')[0], 401)
        self.assertEqual(self.post(base, {'message': 'hello'})[0], 400)
        status, body = self.post(base, self.payload())
        self.assertEqual(status, 200)
        self.assertIn(b'data: [DONE]', body)

    def test_openai_backend_requires_explicit_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                lab.create_server(port=0, backend='openai')

    def test_wrapper_forwards_native_or_json_messages_without_company_cookie(self):
        received = []

        class Upstream(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                received.append((self.path, dict(self.headers), body))
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.end_headers()
                self.wfile.write(b'data: {"choices":[{"delta":{"content":"hello"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n')

        upstream = self.start(ThreadingHTTPServer(('127.0.0.1', 0), Upstream))
        with patch.dict(os.environ, {'OPENAI_BASE_URL': upstream + '/v1', 'OPENAI_MODEL': 'dummy', 'OPENAI_API_KEY': 'dummy-key',
                                     'NO_PROXY': '127.0.0.1', 'no_proxy': '127.0.0.1'}):
            base = self.start(lab.create_server(port=0, backend='openai'))
            payload = self.payload()
            tools = [{'type': 'function', 'function': {'name': 'echo', 'parameters': {'type': 'object'}}}]
            payload.update(messages=[{'role': 'user', 'content': 'native'}], tools=tools)
            self.assertEqual(self.post(base, payload)[0], 200)
            path, headers, body = received[-1]
            self.assertEqual(path, '/v1/chat/completions')
            self.assertEqual(headers.get('Authorization'), 'Bearer dummy-key')
            self.assertNotIn('Cookie', headers)
            self.assertNotIn('guid', body)
            self.assertEqual(body['tools'], tools)
            payload = self.payload()
            payload['message'] = json.dumps({'protocol': 'pi-company-v1', 'instructions': 'JSON only',
                                            'messages': [{'role': 'user', 'content': 'json'}], 'tools': tools})
            self.assertEqual(self.post(base, payload)[0], 200)
            body = received[-1][2]
            self.assertNotIn('tools', body)
            self.assertIn('JSON only', body['messages'][0]['content'])
            self.assertEqual(json.loads(body['messages'][-1]['content'])['messages'][-1]['content'], 'json')

    def test_upstream_redirect_is_not_followed_or_exposed(self):
        paths = []

        class Redirect(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                paths.append(self.path)
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(302)
                self.send_header('Location', '/secret-location')
                self.end_headers()

        upstream = self.start(ThreadingHTTPServer(('127.0.0.1', 0), Redirect))
        with patch.dict(os.environ, {'OPENAI_BASE_URL': upstream, 'OPENAI_MODEL': 'dummy', 'OPENAI_API_KEY': 'dummy-key',
                                     'NO_PROXY': '127.0.0.1', 'no_proxy': '127.0.0.1'}):
            base = self.start(lab.create_server(port=0, backend='openai'))
            status, body = self.post(base, self.payload())
            self.assertEqual(status, 502)
            self.assertEqual(paths, ['/chat/completions'])
            self.assertNotIn(b'secret-location', body)


if __name__ == '__main__':
    unittest.main()
