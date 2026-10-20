import test from 'node:test';
import assert from 'node:assert/strict';
import { nonStreamingResponse, responsesStreaming } from '../editor/pi/responses-json.mjs';

const init = { headers: { Authorization: 'Bearer dummy', 'Content-Type': 'application/json' }, body: JSON.stringify({ model: 'test', stream: true, input: 'hello' }) };
const full = { id: 'resp_test', object: 'response', status: 'completed', output: [
  { type: 'message', id: 'msg_test', role: 'assistant', status: 'completed', content: [{ type: 'output_text', text: '日本語', annotations: [] }] },
], usage: { input_tokens: 10, output_tokens: 2, total_tokens: 12 } };

test('Wire request uses stream=false; response items and usage remain intact for Pi', async () => {
  const result = await nonStreamingResponse(async (_url, request) => {
    assert.equal(JSON.parse(request.body).stream, false);
    assert.equal(request.headers.get('accept'), 'application/json');
    assert.equal(request.headers.get('authorization'), 'Bearer dummy');
    return Response.json(full);
  }, 'https://ai.example/v1/responses', init);
  assert.equal(JSON.parse(init.body).stream, true, 'SDK-facing request must stay streaming');
  const data = await result.text();
  assert.match(data, /event: response.completed/);
  assert.ok(data.includes('日本語'));
  assert.ok(data.includes('"total_tokens":12'));
  assert.equal(responsesStreaming({}), true);
  assert.equal(responsesStreaming({ INTERNAL_AI_STREAM: 'false' }), false);
});

test('Incomplete response stays incomplete; malformed JSON and ignored stream flag fail clearly', async () => {
  const result = await nonStreamingResponse(async () => Response.json({ ...full, status: 'incomplete', incomplete_details: { reason: 'max_output_tokens' } }), '', init);
  const text = await result.text();
  assert.match(text, /event: response.incomplete/);
  assert.ok(!text.includes('event: response.completed'));
  await assert.rejects(nonStreamingResponse(async () => new Response('bad-json', { headers: { 'content-type': 'application/json' } }), '', init), /AI_NONSTREAM_INVALID_JSON/);
  await assert.rejects(nonStreamingResponse(async () => new Response('data: {}\n\n', { headers: { 'content-type': 'text/event-stream' } }), '', init), /AI_NONSTREAM_EXPECTED_JSON/);
  const invalid = { ...full, output: [{ type: 'function_call', name: 'edit', id: 'fc_1', call_id: 'call_1', arguments: 'not-json' }] };
  await assert.rejects(nonStreamingResponse(async () => Response.json(invalid), '', init), /AI_NONSTREAM_INVALID_TOOL_ARGUMENTS/);
});


test('Reports a response-body interruption distinctly from a JSON syntax error', async () => {
  const updates = [];
  const stream = new ReadableStream({ start(c) { c.enqueue(new TextEncoder().encode('{"output":')); }, pull(c) { c.error(new Error('socket closed')); } });
  await assert.rejects(nonStreamingResponse(async () => new Response(stream, { headers: { 'content-type': 'application/json' } }), '', init,
    value => updates.push(value)), /AI_NONSTREAM_BODY_INTERRUPTED/);
  assert.ok(updates.some(value => value.interrupted));
});
