import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { expectAccessible } from '../test/accessibility'
import { DigestArticle } from './DigestArticle'
import { digestLang } from './lang'
import { limitedDigest, unrated } from '../test/limitedDigest'

it('shows only the most important items in their topics', async () => {
  const { container } = render(<MemoryRouter><DigestArticle digest={limitedDigest} topItems={5}/></MemoryRouter>)
  expect(Array.from(container.querySelectorAll('article.item .item-title a')).map(link =>
    link.textContent!.replace(' (opens the original)', ''))).toEqual(['A1', 'A2', 'C1', 'C2', 'C4'])
  expect(screen.queryByRole('heading', { name: 'Beta' })).toBeNull()
  expect(Array.from(screen.getByRole('navigation', { name: 'In this digest' }).querySelectorAll('li'))
    .map(li => li.textContent)).toEqual(['Alpha 2', 'Gamma 3', 'Creator updates 2'])
  expect(screen.getByRole('link', { name: 'Video one (opens the original)' })).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Video two (opens the original)' })).toBeInTheDocument()
  expect(container.querySelector('.digest-meta')).toHaveTextContent('10 items')
  expect(screen.getByText('Showing the 5 most important of the 8 items in topics.')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Show all 8' }))
    .toHaveAccessibleDescription('Showing the 5 most important of the 8 items in topics.')
  await expectAccessible(container)
})

it('shows every item and limits again', () => {
  const { container } = render(<MemoryRouter><DigestArticle digest={limitedDigest} topItems={5}/></MemoryRouter>)
  const button = screen.getByRole('button', { name: 'Show all 8' })
  button.focus()
  fireEvent.click(button)
  expect(container.querySelectorAll('article.item')).toHaveLength(8)
  expect(screen.getByRole('heading', { name: 'Beta' })).toBeInTheDocument()
  expect(container.querySelector('#digest-limit-note')).toHaveTextContent('Showing all 8 items in topics.')
  expect(screen.getByRole('button', { name: 'Show the 5 most important' })).toBe(button)
  expect(button).toHaveFocus()
  expect(screen.getByRole('status')).toHaveTextContent('Showing all 8 items in topics.')
  fireEvent.click(button)
  expect(container.querySelectorAll('article.item')).toHaveLength(5)
  expect(screen.getByRole('status')).toHaveTextContent('Showing the 5 most important of the 8 items in topics.')
})

it('starts limited again for the next digest', () => {
  const { container, rerender } = render(
    <MemoryRouter><DigestArticle digest={limitedDigest} topItems={5}/></MemoryRouter>)
  fireEvent.click(screen.getByRole('button', { name: 'Show all 8' }))
  rerender(<MemoryRouter><DigestArticle digest={{ ...limitedDigest, id: 8 }} topItems={5}/></MemoryRouter>)
  expect(container.querySelectorAll('article.item')).toHaveLength(5)
  expect(screen.getByText('Showing the 5 most important of the 8 items in topics.')).toBeInTheDocument()
})

it('shows short and unrated digests in full', () => {
  const short = render(<MemoryRouter><DigestArticle digest={limitedDigest} topItems={10}/></MemoryRouter>)
  expect(short.container.querySelectorAll('article.item')).toHaveLength(8)
  expect(short.container.querySelector('.digest-limit')).toBeNull()
  short.unmount()
  const old = render(<MemoryRouter><DigestArticle digest={unrated(limitedDigest)} topItems={5}/></MemoryRouter>)
  expect(old.container.querySelectorAll('article.item')).toHaveLength(8)
  expect(old.container.querySelector('.digest-limit')).toBeNull()
})

const digest = {
  id: 7, created_at: '2026-10-03T10:00:00Z', model_id: 'test',
  item_count: 1, source_count: 1,
  topics: [{ title: 'Technology', overview: 'Overview', items: [{
    id: 11, bookmarked: false, liked: false, rating: null, note: null,
    title: 'Article', link: 'https://example.test/article', source_name: 'Blog',
    published_at: null, summary: 'Summary', summary_unavailable: false,
  }] }],
}

it('places the before slot first, headEnd after metadata, and appends its section class', async () => {
  const { container } = render(<MemoryRouter><DigestArticle digest={digest}
    before={<div data-testid="before">Run controls</div>}
    headEnd={<a href="/digests">All digests</a>} className="page-home"/></MemoryRouter>)
  const section = container.querySelector('section.page-digest')!
  expect(section).toHaveClass('page', 'page-digest', 'page-home')
  expect(section.firstElementChild).toBe(screen.getByTestId('before'))
  const head = section.querySelector('.digest-head')!
  expect(head.querySelector('h1')).toBeInTheDocument()
  expect(head.lastElementChild).toContainElement(screen.getByRole('link', { name: 'All digests' }))
  expect(head.querySelector('.digest-meta')!.compareDocumentPosition(screen.getByRole('link', { name: 'All digests' }))
    & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  await expectAccessible(container)
})

it('shows the captured page kind and its own site name', async () => {
  const withCapture = { ...digest, topics: [{ ...digest.topics[0], items: [{
    ...digest.topics[0].items[0], source_kind: 'capture' as const, source_name: 'X · Name',
  }] }] }
  const { container } = render(<MemoryRouter><DigestArticle digest={withCapture}/></MemoryRouter>)
  const source = container.querySelector('.item-meta')!
  expect(source).toHaveTextContent('Saved from browser: X · Name')
  expect(source.querySelector('svg')).toBeInTheDocument()
  await expectAccessible(container)
})

it('shows the X account icon on a digest item', async () => {
  const withX = { ...digest, topics: [{ ...digest.topics[0], items: [{
    ...digest.topics[0].items[0], source_kind: 'x' as const, source_name: 'X · Writer',
  }] }] }
  const { container } = render(<MemoryRouter><DigestArticle digest={withX}/></MemoryRouter>)
  expect(container.querySelector('.item-meta')).toHaveTextContent('X account: X · Writer')
  expect(container.querySelector('.item-meta svg')).toBeInTheDocument()
  await expectAccessible(container)
})

it('does not render an overview after X data was removed from a mixed topic', () => {
  const cleared = { ...digest, topics: [{ ...digest.topics[0], overview: '' }] }
  const { container } = render(<MemoryRouter><DigestArticle digest={cleared}/></MemoryRouter>)
  expect(container.querySelector('.topic-overview')).toBeNull()
})

it('shows used context links after the summary, safely opening originals', async () => {
  const withLinks = { ...digest, topics: [{ ...digest.topics[0], items: [{
    ...digest.topics[0].items[0], also_read: [
      { title: 'GitHub release', url: 'https://github.com/example/release', kind: 'link' },
      { title: 'Author replies (2)', url: 'https://example.test/comments', kind: 'author_replies' },
    ],
  }] }] }
  const { container } = render(<MemoryRouter><DigestArticle digest={withLinks}/></MemoryRouter>)
  const line = screen.getByText(/Also read:/)
  expect(line).toHaveTextContent('Also read: GitHub release · Author replies (2)')
  expect(line.compareDocumentPosition(screen.getByText('Summary')) & Node.DOCUMENT_POSITION_PRECEDING)
    .toBeTruthy()
  for (const link of withinLine(line)) {
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(link).toHaveAttribute('href', expect.stringMatching(/^https:\/\//))
  }
  await expectAccessible(container)
})

function withinLine(line: HTMLElement) {
  return Array.from(line.querySelectorAll('a'))
}

it('omits also-read when the snapshot has no used links', () => {
  render(<MemoryRouter><DigestArticle digest={digest}/></MemoryRouter>)
  expect(screen.queryByText(/Also read:/)).toBeNull()
})

it('omits also-read for an explicitly empty snapshot list', () => {
  const empty = { ...digest, topics: [{ ...digest.topics[0], items: [{
    ...digest.topics[0].items[0], also_read: [],
  }] }] }
  render(<MemoryRouter><DigestArticle digest={empty}/></MemoryRouter>)
  expect(screen.queryByText(/Also read:/)).toBeNull()
})

it('renders chosen images in order between the summary and Also read, and hides a failed figure', async () => {
  const withImages = { ...digest, topics: [{ ...digest.topics[0], items: [{
    ...digest.topics[0].items[0],
    images: [
      { url: 'https://cdn.example/chart.png', alt: 'Growth chart' },
      { url: 'https://cdn.example/shot.png', alt: 'Interface screenshot' },
    ],
    also_read: [{ title: 'Details', url: 'https://docs.example/', kind: 'link' }],
  }] }] }
  const { container } = render(<MemoryRouter><DigestArticle digest={withImages}/></MemoryRouter>)
  const block = container.querySelector('.item-images')!
  const imgs = Array.from(block.querySelectorAll('img'))
  expect(imgs.map(img => img.getAttribute('src'))).toEqual([
    'https://cdn.example/chart.png', 'https://cdn.example/shot.png',
  ])
  expect(imgs.map(img => img.getAttribute('alt'))).toEqual(['', ''])
  expect(Array.from(block.querySelectorAll('figcaption')).map(caption => caption.textContent)).toEqual(['Growth chart', 'Interface screenshot'])
  for (const img of imgs) {
    expect(img).toHaveAttribute('loading', 'lazy')
    expect(img).toHaveAttribute('decoding', 'async')
    expect(img).toHaveAttribute('referrerpolicy', 'no-referrer')
    expect(img.closest('figure')).toBeInTheDocument()
  }
  expect(block.compareDocumentPosition(screen.getByText('Summary')) & Node.DOCUMENT_POSITION_PRECEDING)
    .toBeTruthy()
  expect(block.compareDocumentPosition(screen.getByText(/Also read:/)) & Node.DOCUMENT_POSITION_FOLLOWING)
    .toBeTruthy()
  await expectAccessible(container)
  fireEvent.error(imgs[0])
  expect(container.querySelectorAll('.item-images figure')).toHaveLength(1)
  expect(screen.getByText('Interface screenshot', { selector: 'figcaption' })).toBeInTheDocument()
  fireEvent.error(imgs[1])
  expect(container.querySelector('.item-images')).toBeNull()
  expect(screen.getByText('Summary')).toBeInTheDocument()
  expect(screen.getByText(/Also read:/)).toBeInTheDocument()
  await expectAccessible(container)
})

it('renders no image block for empty images and no image request markup when turned off', async () => {
  const withImages = { ...digest, topics: [{ ...digest.topics[0], items: [{
    ...digest.topics[0].items[0], images: [{ url: 'https://cdn.example/chart.png', alt: 'Chart' }],
  }] }] }
  const empty = render(<MemoryRouter><DigestArticle digest={digest}/></MemoryRouter>)
  expect(empty.container.querySelector('.item-images')).toBeNull()
  empty.unmount()
  const off = render(<MemoryRouter><DigestArticle digest={withImages} showImages={false}/></MemoryRouter>)
  expect(off.container.querySelector('img, .item-images')).toBeNull()
  await expectAccessible(off.container)
})

it("shows each image's text once, as its figure's caption", async () => {
  const withImages = { ...digest, language: 'zh-Hans', topics: [{ ...digest.topics[0], items: [{
    ...digest.topics[0].items[0],
    images: [{ url: 'https://cdn.example/chart.png', alt: 'Sales doubled after the redesign' }],
  }] }] }
  const { container } = render(<MemoryRouter><DigestArticle digest={withImages}/></MemoryRouter>)
  const figure = container.querySelector('.item-images figure')!
  const img = figure.querySelector('img')!
  expect(img).toHaveAttribute('src', 'https://cdn.example/chart.png')
  expect(img).toHaveAttribute('alt', '')
  const caption = screen.getByText('Sales doubled after the redesign', { selector: 'figcaption' })
  expect(img.nextElementSibling).toBe(caption)
  expect(caption).toHaveAttribute('lang', digestLang('zh-Hans'))
  expect(within(container.querySelector('.item-images') as HTMLElement).queryByRole('img')).toBeNull()
  await expectAccessible(container)
})

it('does not show an image without text', () => {
  const images = [
    { url: 'https://cdn.example/a.png', alt: '' },
    { url: 'https://cdn.example/b.png', alt: '  ' },
    { url: 'https://cdn.example/c.png', alt: 'Chart' },
  ]
  const withImages = { ...digest, topics: [{ ...digest.topics[0], items: [{
    ...digest.topics[0].items[0], images,
  }] }] }
  const shown = render(<MemoryRouter><DigestArticle digest={withImages}/></MemoryRouter>)
  expect(shown.container.querySelectorAll('.item-images figure')).toHaveLength(1)
  expect(shown.container.querySelector('.item-images img')).toHaveAttribute('src', 'https://cdn.example/c.png')
  expect(screen.getByText('Chart', { selector: 'figcaption' })).toBeInTheDocument()
  shown.unmount()
  const withoutText = { ...digest, topics: [{ ...digest.topics[0], items: [{
    ...digest.topics[0].items[0], images: images.slice(0, 2),
  }] }] }
  const hidden = render(<MemoryRouter><DigestArticle digest={withoutText}/></MemoryRouter>)
  expect(hidden.container.querySelector('.item-images')).toBeNull()
})

it('does not fail on a saved image without alt text', () => {
  const images = [
    { url: 'https://cdn.example/a.png' },
    { url: 'https://cdn.example/b.png', alt: null },
    { url: 'https://cdn.example/c.png', alt: 'Chart' },
  ] as unknown as { url: string; alt: string }[]
  const withImages = { ...digest, topics: [{ ...digest.topics[0], items: [{
    ...digest.topics[0].items[0], images,
  }] }] }
  const { container } = render(<MemoryRouter><DigestArticle digest={withImages}/></MemoryRouter>)
  expect(container.querySelectorAll('.item-images figure')).toHaveLength(1)
  expect(container.querySelector('.item-images img')).toHaveAttribute('src', 'https://cdn.example/c.png')
  expect(screen.getByText('Chart', { selector: 'figcaption' })).toBeInTheDocument()
})

it('hides a failed image together with its caption', () => {
  const withImages = { ...digest, topics: [{ ...digest.topics[0], items: [{
    ...digest.topics[0].items[0], images: [
      { url: 'https://cdn.example/chart.png', alt: 'Growth chart' },
      { url: 'https://cdn.example/shot.png', alt: 'Interface screenshot' },
    ],
  }] }] }
  const { container } = render(<MemoryRouter><DigestArticle digest={withImages}/></MemoryRouter>)
  fireEvent.error(container.querySelector('.item-images img')!)
  expect(screen.queryByText('Growth chart')).toBeNull()
  expect(screen.getByText('Interface screenshot', { selector: 'figcaption' })).toBeInTheDocument()
})

it('shows no caption when images are turned off', () => {
  const withImages = { ...digest, topics: [{ ...digest.topics[0], items: [{
    ...digest.topics[0].items[0],
    images: [{ url: 'https://cdn.example/chart.png', alt: 'Chart' }],
  }] }] }
  const shown = render(<MemoryRouter><DigestArticle digest={withImages}/></MemoryRouter>)
  expect(screen.getByText('Chart', { selector: 'figcaption' })).toBeInTheDocument()
  shown.unmount()
  const { container } = render(<MemoryRouter><DigestArticle digest={withImages} showImages={false}/></MemoryRouter>)
  expect(container.querySelector('figcaption')).toBeNull()
})

const fetchMock = vi.fn()
const respond = (value: unknown, status = 200) => ({ ok: status < 400, status, json: async () => value })
const unmarked = { id: 11, bookmarked: false, liked: false, rating: null, note: null }
beforeEach(() => vi.stubGlobal('fetch', fetchMock))
afterEach(() => { vi.unstubAllGlobals(); fetchMock.mockReset() })

function actionDigest(marks = {}) {
  return { ...digest, topics: [{ ...digest.topics[0], items: [
    { ...digest.topics[0].items[0], ...marks },
    { ...digest.topics[0].items[0], id: 12, title: 'Missing', summary: null, summary_unavailable: true },
  ] }], creator_updates: [{ source_name: 'Podcast', items: [{
    title: 'Episode', link: 'https://example.test/episode', published_at: null, reason: 'no_transcript',
  }] }] }
}
function actionPage(marks = {}) {
  return render(<MemoryRouter><DigestArticle digest={actionDigest(marks)}/></MemoryRouter>)
}

it('shows Bookmark and Like on topic items and Feedback only with a summary', async () => {
  const { container } = actionPage()
  const article = screen.getByRole('link', { name: 'Article (opens the original)' }).closest('article')!
  expect(article.lastElementChild).toHaveClass('item-actions')
  expect(within(article.lastElementChild as HTMLElement).getAllByRole('button').map(button => button.textContent))
    .toEqual(['Bookmark Article', 'Like Article', 'Feedback on Article'])
  for (const name of ['Bookmark Article', 'Like Article']) {
    const button = screen.getByRole('button', { name })
    expect(button).toHaveAttribute('aria-pressed', 'false')
    expect(button.querySelector('svg')).toBeNull()
  }
  expect(screen.getByRole('button', { name: 'Feedback on Article' })).toHaveAttribute('aria-expanded', 'false')
  expect(screen.getByRole('button', { name: 'Bookmark Missing' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Like Missing' })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Feedback on Missing' })).toBeNull()
  expect(within(container.querySelector('.creator') as HTMLElement).queryByRole('button')).toBeNull()
  await expectAccessible(container)
})

it('starts from the saved marks', () => {
  actionPage({ bookmarked: true, liked: true, rating: 'good' as const })
  for (const name of ['Bookmark Article', 'Like Article']) {
    const button = screen.getByRole('button', { name })
    expect(button).toHaveAttribute('aria-pressed', 'true')
    expect(button.querySelector('svg')).toBeInTheDocument()
  }
  expect(screen.getByRole('button', { name: 'Feedback on Article' }).nextElementSibling)
    .toHaveTextContent('Rated good')
})

it("does not carry an item's marks into the next digest", () => {
  const page = render(<MemoryRouter><DigestArticle digest={digest}/></MemoryRouter>)
  const next = { ...digest, id: 8, topics: [{ ...digest.topics[0], items: [{
    ...digest.topics[0].items[0], id: 81, bookmarked: true,
  }] }] }
  page.rerender(<MemoryRouter><DigestArticle digest={next}/></MemoryRouter>)
  expect(screen.getByRole('button', { name: 'Bookmark Article' })).toHaveAttribute('aria-pressed', 'true')
})

it('keeps an empty status region on the page', () => {
  const { container } = actionPage()
  expect(container.querySelectorAll('section.page-digest [role="status"]')).toHaveLength(1)
  expect(screen.getByRole('status')).toBeEmptyDOMElement()
})

it('bookmarks an item once the server saves it', async () => {
  let resolve!: (value: ReturnType<typeof respond>) => void
  fetchMock.mockImplementationOnce(() => new Promise(done => { resolve = done }))
    .mockResolvedValueOnce(respond(unmarked))
  actionPage()
  const button = screen.getByRole('button', { name: 'Bookmark Article' })
  button.focus()
  fireEvent.click(button)
  expect(button).toHaveAttribute('aria-disabled', 'true')
  expect(button).toHaveAttribute('aria-pressed', 'false')
  expect(button).toHaveFocus()
  fireEvent.click(button)
  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(fetchMock).toHaveBeenCalledWith('/api/digest-items/11/bookmark', { method: 'PUT' })
  await act(async () => resolve(respond({ ...unmarked, bookmarked: true })))
  expect(button).toHaveAttribute('aria-pressed', 'true')
  expect(button).not.toHaveAttribute('aria-disabled', 'true')
  expect(screen.getByRole('status')).toHaveTextContent('Bookmarked.')
  fireEvent.click(button)
  await waitFor(() => expect(button).toHaveAttribute('aria-pressed', 'false'))
  expect(fetchMock).toHaveBeenLastCalledWith('/api/digest-items/11/bookmark', { method: 'DELETE' })
  expect(screen.getByRole('status')).toHaveTextContent('Bookmark removed.')
})

it('ignores a second Like while the change is saved', async () => {
  let resolve!: (value: ReturnType<typeof respond>) => void
  fetchMock.mockImplementationOnce(() => new Promise(done => { resolve = done }))
  actionPage()
  const button = screen.getByRole('button', { name: 'Like Article' })
  button.focus()
  fireEvent.click(button)
  expect(button).toHaveAttribute('aria-disabled', 'true')
  expect(button).toHaveAttribute('aria-pressed', 'false')
  expect(button).not.toBeDisabled()
  expect(button).toHaveFocus()
  fireEvent.click(button)
  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(fetchMock).toHaveBeenCalledWith('/api/digest-items/11/like', { method: 'PUT' })
  await act(async () => resolve(respond({ ...unmarked, liked: true })))
  expect(button).toHaveAttribute('aria-pressed', 'true')
})

it('likes and unlikes an item', async () => {
  fetchMock.mockResolvedValueOnce(respond({ ...unmarked, liked: true }))
    .mockResolvedValueOnce(respond(unmarked))
  actionPage()
  const button = screen.getByRole('button', { name: 'Like Article' })
  fireEvent.click(button)
  await waitFor(() => expect(button).toHaveAttribute('aria-pressed', 'true'))
  expect(fetchMock).toHaveBeenLastCalledWith('/api/digest-items/11/like', { method: 'PUT' })
  expect(screen.getByRole('status')).toHaveTextContent('Liked.')
  fireEvent.click(button)
  await waitFor(() => expect(button).toHaveAttribute('aria-pressed', 'false'))
  expect(fetchMock).toHaveBeenLastCalledWith('/api/digest-items/11/like', { method: 'DELETE' })
  expect(screen.getByRole('status')).toHaveTextContent('Like removed.')
  let resolve!: (value: ReturnType<typeof respond>) => void
  fetchMock.mockImplementationOnce(() => new Promise(done => { resolve = done }))
  fireEvent.click(button)
  expect(screen.getByRole('status')).toBeEmptyDOMElement()
  await act(async () => resolve(respond({ ...unmarked, liked: true })))
  expect(screen.getByRole('status')).toHaveTextContent('Liked.')
})

it("shows the server's message and keeps the state when a change fails", async () => {
  fetchMock.mockResolvedValue(respond({ error: { code: 'not_found', message: 'Digest item not found.' } }, 404))
  actionPage()
  const button = screen.getByRole('button', { name: 'Bookmark Article' })
  fireEvent.click(button)
  expect(await within(button.closest('.item-actions') as HTMLElement).findByRole('alert'))
    .toHaveTextContent('Digest item not found.')
  expect(button).toHaveAttribute('aria-pressed', 'false')
  expect(screen.getByRole('status')).toBeEmptyDOMElement()
})

it('opens the feedback panel with the saved rating and note', async () => {
  const { container } = actionPage({ rating: 'poor' as const, note: 'Earlier note' })
  const button = screen.getByRole('button', { name: 'Feedback on Article' })
  button.focus()
  fireEvent.click(button)
  expect(button).toHaveAttribute('aria-expanded', 'true')
  expect(button).toHaveFocus()
  const panel = screen.getByRole('group', { name: 'Feedback on Article' })
  const choices = within(panel).getByRole('group', { name: 'How was this summary?' })
  expect(within(choices).getByRole('radio', { name: 'Poor' })).toBeChecked()
  expect(within(choices).getByRole('radio', { name: 'Good' })).not.toBeChecked()
  const note = within(panel).getByRole('textbox', { name: 'Note (optional)' })
  expect(note).toHaveValue('Earlier note')
  expect(note).toHaveAttribute('maxlength', '500')
  expect(note).toHaveAccessibleDescription('Only kept in CatchUp. Up to 500 characters.')
  expect(within(panel).getAllByRole('button').map(button => button.textContent))
    .toEqual(['Save feedback', 'Remove feedback', 'Cancel'])
  await expectAccessible(container)
})

it('saves rating and note together and returns focus to Feedback', async () => {
  let resolve!: (value: ReturnType<typeof respond>) => void
  fetchMock.mockImplementationOnce(() => new Promise(done => { resolve = done }))
  actionPage()
  const button = screen.getByRole('button', { name: 'Feedback on Article' })
  fireEvent.click(button)
  const panel = screen.getByRole('group', { name: 'Feedback on Article' })
  expect(within(panel).getAllByRole('button').map(button => button.textContent))
    .toEqual(['Save feedback', 'Cancel'])
  fireEvent.click(within(panel).getByRole('radio', { name: 'Good' }))
  fireEvent.change(within(panel).getByRole('textbox', { name: 'Note (optional)' }), { target: { value: 'Clear' } })
  const save = within(panel).getByRole('button', { name: 'Save feedback' })
  save.focus()
  fireEvent.click(save)
  expect(save).toHaveAttribute('aria-disabled', 'true')
  const [url, options] = fetchMock.mock.calls[0]
  expect(url).toBe('/api/digest-items/11/feedback')
  expect(options.method).toBe('PUT')
  expect(JSON.parse(options.body)).toEqual({ rating: 'good', note: 'Clear' })
  await act(async () => resolve(respond({ ...unmarked, rating: 'good', note: 'Clear' })))
  expect(screen.queryByRole('group', { name: 'Feedback on Article' })).toBeNull()
  expect(button).toHaveFocus()
  expect(button).toHaveAttribute('aria-expanded', 'false')
  expect(button.nextElementSibling).toHaveTextContent('Rated good')
  expect(screen.getByRole('status')).toHaveTextContent('Feedback saved.')
})

it('ignores Save feedback while the feedback is saved', async () => {
  let resolve!: (value: ReturnType<typeof respond>) => void
  fetchMock.mockImplementationOnce(() => new Promise(done => { resolve = done }))
  actionPage({ rating: 'good' as const })
  fireEvent.click(screen.getByRole('button', { name: 'Feedback on Article' }))
  fireEvent.click(screen.getByRole('radio', { name: 'Poor' }))
  const save = screen.getByRole('button', { name: 'Save feedback' })
  fireEvent.click(save)
  expect(save).toHaveAttribute('aria-disabled', 'true')
  expect(screen.getByRole('button', { name: 'Remove feedback' })).toHaveAttribute('aria-disabled', 'true')
  fireEvent.click(save)
  expect(fetchMock).toHaveBeenCalledTimes(1)
  const [url, options] = fetchMock.mock.calls[0]
  expect(url).toBe('/api/digest-items/11/feedback')
  expect(options.method).toBe('PUT')
  expect(JSON.parse(options.body)).toEqual({ rating: 'poor', note: '' })
  await act(async () => resolve(respond({ ...unmarked, rating: 'poor' })))
})

it("shows the saved rating's own word", async () => {
  fetchMock.mockResolvedValueOnce(respond({ ...unmarked, rating: 'poor' }))
  actionPage()
  const button = screen.getByRole('button', { name: 'Feedback on Article' })
  fireEvent.click(button)
  fireEvent.click(screen.getByRole('radio', { name: 'Poor' }))
  fireEvent.click(screen.getByRole('button', { name: 'Save feedback' }))
  await waitFor(() => expect(button.nextElementSibling).toHaveTextContent('Rated poor'))
})

it('asks for a rating before saving', () => {
  actionPage()
  fireEvent.click(screen.getByRole('button', { name: 'Feedback on Article' }))
  fireEvent.click(screen.getByRole('button', { name: 'Save feedback' }))
  expect(fetchMock).not.toHaveBeenCalled()
  expect(screen.getByRole('alert')).toHaveTextContent('Choose Good or Poor.')
  for (const radio of screen.getAllByRole('radio')) {
    expect(radio).toHaveAttribute('aria-invalid', 'true')
    expect(radio).toHaveAccessibleDescription('Choose Good or Poor.')
  }
})

it('removes feedback', async () => {
  fetchMock.mockResolvedValue(respond(unmarked))
  actionPage({ rating: 'good' as const })
  const button = screen.getByRole('button', { name: 'Feedback on Article' })
  fireEvent.click(button)
  const remove = screen.getByRole('button', { name: 'Remove feedback' })
  remove.focus()
  fireEvent.click(remove)
  await waitFor(() => expect(screen.queryByRole('group', { name: 'Feedback on Article' })).toBeNull())
  expect(fetchMock).toHaveBeenCalledWith('/api/digest-items/11/feedback', { method: 'DELETE' })
  expect(button).toHaveFocus()
  expect(screen.queryByText(/Rated/)).toBeNull()
  expect(screen.getByRole('status')).toHaveTextContent('Feedback removed.')
})

it('cancel closes the panel without a request', () => {
  actionPage({ rating: 'poor' as const })
  const button = screen.getByRole('button', { name: 'Feedback on Article' })
  fireEvent.click(button)
  fireEvent.click(screen.getByRole('radio', { name: 'Good' }))
  const cancel = screen.getByRole('button', { name: 'Cancel' })
  cancel.focus()
  fireEvent.click(cancel)
  expect(fetchMock).not.toHaveBeenCalled()
  expect(button).toHaveFocus()
  fireEvent.click(button)
  expect(screen.getByRole('radio', { name: 'Poor' })).toBeChecked()
})

it('keeps the panel open with the error when saving fails', async () => {
  fetchMock.mockResolvedValue(respond({ error: {
    code: 'no_summary', message: 'This item has no summary to rate.',
  } }, 422))
  actionPage()
  const button = screen.getByRole('button', { name: 'Feedback on Article' })
  fireEvent.click(button)
  fireEvent.click(screen.getByRole('radio', { name: 'Good' }))
  fireEvent.click(screen.getByRole('button', { name: 'Save feedback' }))
  expect(await within(button.closest('.item-actions') as HTMLElement).findByRole('alert'))
    .toHaveTextContent('This item has no summary to rate.')
  expect(screen.getByRole('group', { name: 'Feedback on Article' })).toBeInTheDocument()
  expect(screen.queryByText(/Rated/)).toBeNull()
})
