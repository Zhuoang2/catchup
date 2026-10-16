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
