// Observe framing without changing bytes or retaining response text in diagnostics.
const LIMIT = 65536;
const knownEvents = new Set(['response.created', 'response.in_progress', 'response.completed', 'response.failed',
  'response.incomplete', 'response.output_item.added', 'response.output_item.done', 'response.content_part.added',
  'response.content_part.done', 'response.output_text.delta', 'response.output_text.done',
  'response.function_call_arguments.delta', 'response.function_call_arguments.done', 'error']);
const eventLabel = value => knownEvents.has(value) ? value : value ? 'other' : 'message';

export function createSseDiagnostics() {
  let http = 'unknown', media = 'unknown', count = 0, invalid = '', last = '', line = '', data = [], name = '', size = 0, capped = false;
  const decoder = new TextDecoder();
  function frame() {
    if (!data.length && !capped) { name = ''; return; }
    count++;
    const text = data.join('\n');
    let kind = 'empty', valid = false;
    if (capped) kind = 'oversize';
    else if (text.trim() === '[DONE]') { kind = 'done-sentinel'; valid = true; }
    else {
      kind = text.trimStart().startsWith('{') ? 'object-like' : text.trimStart().startsWith('[') ? 'array-like' : text ? 'other' : 'empty';
      try {
        const value = JSON.parse(text);
        valid = true;
        if (value && typeof value === 'object') {
          kind = knownEvents.has(value.type) ? value.type : Array.isArray(value.choices) ? 'chat-completions-object' : 'other-json';
        } else kind = 'json-scalar';
      } catch { /* Keep only a shape label, never the payload or parser message. */ }
    }
    last = `#${count} event=${eventLabel(name)} data=${kind}`;
    if (!valid && !invalid) invalid = last;
    data = []; name = ''; size = 0; capped = false;
  }
  function consume(value) {
    if (!value) { frame(); return; }
    if (value.startsWith('event:')) name = value.slice(6).trim();
    if (value === 'data' || value.startsWith('data:')) {
      const part = value === 'data' ? '' : value.slice(5).replace(/^ /, '');
      size += part.length;
      if (size <= LIMIT && !capped) data.push(part);
      else { data = []; capped = true; }
    }
  }
  function feed(text, final = false) {
    line += text;
    let match;
    while ((match = /\r\n|\n|\r(?!$)/.exec(line))) {
      consume(line.slice(0, match.index));
      line = line.slice(match.index + match[0].length);
    }
    if (line.length > LIMIT) { line = line.slice(-LIMIT); capped = true; }
    if (final) { if (line) consume(line.replace(/\r$/, '')); line = ''; frame(); }
  }
  return {
    observe(response) {
      http = response.status;
      const value = (response.headers.get('content-type') || '').split(';')[0].trim();
      media = /^[a-z0-9.+-]+\/[a-z0-9.+-]+$/i.test(value) ? value : 'other';
      if (!response.ok || !response.body) return response;
      return new Response(response.body.pipeThrough(new TransformStream({
        transform(chunk, controller) { feed(decoder.decode(chunk, { stream: true })); controller.enqueue(chunk); },
        flush() { feed(decoder.decode(), true); },
      })), { status: response.status, statusText: response.statusText, headers: response.headers });
    },
    summary() { return `SSE diagnostic: HTTP=${http}; media=${media}; events=${count}; ${invalid ? 'first_invalid=' + invalid : 'last=' + (last || 'none')}`; },
  };
}
