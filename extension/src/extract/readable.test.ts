import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, beforeEach, expect, it } from 'vitest'
import { extractReadable } from './readable'

const library = readFileSync(resolve('node_modules/@mozilla/readability/Readability.js'), 'utf8')
const fixture = readFileSync(resolve('src/extract/fixtures/blog-no-article.html'), 'utf8')
const execute = [extractReadable, () =>
  new Function(`return (${extractReadable.toString()})()`)() as ReturnType<typeof extractReadable>]
type ReadabilityWindow = Window & { Readability?: unknown }

beforeEach(() => {
  document.documentElement.innerHTML = fixture
  window.eval(library)
})
afterEach(() => {
  delete (window as ReadabilityWindow).Readability
  document.head.innerHTML = ''
  document.body.innerHTML = ''
})

for (const [index, run] of execute.entries()) {
  it(`${index ? 'serialized' : 'direct'}: keeps only post text, links and images from a page without article`, () => {
    const original = document.body.outerHTML
    const page = run()
    expect(page).not.toBeNull()
    expect(page).toMatchObject({
      title: 'A practical field guide to tiny gardens',
      site_name: 'Field Notes', author: 'Robin Example',
      published_at: '2026-05-11T10:00:00Z',
      links: [{ url: 'https://garden.example/soil-guide', text: 'the soil guide' }],
      images: [{ url: 'https://garden.example/pot.png', alt: 'A garden pot' }],
    })
    expect(page?.content_text).toContain('Tiny gardens thrive')
    expect(page?.content_text).toContain('Keep a record of what worked')
    expect(page?.content_text).not.toMatch(/Recent articles|Unrelated recent story|Sponsored|Archive 2023/)
    expect(document.body.outerHTML).toBe(original)
  })

  it(`${index ? 'serialized' : 'direct'}: rejects short navigation-only pages`, () => {
    document.head.innerHTML = '<title>Navigation</title>'
    document.body.innerHTML = '<nav><a href="https://garden.example/">Home</a></nav><ul><li>2023</li><li>2024</li></ul>'
    expect(run()).toBeNull()
  })

  it(`${index ? 'serialized' : 'direct'}: returns null without an injected Readability global`, () => {
    delete (window as ReadabilityWindow).Readability
    expect(run()).toBeNull()
  })
}
