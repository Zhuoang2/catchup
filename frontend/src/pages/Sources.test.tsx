import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Sources from './Sources'
import { expectAccessible } from '../test/accessibility'

const fetchMock = vi.fn()
function respond(data: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => data }
}
const saved = {
  id: 2, title: 'Example News', feed_url: 'https://site.example/feed',
  site_url: 'https://site.example/', kind: 'feed', last_check_at: '2026-10-03T10:00:00Z',
  last_check_status: 'failed', possible_gap: true,
  http_status: 503, rate_limited: false,
}
const preview = {
  feed_url: saved.feed_url, site_url: saved.site_url, title: saved.title,
  follows_site_feed_notice: true, kind: 'feed', captions_enabled: false,
  entries: [{ title: 'Recent article', link: 'https://site.example/a', published_at: null }],
}
function page() { return render(<MemoryRouter><Sources /></MemoryRouter>) }

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  fetchMock.mockImplementation(async (path: string) => {
    if (path === '/api/sources') return respond([])
    if (path === '/api/sources/preview') return respond(preview)
    throw new Error(`Unexpected request: ${path}`)
  })
})
afterEach(() => {
  vi.unstubAllGlobals()
  fetchMock.mockReset()
})

describe('sources', () => {
  it.each([
    ['podcast', false, 'Transcripts published by the show'],
    ['youtube', false, 'Caption fetching is off; videos will be listed without summaries'],
    ['youtube', true, 'Captions fetched from YouTube on this computer'],
  ])('describes %s preview with captions %s', async (kind, enabled, text) => {
    fetchMock.mockImplementation(async (path: string) => path === '/api/sources'
      ? respond([])
      : respond({ ...preview, kind, captions_enabled: enabled }))
    const { container } = page()
    fireEvent.change(screen.getByLabelText('Website or feed URL'), {
      target: { value: saved.feed_url },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    expect(await screen.findByText((_, node) => node?.tagName === 'P' && node.textContent?.startsWith(text) === true))
      .toBeInTheDocument()
    if (kind === 'podcast') expect(screen.getByText(/whole show/)).toBeInTheDocument()
    else expect(screen.getByText(/whole site's feed/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Preview' })).toHaveClass('btn-secondary')
    expect(container.querySelectorAll('.btn-primary')).toHaveLength(1)
    await expectAccessible(container)
  })
  it('previews a source and explains site scope before confirmation', async () => {
    page()
    fireEvent.change(screen.getByLabelText('Website or feed URL'), {
      target: { value: 'https://site.example/story' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    expect(await screen.findByRole('region', { name: 'Source preview' })).toHaveTextContent(
      "whole site's feed",
    )
    expect(screen.getByText('Recent article')).toHaveAttribute('href', 'https://site.example/a')
    expect(screen.getByRole('button', { name: 'Confirm source' })).toBeInTheDocument()
  })

  it('shows the named duplicate error', async () => {
    fetchMock.mockImplementation(async (path: string) => {
      if (path === '/api/sources') return respond([])
      return respond({ error: {
        code: 'duplicate', message: 'Already following Example News.',
        existing_source: saved,
      } }, 422)
    })
    const { container } = page()
    fireEvent.change(screen.getByLabelText('Website or feed URL'), {
      target: { value: saved.feed_url },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Already following Example News.')
    const input = screen.getByLabelText('Website or feed URL')
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAttribute('aria-describedby', 'url-error url-hint')
    await expectAccessible(container)
  })

  it.each([
    ['fetch_failed', 403, 'The site refused the request (HTTP 403). If you know its feed URL, paste that instead.'],
    ['fetch_failed', 404, "The page was not found (HTTP 404). Check the URL, or paste the site's feed URL."],
    ['fetch_failed', 503, 'The site is not responding (HTTP 503). Try again later.'],
    ['fetch_failed', 418, "The site answered HTTP 418. Check the URL, or paste the site's feed URL."],
    ['fetch_failed', null, 'Could not fetch the source. Check the URL and try again.'],
    ['feed_unavailable', 404, "The site's feed is temporarily unavailable (HTTP 404). Try again later."],
    ['feed_unavailable', null, "The site's feed is temporarily unavailable. Try again later."],
  ])('shows the preview error for %s with HTTP status %s', async (code, httpStatus, expected) => {
    fetchMock.mockImplementation(async (path: string) => {
      if (path === '/api/sources') return respond([])
      if (path === '/api/sources/preview') return respond({ error: {
        code, message: 'Backend error',
        ...(httpStatus === null ? {} : { http_status: httpStatus }),
      } }, 422)
      throw new Error(`Unexpected request: ${path}`)
    })
    page()
    fireEvent.change(screen.getByLabelText('Website or feed URL'), {
      target: { value: saved.feed_url },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    expect((await screen.findByRole('alert')).textContent).toBe(expected)
  })

  it.each([
    ['fetch_failed', 401, 'The site refused the request (HTTP 401). If you know its feed URL, paste that instead.'],
    ['fetch_failed', 410, "The page was not found (HTTP 410). Check the URL, or paste the site's feed URL."],
    ['fetch_failed', 500, 'The site is not responding (HTTP 500). Try again later.'],
    ['fetch_failed', 599, 'The site is not responding (HTTP 599). Try again later.'],
    ['fetch_failed', 499, "The site answered HTTP 499. Check the URL, or paste the site's feed URL."],
    ['fetch_failed', 600, "The site answered HTTP 600. Check the URL, or paste the site's feed URL."],
    ['fetch_failed', 200, 'Could not fetch the source. Check the URL and try again.'],
    ['fetch_failed', 302, 'Could not fetch the source. Check the URL and try again.'],
    ['fetch_failed', 307, 'Could not fetch the source. Check the URL and try again.'],
    ['feed_unavailable', 200, "The site's feed is temporarily unavailable. Try again later."],
  ])('bounds the preview message for %s with status %s', async (code, httpStatus, expected) => {
    fetchMock.mockImplementation(async (path: string) => {
      if (path === '/api/sources') return respond([])
      if (path === '/api/sources/preview') return respond({ error: {
        code, message: 'Backend error', http_status: httpStatus,
      } }, 422)
      throw new Error(`Unexpected request: ${path}`)
    })
    const { container } = page()
    fireEvent.change(screen.getByLabelText('Website or feed URL'), {
      target: { value: saved.feed_url },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    expect((await screen.findByRole('alert')).textContent).toBe(expected)
    await expectAccessible(container)
  })

  it('shows HTTP 400 as an other-status preview error (mutation: D4 bound > 400)', async () => {
    fetchMock.mockImplementation(async (path: string) => {
      if (path === '/api/sources') return respond([])
      if (path === '/api/sources/preview') return respond({ error: {
        code: 'fetch_failed', message: 'Backend error', http_status: 400,
      } }, 422)
      throw new Error(`Unexpected request: ${path}`)
    })
    page()
    fireEvent.change(screen.getByLabelText('Website or feed URL'), {
      target: { value: saved.feed_url },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    expect((await screen.findByRole('alert')).textContent)
      .toBe("The site answered HTTP 400. Check the URL, or paste the site's feed URL.")
  })

  it('shows a rate-limited preview with suggested wait', async () => {
    fetchMock.mockImplementation(async (path: string) => path === '/api/sources'
      ? respond([])
      : respond({ error: {
        code: 'rate_limited', message: 'The source is rate limiting requests.',
        retry_after: 120,
      } }, 422))
    page()
    fireEvent.change(screen.getByLabelText('Website or feed URL'), {
      target: { value: saved.feed_url },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Rate limited — try again later (about 120 seconds).',
    )
  })

  it('shows a rate-limited confirm without a suggested wait', async () => {
    fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
      if (path === '/api/sources' && options?.method === 'POST') {
        return respond({ error: { code: 'rate_limited', message: 'Rate limited', retry_after: null } }, 422)
      }
      if (path === '/api/sources') return respond([])
      return respond(preview)
    })
    page()
    fireEvent.change(screen.getByLabelText('Website or feed URL'), {
      target: { value: saved.feed_url },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Confirm source' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Rate limited — try again later.')
  })

  it('renders saved source outcomes and possible gaps', async () => {
    fetchMock.mockResolvedValue(respond([{ ...saved, rate_limited: true }]))
    const { container } = page()
    expect(await screen.findByText('Example News')).toBeInTheDocument()
    expect(screen.getByText('Website feed')).toBeInTheDocument()
    expect(screen.getByText(saved.feed_url)).toHaveAttribute('title', saved.feed_url)
    expect(screen.getByText('Possible gap')).toBeInTheDocument()
    expect(screen.getByText('Rate limited · try later')).toBeInTheDocument()
    expect(container.querySelector('.source-time')).toHaveTextContent(/\d{1,2} Oct 2026, \d{2}:\d{2}/)
    await expectAccessible(container)
  })

  it('asks before deleting and refreshes the list', async () => {
    let deleted = false
    fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
      if (options?.method === 'DELETE') { deleted = true; return { ok: true, status: 204 } }
      if (path === '/api/sources') return respond(deleted ? [] : [saved])
      throw new Error(`Unexpected request: ${path}`)
    })
    const { container } = page()
    fireEvent.click(await screen.findByRole('button', { name: 'Delete Example News' }))
    expect(screen.getByRole('group', { name: 'Confirm deletion' })).toHaveTextContent(
      'Delete Example News? Saved digests will remain available.',
    )
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Cancel' }))
    await expectAccessible(container)
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.getByRole('button', { name: 'Delete Example News' })).toBeInTheDocument()
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Delete Example News' }))
    fireEvent.click(screen.getByRole('button', { name: 'Delete Example News' }))
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Cancel' }))
    fireEvent.click(screen.getByRole('group', { name: 'Confirm deletion' }).querySelector('button')!)
    expect(fetchMock).toHaveBeenCalledWith('/api/sources/2', { method: 'DELETE' })
    expect(await screen.findByText('No sources yet')).toBeInTheDocument()
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('heading', { name: 'No sources yet' })))
    await expectAccessible(container)
  })

  it('moves focus to the list heading when other sources remain after a delete', async () => {
    const other = { ...saved, id: 3, title: 'Other Weekly', feed_url: 'https://other.example/feed' }
    let deleted = false
    fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
      if (options?.method === 'DELETE') { deleted = true; return { ok: true, status: 204 } }
      if (path === '/api/sources') return respond(deleted ? [other] : [saved, other])
      throw new Error(`Unexpected request: ${path}`)
    })
    page()
    fireEvent.click(await screen.findByRole('button', { name: 'Delete Example News' }))
    fireEvent.click(screen.getByRole('group', { name: 'Confirm deletion' }).querySelector('button')!)
    await waitFor(() => expect(screen.queryByText('Example News')).toBeNull())
    expect(screen.getByText('Other Weekly')).toBeInTheDocument()
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('heading', { name: /Your sources/ })))
  })

  it('removes a deleted row before refresh and reports a refresh failure', async () => {
    let deleted = false
    let rejectRefresh!: (reason: Error) => void
    const pendingRefresh = new Promise<ReturnType<typeof respond>>((_, reject) => {
      rejectRefresh = reject
    })
    fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
      if (path === '/api/sources' && !deleted) return respond([saved])
      if (options?.method === 'DELETE') { deleted = true; return { ok: true, status: 204 } }
      if (path === '/api/sources') return pendingRefresh
      throw Error(path)
    })
    page()
    fireEvent.click(await screen.findByRole('button', { name: 'Delete Example News' }))
    fireEvent.click(screen.getByRole('group', { name: 'Confirm deletion' }).querySelector('button')!)
    await waitFor(() => expect(fetchMock.mock.calls.filter(([path]) => path === '/api/sources')).toHaveLength(2))
    expect(screen.queryByText('Example News')).toBeNull()
    expect(screen.queryByRole('group', { name: 'Confirm deletion' })).toBeNull()
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('heading', { name: 'No sources yet' })))
    await act(async () => { rejectRefresh(new Error('Offline')) })
    expect(screen.getByRole('alert')).toHaveTextContent(/refresh/i)
    expect(screen.getByLabelText('Website or feed URL')).not.toHaveAttribute('aria-invalid')
  })

  it('keeps delete failures at page level without invalidating the URL', async () => {
    fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
      if (options?.method === 'DELETE') return respond({
        error: { code: 'request_failed', message: 'Could not delete this source.' },
      }, 503)
      if (path === '/api/sources') return respond([saved])
      throw new Error(`Unexpected request: ${path}`)
    })
    const { container } = page()
    fireEvent.click(await screen.findByRole('button', { name: 'Delete Example News' }))
    fireEvent.click(screen.getByRole('group', { name: 'Confirm deletion' }).querySelector('button')!)
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not delete this source.')
    expect(screen.getByRole('group', { name: 'Confirm deletion' })).toHaveTextContent('Delete Example News?')
    expect(screen.getByLabelText('Website or feed URL')).not.toHaveAttribute('aria-invalid')
    expect(screen.getByLabelText('Website or feed URL')).toHaveAttribute('aria-describedby', 'url-hint')
    await expectAccessible(container)
  })

  it('displays a list-load error at page level', async () => {
    fetchMock.mockResolvedValue(respond({
      error: { code: 'request_failed', message: 'Could not load sources.' },
    }, 503))
    const { container } = page()
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load sources.')
    expect(screen.getByLabelText('Website or feed URL')).not.toHaveAttribute('aria-invalid')
    expect(screen.queryByRole('heading', { name: 'No sources yet' })).toBeNull()
    expect(container.querySelector('.examples')).toBeNull()
    expect(screen.queryByRole('heading', { name: 'Checks' })).toBeNull()
  })

  it('has a useful empty state without a checks rail', async () => {
    const { container } = page()
    expect(await screen.findByText('No sources yet')).toBeInTheDocument()
    expect(container.querySelectorAll('.empty-state h2')).toHaveLength(1)
    expect(screen.getAllByRole('heading', { level: 2 }).map(heading => heading.textContent))
      .toEqual(['No sources yet', 'What you can add'])
    expect(screen.queryByRole('heading', { name: 'Your sources' })).toBeNull()
    expect(screen.getByRole('heading', { name: 'No sources yet' })).toHaveAttribute('tabIndex', '-1')
    expect(screen.queryByRole('heading', { name: 'Checks' })).toBeNull()
    await expectAccessible(container)
  })
})
