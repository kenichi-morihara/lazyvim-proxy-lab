// Preserve the standard Responses protocol; only configure gateway authentication.
import { withoutInputStatus } from './responses-request.mjs';
import { responsesStreaming, nonStreamingResponse } from './responses-json.mjs';
import { createSseDiagnostics } from './sse-diagnostics.mjs';
import { createAssistantMessageEventStream } from '@earendil-works/pi-ai';
import { streamSimple } from '@earendil-works/pi-ai/api/openai-responses';

export function responsesModel(env = process.env) {
  responsesStreaming(env);
  const url = new URL(env.INTERNAL_AI_BASE_URL);
  if ((url.protocol !== 'https:' && !(url.protocol === 'http:' && (['localhost', '127.0.0.1', '[::1]'].includes(url.hostname) || env.INTERNAL_AI_ALLOW_HTTP === '1'))) ||
      url.username || url.password || url.search || url.hash) throw new Error('Invalid Responses base URL');
  const userHeader = env.INTERNAL_AI_USER_HEADER || 'user';
  const keyHeader = env.INTERNAL_AI_AUTH_HEADER || 'Authorization';
  if (!/^[A-Za-z0-9-]+$/.test(userHeader) ||
      ['authorization', 'host', 'content-type', 'content-length', 'connection', 'transfer-encoding'].includes(userHeader.toLowerCase()) ||
      !env.INTERNAL_AI_USER || /[\x00-\x1f\x7f]/.test(env.INTERNAL_AI_USER) ||
      (env.INTERNAL_AI_API_KEY && (!/^[A-Za-z0-9-]+$/.test(keyHeader) || keyHeader.toLowerCase() === userHeader.toLowerCase()))) {
    throw new Error('Invalid Responses user header configuration');
  }
  return { id: env.INTERNAL_AI_MODEL, name: env.INTERNAL_AI_MODEL, api: 'openai-responses', provider: 'internal', baseUrl: env.INTERNAL_AI_BASE_URL,
    reasoning: false, input: ['text'], contextWindow: 32768, maxTokens: 4096,
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 } };
}

let lastError = '';
let lastDiagnostic = 'No request failure recorded in this Pi process.';

function diagnosticError(model, detail, diagnostic) {
  const report = diagnostic.report();
  lastDiagnostic = report.code + '\n' + report.details;
  return report.code + '\n' + requestError(model, detail) + '\n' + diagnostic.summary() + '\n' + report.details;
}

