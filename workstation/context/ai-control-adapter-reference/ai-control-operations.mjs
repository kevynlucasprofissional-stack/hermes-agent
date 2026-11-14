// REFERENCE ONLY; shape validation is NOT authorization.
// Adopt into apps/desktop/electron/ai-control-operations.ts only after required gates.
const OPS = new Set(['status','snapshot','locate','waitFor','click','fill','press','screenshot'])
const MUTATING = new Set(['click','fill','press'])
const TARGETED = new Set(['locate','waitFor','click','fill','press'])
const KINDS = new Set(['css','role','label','text','testId'])
const KEYS = new Set(['Enter','Escape','Tab','Backspace','Delete','ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Home','End','Space'])
const obj = x => x !== null && typeof x === 'object' && !Array.isArray(x)
const string = (x,n) => typeof x === 'string' && x.length > 0 && x.length <= n && !x.includes('\0')
const failure = name => { throw new Error(name) }
function keys(x,allow) { for(const k of Object.keys(x)) if(!allow.includes(k)) failure('unknown_field') }

export function validateAiControlOperation(raw) {
  if(!obj(raw)) failure('invalid_request')
  keys(raw,['op','surface','target','text','key','timeoutMs','expected'])
  if(raw.surface !== 'desktop' || !OPS.has(raw.op)) failure('unsupported_scope_or_op')
  const timeoutMs = raw.timeoutMs ?? 5000
  if(!Number.isInteger(timeoutMs) || timeoutMs < 0 || timeoutMs > 10000) failure('invalid_timeout')
  const out = { op:raw.op, surface:'desktop', timeoutMs }

  if(TARGETED.has(raw.op)) {
    if(!obj(raw.target)) failure('target_required')
    keys(raw.target,['kind','value','exact'])
    if(!KINDS.has(raw.target.kind) || !string(raw.target.value,256) ||
      (raw.target.exact !== undefined && typeof raw.target.exact !== 'boolean')) failure('invalid_target')
    out.target = { kind:raw.target.kind, value:raw.target.value, exact:raw.target.exact ?? true }
  } else if ('target' in raw) failure('target_not_supported')

  if(raw.op === 'fill') {
    if(typeof raw.text !== 'string' || raw.text.length > 4096 || raw.text.includes('\0')) failure('invalid_fill')
    out.text = raw.text
  } else if('text' in raw) failure('text_not_supported')

  if(raw.op === 'press') {
    if(!KEYS.has(raw.key)) failure('invalid_key')
    out.key = raw.key
  } else if('key' in raw) failure('key_not_supported')

  if(MUTATING.has(raw.op)) {
    if(!obj(raw.expected)) failure('expected_binding_required')
    keys(raw.expected,['documentId','grantId'])
    if(!string(raw.expected.documentId,128) || !string(raw.expected.grantId,128)) failure('invalid_binding')
    out.expected = { documentId:raw.expected.documentId, grantId:raw.expected.grantId }
  } else if('expected' in raw) failure('binding_not_supported')
  return Object.freeze(out)
}
export function isMutation(op) { return MUTATING.has(op) }
