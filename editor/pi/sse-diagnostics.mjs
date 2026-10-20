// Observe framing without changing bytes or retaining response text in diagnostics.
const LIMIT = 65536;
const knownEvents = new Set(['response.created', 'response.in_progress', 'response.completed', 'response.failed',
  'response.incomplete', 'response.output_item.added', 'response.output_item.done', 'response.content_part.added',
  'response.content_part.done', 'response.output_text.delta', 'response.output_text.done',
  'response.function_call_arguments.delta', 'response.function_call_arguments.done', 'error']);
const eventLabel = value => knownEvents.has(value) ? value : value ? 'other' : 'message';

export function createSseDiagnostics() {
  let http = 'unknown', media = 'unknown', count = 0, invalid = '', last = '', line = '', data = [], name = '', size = 0, capped = false;
  let badIndex = 0, completed = false, sentinel = false, eof = false, bytes = 0, chunks = 0, jsonFrames = 0, replacements = 0;
  let requestBytes = 0, inputItems = 0, toolCount = 0, wireStreaming = true, wireBytes = 0, wireDone = false, wireInterrupted = false, jsonValid = 'unknown';
  const history = [];
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
    if (valid) jsonFrames++;
    if (kind === 'response.completed') completed = true;
    if (kind === 'done-sentinel') sentinel = true;
    last = `#${count} event=${eventLabel(name)} data=${kind}`;
    history.push(last); if (history.length > 6) history.shift();
    if (!valid && !badIndex) badIndex = count;
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
    replacements += (text.match(/\ufffd/g) || []).length;
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
    request(init) {
      if (typeof init?.body !== 'string') return;
      requestBytes = new TextEncoder().encode(init.body).byteLength;
      try {
        const value = JSON.parse(init.body);
        inputItems = Array.isArray(value.input) ? value.input.length : value.input ? 1 : 0;
        toolCount = Array.isArray(value.tools) ? value.tools.length : 0;
        wireStreaming = value.stream !== false;
      } catch { /* Only numeric request metadata is retained. */ }
    },
    jsonMeta(value) {
      if (value.status !== undefined) http = value.status;
      if (value.media !== undefined) media = ['application/json', 'text/event-stream'].includes(value.media) ? value.media : 'other';
      if (value.bytes !== undefined) wireBytes = value.bytes;
      if (value.done !== undefined) wireDone = value.done;
      if (value.interrupted) wireInterrupted = true;
      if (value.valid !== undefined) jsonValid = value.valid ? '1' : '0';
    },
    observe(response) {
      if (wireStreaming) http = response.status;
      const value = (response.headers.get('content-type') || '').split(';')[0].trim();
      if (wireStreaming) media = /^[a-z0-9.+-]+\/[a-z0-9.+-]+$/i.test(value) ? value : 'other';
      if (!response.ok || !response.body) return response;
      return new Response(response.body.pipeThrough(new TransformStream({
        transform(chunk, controller) { bytes += chunk.byteLength; chunks++; feed(decoder.decode(chunk, { stream: true })); controller.enqueue(chunk); },
        flush() { eof = true; feed(decoder.decode(), true); },
      })), { status: response.status, statusText: response.statusText, headers: response.headers });
    },
    summary() { return `SSE diagnostic: HTTP=${http}; media=${media}; events=${count}; ${invalid ? 'first_invalid=' + invalid : 'last=' + (last || 'none')}`; },
    report() {
      const pending = size + line.length;
      const code = wireStreaming
        ? `AI-SSE H${http} E${count} B${badIndex} P${pending} C${+completed} D${+sentinel} F${+eof} Q${requestBytes} I${inputItems}`
        : `AI-JSON H${http} Q${requestBytes} I${inputItems} R${wireBytes} J${jsonValid} X${+wireInterrupted}`;
      const hint = !wireStreaming
        ? wireInterrupted ? 'The JSON response body was interrupted during reading.'
          : jsonValid === '0' ? 'Received bytes could not be parsed as JSON; request-size limits are not established by this alone.'
          : jsonValid === '1' ? 'The JSON body parsed successfully. Inspect the response-schema or tool-argument error.'
          : 'JSON response not parsed yet. Inspect HTTP status and Content-Type.'
        : badIndex ? `Non-JSON event observed at #${badIndex}; the server SSE format needs inspection.`
        : pending ? 'Unfinished SSE data remained when the client failed.'
        : !completed ? 'No response.completed event observed. All completed frames seen so far were JSON; the failing bytes may not have reached this observer.'
        : 'response.completed was observed. Inspect the client error and later events.';
      return { code, details: `Request bytes=${requestBytes}; input-items=${inputItems}; tools=${toolCount}. Byte size is not token count.\nJSON wire: received-bytes=${wireBytes}; EOF=${+wireDone}; interrupted=${+wireInterrupted}; valid=${jsonValid}\n${hint}\nHTTP=${http}; media=${media}; bytes=${bytes}; chunks=${chunks}; JSON-frames=${jsonFrames}; UTF8-replacements=${replacements}; pending-data-lines=${data.length}; pending-line-chars=${line.length}\nRecent frame shapes (no payload):\n${history.join('\n') || 'none'}` };
    },
  };
}
