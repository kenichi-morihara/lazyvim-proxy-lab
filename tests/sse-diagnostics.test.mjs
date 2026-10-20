import test from 'node:test';
import assert from 'node:assert/strict';
import { createSseDiagnostics } from '../editor/pi/sse-diagnostics.mjs';

test('Observes byte-split CRLF and Japanese without changing the stream', async () => {
  const text = 'event: response.output_text.delta\r\ndata: {"type":"response.output_text.delta","delta":"日本語"}\r\n\r\ndata: [DONE]\r\n\r\n';
  const bytes = new TextEncoder().encode(text);
  const source = new ReadableStream({ start(c) { for (const byte of bytes) c.enqueue(Uint8Array.of(byte)); c.close(); } });
  const d = createSseDiagnostics();
  const observed = d.observe(new Response(source, { headers: { 'content-type': 'text/event-stream; charset=utf-8' } }));
  assert.equal(await observed.text(), text);
  assert.match(d.summary(), /events=2/);
  assert.ok(!d.summary().includes('first_invalid'));
  assert.ok(!d.summary().includes('日本語'));
});

test('Reports the malformed later frame without exposing its payload', async () => {
  const text = 'data: {"type":"response.output_text.delta","delta":"hello"}\n\nevent: response.completed\ndata: private-response-body\n\n';
  const d = createSseDiagnostics();
  assert.equal(await d.observe(new Response(text, { headers: { 'content-type': 'text/event-stream' } })).text(), text);
  assert.match(d.summary(), /first_invalid=#2 event=response.completed data=other/);
  assert.ok(!d.summary().includes('private-response-body'));
  assert.ok(!d.summary().includes('hello'));
});
