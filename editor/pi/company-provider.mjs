import { readFile, stat } from 'node:fs/promises';
import { fetch, EnvHttpProxyAgent } from 'undici';
import { streamSimple as openaiStream } from '@earendil-works/pi-ai/api/openai-completions';
import { createAssistantMessageEventStream, getCurrentTools, validateToolCall } from '@earendil-works/pi-ai';

const fail = (code) => new Error(`COMPANY_${code}`);
const MAX_STREAM = 32 * 1024 * 1024;
const MAX_JSON = 4 * 1024 * 1024;
export const jsonInstructions = 'Return ONLY one JSON object, without markdown: {"type":"text","text":"your answer"} or {"type":"tool_calls","calls":[{"id":"unique_id","name":"registered tool name","arguments":{}}]}. Tool results appear in the conversation. Use only listed tools, with arguments matching their schema.';

export async function companyConfig(env = process.env) {
  let endpoint;
  try { endpoint = new URL(env.INTERNAL_AI_ENDPOINT); } catch { throw fail('ENDPOINT_REQUIRED'); }
  if (!['http:', 'https:'].includes(endpoint.protocol) || endpoint.username || endpoint.password || endpoint.hash) throw fail('INVALID_ENDPOINT');
  const mode = env.INTERNAL_AI_TOOL_MODE || 'native';
  if (!['native', 'json'].includes(mode)) throw fail('INVALID_TOOL_MODE');
  if (!env.INTERNAL_AI_COOKIE_FILE) throw fail('COOKIE_FILE_REQUIRED');
  const info = await stat(env.INTERNAL_AI_COOKIE_FILE).catch(() => { throw fail('COOKIE_FILE_UNREADABLE'); });
  if (!info.isFile() || (info.mode & 0o077)) throw fail('COOKIE_FILE_MUST_BE_PRIVATE_0600');
  const cookie = (await readFile(env.INTERNAL_AI_COOKIE_FILE, 'utf8')).trim();
  if (!cookie || /[\r\n]/.test(cookie) || cookie.length > 32768) throw fail('INVALID_COOKIE_FILE');
  const timeout = Number(env.INTERNAL_AI_TIMEOUT_MS || '120000');
  if (!Number.isInteger(timeout) || timeout < 1) throw fail('INVALID_TIMEOUT');
  const headers = { 'Content-Type': 'application/json', Accept: 'text/event-stream', Cookie: cookie,
    Origin: env.INTERNAL_AI_ORIGIN || endpoint.origin,
    Referer: env.INTERNAL_AI_REFERER || new URL('.', endpoint).href };
  if (Object.values(headers).some(value => /[\r\n]/.test(value))) throw fail('INVALID_HEADER');
  return { endpoint: endpoint.href, mode, headers, timeout };
}

export function companyModel(env = process.env) {
  const contextWindow = Number(env.INTERNAL_AI_CONTEXT_WINDOW || 32768);
  const maxTokens = Number(env.INTERNAL_AI_MAX_TOKENS || 4096);
  if (![contextWindow, maxTokens].every(n => Number.isInteger(n) && n > 0) || maxTokens >= contextWindow) throw fail('INVALID_TOKEN_LIMITS');
  return { id: env.INTERNAL_AI_MODEL || 'company-chat', name: 'Company chat', api: 'openai-completions',
    provider: 'internal', baseUrl: 'http://127.0.0.1', input: ['text'], reasoning: false,
    contextWindow, maxTokens, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
    compat: { supportsDeveloperRole: false, supportsStore: false } };
}

export function wrapPayload(params, mode) {
  const messages = params.messages || [];
  const lastUser = messages.findLast(message => message.role === 'user');
  const base = { guid: '', premium: false, secondary: false, message: '', fileMessage: [] };
  if (mode === 'json') {
    base.message = JSON.stringify({ protocol: 'pi-company-v1', instructions: jsonInstructions, messages, tools: params.tools || [] });
    return base;
  }
  base.message = typeof lastUser?.content === 'string' ? lastUser.content : JSON.stringify(lastUser?.content || '');
  return { ...base, messages, ...(params.tools ? { tools: params.tools, tool_choice: params.tool_choice || 'auto' } : {}), stream: true };
}

