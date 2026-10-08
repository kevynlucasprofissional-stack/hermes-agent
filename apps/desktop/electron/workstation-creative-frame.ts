import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'

import { nativeImage, type WebContentsView } from 'electron'

export interface CreativeCanvasDocument {
  schemaVersion: 1
  width: number
  height: number
  background: string
  elements: Array<Record<string, unknown>>
}

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('invalid_creative_object')
  return value as Record<string, unknown>
}

function fields(value: Record<string, unknown>, allowed: string[]): void {
  if (Object.keys(value).some(key => !allowed.includes(key))) throw new Error('unknown_creative_field')
}

function number(value: unknown, min = -8192, max = 8192): number {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) {
    throw new Error('invalid_creative_number')
  }
  return value
}

function color(value: unknown): string {
  if (typeof value !== 'string' || !/^#[0-9a-fA-F]{6}$/.test(value)) throw new Error('invalid_creative_color')
  return value
}

function text(value: unknown): string {
  if (typeof value !== 'string' || value.length > 4096) throw new Error('invalid_creative_text')
  return value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&apos;')
}

const elements: Record<string, (value: Record<string, unknown>) => string> = {
  rect: value => {
    fields(value, ['kind', 'x', 'y', 'width', 'height', 'fill', 'radius'])
    return `<rect x="${number(value.x)}" y="${number(value.y)}" width="${number(value.width, 0)}" height="${number(value.height, 0)}" rx="${number(value.radius ?? 0, 0)}" fill="${color(value.fill)}"/>`
  },
  circle: value => {
    fields(value, ['kind', 'x', 'y', 'radius', 'fill'])
    return `<circle cx="${number(value.x)}" cy="${number(value.y)}" r="${number(value.radius, 0)}" fill="${color(value.fill)}"/>`
  },
  text: value => {
    fields(value, ['kind', 'x', 'y', 'text', 'size', 'fill', 'font', 'anchor'])
    const font = value.font ?? 'sans-serif'
    const anchor = value.anchor ?? 'start'
    if (!['sans-serif', 'serif', 'monospace'].includes(String(font)) || !['start', 'middle', 'end'].includes(String(anchor))) {
      throw new Error('invalid_creative_font')
    }
    return `<text x="${number(value.x)}" y="${number(value.y)}" font-size="${number(value.size, 1, 512)}" font-family="${font}" text-anchor="${anchor}" fill="${color(value.fill)}">${text(value.text)}</text>`
  }
}

export function creativeSvg(input: unknown): { document: CreativeCanvasDocument; svg: string } {
  const value = object(input)
  fields(value, ['schemaVersion', 'width', 'height', 'background', 'elements'])
  if (value.schemaVersion !== 1 || !Array.isArray(value.elements) || value.elements.length > 256) {
    throw new Error('invalid_creative_document')
  }
  const width = number(value.width, 32, 4096)
  const height = number(value.height, 32, 4096)
  if (!Number.isInteger(width) || !Number.isInteger(height) || width * height > 8_388_608) {
    throw new Error('invalid_creative_dimensions')
  }
  const body = value.elements.map(item => {
    const element = object(item)
    const handler = Object.hasOwn(elements, String(element.kind)) ? elements[String(element.kind)] : null
    if (!handler) throw new Error('unknown_creative_element')
    return handler(element)
  }).join('')
  const background = color(value.background)
  return {
    document: { schemaVersion: 1, width, height, background, elements: value.elements },
    svg: `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><rect width="${width}" height="${height}" fill="${background}"/>${body}</svg>`
  }
}

export async function renderCreativeFrame(
  view: WebContentsView, args: Record<string, unknown>, directory: string, assertOwner: () => void
): Promise<Record<string, unknown>> {
  fields(args, ['source_json', 'source_sha256'])
  if (typeof args.source_json !== 'string' || Buffer.byteLength(args.source_json) > 262_144) {
    throw new Error('invalid_creative_source')
  }
  const sourceSha = crypto.createHash('sha256').update(args.source_json, 'utf8').digest('hex')
  if (args.source_sha256 !== sourceSha) throw new Error('creative_source_revision_mismatch')
  const { document, svg } = creativeSvg(JSON.parse(args.source_json))
  const html = `<html><head><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; form-action 'none'; base-uri 'none'"><style>html,body{margin:0;padding:0;overflow:hidden;width:${document.width}px;height:${document.height}px}</style></head><body>${svg}</body></html>`
  const target = `data:text/html;charset=utf-8,${encodeURIComponent(html)}`
  const wc = view.webContents
  const bounds = view.getBounds()
  const zoom = wc.getZoomFactor()
  assertOwner()
  try {
    view.setBounds({ x: bounds.x, y: bounds.y, width: document.width, height: document.height })
    wc.setZoomFactor(1)
    await wc.loadURL(target)
    await wc.executeJavaScript('document.fonts.ready.then(() => ({width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight}))')
    const painted = await wc.executeJavaScript('Promise.race([new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve(true)))), new Promise(resolve => setTimeout(() => resolve(false), 2000))])')
    if (!painted) throw new Error('creative_paint_timeout')
    assertOwner()
    if (wc.getURL() !== target) throw new Error('creative_preview_navigated')
    const image = await wc.capturePage({ x: 0, y: 0, width: document.width, height: document.height }, { stayHidden: true, stayAwake: true })
    let png = image.toPNG()
    if (!png.length) throw new Error('creative_empty_frame')
    if (png.readUInt32BE(16) !== document.width || png.readUInt32BE(20) !== document.height) {
      png = nativeImage.createFromBuffer(png).resize({ width: document.width, height: document.height }).toPNG()
    }
    assertOwner()
    if (wc.getURL() !== target || png.readUInt32BE(16) !== document.width || png.readUInt32BE(20) !== document.height) {
      throw new Error('creative_frame_readback_mismatch')
    }
    fs.mkdirSync(directory, { recursive: true })
    const filePath = path.join(directory, `creative-${crypto.randomUUID()}.png`)
    fs.writeFileSync(filePath, png, { flag: 'wx' })
    return {
      success: true, runtime: 'electron-chromium', screenshot_path: filePath,
      width: document.width, height: document.height, source_sha256: sourceSha,
      sha256: crypto.createHash('sha256').update(png).digest('hex'),
      svg_sha256: crypto.createHash('sha256').update(svg).digest('hex'), svg_source: svg,
      media_type: 'image/png'
    }
  } finally {
    if (!wc.isDestroyed()) {
      wc.setZoomFactor(zoom)
      view.setBounds(bounds)
    }
  }
}
