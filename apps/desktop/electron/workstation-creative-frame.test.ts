import { describe, expect, it } from 'vitest'

import { creativeSvg } from './workstation-creative-frame'

describe('Creative canvas document', () => {
  it('preserves editable values and escapes text without accepting executable content', () => {
    const document = {
      schemaVersion: 1, width: 360, height: 640, background: '#112233',
      elements: [{ kind: 'text', x: 20, y: 100, size: 24, fill: '#ffffff', text: '<script>alert(1)</script>' }]
    }
    const result = creativeSvg(document)
    expect(result.document).toEqual(document)
    expect(result.svg).toContain('&lt;script&gt;alert(1)&lt;/script&gt;')
    expect(result.svg).not.toContain('<script>')
    expect(result.svg).toContain('width="360" height="640"')
  })

  it('rejects injected fields, external resources, unsupported objects and unbounded dimensions', () => {
    const document = { schemaVersion: 1, width: 360, height: 640, background: '#112233', elements: [] }
    for (const invalid of [
      { ...document, width: 1e20 }, { ...document, height: 640.5 },
      { ...document, elements: [{ kind: 'image', url: 'https://example.com' }] },
      { ...document, elements: [{ kind: '__proto__' }] },
      { ...document, javascript: 'process.exit()' },
      { ...document, background: 'url(https://example.com)' },
      { ...document, elements: [{ kind: 'rect', x: 0, y: 0, width: 10, height: 10, fill: '#ffffff', onclick: 'alert(1)' }] }
    ]) expect(() => creativeSvg(invalid)).toThrow()
  })
})
