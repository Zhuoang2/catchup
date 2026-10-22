import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, expect, it } from 'vitest'
import { extractX } from './x'

beforeEach(() => { document.head.innerHTML = ''; document.body.innerHTML = '' })
const runs = [extractX, () => new Function(`return (${extractX.toString()})()`)() as ReturnType<typeof extractX>]

for (const [index, run] of runs.entries()) {
  const mode = index === 0 ? 'direct' : 'serialized'
  it(`${mode}: selects the matching post and only its author's later replies`, () => {
    document.body.innerHTML = readFileSync(resolve('src/extract/fixtures/x-post.html'), 'utf8')
    const before = document.body.outerHTML
    expect(run()).toMatchObject({
      url: 'https://x.com/alice/status/123',
      title: 'Alice Example on X', site_name: 'X · Alice Example',
      author: 'Alice Example @alice', published_at: '2025-03-04T12:00:00Z',
      images: [{ url: 'https://images.example/photo.jpg', alt: 'A photo' }],
      replies: ['First author reply', 'Second author reply'],
      links: [
        { url: 'https://news.example/story', text: 'https://news.example/story' },
        { url: 'https://news.example/ordinary', text: 'an ordinary link' },
        { url: 'https://x.com/alice/status/123', text: 'status' },
      ],
    })
    expect(run()?.content_text).toContain('The main post')
    expect(document.body.outerHTML).toBe(before)
  })
  it(`${mode}: returns null when the status post is missing`, () => {
    document.body.innerHTML = '<article data-testid="tweet"><a href="https://x.com/alice/status/999">Other</a></article>'
    expect(run()).toBeNull()
  })
  it(`${mode}: matches the post even when a quoted status link appears first`, () => {
    document.body.innerHTML = `<article data-testid="tweet">
      <div data-testid="User-Name">Alice <span>@alice</span></div>
      <div data-testid="tweetText">Quoted a post</div>
      <a href="https://x.com/bob/status/999">Quote</a>
      <a href="https://x.com/alice/status/123">Own post</a>
    </article>`
    expect(run()?.content_text).toBe('Quoted a post')
  })
}