// Read SSE incrementally: neither Unicode nor CRLF boundaries need align with network chunks.
export async function* sseEvents(response) {
  if (!response.headers.get('content-type')?.toLowerCase().startsWith('text/event-stream')) throw fail('EXPECTED_SSE_OR_LOGIN_PAGE');
  const reader = response.body?.getReader();
  if (!reader) throw fail('EMPTY_STREAM');
  const decoder = new TextDecoder('utf-8', { fatal: true });
  let pending = '', bytes = 0, data = [], finished = false, doneMarker = false;
  try {
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) { pending += decoder.decode(); break; }
      bytes += chunk.value.byteLength;
      if (bytes > MAX_STREAM) throw fail('STREAM_TOO_LARGE');
      pending += decoder.decode(chunk.value, { stream: true });
      let index;
      while ((index = pending.indexOf('\n')) !== -1) {
        const line = pending.slice(0, index).replace(/\r$/, '');
        pending = pending.slice(index + 1);
        if (line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''));
        if (line === '' && data.length) {
          const value = data.join('\n'); data = [];
          if (value === '[DONE]') {
            if (!finished) throw fail('MISSING_FINISH_REASON');
            doneMarker = true;
            return;
          }
          let event;
          try { event = JSON.parse(value); } catch { throw fail('INVALID_SSE_JSON'); }
          if (!event || !Array.isArray(event.choices) || event.error) throw fail('UNSUPPORTED_RESPONSE');
          if (event.choices.some(choice => choice.finish_reason != null)) finished = true;
          yield event;
        }
      }
      if (pending.length > MAX_JSON) throw fail('SSE_EVENT_TOO_LARGE');
    }
    if (!doneMarker) throw fail('TRUNCATED_STREAM');
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}

function encodeEvent(event) { return new TextEncoder().encode('data: ' + JSON.stringify(event) + '\n\n'); }
function envelope(model, delta, finish = null) {
  return { id: 'company', object: 'chat.completion.chunk', created: Math.floor(Date.now() / 1000), model: model.id,
    choices: [{ index: 0, delta, finish_reason: finish }] };
}

export function validateJsonAnswer(text, tools) {
  let answer;
  try { answer = JSON.parse(text); } catch { throw fail('INVALID_PROTOCOL_JSON'); }
  if (answer?.type === 'text' && typeof answer.text === 'string' && Object.keys(answer).every(key => ['type', 'text'].includes(key))) return answer;
  if (answer?.type !== 'tool_calls' || !Array.isArray(answer.calls) || !answer.calls.length || answer.calls.length > 32 ||
      Object.keys(answer).some(key => !['type', 'calls'].includes(key))) throw fail('INVALID_PROTOCOL_SHAPE');
  const ids = new Set();
  for (const call of answer.calls) {
    if (!call || typeof call.name !== 'string' || typeof call.id !== 'string' || !/^[A-Za-z0-9_-]{1,64}$/.test(call.id) || ids.has(call.id) ||
        !call.arguments || typeof call.arguments !== 'object' || Array.isArray(call.arguments) ||
        Object.keys(call).some(key => !['id', 'name', 'arguments'].includes(key))) throw fail('INVALID_TOOL_CALL');
    ids.add(call.id);
    if (!tools.some(tool => tool.name === call.name)) throw fail('UNKNOWN_TOOL');
    try { validateToolCall(tools, { type: 'toolCall', ...call }); } catch { throw fail('INVALID_TOOL_ARGUMENTS'); }
  }
  return answer;
}

async function* jsonAsNative(response, model, tools) {
  let text = '', usage, finish;
  for await (const event of sseEvents(response)) {
    if (event.usage) usage = event.usage;
    for (const choice of event.choices) {
      if (choice.index !== 0) continue;
      if (choice.delta?.tool_calls) throw fail('UNEXPECTED_NATIVE_TOOLS_IN_JSON_MODE');
      text += choice.delta?.content || '';
      if (text.length > MAX_JSON) throw fail('PROTOCOL_TOO_LARGE');
      if (choice.finish_reason) finish = choice.finish_reason;
    }
  }
  if (finish !== 'stop') throw fail('INCOMPLETE_PROTOCOL');
  const answer = validateJsonAnswer(text, tools);
  const delta = answer.type === 'text' ? { role: 'assistant', content: answer.text } : {
    role: 'assistant', tool_calls: answer.calls.map((call, index) => ({ index, id: call.id, type: 'function',
      function: { name: call.name, arguments: JSON.stringify(call.arguments) } })) };
  yield envelope(model, delta);
  yield { ...envelope(model, {}, answer.type === 'text' ? 'stop' : 'tool_calls'), ...(usage ? { usage } : {}) };
}

