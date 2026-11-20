import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { extractPage } from './page'

const REL = 'https://code.example/garden-tools/releases/1.2'
const library = readFileSync(resolve('node_modules/@mozilla/readability/Readability.js'), 'utf8')
const fixture = (name: string) => readFileSync(resolve(`src/extract/fixtures/${name}.html`), 'utf8')
const execute = [extractPage, () =>
  new Function(`return (${extractPage.toString()})()`)() as ReturnType<typeof extractPage>]
type ReadabilityWindow = Window & { Readability?: unknown }
const PLAIN = '<head><title>Plain</title></head><body><nav><a href="https://garden.example/nav">Nav</a></nav><main><p>Start here.</p><p>Continue here.</p></main></body>'

beforeEach(() => {
  document.documentElement.innerHTML = fixture('blog-no-article')
  window.eval(library)
})
afterEach(() => {
  delete (window as ReadabilityWindow).Readability
  document.head.innerHTML = ''
  document.body.innerHTML = ''
})

for (const [index, extract] of execute.entries()) {
  const mode = index === 0 ? 'direct' : 'serialized'
  const run = () => {
    const original = document.body.outerHTML
    const page = extract()
    expect(document.body.outerHTML).toBe(original)
    return page
  }

  it(`${mode}: saves a tiny note, not the longer sponsor banner beside it`, () => {
    document.documentElement.innerHTML = fixture('blog-tiny-note')
    const page = run()
    expect(page.content_text).toBe('My tiny garden is ready. Start with seeds today.')
    expect(page.links).toEqual([{ url: 'https://garden.example/seeds', text: 'Start with seeds' }])
  })

  it(`${mode}: saves a post before an indented sponsor block`, () => {
    document.documentElement.innerHTML = fixture('blog-indented-sponsor')
    const page = run()
    expect(page.content_text.startsWith('Tiny gardens thrive')).toBe(true)
    expect(page.content_text).not.toMatch(/Support our imaginary/)
    expect(page.links).toEqual([{ url: 'https://garden.example/log', text: 'keep a log' }])
  })

  it(`${mode}: saves a short link post, not the sidebar`, () => {
    document.documentElement.innerHTML = fixture('link-post')
    const page = run()
    expect(page.content_text).toContain('The community garden fund drive. Please consider giving to the garden fund this year.')
    expect(page.content_text).not.toMatch(/This is a link post|Monthly briefing|Sponsor me|Sponsored by|Recent articles/)
    expect(page.links).toEqual([{ url: 'https://fund.example/', text: 'The community garden fund drive' }])
  })

  it(`${mode}: saves the release link from the title row first`, () => {
    document.documentElement.innerHTML = fixture('release-note')
    const page = run()
    expect(page.links[0]).toEqual({ url: REL, text: 'garden-tools 1.2' })
    expect(page.content_text.startsWith('A bug fix release for garden-tools')).toBe(true)
    expect(page.content_text).not.toMatch(/Sponsored by|Sponsor me|This is a beat|Recent articles|Monthly briefing/)
    expect(page.links.some(link => /ads\.example|sponsors\.example|\/tags\//.test(link.url))).toBe(false)
  })

  it(`${mode}: saves the title row of a release note without a body`, () => {
    document.documentElement.innerHTML = fixture('release-note')
    document.querySelector('.beat-note')!.remove()
    const page = run()
    expect(page.links[0].url).toBe(REL)
    expect(page.content_text).toContain('garden-tools 1.2')
    expect(page.content_text).not.toMatch(/This is a beat|Sponsor me|Sponsored by/)
  })

  for (const readability of [true, false]) {
    it(`${mode}: leaves out hidden text and links ${readability ? 'with' : 'without'} Readability`, () => {
      document.documentElement.innerHTML = fixture('hidden-main')
      if (!readability) delete (window as ReadabilityWindow).Readability
      const page = run()
      expect(page.content_text).toContain('Water tiny gardens in the morning')
      expect(page.content_text).toContain('Shown inside ghost')
      expect(page.content_text).not.toMatch(/Hidden menu|Collapsed block|Inline hidden|Ghost text|Ghost paragraph/)
      expect(page.links).toEqual([{ url: 'https://garden.example/soil', text: 'the soil guide' }])
    })
  }

  it(`${mode}: reads the date from the article header`, () => {
    document.documentElement.innerHTML = fixture('python-post')
    const page = run()
    expect(page.published_at).toBe('2026-11-10T00:00:00.000Z')
    expect(page.title).toBe('Garden tools 2.0 is now available | Garden Insider')
  })

  it(`${mode}: does not put a title link to the page itself first`, () => {
    document.documentElement.innerHTML = '<head><title>Small garden note</title><link rel="canonical" href="https://garden.example/2026/note"></head><body><div class="masthead"><h2><a href="https://garden.example/2026/note#top">Small garden note</a></h2></div><article><p>My tiny garden is ready, and the first seedlings came up this week after a long and rainy start to the season.</p><p>See <a href="https://garden.example/seeds">the seed list</a>.</p></article></body>'
    expect(run().links).toEqual([{ url: 'https://garden.example/seeds', text: 'the seed list' }])
  })

  it(`${mode}: saves each link address once`, () => {
    document.documentElement.innerHTML = '<head><title>Notes</title></head><body><main><p>Read <a href="https://garden.example/a">the guide</a> and then <a href="https://garden.example/a">the guide again</a>, and <a href="https://garden.example/b">more</a>.</p></main></body>'
    expect(run().links).toEqual([
      { url: 'https://garden.example/a', text: 'the guide' },
      { url: 'https://garden.example/b', text: 'more' },
    ])
  })

  it(`${mode}: saves the image address the page loaded`, () => {
    document.documentElement.innerHTML = '<head><title>Pots</title></head><body><main><p>A pot on the windowsill.</p><img src="https://garden.example/small.png" alt="Pot"></main></body>'
    Object.defineProperty(document.querySelector('img')!, 'currentSrc', { value: 'https://garden.example/large.png' })
    expect(run().images).toEqual([{ url: 'https://garden.example/large.png', alt: 'Pot' }])
  })

  it(`${mode}: saves the short post instead of the longer sponsor banner`, () => {
    document.documentElement.innerHTML = fixture('blog-short-post')
    const original = document.body.outerHTML
    const page = run()
    expect(page?.content_text).toContain('My tiny garden is ready. Start with seeds, then check watering. I will share the first results next week.')
    expect(page?.links).toEqual([
      { url: 'https://garden.example/seeds', text: 'Start with seeds' },
      { url: 'https://garden.example/water', text: 'check watering' },
    ])
    expect(page?.content_text).not.toMatch(/Support our imaginary|Recent articles|Support promo|Archive 202[45]/)
    expect(document.body.outerHTML).toBe(original)
    expect(page.published_at).toBe('2026-10-21')
  })

  it(`${mode}: keeps only post text, links and images from a page without article`, () => {
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

  it(`${mode}: reads a page without main text from its body, without navigation`, () => {
    document.documentElement.innerHTML = '<head><title>Navigation</title></head><body><nav><a href="https://garden.example/">Home</a></nav><ul><li>2023</li><li>2024</li></ul></body>'
    const page = run()
    expect(page.content_text).toBe('2023\n2024')
    expect(page.links).toEqual([])
  })

  it(`${mode}: matches the title without its site name, and skips header, aside and footer links`, () => {
    document.documentElement.innerHTML = '<head><title>Small garden note | Field Notes</title></head><body><header><a href="https://garden.example/home">Small garden note</a></header><aside><a href="https://garden.example/aside">Small garden note</a></aside><footer><a href="https://garden.example/footer">Small garden note</a></footer><div class="masthead"><a href="https://notes.example/small">Small garden note</a></div><article><p>My tiny garden is ready, and the first seedlings came up this week after a long and rainy start to the season.</p><p>See <a href="https://garden.example/seeds">the seed list</a>.</p></article></body>'
    expect(run().links).toEqual([
      { url: 'https://notes.example/small', text: 'Small garden note' },
      { url: 'https://garden.example/seeds', text: 'the seed list' },
    ])
  })

  it(`${mode}: adds no title link when the page has no title`, () => {
    document.documentElement.innerHTML = '<head></head><body><div class="promo"><a href="https://ads.example/x"><img src="https://ads.example/x.png" alt=""></a></div><div class="entry"><p>My tiny garden is ready, and the first seedlings came up this week after a long and rainy start.</p><p>See <a href="https://garden.example/seeds">the seed list</a>.</p></div></body>'
    expect(run().links).toEqual([{ url: 'https://garden.example/seeds', text: 'the seed list' }])
  })

  for (const readability of [true, false]) {
    it(`${mode}: leaves out a hidden link whose content is an element ${readability ? 'with' : 'without'} Readability`, () => {
      document.documentElement.innerHTML = '<head><title>Guide</title><style>.ghost { visibility: hidden }</style></head><body><main><p>Water tiny gardens in the morning, when the soil is cool and the leaves dry quickly. <span class="ghost"><a href="https://garden.example/share"><b>Share</b></a></span></p><p>Read <a href="https://garden.example/soil">the soil guide</a> for more.</p></main></body>'
      if (!readability) delete (window as ReadabilityWindow).Readability
      const page = run()
      expect(page.content_text).not.toContain('Share')
      expect(page.links).toEqual([{ url: 'https://garden.example/soil', text: 'the soil guide' }])
    })
  }

  it(`${mode}: falls back to the main region when Readability finds no text`, () => {
    document.documentElement.innerHTML = PLAIN
    window.eval('window.Readability = class { parse() { return { content: "<p> </p>", textContent: " \\n ", title: "" } } }')
    const page = run()
    expect(page.content_text).toBe('Start here.\nContinue here.')
    expect(page.links).toEqual([])
  })

  it(`${mode}: falls back to the main region when Readability throws`, () => {
    document.documentElement.innerHTML = PLAIN
    window.eval('window.Readability = class { parse() { throw new Error("broken") } }')
    const page = run()
    expect(page.content_text).toBe('Start here.\nContinue here.')
    expect(page.links).toEqual([])
  })

  describe(`${mode}: without Readability`, () => {
    beforeEach(() => { delete (window as ReadabilityWindow).Readability })
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

    it(`${mode}: reads a main region inside a form without its outside form ancestor excluding it`, () => {
      document.body.innerHTML = '<form><main><p>Main text</p></main></form>'
      expect(run().content_text).toBe('Main text')
    })

    it(`${mode}: excludes nav text, links and images strictly inside the selected root`, () => {
      document.body.innerHTML = `<main>
        <nav><a href="https://garden.example/nav">Navigation</a>
          <img src="https://garden.example/nav.png"></nav>
        <p>Main text</p><a href="https://garden.example/post">Post link</a>
        <img src="https://garden.example/post.png"></main>`
      const result = run()
      expect(result.content_text).toBe('Main text\nPost link')
      expect(result.links).toEqual([{ url: 'https://garden.example/post', text: 'Post link' }])
      expect(result.images).toEqual([{ url: 'https://garden.example/post.png', alt: '' }])
    })

    it(`${mode}: does not exclude the selected root even if it is a form`, () => {
      document.body.innerHTML = '<form role="main"><p>Main text</p></form>'
      expect(run().content_text).toBe('Main text')
    })
  })
}
