import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { expect, it } from 'vitest'
import { expectAccessible } from '../test/accessibility'
import { DigestArticle } from './DigestArticle'
import { digestLang } from './lang'

const digest = {
  id: 7, created_at: '2026-10-03T10:00:00Z', model_id: 'test',
  item_count: 1, source_count: 1,
  topics: [{ title: 'Technology', overview: 'Overview', items: [{
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
