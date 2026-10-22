import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { expect, it } from 'vitest'
import { expectAccessible } from '../test/accessibility'
import { DigestArticle } from './DigestArticle'

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
  expect(imgs.map(img => img.alt)).toEqual(['Growth chart', 'Interface screenshot'])
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
  expect(screen.getByRole('img', { name: 'Interface screenshot' })).toBeInTheDocument()
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
