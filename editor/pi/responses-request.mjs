// Some Responses-compatible gateways reject output-only status fields in replayed input items.
export function withoutInputStatus(init) {
  if (typeof init?.body !== 'string') return init;
  const body = JSON.parse(init.body);
  if (!Array.isArray(body.input)) return init;
  let changed = false;
  body.input = body.input.map(item => {
    if (!item || typeof item !== 'object' || Array.isArray(item) || !Object.hasOwn(item, 'status')) return item;
    const { status: _status, ...rest } = item;
    changed = true;
    return rest;
  });
  return changed ? { ...init, body: JSON.stringify(body) } : init;
}
