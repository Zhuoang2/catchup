import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { inflateSync } from 'node:zlib'
import { describe, expect, it } from 'vitest'

const smallIconPattern = [
  '................',
  '................',
  '..############..',
  '..############..',
  '..############..',
  '..############..',
  '..###......###..',
  '..############..',
  '..############..',
  '..###......###..',
  '..############..',
  '..############..',
  '..############..',
  '..############..',
  '................',
  '................',
]

const icons = [
  { src: '/icon-192.png', sizes: '192x192', purpose: 'any', size: 192 },
  { src: '/icon-512.png', sizes: '512x512', purpose: 'any', size: 512 },
  { src: '/icon-maskable-512.png', sizes: '512x512', purpose: 'maskable', size: 512 },
  { src: '/icon-1024.png', sizes: '1024x1024', purpose: 'any', size: 1024 },
]
function sizeAt(bytes: Uint8Array, offset: number): number {
  return (bytes[offset] * 2 ** 24 + bytes[offset + 1] * 2 ** 16
    + bytes[offset + 2] * 2 ** 8 + bytes[offset + 3])
}

describe('install assets', () => {
  it('draws the tab icon on the 16 px grid', () => {
    const document = new DOMParser().parseFromString(readFileSync('public/icon.svg', 'utf8'), 'image/svg+xml')
    const rectangles: { left: number; top: number; right: number; bottom: number; color: string | null }[] = []
    for (const shape of document.querySelectorAll('rect, path')) {
      if (shape.localName === 'rect') {
        const left = Number(shape.getAttribute('x') ?? 0)
        const top = Number(shape.getAttribute('y') ?? 0)
        rectangles.push({
          left, top,
          right: left + Number(shape.getAttribute('width')),
          bottom: top + Number(shape.getAttribute('height')),
          color: shape.getAttribute('fill'),
        })
      } else {
        const path = shape.getAttribute('d') ?? ''
        const segment = /M\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*h\s*(-?\d+(?:\.\d+)?)/g
        expect(path.replace(segment, '').trim(), 'SVG path must contain only M x y h length segments').toBe('')
        const width = Number(shape.getAttribute('stroke-width'))
        for (const match of path.matchAll(segment)) {
          const [, x, y, length] = match.map(Number)
          rectangles.push({
            left: x, right: x + length, top: y - width / 2, bottom: y + width / 2,
            color: shape.getAttribute('stroke'),
          })
        }
      }
    }
    for (const { left, top, right, bottom } of rectangles) {
      for (const edge of [left, top, right, bottom]) {
        expect(edge % 64, `SVG edge ${edge} must align to the 16 px grid`).toBe(0)
      }
    }
    const picture = smallIconPattern.map((row, y) => [...row].map((_, x) => {
      const centerX = (x + 0.5) * 64
      const centerY = (y + 0.5) * 64
      let color: string | null = null
      for (const rectangle of rectangles) {
        if (rectangle.left <= centerX && centerX < rectangle.right
          && rectangle.top <= centerY && centerY < rectangle.bottom) color = rectangle.color
      }
      return color === '#f4f0e6' ? '.' : color === '#151412' ? '#' : '?'
    }).join(''))
    expect(picture).toEqual(smallIconPattern)
  })

  it('keeps every app icon sharp at 16 px', () => {
    for (const file of ['icon-192.png', 'icon-512.png', 'icon-1024.png']) {
      const bytes = readFileSync(`public/${file}`)
      expect([...bytes.subarray(0, 8)], `${file}: PNG signature`).toEqual([137, 80, 78, 71, 13, 10, 26, 10])
      const chunks: Uint8Array[] = []
      let width = 0
      let height = 0
      for (let offset = 8; offset < bytes.length;) {
        const length = sizeAt(bytes, offset)
        expect(offset + length + 12, `${file}: complete PNG chunk`).toBeLessThanOrEqual(bytes.length)
        const type = new TextDecoder().decode(bytes.subarray(offset + 4, offset + 8))
        const data = bytes.subarray(offset + 8, offset + 8 + length)
        if (type === 'IHDR') {
          expect(data.length, `${file}: IHDR length`).toBe(13)
          width = sizeAt(data, 0)
          height = sizeAt(data, 4)
          expect([...data.subarray(8)], `${file}: requires 8-bit RGB, standard compression/filtering, no interlace`)
            .toEqual([8, 2, 0, 0, 0])
        } else if (type === 'IDAT') chunks.push(data)
        offset += length + 12
      }
      expect(width, `${file}: positive image width`).toBeGreaterThan(0)
      expect(height, `${file}: square image`).toBe(width)
      expect(width % 16, `${file}: whole 16 px blocks`).toBe(0)
      expect(chunks.length, `${file}: IDAT data`).toBeGreaterThan(0)
      const compressed = new Uint8Array(chunks.reduce((length, chunk) => length + chunk.length, 0))
      let offset = 0
      for (const chunk of chunks) {
        compressed.set(chunk, offset)
        offset += chunk.length
      }
      const pixels = inflateSync(compressed)
      const stride = width * 3 + 1
      expect(pixels.length, `${file}: complete RGB rows`).toBe(height * stride)
      for (let y = 0; y < height; y++) {
        expect(pixels[y * stride], `${file}: row ${y} requires PNG filter type 0`).toBe(0)
      }
      const wrongPixels: { file: string; block: number[]; pixel: number[]; color: number[] }[] = []
      const blockSize = width / 16
      for (let blockY = 0; blockY < 16; blockY++) {
        for (let blockX = 0; blockX < 16; blockX++) {
          const color = smallIconPattern[blockY][blockX] === '.' ? [244, 240, 230] : [21, 20, 18]
          for (let y = blockY * blockSize; y < (blockY + 1) * blockSize; y++) {
            for (let x = blockX * blockSize; x < (blockX + 1) * blockSize; x++) {
              const start = y * stride + 1 + x * 3
              if ((pixels[start] !== color[0] || pixels[start + 1] !== color[1] || pixels[start + 2] !== color[2])
                && wrongPixels.length < 8) {
                wrongPixels.push({
                  file, block: [blockX, blockY], pixel: [x, y],
                  color: [...pixels.subarray(start, start + 3)],
                })
              }
            }
          }
        }
      }
      expect(wrongPixels, `${file}: pixels must match the fixed 16 px pattern`).toEqual([])
    }
  })

  it('declares real SVG and PNG icons for the browser tab', () => {
    const html = new DOMParser().parseFromString(readFileSync('index.html', 'utf8'), 'text/html')
    const links = [...html.querySelectorAll('link[rel="icon"]')]
    const svg = links.find(link => link.getAttribute('href') === '/icon.svg')
    const png = links.find(link => link.getAttribute('href') === '/icon-192.png')

    expect(svg?.getAttribute('type')).toBe('image/svg+xml')
    expect(readFileSync('public/icon.svg', 'utf8')).toContain('<svg')
    expect(png?.getAttribute('type')).toBe('image/png')
    expect(png?.getAttribute('sizes')).toBe('192x192')
    expect([...readFileSync('public/icon-192.png').subarray(0, 8)])
      .toEqual([137, 80, 78, 71, 13, 10, 26, 10])
  })

  it('declares CatchUp and four real PNG icons with correct dimensions', () => {
    const manifest = JSON.parse(readFileSync('public/manifest.webmanifest', 'utf8'))
    expect(manifest).toMatchObject({
      name: 'CatchUp', short_name: 'CatchUp', start_url: '/', scope: '/', display: 'standalone',
      background_color: '#f4f0e6', theme_color: '#151412',
    })
    expect(manifest.icons).toHaveLength(4)
    for (const icon of icons) {
      expect(manifest.icons).toContainEqual(expect.objectContaining({
        src: icon.src, sizes: icon.sizes, purpose: icon.purpose,
      }))
      const bytes = readFileSync(`public${icon.src}`)
      expect([...bytes.slice(0, 8)]).toEqual([137, 80, 78, 71, 13, 10, 26, 10])
      expect(sizeAt(bytes, 16)).toBe(icon.size)
      expect(sizeAt(bytes, 20)).toBe(icon.size)
    }
    expect(readFileSync('public/icon.svg', 'utf8')).toContain('viewBox="0 0 1024 1024"')
  })

  it('regenerates byte-identical icons in a temporary directory', () => {
    const directory = mkdtempSync(join(tmpdir(), 'catchup-icons-'))
    try {
      execFileSync('python3', ['scripts/make-icons.py', '--output', directory])
      for (const name of ['icon.svg', ...icons.map(icon => icon.src.slice(1))]) {
        expect(readFileSync(join(directory, name))).toEqual(readFileSync(join('public', name)))
      }
    } finally {
      rmSync(directory, { recursive: true, force: true })
    }
  }, 30_000)

  it('provides both start commands and a working Reload button on the offline page', () => {
    const html = readFileSync('public/offline.html', 'utf8')
    expect(html).toContain('docker compose up -d')
    expect(html).toContain('uv run catchup serve')
    expect(html).toContain('<button type="button" id="reload">Reload</button>')
    expect(html).toContain("location.reload()")
    expect(html).toContain('prefers-color-scheme: dark')
    expect(html).toContain('font-family: var(--body)')
    expect(html).toContain('.brand { font: 2rem var(--heading); }')
    expect(html).toContain('justify-items: center; text-align: center;')
    expect(html).toContain('font-variant-caps: all-small-caps')
    expect(html).not.toContain('<span class="logo"')
    expect(html).not.toContain('.logo {')
  })

  it('embeds the CatchUp tab icon in the offline page without another icon request', () => {
    const page = new DOMParser().parseFromString(readFileSync('public/offline.html', 'utf8'), 'text/html')
    const links = [...page.querySelectorAll('link[rel$="icon"]')]
    expect(links).toHaveLength(1)
    expect(links[0].getAttribute('rel')).toBe('icon')
    const href = links[0].getAttribute('href')
    expect(href).toMatch(/^data:image\/svg\+xml(?:;base64)?,/)
    const [metadata, payload] = href!.slice(5).split(',', 2)
    const svg = metadata.endsWith(';base64')
      ? new TextDecoder().decode(Uint8Array.from(atob(payload), char => char.charCodeAt(0)))
      : decodeURIComponent(payload)
    const icon = readFileSync('public/icon.svg', 'utf8').trim()
    expect(svg).toBe(icon)
    const document = new DOMParser().parseFromString(svg, 'image/svg+xml')
    expect(document.documentElement.localName).toBe('svg')
    expect(document.documentElement.getAttribute('viewBox')).toBe('0 0 1024 1024')
    expect([...document.querySelectorAll('[fill]')].map(node => node.getAttribute('fill')))
      .toEqual(['#f4f0e6', '#151412'])
    const otherIconReferences = [...page.querySelectorAll('img, link, source')]
      .filter(element => element !== links[0]
        && ['src', 'href'].some(attribute => element.getAttribute(attribute)?.toLowerCase().includes('icon')))
    expect(otherIconReferences).toEqual([])
  })
})