export function redactError(value, env = process.env) {
  let text = String(value || 'No error detail returned');
  for (const secret of [env.INTERNAL_AI_API_KEY, env.INTERNAL_AI_USER].filter(Boolean).sort((a, b) => b.length - a.length)) {
    text = text.split(secret).join('[REDACTED]');
  }
  return text.replace(/Bearer\s+[^\s"',;}]+/gi, 'Bearer [REDACTED]')
    .replace(/sk-(?:proj-)?[A-Za-z0-9_-]{12,}/g, '[REDACTED]')
    .replace(/[\x00-\x08\x0b-\x1f\x7f]/g, '').slice(0, 2000);
}

export function connectionStatus(model = responsesModel(), env = process.env) {
  return `API: Responses\nWire stream: ${responsesStreaming(env)}\nModel ID: ${model.id}\nPOST: ${model.baseUrl.replace(/\/$/, '')}/responses\nUser header: ${env.INTERNAL_AI_USER_HEADER || 'user'} (value hidden)\nBearer: ${env.INTERNAL_AI_API_KEY ? 'set' : 'not set'}`;
}

function requestError(model, detail) {
  const safe = redactError(detail);
  const hint = /model.*(?:not.*registered|not.*found|does not exist)|model_not_found/i.test(safe)
    ? '\nCheck the exact model ID registered by your service; change it with make config.' : '';
  return 'AI request failed\n' + redactError(connectionStatus(model)) + '\nDetails: ' + safe + hint;
}

export function responsesStream(model, context, options = {}) {
  const env = process.env;
  const headers = { [env.INTERNAL_AI_USER_HEADER || 'user']: env.INTERNAL_AI_USER };
  const header = env.INTERNAL_AI_AUTH_HEADER || 'Authorization';
  if (env.INTERNAL_AI_API_KEY) {
    headers[header] = header.toLowerCase() === 'authorization'
      ? `Bearer ${env.INTERNAL_AI_API_KEY}` : env.INTERNAL_AI_API_KEY;
  }
  const diagnostic = createSseDiagnostics();
  const requestFetch = options.fetch || globalThis.fetch;
  let transportFailure = '';
  const measuredFetch = async (input, init) => {
    init = withoutInputStatus(init);
    diagnostic.request(init);
    return requestFetch(input, init);
  };
  const inner = streamSimple(model, context, {
    ...options, apiKey: env.INTERNAL_AI_API_KEY || 'unused',
    fetch: async (input, init) => {
      try {
        return diagnostic.observe(await (responsesStreaming(env)
          ? measuredFetch(input, init) : nonStreamingResponse(measuredFetch, input, init, diagnostic.jsonMeta)));
      } catch (error) {
        if (error?.message?.startsWith('AI_NONSTREAM_')) transportFailure = error.message;
        throw error;
      }
    },
    ...(!responsesStreaming(env) ? { maxRetries: 0 } : {}),
    headers: { ...options.headers, ...headers,
      ...(!env.INTERNAL_AI_API_KEY || header.toLowerCase() !== 'authorization'
        ? { Authorization: null } : {}) },
  });
  const output = createAssistantMessageEventStream();
  (async () => {
    try {
      for await (const event of inner) {
        if (event.type === 'error') {
          lastError = diagnosticError(model, transportFailure || event.error.errorMessage, diagnostic);
          event.error.errorMessage = lastError;
        }
        output.push(event);
      }
    } catch (error) {
      lastError = diagnosticError(model, error?.message, diagnostic);
      output.push({ type: 'error', reason: options.signal?.aborted ? 'aborted' : 'error', error: {
        role: 'assistant', content: [], api: model.api, provider: model.provider, model: model.id,
        stopReason: options.signal?.aborted ? 'aborted' : 'error', errorMessage: lastError, timestamp: Date.now(),
        usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0,
          cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } },
      } });
    } finally { output.end(); }
  })();
  return output;
}

export default function (pi) {
  const env = process.env;
  pi.registerCommand('ai-diagnostic', {
    description: 'Show a short failure code and stream metadata only; no response text or credentials',
    async handler() {
      pi.sendMessage({ customType: 'ai-diagnostic', content: lastDiagnostic, display: true }, { triggerTurn: false });
    },
  });
  pi.registerCommand('ai-headers', {
    description: 'Reveal actual request authentication headers on screen only (not saved in chat)',
    async handler(_args, ctx) {
      const header = env.INTERNAL_AI_AUTH_HEADER || 'Authorization';
      const lines = [`${env.INTERNAL_AI_USER_HEADER || 'user'}: ${env.INTERNAL_AI_USER}`];
      if (env.INTERNAL_AI_API_KEY) lines.push(`${header}: ${header.toLowerCase() === 'authorization' ? 'Bearer ' : ''}${env.INTERNAL_AI_API_KEY}`);
      ctx.ui.notify(lines.join('\n'), 'info');
    },
  });
  pi.registerCommand('ai-status', {
    description: 'Show configured model, Responses endpoint and the last failure (secrets hidden)',
    async handler() {
      pi.sendMessage({ customType: 'ai-status', content: redactError(connectionStatus()) +
        (lastError ? '\n\nLast failure:\n' + lastError : ''), display: true }, { triggerTurn: false });
    },
  });
  pi.registerProvider('internal', {
    api: 'openai-responses', apiKey: env.INTERNAL_AI_API_KEY || 'unused',
    baseUrl: env.INTERNAL_AI_BASE_URL, models: [responsesModel()], streamSimple: responsesStream,
  });
}
