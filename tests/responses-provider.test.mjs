import test from 'node:test';
import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';

const prefix = process.env.EDITOR_PI_TEST_PREFIX;

test('Responses failure and status command show actionable details without credentials', { skip: !prefix }, async () => {
  const old = { ...process.env };
  try {
    Object.assign(process.env, {
      INTERNAL_AI_BASE_URL: 'https://ai.example/v1', INTERNAL_AI_MODEL: 'missing-model',
      INTERNAL_AI_USER_HEADER: 'X-User', INTERNAL_AI_USER: 'private-user', INTERNAL_AI_API_KEY: 'private-token',
    });
    const provider = await import(pathToFileURL(prefix + '/share/editor-pi/company/responses-provider.mjs'));
    const { normalizeContext } = await import(pathToFileURL(prefix + '/share/editor-pi/node_modules/@earendil-works/pi-ai/dist/index.js'));
    const context = normalizeContext({ systemPrompt: '', messages: [
      { role: 'user', content: 'hello', timestamp: Date.now() },
    ], tools: [] });
    const result = await provider.responsesStream(provider.responsesModel(), context, {
      fetch: async () => new Response(JSON.stringify({ error: {
        type: 'invalid_request_error', code: 'model_not_found',
        message: 'model is not registered; private-user Bearer private-token',
      } }), { status: 404, headers: { 'Content-Type': 'application/json' } }),
    }).result();
    assert.equal(result.stopReason, 'error');
    for (const text of ['AI request failed', '404', 'missing-model', '/v1/responses', 'model is not registered', 'make config']) {
      assert.ok(result.errorMessage.includes(text), text);
    }
    for (const secret of ['private-user', 'private-token']) assert.ok(!result.errorMessage.includes(secret));
    let command, headersCommand, message;
    provider.default({ registerProvider() {}, registerCommand(name, spec) { if (name === 'ai-status') command = spec; else if (name === 'ai-headers') headersCommand = spec; else assert.fail(name); },
      sendMessage(value, options) { assert.equal(options.triggerTurn, false); message = value; } });
    await command.handler();
    assert.equal(message.display, true);
    assert.ok(message.content.includes('Model ID: missing-model'));
    assert.ok(message.content.includes('Last failure:'));
    let revealed;
    const previousMessage = message;
    await headersCommand.handler('', { ui: { notify(value) { revealed = value; } } });
    assert.equal(revealed, 'X-User: private-user\nAuthorization: Bearer private-token');
    assert.equal(message, previousMessage, 'Revealed headers must not be saved to chat');
    for (const secret of ['private-user', 'private-token']) assert.ok(!message.content.includes(secret));
  } finally {
    for (const key of Object.keys(process.env)) if (!(key in old)) delete process.env[key];
    Object.assign(process.env, old);
  }
});