function streamResponse(iterator, signal) {
  return new Response(new ReadableStream({
    async pull(controller) {
      try {
        signal?.throwIfAborted();
        const next = await iterator.next();
        if (next.done) {
          controller.enqueue(new TextEncoder().encode('data: [DONE]\n\n'));
          controller.close();
        } else controller.enqueue(encodeEvent(next.value));
      } catch (error) { await iterator.return?.(); controller.error(error); }
    },
    async cancel() { await iterator.return?.(); },
  }), { headers: { 'Content-Type': 'text/event-stream' } });
}

export function companyStream(model, context, options = {}) {
  const stream = createAssistantMessageEventStream();
  (async () => {
    const env = { ...process.env, ...options.env };
    let dispatcher;
    let safeError = 'COMPANY_STREAM_OR_NETWORK_ERROR';
    try {
      dispatcher = new EnvHttpProxyAgent({ httpProxy: env.http_proxy || env.HTTP_PROXY,
        httpsProxy: env.https_proxy || env.HTTPS_PROXY, noProxy: env.no_proxy || env.NO_PROXY });
      const mode = env.INTERNAL_AI_TOOL_MODE || 'native';
      const inner = openaiStream(model, context, { ...options, apiKey: 'unused', maxRetries: 0,
        onPayload: async (params) => {
          const wrapped = wrapPayload(params, mode);
          // The SDK needs stream=true even though the company JSON-mode wire
          // contract has only the five photographed fields. Remove it in fetch.
          return { ...((await options.onPayload?.(wrapped, model)) ?? wrapped), stream: true };
        },
        fetch: async (_url, init) => {
          let response;
          try {
            const config = await companyConfig(env); // Re-read Cookie on every actual request.
            const signal = AbortSignal.any([...(init.signal ? [init.signal] : []), AbortSignal.timeout(config.timeout)]);
            const body = JSON.parse(init.body);
            if (config.mode === 'json') delete body.stream;
            response = await fetch(config.endpoint, { method: 'POST', headers: config.headers,
              body: JSON.stringify(body), signal, redirect: 'manual', dispatcher });
            if (response.status >= 300 && response.status < 400 || [401, 403].includes(response.status)) {
              await response.body?.cancel(); throw fail('AUTH_EXPIRED_UPDATE_COOKIE');
            }
            if (!response.ok) {
              await response.body?.cancel(); throw fail(`HTTP_${response.status}`);
            }
            const iterator = config.mode === 'json' ? jsonAsNative(response, model, getCurrentTools(context.messages)) : sseEvents(response);
            // Sanitize stream failures before the SDK can include body text in its error.
            const guarded = (async function* () {
              try { yield* iterator; } catch (error) {
                safeError = /^COMPANY_[A-Z0-9_]+$/.test(error.message) ? error.message : 'COMPANY_STREAM_OR_NETWORK_ERROR';
                throw new Error(safeError);
              }
            })();
            return streamResponse(guarded, signal);
          } catch (error) {
            safeError = /^COMPANY_[A-Z0-9_]+$/.test(error.message) ? error.message : 'COMPANY_STREAM_OR_NETWORK_ERROR';
            throw new Error(safeError);
          }
        },
      });
      for await (const event of inner) {
        if (event.type === 'error') event.error.errorMessage = options.signal?.aborted ? 'COMPANY_REQUEST_ABORTED' : safeError;
        stream.push(event);
      }
    } catch {
      stream.push({ type: 'error', reason: options.signal?.aborted ? 'aborted' : 'error', error: {
        role: 'assistant', content: [], api: model.api, provider: model.provider, model: model.id,
        stopReason: options.signal?.aborted ? 'aborted' : 'error', errorMessage: safeError, timestamp: Date.now(),
        usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0,
          cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } },
      } });
    } finally { await dispatcher?.close(); stream.end(); }
  })();
  return stream;
}

export default function (pi) {
  const model = companyModel();
  pi.registerProvider('internal', { api: 'openai-completions', apiKey: 'unused', baseUrl: model.baseUrl,
    models: [model], streamSimple: companyStream });
}
