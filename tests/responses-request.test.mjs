import test from 'node:test';
import assert from 'node:assert/strict';
import { withoutInputStatus } from '../editor/pi/responses-request.mjs';

test('Drops only input-item status while preserving message and tool roundtrip fields', () => {
  const input = [
    { role: 'user', content: 'hello' },
    { type: 'message', role: 'assistant', status: 'completed', content: [{ type: 'output_text', text: 'reply' }] },
    { type: 'function_call', id: 'fc_1', call_id: 'call_1', status: 'completed', name: 'edit', arguments: '{"status":"keep-me"}' },
    { type: 'function_call_output', call_id: 'call_1', status: 'completed', output: '{"status":"also-keep"}' },
  ];
  for (const stream of [true, false]) {
    const body = { model: 'test', stream, input, tools: [{ type: 'function', name: 'edit' }] };
    const init = { body: JSON.stringify(body), headers: { Authorization: 'Bearer dummy' }, signal: new AbortController().signal };
    const result = withoutInputStatus(init);
    const actual = JSON.parse(result.body);
    assert.ok(actual.input.every(item => !Object.hasOwn(item, 'status')));
    assert.equal(actual.input[2].arguments, '{"status":"keep-me"}');
    assert.equal(actual.input[3].call_id, 'call_1');
    assert.equal(actual.input[3].output, '{"status":"also-keep"}');
    assert.equal(actual.stream, stream);
    assert.deepEqual(actual.tools, body.tools);
    assert.equal(result.headers, init.headers);
    assert.equal(result.signal, init.signal);
    assert.equal(JSON.parse(init.body).input[1].status, 'completed', 'Original request/context remains intact');
  }
});
