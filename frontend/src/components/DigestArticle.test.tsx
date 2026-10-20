import { render, screen } from '@testing-library/react'
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
