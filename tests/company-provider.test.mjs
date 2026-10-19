// EDITOR_PI_TEST_PREFIX=/prefix node --test tests/company-provider.test.mjs
import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtemp, writeFile, chmod, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { pathToFileURL } from 'node:url';
import { createServer } from 'node:http';

const runtime = pathToFileURL(process.env.EDITOR_PI_TEST_PREFIX + '/share/editor-pi/');
const provider = await import(new URL('company/company-provider.mjs', runtime));
const { normalizeContext } = await import(new URL('node_modules/@earendil-works/pi-ai/dist/index.js', runtime));
const { companyConfig, companyModel, companyStream, sseEvents, validateJsonAnswer } = provider;

test('SSE splits UTF-8, CRLF, comments and usage across arbitrary byte boundaries', async () => {
  const event = { choices: [{ index: 0, delta: { content: '日本語' }, finish_reason: 'stop' }] };
  const encoded = new TextEncoder().encode(':keepalive\r\n\r\ndata: ' + JSON.stringify(event) + '\r\n\r\ndata: [DONE]\r\n\r\n');
  let i = 0;
  const response = new Response(new ReadableStream({ pull(c) {
    if (i === encoded.length) c.close(); else c.enqueue(encoded.slice(i, ++i));
  } }), { headers: { 'Content-Type': 'text/event-stream' } });
  const results = [];
  for await (const value of sseEvents(response)) results.push(value);
  assert.deepEqual(results, [event]);
  const truncated = new Response('data: ' + JSON.stringify(event) + '\n\n', { headers: { 'Content-Type': 'text/event-stream' } });
  await assert.rejects(async () => { for await (const _ of sseEvents(truncated)) {} }, /COMPANY_TRUNCATED_STREAM/);
});

test('JSON protocol only accepts complete explicit valid registered tool calls', () => {
  const tools = [{ name: 'read', parameters: { type: 'object', properties: { path: { type: 'string' } }, required: ['path'], additionalProperties: false } }];
  assert.equal(validateJsonAnswer('{"type":"text","text":"hello"}', tools).text, 'hello');
  const call = { id: 'x', name: 'read', arguments: { path: 'sample.txt' } };
  assert.equal(validateJsonAnswer(JSON.stringify({ type: 'tool_calls', calls: [call] }), tools).calls.length, 1);
  for (const invalid of ['ordinary prose', '```json\n{}\n```', '{"type":"tool_calls","calls":[]}',
    JSON.stringify({ type: 'tool_calls', calls: [{ ...call, name: 'bash' }] }),
    JSON.stringify({ type: 'tool_calls', calls: [call, call] }),
    JSON.stringify({ type: 'tool_calls', calls: [{ ...call, arguments: {} }] })]) {
    assert.throws(() => validateJsonAnswer(invalid, tools), /COMPANY_/);
  }
});

test('Cookie is read per request, requires private permissions and rejects line breaks', async () => {
  const directory = await mkdtemp(tmpdir() + '/pi-cookie-');
  const file = directory + '/cookie';
  const env = { INTERNAL_AI_ENDPOINT: 'http://127.0.0.1/chat', INTERNAL_AI_COOKIE_FILE: file };
  try {
    await writeFile(file, 'session=old', { mode: 0o600 });
    assert.equal((await companyConfig(env)).headers.Cookie, 'session=old');
    await writeFile(file, 'session=new');
    assert.equal((await companyConfig(env)).headers.Cookie, 'session=new');
    await chmod(file, 0o644);
    await assert.rejects(companyConfig(env), /PRIVATE_0600/);
    await chmod(file, 0o600);
    await writeFile(file, 'session=one\nInjected: two');
    await assert.rejects(companyConfig(env), /INVALID_COOKIE_FILE/);
  } finally { await rm(directory, { recursive: true, force: true }); }
});

test('Native stream preserves hooks and usage; abort cancels without exposing provider data', async () => {
  const directory = await mkdtemp(tmpdir() + '/pi-stream-');
  const file = directory + '/cookie';
  await writeFile(file, 'session=dummy', { mode: 0o600 });
  let hang = false, requests = 0;
  const server = createServer(async (req, res) => {
    requests++;
    assert.equal(req.headers.cookie, 'session=dummy');
    assert.equal(req.headers.authorization, undefined);
    const chunks = [];
    for await (const part of req) chunks.push(part);
    const payload = JSON.parse(Buffer.concat(chunks));
    assert.equal(payload.guid, '');
    assert.ok(Array.isArray(payload.messages));
    res.writeHead(200, { 'Content-Type': 'text/event-stream' });
    if (hang) { res.write(':waiting\n\n'); return; }
    res.end('data: ' + JSON.stringify({ choices: [{ index: 0, delta: { content: '日本語' }, finish_reason: 'stop' }],
      usage: { prompt_tokens: 12, completion_tokens: 3, total_tokens: 15 } }) + '\n\ndata: [DONE]\n\n');
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const env = { INTERNAL_AI_ENDPOINT: `http://127.0.0.1:${server.address().port}/chat`, INTERNAL_AI_COOKIE_FILE: file,
    no_proxy: '127.0.0.1', NO_PROXY: '127.0.0.1' };
  const context = normalizeContext({ messages: [{ role: 'user', content: 'hello', timestamp: Date.now() }] });
  try {
    const hooks = [];
    const answer = await companyStream(companyModel(), context, { env,
      onPayload: payload => { hooks.push('payload'); assert.equal(payload.message, 'hello'); },
      onResponse: response => { hooks.push('response'); assert.equal(response.status, 200); },
      onProviderStreamEvent: () => { hooks.push('event'); },
    }).result();
    assert.equal(answer.stopReason, 'stop');
    assert.equal(answer.content[0].text, '日本語');
    assert.equal(answer.usage.totalTokens, 15);
    assert.deepEqual(hooks, ['payload', 'response', 'event']);
    hang = true;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 150);
    const aborted = await companyStream(companyModel(), context, { env, signal: controller.signal }).result();
    clearTimeout(timer);
    assert.equal(aborted.stopReason, 'aborted');
    assert.equal(aborted.errorMessage, 'COMPANY_REQUEST_ABORTED');
    assert.equal(requests, 2);
  } finally {
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
    await rm(directory, { recursive: true, force: true });
  }
});
