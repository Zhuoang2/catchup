import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, expect, it } from 'vitest'
import { extractGeneric } from './generic'

const cases = [extractGeneric, () => new Function(`return (${extractGeneric.toString()})()`)() as ReturnType<typeof extractGeneric>]
const fixture = (name: string) => readFileSync(resolve(`src/extract/fixtures/${name}.html`), 'utf8')

beforeEach(() => { document.head.innerHTML = ''; document.body.innerHTML = '' })

for (const [index, run] of cases.entries()) {
  const mode = index === 0 ? 'direct' : 'serialized'
  it(`${mode}: reads article metadata, text, images and links without changing the page`, () => {
    document.documentElement.innerHTML = fixture('article')
    const original = document.body.outerHTML
    const result = run()
    expect(result).toMatchObject({
      url: 'https://read.example/story', title: 'A better headline',
      site_name: 'Daily Example', author: 'A Writer',
      published_at: '2025-01-02T00:00:00Z',
      images: [
        { url: 'https://read.example/one.png', alt: 'One' },
        { url: 'https://read.example/two.png', alt: 'Two' },
      ],
      links: [{ url: 'https://read.example/more', text: 'More reading' }],
    })
    expect(result.content_text).toMatch(/First paragraph with emphasis\.\nSecond paragraph\./)
    expect(result.content_text).not.toMatch(/navigation|sidebar|footer/i)
    expect(document.body.outerHTML).toBe(original)
  })

  it(`${mode}: falls back to title, host and main text when metadata is absent`, () => {
    document.documentElement.innerHTML = fixture('plain')
    const original = document.body.outerHTML
    const result = run()
    expect(result.url).toBe(location.href)
    expect(result.title).toBe('Plain document')
    expect(result.site_name).toBe(location.hostname)
    expect(result.content_text).toBe('Start here.\nContinue here.')
    expect(document.body.outerHTML).toBe(original)
  })

  it(`${mode}: limits content, images, links and rejects non-HTTP URLs`, () => {
    document.head.innerHTML = '<link rel="canonical" href="javascript:alert(1)"><meta property="og:url" content="file:///secret">'
    document.body.innerHTML = `<article><p>${'A'.repeat(17000)}</p>
      ${Array.from({ length: 12 }, (_, n) => `<img src="https://img.example/${n}" alt="${n}">`).join('')}
      <img src="data:image/png;base64,abcd">
      ${Array.from({ length: 55 }, (_, n) => `<a href="https://links.example/${n}">Link ${n}</a>`).join('')}
      <a href="mailto:x@example.com">Bad link</a></article>`
    const original = document.body.outerHTML
    const result = run()
    expect(result.url).toBe(location.href)
    expect(result.content_text.length).toBeLessThanOrEqual(16000)
    expect(result.images).toHaveLength(8)
    expect(result.links).toHaveLength(50)
    expect(result.images.every(image => image.url.startsWith('https://'))).toBe(true)
    expect(result.links.every(link => link.url.startsWith('https://'))).toBe(true)
    expect(document.body.outerHTML).toBe(original)
  })
}
