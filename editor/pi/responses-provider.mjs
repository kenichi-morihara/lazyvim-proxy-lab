// Preserve the standard Responses protocol; only configure gateway authentication.
import { streamSimple } from '@earendil-works/pi-ai/api/openai-responses';

export function responsesModel(env = process.env) {
  const url = new URL(env.INTERNAL_AI_BASE_URL);
  if ((url.protocol !== 'https:' && !(url.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname))) ||
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

export function responsesStream(model, context, options = {}) {
  const env = process.env;
  const headers = { [env.INTERNAL_AI_USER_HEADER || 'user']: env.INTERNAL_AI_USER };
  const header = env.INTERNAL_AI_AUTH_HEADER || 'Authorization';
  if (env.INTERNAL_AI_API_KEY) {
    headers[header] = header.toLowerCase() === 'authorization'
      ? `Bearer ${env.INTERNAL_AI_API_KEY}` : env.INTERNAL_AI_API_KEY;
  }
  return streamSimple(model, context, {
    ...options, apiKey: env.INTERNAL_AI_API_KEY || 'unused',
    headers: { ...options.headers, ...headers,
      ...(!env.INTERNAL_AI_API_KEY || header.toLowerCase() !== 'authorization'
        ? { Authorization: null } : {}) },
  });
}

export default function (pi) {
  const env = process.env;
  pi.registerProvider('internal', {
    api: 'openai-responses', apiKey: env.INTERNAL_AI_API_KEY || 'unused',
    baseUrl: env.INTERNAL_AI_BASE_URL, models: [responsesModel()], streamSimple: responsesStream,
  });
}
