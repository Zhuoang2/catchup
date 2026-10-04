import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Sources from './Sources'

const fetchMock = vi.fn()
function respond(data: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => data }
}
const saved = {
  id: 2, title: 'Example News', feed_url: 'https://site.example/feed',
  site_url: 'https://site.example/', last_check_at: '2026-10-03T10:00:00Z',
  last_check_status: 'failed', possible_gap: true,
}
const preview = {
  feed_url: saved.feed_url, site_url: saved.site_url, title: saved.title,
  follows_site_feed_notice: true,
  entries: [{ title: 'Recent article', link: 'https://site.example/a', published_at: null }],
}

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
  it('previews a source and explains site scope before confirmation', async () => {
    render(<Sources />)
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
    render(<Sources />)
    fireEvent.change(screen.getByLabelText('Website or feed URL'), {
      target: { value: saved.feed_url },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Already following Example News.')
  })

  it('renders saved source outcomes and possible gaps', async () => {
    fetchMock.mockResolvedValue(respond([saved]))
    render(<Sources />)
    expect(await screen.findByText('Example News')).toBeInTheDocument()
    expect(screen.getByText(/Last check: failed/)).toBeInTheDocument()
    expect(screen.getByText('Possible gap')).toBeInTheDocument()
  })

  it('asks before deleting and refreshes the list', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
    fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
      if (options?.method === 'DELETE') return { ok: true, status: 204 }
      if (path === '/api/sources') return respond([saved])
      throw new Error(`Unexpected request: ${path}`)
    })
    render(<Sources />)
    fireEvent.click(await screen.findByRole('button', { name: 'Delete Example News' }))
    expect(confirm).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledWith('/api/sources/2', { method: 'DELETE' })
    confirm.mockRestore()
  })
})
