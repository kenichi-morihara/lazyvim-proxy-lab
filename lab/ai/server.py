#!/usr/bin/env python3
"""Local company-chat reproduction. Mock by default; explicit OpenAI backend only."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ENDPOINT = "/nomuchat/sendmessageforstream"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def request_parts(payload):
    required = {"guid": str, "premium": bool, "secondary": bool, "message": str, "fileMessage": list}
    if not isinstance(payload, dict) or any(type(payload.get(key)) is not kind for key, kind in required.items()):
        raise ValueError("invalid company request")
    if payload["fileMessage"]:
        raise ValueError("file attachments are not supported")
    try:
        envelope = json.loads(payload["message"])
    except ValueError:
        envelope = None
    if isinstance(envelope, dict) and envelope.get("protocol") == "pi-company-v1":
        messages = envelope["messages"]
        tools = envelope.get("tools", [])
        instructions = envelope["instructions"] + "\nAvailable tool schemas:\n" + json.dumps(tools)
        return [{"role": "system", "content": instructions}, *messages], tools, "json"
    return payload.get("messages") or [{"role": "user", "content": payload["message"]}], payload.get("tools", []), "native"


def mock_answer(messages, tools):
    declarations = {tool["function"]["name"]: tool["function"] for tool in tools}
    if "diagnostic_echo" in declarations:
        nonce = declarations["diagnostic_echo"]["parameters"]["properties"]["nonce"]["const"]
        return {"type": "tool_calls", "calls": [{"id": "probe", "name": "diagnostic_echo", "arguments": {"nonce": nonce}}]}
    user_text = " ".join(str(message.get("content", "")) for message in messages if message["role"] == "user")
    results = [message for message in messages if message["role"] == "tool"]
    if "edit sample.txt" in user_text and {"read", "edit"} <= declarations.keys():
        if not results:
            return {"type": "tool_calls", "calls": [{"id": "read_sample", "name": "read", "arguments": {"path": "sample.txt"}}]}
        if len(results) == 1:
            arguments = {"path": "sample.txt", "oldText": "before", "newText": "after"}
            if "edits" in declarations["edit"].get("parameters", {}).get("properties", {}):
                arguments = {"path": "sample.txt", "edits": [{"oldText": "before", "newText": "after"}]}
            return {"type": "tool_calls", "calls": [{"id": "edit_sample", "name": "edit", "arguments": arguments}]}
        return {"type": "text", "text": "mock edit complete 日本語"}
    return {"type": "text", "text": "mock reply 日本語: " + user_text[-200:]}


def mock_events(answer, mode):
    def event(delta, finish=None):
        return {"id": "lab-mock", "object": "chat.completion.chunk", "created": int(time.time()), "model": "lab-mock",
                "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
    if mode == "json":
        text = json.dumps(answer, ensure_ascii=False)
    elif answer["type"] == "tool_calls":
        yield event({"role": "assistant", "tool_calls": [{"index": i, "id": call["id"], "type": "function", "function": {
            "name": call["name"], "arguments": json.dumps(call["arguments"])}} for i, call in enumerate(answer["calls"])]})
        yield event({}, "tool_calls")
        return
    else:
        text = answer["text"]
    for position in range(0, len(text), 16):
        yield event({"content": text[position:position + 16]})
    yield event({}, "stop")


def create_server(host="127.0.0.1", port=8766, backend="mock"):
    if backend not in ("mock", "openai"):
        raise ValueError("PI_LAB_BACKEND must be mock or openai")
    if backend == "openai" and not all(os.environ.get(key) for key in ("OPENAI_API_KEY", "OPENAI_MODEL")):
        raise ValueError("OpenAI backend requires OPENAI_API_KEY and OPENAI_MODEL")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def setup(self):
            super().setup()
            self.connection.settimeout(120)

        def reply(self, status, value):
            encoded = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self):
            if self.path == "/health":
                self.reply(200, {"status": "ready", "backend": backend})
            else:
                self.reply(404, {"error": "not found"})

        def do_POST(self):
            if self.path != ENDPOINT:
                return self.reply(404, {"error": "not found"})
            expected = os.environ.get("PI_LAB_COOKIE", "lab-session=demo")
            if not hmac.compare_digest(self.headers.get("Cookie", "").encode(), expected.encode()):
                return self.reply(401, {"error": "cookie required or expired"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 8 * 1024 * 1024 or self.headers.get_content_type() != "application/json" or self.headers.get("Transfer-Encoding"):
                    raise ValueError()
                raw = self.rfile.read(size)
                if len(raw) != size:
                    raise ValueError()
                payload = json.loads(raw)
                messages, tools, mode = request_parts(payload)
                if not isinstance(messages, list) or not isinstance(tools, list):
                    raise ValueError()
            except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
                return self.reply(400, {"error": "invalid company request"})
            upstream = None
            if backend == "openai":
                base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
                target = urlsplit(base)
                if target.scheme != "https" and not (target.scheme == "http" and target.hostname in ("127.0.0.1", "localhost")):
                    return self.reply(500, {"error": "invalid upstream configuration"})
                if target.username or target.password or target.query or target.fragment:
                    return self.reply(500, {"error": "invalid upstream configuration"})
                # Never forward the company Cookie or arbitrary incoming headers to OpenAI.
                body = {"model": os.environ["OPENAI_MODEL"], "messages": messages, "stream": True}
                if mode == "json":
                    # Carry the entire transcript as text, exactly as a message-only
                    # company service would. Native tool roles must not leak into it.
                    body["messages"] = [messages[0], {"role": "user", "content": payload["message"]}]
                if mode == "native" and tools:
                    body.update(tools=tools, tool_choice=payload.get("tool_choice", "auto"))
                request = urllib.request.Request(base + "/chat/completions", data=json.dumps(body).encode(), headers={
                    "Content-Type": "application/json", "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]})
                try:
                    context = ssl.create_default_context()  # Also honors SSL_CERT_FILE.
                    if os.environ.get("NODE_EXTRA_CA_CERTS"):
                        context.load_verify_locations(cafile=os.environ["NODE_EXTRA_CA_CERTS"])
                    opener = urllib.request.build_opener(NoRedirect(), urllib.request.HTTPSHandler(context=context))
                    upstream = opener.open(request, timeout=120)
                    if not upstream.headers.get("Content-Type", "").lower().startswith("text/event-stream"):
                        upstream.close()
                        return self.reply(502, {"error": "upstream did not return SSE"})
                except (OSError, ValueError, urllib.error.URLError):
                    return self.reply(502, {"error": "upstream request failed"})
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                if upstream:
                    while chunk := upstream.read1(8192):
                        self.wfile.write(chunk)
                        self.wfile.flush()
                else:
                    for event in mock_events(mock_answer(messages, tools), mode):
                        self.wfile.write(("data: " + json.dumps(event, ensure_ascii=False) + "\n\n").encode())
                        self.wfile.flush()
                    self.wfile.write(b"data: [DONE]\n\n")
            except (OSError, ValueError, KeyError, TypeError):
                # A partial stream stays incomplete; never append a successful terminator.
                pass
            finally:
                if upstream:
                    upstream.close()
                self.close_connection = True

    return ThreadingHTTPServer((host, port), Handler)


if __name__ == "__main__":
    try:
        server = create_server(os.environ.get("PI_LAB_HOST", "127.0.0.1"), int(os.environ.get("PI_LAB_PORT", "8766")), os.environ.get("PI_LAB_BACKEND", "mock"))
        print(f"Company API lab ready on port {server.server_port}; backend={os.environ.get('PI_LAB_BACKEND', 'mock')}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    except (OSError, ValueError):
        raise SystemExit("Cannot start AI lab; check local port and backend configuration (values hidden).")
