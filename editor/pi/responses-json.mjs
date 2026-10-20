// Ask the server for ordinary Responses JSON, then feed its items to Pi's existing decoder.
// The SDK-facing request stays stream=true; only the wire request is changed.
export function responsesStreaming(env = process.env) {
  const value = env.INTERNAL_AI_STREAM ?? 'true';
  if (!['true', 'false', '1', '0'].includes(value)) throw new Error('INTERNAL_AI_STREAM must be true or false');
  return value === 'true' || value === '1';
}

async function readJson(response) {
  if (!(response.headers.get('content-type') || '').toLowerCase().includes('application/json')) {
    throw new Error('AI_NONSTREAM_EXPECTED_JSON: server did not return application/json');
  }
  const reader = response.body?.getReader();
  if (!reader) throw new Error('AI_NONSTREAM_EMPTY_RESPONSE');
  let text = '', size = 0;
  const decoder = new TextDecoder();
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 8 * 1024 * 1024) throw new Error('AI_NONSTREAM_RESPONSE_TOO_LARGE');
      text += decoder.decode(value, { stream: true });
    }
    text += decoder.decode();
  } finally { reader.cancel().catch(() => {}); reader.releaseLock(); }
  try { return JSON.parse(text); }
  catch { throw new Error('AI_NONSTREAM_INVALID_JSON'); }
}

export async function nonStreamingResponse(fetcher, input, init) {
  if (typeof init?.body !== 'string') throw new Error('AI_NONSTREAM_UNSUPPORTED_REQUEST');
  const body = JSON.parse(init.body);
  body.stream = false;
  const headers = new Headers(init.headers);
  headers.set('Accept', 'application/json');
  const response = await fetcher(input, { ...init, headers, body: JSON.stringify(body) });
  if (!response.ok) return response; // Preserve normal HTTP errors for the SDK.
  const value = await readJson(response);
  if (!value || value.object !== 'response' || !['completed', 'incomplete', 'failed'].includes(value.status) || !Array.isArray(value.output)) {
    throw new Error('AI_NONSTREAM_UNSUPPORTED_RESPONSE');
  }
  const events = [{ type: 'response.created', response: { ...value, output: [], status: 'in_progress' } }];
  if (value.status !== 'failed') {
    for (const [index, item] of value.output.entries()) {
      if (!item || !['message', 'function_call', 'reasoning'].includes(item.type)) throw new Error('AI_NONSTREAM_UNSUPPORTED_OUTPUT_ITEM');
      if (item.type === 'message' && (!Array.isArray(item.content) || item.content.some(part =>
        !(part.type === 'output_text' && typeof part.text === 'string') && !(part.type === 'refusal' && typeof part.refusal === 'string')))) {
        throw new Error('AI_NONSTREAM_UNSUPPORTED_MESSAGE');
      }
      if (item.type === 'function_call') {
        if (typeof item.name !== 'string' || typeof item.call_id !== 'string' || typeof item.arguments !== 'string') throw new Error('AI_NONSTREAM_INVALID_TOOL_CALL');
        try { const args = JSON.parse(item.arguments); if (!args || typeof args !== 'object' || Array.isArray(args)) throw new Error(); }
        catch { throw new Error('AI_NONSTREAM_INVALID_TOOL_ARGUMENTS'); }
      }
      events.push({ type: 'response.output_item.added', output_index: index, item: item.type === 'function_call'
        ? { ...item, arguments: '' } : item.type === 'message' ? { ...item, content: [] } : item });
      events.push({ type: 'response.output_item.done', output_index: index, item });
    }
  }
  events.push({ type: `response.${value.status}`, response: value });
  const encoded = events.map(event => `event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`).join('');
  return new Response(encoded, { status: response.status, headers: { 'content-type': 'text/event-stream' } });
}
