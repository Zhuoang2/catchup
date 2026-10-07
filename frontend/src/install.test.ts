import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

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
  })

  it('provides both start commands and a working Reload button on the offline page', () => {
    const html = readFileSync('public/offline.html', 'utf8')
    expect(html).toContain('docker compose up -d')
    expect(html).toContain('uv run catchup serve')
    expect(html).toContain('<button type="button" id="reload">Reload</button>')
    expect(html).toContain("location.reload()")
    expect(html).toContain('prefers-color-scheme: dark')
  })
})
