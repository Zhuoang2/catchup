import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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
  it('shows loading progress and ignores Preview while a preview loads', async () => {
    let finish!: (response: ReturnType<typeof respond>) => void
    const pending = new Promise<ReturnType<typeof respond>>(resolve => { finish = resolve })
    fetchMock.mockImplementation(async (path: string) =>
      path === '/api/sources/preview' ? pending : respond([]))
    page()
    await screen.findByText('No sources yet')
    fireEvent.change(screen.getByLabelText('Website or feed URL'), { target: { value: saved.feed_url } })
    const button = screen.getByRole('button', { name: 'Preview' })
    button.focus()
    fireEvent.click(button)
    expect(button).toHaveAttribute('aria-disabled', 'true')
    expect(button).not.toBeDisabled()
    expect(button).toHaveFocus()
    expect(screen.getByRole('status')).toHaveTextContent('Loading the preview…')
    fireEvent.click(button)
    expect(fireEvent.submit(button.closest('form')!)).toBe(false)
    expect(fetchMock.mock.calls.filter(([path]) => path === '/api/sources/preview')).toHaveLength(1)
    await act(async () => { finish(respond(preview)) })
    expect(screen.getByRole('heading', { name: preview.title })).toBeInTheDocument()
    expect(button).not.toHaveAttribute('aria-disabled', 'true')
    expect(screen.getByRole('status')).toBeEmptyDOMElement()
  })

  it('shows only the preview of the address in the field', async () => {
    let finishA!: (response: ReturnType<typeof respond>) => void
    let finishB!: (response: ReturnType<typeof respond>) => void
    const pendingA = new Promise<ReturnType<typeof respond>>(resolve => { finishA = resolve })
    const pendingB = new Promise<ReturnType<typeof respond>>(resolve => { finishB = resolve })
    fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
      if (path === '/api/sources/preview') {
        return JSON.parse(options?.body as string).url === 'https://a.example/' ? pendingA : pendingB
      }
      if (path === '/api/sources' && options?.method === 'POST') return respond(saved, 201)
      if (path === '/api/sources') return respond([])
      throw Error(path)
    })
    page()
    await screen.findByText('No sources yet')
    const address = screen.getByLabelText('Website or feed URL')
    const button = screen.getByRole('button', { name: 'Preview' })
    fireEvent.change(address, { target: { value: 'https://a.example/' } })
    fireEvent.click(button)
    fireEvent.change(address, { target: { value: 'https://b.example/' } })
    expect(button).not.toHaveAttribute('aria-disabled', 'true')
    expect(screen.getByRole('status')).toBeEmptyDOMElement()
    fireEvent.click(button)
    await act(async () => { finishB(respond({ ...preview, title: 'B News', feed_url: 'https://b.example/feed' })) })
    await act(async () => { finishA(respond({ ...preview, title: 'A News', feed_url: 'https://a.example/feed' })) })
    expect(screen.getByRole('heading', { name: 'B News' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'A News' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm source' }))
    await screen.findByText('Source saved.')
    const save = fetchMock.mock.calls.find(([path, options]) =>
      path === '/api/sources' && options?.method === 'POST')
    expect(JSON.parse(save?.[1].body as string)).toEqual({ feed_url: 'https://b.example/feed' })
  })

  it('ignores an error for an earlier address', async () => {
    let finish!: (response: ReturnType<typeof respond>) => void
    const pending = new Promise<ReturnType<typeof respond>>(resolve => { finish = resolve })
    fetchMock.mockImplementation(async (path: string) =>
      path === '/api/sources/preview' ? pending : respond([]))
    page()
    await screen.findByText('No sources yet')
    const address = screen.getByLabelText('Website or feed URL')
    fireEvent.change(address, { target: { value: 'https://a.example/' } })
    const button = screen.getByRole('button', { name: 'Preview' })
    fireEvent.click(button)
    fireEvent.change(address, { target: { value: 'https://b.example/' } })
    await act(async () => { finish(respond({ error: { code: 'no_feed', message: 'No feed.' } }, 422)) })
    expect(screen.queryByRole('alert')).toBeNull()
    expect(screen.getByRole('status')).toBeEmptyDOMElement()
    expect(button).not.toHaveAttribute('aria-disabled', 'true')
  })

  it('announces the saved token but does not preview an address that changed during the save', async () => {
    let finish!: (response: ReturnType<typeof respond>) => void
    const pending = new Promise<ReturnType<typeof respond>>(resolve => { finish = resolve })
    fetchMock.mockImplementation(async (path: string) => {
      if (path === '/api/sources') return respond([])
      if (path === '/api/settings/x') return pending
      if (path === '/api/sources/preview') return respond(
        { error: { code: 'x_token_required', message: 'X token needed.' } }, 422)
      throw Error(path)
    })
    page()
    const address = screen.getByLabelText('Website or feed URL')
    fireEvent.change(address, { target: { value: 'https://x.com/writer' } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    fireEvent.change(await screen.findByLabelText('X API token'), { target: { value: 'fake-token' } })
    const save = screen.getByRole('button', { name: 'Save and preview' })
    fireEvent.click(save)
    expect(save).toHaveAttribute('aria-disabled', 'true')
    fireEvent.click(save)
    expect(fetchMock.mock.calls.filter(([path]) => path === '/api/settings/x')).toHaveLength(1)
    fireEvent.change(address, { target: { value: 'https://b.example/' } })
    await act(async () => { finish(respond({ token_set: true, token_last4: 'oken' })) })
    expect(screen.getByRole('status')).toHaveTextContent('X token saved.')
    expect(fetchMock.mock.calls.filter(([path]) => path === '/api/sources/preview')).toHaveLength(1)
    fireEvent.change(address, { target: { value: 'https://x.com/other' } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    expect(await screen.findByLabelText('X API token')).toHaveValue('')
  })

  it('ignores a repeated preview for an address that changed while it loaded', async () => {
    let finish!: (response: ReturnType<typeof respond>) => void
    const pending = new Promise<ReturnType<typeof respond>>(resolve => { finish = resolve })
    let previews = 0
    fetchMock.mockImplementation(async (path: string) => {
      if (path === '/api/sources') return respond([])
      if (path === '/api/settings/x') return respond({ token_set: true, token_last4: 'oken' })
      if (path === '/api/sources/preview') return ++previews === 1
        ? respond({ error: { code: 'x_token_required', message: 'X token needed.' } }, 422) : pending
      throw Error(path)
    })
    page()
    const address = screen.getByLabelText('Website or feed URL')
    fireEvent.change(address, { target: { value: 'https://x.com/writer' } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    fireEvent.change(await screen.findByLabelText('X API token'), { target: { value: 'fake-token' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save and preview' }))
    await waitFor(() => expect(previews).toBe(2))
    fireEvent.change(address, { target: { value: 'https://b.example/' } })
    await act(async () => { finish(respond({ ...preview, kind: 'x', title: 'Writer', username: 'writer' })) })
    expect(screen.queryByRole('region', { name: 'Source preview' })).toBeNull()
    expect(screen.getByRole('status')).toBeEmptyDOMElement()
    expect(screen.getByRole('button', { name: 'Preview' })).not.toHaveAttribute('aria-disabled', 'true')
  })

  it.each([
    ['succeeds', respond({ token_set: true, token_last4: 'oken' })],
    ['fails', respond({ error: { code: 'invalid_token', message: 'Bad token.' } }, 422)],
  ])('keeps a newer preview loading when an older token save %s', async (_outcome, answer) => {
    let finishSave!: (response: ReturnType<typeof respond>) => void
    const save = new Promise<ReturnType<typeof respond>>(resolve => { finishSave = resolve })
    let finishB!: (response: ReturnType<typeof respond>) => void
    const previewB = new Promise<ReturnType<typeof respond>>(resolve => { finishB = resolve })
    fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
      if (path === '/api/sources') return respond([])
      if (path === '/api/settings/x') return save
      if (path === '/api/sources/preview') return JSON.parse(String(options?.body)).url === 'https://b.example/'
        ? previewB : respond({ error: { code: 'x_token_required', message: 'X token needed.' } }, 422)
      throw Error(path)
    })
    page()
    const address = screen.getByLabelText('Website or feed URL')
    fireEvent.change(address, { target: { value: 'https://x.com/writer' } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    fireEvent.change(await screen.findByLabelText('X API token'), { target: { value: 'fake-token' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save and preview' }))
    fireEvent.change(address, { target: { value: 'https://b.example/' } })
    const button = screen.getByRole('button', { name: 'Preview' })
    fireEvent.click(button)
    expect(button).toHaveAttribute('aria-disabled', 'true')
    await act(async () => { finishSave(answer) })
    expect(screen.getByRole('status')).toHaveTextContent('Loading the preview…')
    expect(button).toHaveAttribute('aria-disabled', 'true')
    await act(async () => { finishB(respond({ ...preview, title: 'B News', feed_url: 'https://b.example/feed' })) })
    expect(screen.getByRole('heading', { name: 'B News' })).toBeInTheDocument()
    expect(button).not.toHaveAttribute('aria-disabled', 'true')
  })

  it('keeps Save and preview focused until the repeated preview answers, then focuses its heading', async () => {
    let finish!: (response: ReturnType<typeof respond>) => void
    const pending = new Promise<ReturnType<typeof respond>>(resolve => { finish = resolve })
    let previews = 0
    fetchMock.mockImplementation(async (path: string) => {
      if (path === '/api/sources') return respond([])
      if (path === '/api/settings/x') return respond({ token_set: true, token_last4: 'oken' })
      if (path === '/api/sources/preview') return ++previews === 1
        ? respond({ error: { code: 'x_token_required', message: 'X token needed.' } }, 422) : pending
      throw Error(path)
    })
    const { container } = page()
    const status = container.querySelector('[role="status"]')
    fireEvent.change(screen.getByLabelText('Website or feed URL'), { target: { value: 'https://x.com/writer' } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    const token = await screen.findByLabelText('X API token')
    fireEvent.change(token, { target: { value: 'fake-token' } })
    const save = screen.getByRole('button', { name: 'Save and preview' })
    save.focus()
    fireEvent.click(save)
    await waitFor(() => expect(previews).toBe(2))
    expect(token.closest('form')).toBeInTheDocument()
    expect(save).toHaveFocus()
    expect(status).toHaveTextContent('Loading the preview…')
    await act(async () => { finish(respond({ ...preview, kind: 'x', title: 'Writer', username: 'writer' })) })
    expect(screen.queryByLabelText('X API token')).toBeNull()
    expect(screen.getByRole('heading', { name: 'Writer' })).toHaveFocus()
    expect(screen.getByRole('button', { name: 'Preview' })).not.toHaveAttribute('aria-disabled', 'true')
    expect(screen.getByRole('status')).toBe(status)
    expect(status).toHaveTextContent('X token saved.')
    await expectAccessible(container)
  })

  it('focuses the address and shows the error when the token saves but the repeated preview fails', async () => {
    let previews = 0
    fetchMock.mockImplementation(async (path: string) => {
      if (path === '/api/sources') return respond([])
      if (path === '/api/settings/x') return respond({ token_set: true, token_last4: 'oken' })
      if (path === '/api/sources/preview') return ++previews === 1
        ? respond({ error: { code: 'x_token_required', message: 'X token needed.' } }, 422)
        : respond({ error: { code: 'x_account_not_found', message: 'Not found.' } }, 422)
      throw Error(path)
    })
    const { container } = page()
    const address = screen.getByLabelText('Website or feed URL')
    fireEvent.change(address, { target: { value: 'https://x.com/writer' } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    fireEvent.change(await screen.findByLabelText('X API token'), { target: { value: 'fake-token' } })
    const save = screen.getByRole('button', { name: 'Save and preview' })
    save.focus()
    fireEvent.click(save)
    expect(await screen.findByRole('alert')).toHaveTextContent('X account not found.')
    expect(address).toHaveFocus()
    expect(screen.getByRole('status')).toBeEmptyDOMElement()
    expect(screen.getByRole('button', { name: 'Preview' })).not.toHaveAttribute('aria-disabled', 'true')
    await expectAccessible(container)
  })

  it('focuses the empty address after Confirm source and announces in the existing status region', async () => {
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (path: string, options?: RequestInit) =>
      path === '/api/sources' && options?.method === 'POST' ? respond(saved, 201) : original(path, options))
    const { container } = page()
    const status = container.querySelector('[role="status"]')
    const address = screen.getByLabelText('Website or feed URL')
    fireEvent.change(address, { target: { value: saved.feed_url } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    const confirm = await screen.findByRole('button', { name: 'Confirm source' })
    confirm.focus()
    fireEvent.click(confirm)
    await screen.findByText('Source saved.')
    expect(address).toHaveValue('')
    expect(address).toHaveFocus()
    expect(screen.getByRole('status')).toBe(status)
    await expectAccessible(container)
  })

  it('returns focus to the address after Cancel in the preview', async () => {
    page()
    const address = screen.getByLabelText('Website or feed URL')
    fireEvent.change(address, { target: { value: saved.feed_url } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    const cancel = await screen.findByRole('button', { name: 'Cancel' })
    cancel.focus()
    fireEvent.click(cancel)
    expect(address).toHaveFocus()
    expect(screen.queryByRole('region', { name: 'Source preview' })).toBeNull()
  })

  it('previews an X account with a public profile instead of its internal id', async () => {
    const xPreview = { feed_url: 'x:user:123', site_url: 'https://x.com/writer',
      title: 'Sample Writer', username: 'writer', kind: 'x', captions_enabled: false,
      follows_site_feed_notice: false, entries: [] }
    fetchMock.mockImplementation(async (path: string) => path === '/api/sources'
      ? respond([{ ...saved, id: 3, title: 'Sample Writer', kind: 'x',
        feed_url: 'x:user:123', site_url: 'https://x.com/writer', last_check_status: 'deferred',
        rate_limited: false, possible_gap: false }])
      : respond(xPreview))
    const { container } = page()
    const row = (await screen.findByRole('button', { name: 'Delete Sample Writer' })).closest('li')!
    expect(row).toHaveTextContent('https://x.com/writer')
    expect(row).toHaveTextContent('Waits for the next run')
    fireEvent.change(screen.getByLabelText('Website or feed URL'),
      { target: { value: 'https://x.com/writer' } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    const region = await screen.findByRole('region', { name: 'Source preview' })
    expect(region).toHaveTextContent('X account')
    expect(region).toHaveTextContent('Posts read through the X API with your token')
    expect(region).toHaveTextContent('@writer')
    expect(region).toHaveTextContent('https://x.com/writer')
    expect(container).not.toHaveTextContent('x:user:')
    await expectAccessible(container)
  })

  it('asks for a token in place, saves it, and repeats the same preview', async () => {
    let previewCount = 0
    fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
      if (path === '/api/sources') return respond([])
      if (path === '/api/settings/x') {
        expect(options?.method).toBe('PUT')
        expect(JSON.parse(options?.body as string)).toEqual({ token: 'test-x-token' })
        return respond({ token_set: true, token_last4: 'oken' })
      }
      if (path === '/api/sources/preview') {
        expect(JSON.parse(options?.body as string)).toEqual({ url: 'https://x.com/writer' })
        return ++previewCount === 1
          ? respond({ error: { code: 'x_token_required', message: 'X token needed.' } }, 422)
          : respond({ feed_url: 'x:user:123', site_url: 'https://x.com/writer',
            title: 'Sample Writer', username: 'writer', kind: 'x',
            follows_site_feed_notice: false, captions_enabled: false, entries: [] })
      }
      throw Error(path)
    })
    const { container } = page()
    fireEvent.change(screen.getByLabelText('Website or feed URL'),
      { target: { value: 'https://x.com/writer' } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    const input = await screen.findByLabelText('X API token')
    expect(input).toHaveAttribute('type', 'password')
    expect(input).toHaveAccessibleDescription(/Bearer token/i)
    expect(screen.getByRole('link', { name: /how to get/i })).toHaveAttribute('href',
      'https://github.com/Zhuoang2/catchup#x-accounts')
    await expectAccessible(container)
    fireEvent.change(input, { target: { value: 'test-x-token' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save and preview' }))
    expect(await screen.findByRole('region', { name: 'Source preview' })).toHaveTextContent('@writer')
    expect(screen.getByRole('status')).toHaveTextContent('X token saved.')
    expect(screen.queryByLabelText('X API token')).toBeNull()
    expect(previewCount).toBe(2)
  })

  it('marks the X token field, not the address, when saving the token fails', async () => {
    fetchMock.mockImplementation(async (path: string) => {
      if (path === '/api/sources') return respond([])
      if (path === '/api/settings/x') return respond(
        { error: { code: 'invalid_x_token', message: 'Enter a printable ASCII X API token.' } }, 422)
      if (path === '/api/sources/preview') return respond(
        { error: { code: 'x_token_required', message: 'X token needed.' } }, 422)
      throw Error(path)
    })
    const { container } = page()
    const url = screen.getByLabelText('Website or feed URL')
    fireEvent.change(url, { target: { value: 'https://x.com/writer' } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    const token = await screen.findByLabelText('X API token')
    fireEvent.change(token, { target: { value: 'bad token' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save and preview' }))
    expect(await screen.findByText('Enter a printable ASCII X API token.')).toBeInTheDocument()
    expect(token).toHaveAttribute('aria-invalid', 'true')
    expect(token).toHaveAccessibleDescription(/Enter a printable ASCII X API token/)
    expect(url).not.toHaveAttribute('aria-invalid')
    expect(screen.getByRole('status')).toBeEmptyDOMElement()
    expect(screen.getByRole('button', { name: 'Save and preview' })).not.toHaveAttribute('aria-disabled', 'true')
    await expectAccessible(container)
  })

  it.each([
    ['x_token_rejected', 'Replace the X token in CatchUp Settings'],
    ['x_account_protected', 'Protected X accounts cannot be followed'],
    ['x_account_not_found', 'X account not found'],
    ['x_account_suspended', 'X account suspended'],
    ['not_an_x_account', 'This is not an X account address'],
  ])('explains X error %s', async (code, expected) => {
    fetchMock.mockImplementation(async (path: string) => path === '/api/sources'
      ? respond([])
      : respond({ error: { code, message: 'Backend error' } }, 422))
    page()
    fireEvent.change(screen.getByLabelText('Website or feed URL'),
      { target: { value: 'https://x.com/writer' } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(expected)
  })

  it('shows captures as pages waiting without feed or check and confirms deletion', async () => {
    const capture = { ...saved, id: 8, title: 'Saved from browser', kind: 'capture',
      feed_url: 'catchup:captures', waiting_count: 2, last_check_status: null, last_check_at: null }
    fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
      if (path === '/api/sources/8' && options?.method === 'DELETE') return respond(null, 204)
      if (path === '/api/sources') return respond([capture])
      throw Error(path)
    })
    const { container } = page()
    const row = (await screen.findByText('Saved from browser', { selector: '.badge' })).closest('li')!
    expect(row).toHaveTextContent('2 pages waiting')
    expect(row).not.toHaveTextContent('catchup:captures')
    expect(row.querySelector('.source-status')).toBeNull()
    await expectAccessible(container)
    fireEvent.click(screen.getByRole('button', { name: 'Delete Saved from browser' }))
    expect(screen.getByText(/Delete Saved from browser\?/).closest('p'))
      .toHaveTextContent('Saved digests will remain available.')
    fireEvent.click(screen.getByRole('button', { name: /^Delete$/ }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/sources/8', { method: 'DELETE' }))
  })

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
  it('flows the captions-off method text and its Settings link as one text', async () => {
    fetchMock.mockImplementation(async (path: string) => path === '/api/sources'
      ? respond([])
      : respond({ ...preview, kind: 'youtube', captions_enabled: false }))
    page()
    fireEvent.change(screen.getByLabelText('Website or feed URL'), {
      target: { value: saved.feed_url },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
    const region = await screen.findByRole('region', { name: 'Source preview' })
    const method = region.querySelector('p.preview-method')!
    expect([...method.children].map(child => child.tagName.toLowerCase())).toEqual(['svg', 'span'])
    const text = method.children[1] as HTMLElement
    expect(text).toHaveTextContent('Caption fetching is off; videos will be listed without summaries')
    expect(within(text).getByRole('link', { name: 'Change in Settings' })).toHaveAttribute('href', '/settings')
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
