import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Settings from './Settings'
import { expectAccessible } from '../test/accessibility'

const fetchMock = vi.fn()

function respond(data: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => data }
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
  fetchMock.mockImplementation(async (url: string) => {
    if (url === '/api/settings/model') return respond({
      base_url: 'https://api.deepseek.com', model_id: 'saved-model',
      key_set: true, api_key_last4: '1234',
    })
    if (url === '/api/settings/preferences') return respond({
      digest_language: 'en', youtube_captions: false, youtube_skip_shorts: true,
    })
    if (url === '/api/settings/extension-tokens') return respond([])
    throw new Error(`Unexpected request: ${url}`)
  })
})
afterEach(() => {
  vi.unstubAllGlobals()
  fetchMock.mockReset()
})

describe('model settings', () => {
  it('describes the extension as optional for a first-run model', async () => {
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (url: string) => url === '/api/settings/model'
      ? respond({ base_url: 'https://api.deepseek.com', model_id: '', key_set: false, api_key_last4: null })
      : original(url))
    const { container } = render(<Settings/>)
    await screen.findByLabelText('API key')
    expect(container.querySelector('.lede')?.textContent)
      .toBe('Three quick steps, and an optional browser extension. Your key stays on this computer, encrypted.')
    await expectAccessible(container)
  })

  it('connects by Enter without saving the model and shows a token only until reload', async () => {
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (url: string, options?: RequestInit) => {
      if (url === '/api/settings/extension-tokens' && options?.method === 'POST') {
        expect(JSON.parse(options.body as string)).toEqual({ name: 'Chrome' })
        return respond({ id: 3, name: 'Chrome', created_at: '2026-10-21T12:00:00Z',
          token: 'fake-browser-token' }, 201)
      }
      if (url === '/api/settings/extension-tokens') return respond([{
        id: 3, name: 'Chrome', created_at: '2026-10-21T12:00:00Z', last_used_at: null,
      }])
      return original(url)
    })
    const first = render(<Settings/>)
    const input = await screen.findByLabelText('Browser name')
    expect(input).toHaveValue('Chrome')
    fireEvent.submit(input.closest('form')!)
    const token = await screen.findByRole('textbox', { name: 'Connection token' })
    expect(token).toHaveValue('fake-browser-token')
    expect(token).toHaveAttribute('readonly')
    expect(token).toHaveAccessibleDescription("Paste this into the CatchUp extension's options. It is shown only once.")
    expect(fetchMock.mock.calls.some(([path, options]) => path === '/api/settings/model'
      && (options as RequestInit | undefined)?.method === 'PUT')).toBe(false)
    expect(await screen.findByText(/Last used: Never/)).toBeInTheDocument()
    await expectAccessible(first.container)
    first.unmount()
    const second = render(<Settings/>)
    expect(await screen.findByText(/Last used: Never/)).toBeInTheDocument()
    expect(screen.queryByRole('textbox', { name: 'Connection token' })).toBeNull()
    await expectAccessible(second.container)
  })

  it.each(['missing', 'rejected'] as const)(
    'selects the token and announces copy failure when clipboard is %s', async variant => {
      const original = fetchMock.getMockImplementation()!
      fetchMock.mockImplementation(async (url: string, options?: RequestInit) =>
        url === '/api/settings/extension-tokens' && options?.method === 'POST'
          ? respond({ id: 1, name: 'Chrome', created_at: '2026-10-21T12:00:00Z',
            token: 'fake-browser-token' }, 201)
          : original(url))
      if (variant === 'missing') vi.stubGlobal('navigator', {
        ...navigator, clipboard: undefined,
      })
      else vi.stubGlobal('navigator', { ...navigator, clipboard: {
        writeText: vi.fn().mockRejectedValue(new Error('Denied')),
      } })
      const { container } = render(<Settings/>)
      const input = await screen.findByLabelText('Browser name')
      fireEvent.submit(input.closest('form')!)
      const token = await screen.findByRole('textbox', { name: 'Connection token' }) as HTMLInputElement
      fireEvent.click(screen.getByRole('button', { name: 'Copy' }))
      expect(await screen.findByRole('status', { name: 'Copy result' }))
        .toHaveTextContent('Copy failed. Select the token and copy it.')
      expect(token.selectionStart).toBe(0)
      expect(token.selectionEnd).toBe(token.value.length)
      await expectAccessible(container)
    },
  )

  it('copies the one-time token and disconnects its browser', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText } })
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (url: string, options?: RequestInit) => {
      if (url === '/api/settings/extension-tokens' && options?.method === 'POST') return respond({
        id: 1, name: 'Chrome', created_at: '2026-10-21T12:00:00Z', token: 'fake-browser-token',
      }, 201)
      if (url === '/api/settings/extension-tokens/1' && options?.method === 'DELETE') return respond(null, 204)
      if (url === '/api/settings/extension-tokens') return respond([{
        id: 1, name: 'Chrome', created_at: '2026-10-21T12:00:00Z', last_used_at: null,
      }])
      return original(url)
    })
    const { container } = render(<Settings/>)
    const input = await screen.findByLabelText('Browser name')
    fireEvent.submit(input.closest('form')!)
    await screen.findByRole('textbox', { name: 'Connection token' })
    fireEvent.click(screen.getByRole('button', { name: 'Copy' }))
    await waitFor(() => expect(writeText).toHaveBeenCalledWith('fake-browser-token'))
    expect(screen.getByRole('status', { name: 'Copy result' })).toHaveTextContent('Copied.')
    expect(screen.getByText(/Last used: Never/)).toBeInTheDocument()
    expect(container.querySelector('li time')).toHaveAttribute('datetime', '2026-10-21T12:00:00Z')
    fireEvent.click(screen.getByRole('button', { name: 'Disconnect Chrome' }))
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Disconnect Chrome' })).toBeNull())
    await expectAccessible(container)
  })

  it('defaults images on, describes the site contact, and limits the clickable area', async () => {
    const { container } = render(<Settings />)
    const images = await screen.findByRole('switch', { name: 'Show images from source sites' })
    expect(images).toBeChecked()
    expect(images).toHaveAccessibleDescription(
      'Opening a digest loads its images from the sites that published them.',
    )
    const note = screen.getByText('Opening a digest loads its images from the sites that published them.')
    expect(images.closest('label')).not.toContainElement(note)
    fireEvent.click(note)
    expect(images).toBeChecked()
    fireEvent.click(images)
    expect(images).not.toBeChecked()
    await expectAccessible(container)
  })

  it('saves the image preference with the other digest preferences', async () => {
    const original = fetchMock.getMockImplementation()!
    let saved: Record<string, unknown> | undefined
    fetchMock.mockImplementation(async (url: string, options?: RequestInit) => {
      if (options?.method === 'PUT' && url === '/api/settings/model') return respond({
        base_url: 'https://api.deepseek.com', model_id: 'saved-model',
        key_set: true, api_key_last4: '1234',
      })
      if (options?.method === 'PUT' && url === '/api/settings/preferences') {
        saved = JSON.parse(options.body as string) as Record<string, unknown>
        return respond(saved)
      }
      return original(url)
    })
    const { container } = render(<Settings />)
    const images = await screen.findByRole('switch', { name: 'Show images from source sites' })
    fireEvent.click(images)
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await screen.findByText('Settings saved.')
    expect(saved).toMatchObject({ show_images: false, digest_language: 'en',
      youtube_captions: false, youtube_skip_shorts: true })
    await expectAccessible(container)
  })

  it('loads stored images off and preserves off when saving without changing it', async () => {
    const original = fetchMock.getMockImplementation()!
    let saved: Record<string, unknown> | undefined
    fetchMock.mockImplementation(async (url: string, options?: RequestInit) => {
      if (url === '/api/settings/preferences' && !options?.method) return respond({
        digest_language: 'en', youtube_captions: false, youtube_skip_shorts: true,
        show_images: false,
      })
      if (url === '/api/settings/preferences' && options?.method === 'PUT') {
        saved = JSON.parse(options.body as string) as Record<string, unknown>
        return respond(saved)
      }
      if (url === '/api/settings/model' && options?.method === 'PUT') return respond({
        base_url: 'https://api.deepseek.com', model_id: 'saved-model',
        key_set: true, api_key_last4: '1234',
      })
      return original(url)
    })
    const { container } = render(<Settings />)
    const images = await screen.findByRole('switch', { name: 'Show images from source sites' })
    expect(images).not.toBeChecked()
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await screen.findByText('Settings saved.')
    expect(images).not.toBeChecked()
    expect(saved).toMatchObject({ show_images: false })
    await expectAccessible(container)
  })

  it('shows opt-in captions and default Shorts settings with the risk notice', async () => {
    const { container } = render(<Settings />)
    const captions = await screen.findByLabelText('Fetch captions locally')
    expect(captions).not.toBeChecked()
    expect(screen.getByLabelText('Skip Shorts')).toBeChecked()
    expect(screen.getByText(/YouTube's Terms of Service do not allow automated access/)).toBeInTheDocument()
    expect(captions).toHaveAttribute('role', 'switch')
    expect(captions).toHaveAccessibleDescription(/YouTube's Terms of Service do not allow automated access/)
    expect(captions.closest('label')?.querySelector('.risk')).toBeNull()
    fireEvent.click(captions)
    expect(captions).toBeChecked()
    await expectAccessible(container)
  })
  it('loads provider settings without revealing the key', async () => {
    const { container } = render(<Settings />)
    expect(await screen.findByDisplayValue('https://api.deepseek.com')).toBeInTheDocument()
    expect(screen.getByLabelText('API key')).toHaveAttribute('type', 'password')
    expect(screen.getByText(/Saved key ending in/)).toHaveTextContent('1234')
    expect(screen.getByLabelText('API key')).toHaveValue('')
    expect(screen.getByLabelText('API key')).toHaveAttribute('placeholder', 'Paste a new key to replace it')
    expect(screen.getByLabelText('API key')).toHaveAttribute('aria-describedby', 'key-saved key-hint')
    expect(screen.getByDisplayValue('saved-model')).toBeInTheDocument()
    for (const title of ['Step 1: Model provider', 'Step 2: Digest', 'Step 3: YouTube']) {
      expect(screen.getByRole('heading', { name: title })).toBeInTheDocument()
    }
    await expectAccessible(container)
  })

  it('fills model options from a successful provider test', async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url === '/api/settings/model/test') return respond({ ok: true, models: ['live-a', 'live-b'] })
      if (url === '/api/settings/model') return respond({
        base_url: 'https://api.deepseek.com', model_id: '',
        key_set: false, api_key_last4: null,
      })
      return respond({ digest_language: 'en', youtube_captions: false, youtube_skip_shorts: true })
    })
    const { container } = render(<Settings />)
    await screen.findByRole('button', { name: 'Test connection' })
    await waitFor(() => expect(screen.getByLabelText('Model')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    expect(await screen.findByRole('option', { name: 'live-b' })).toBeInTheDocument()
    expect(screen.getByLabelText('Model')).toHaveValue('live-a')
    expect(screen.getByLabelText('API key')).toHaveValue('')
    // The Save button can sit below the fold, so the success message names it.
    expect(screen.getByText('Connection succeeded. Choose a model, then click Save.')).toBeInTheDocument()
    await expectAccessible(container)
  })

  it('explains authentication errors', async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url === '/api/settings/model/test')
        return respond({ error: { code: 'auth_failed', message: 'Rejected' } }, 401)
      if (url === '/api/settings/model') return respond({
        base_url: 'https://api.deepseek.com', model_id: 'saved-model',
        key_set: true, api_key_last4: '1234',
      })
      return respond({ digest_language: 'en', youtube_captions: false, youtube_skip_shorts: true })
    })
    const { container } = render(<Settings />)
    await screen.findByLabelText('API key')
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('rejected the API key')
    expect(screen.getByLabelText('API key')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('API key')).toHaveAttribute('aria-describedby', 'key-saved key-hint key-error')
    await expectAccessible(container)
  })

  it('links a connection failure to the base URL instead of the key', async () => {
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (url: string) => url === '/api/settings/model/test'
      ? respond({ error: { code: 'connection_failed', message: 'Provider unreachable' } }, 503)
      : original(url))
    render(<Settings/>)
    await screen.findByLabelText('Base URL')
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not reach the model provider')
    expect(screen.getByLabelText('Base URL')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('Base URL')).toHaveAttribute('aria-describedby', 'base-error')
    expect(screen.getByLabelText('API key')).not.toHaveAttribute('aria-invalid')
  })

  it('shows an input when another language is chosen', async () => {
    render(<Settings />)
    await screen.findByLabelText('Digest language')
    fireEvent.change(screen.getByLabelText('Digest language'), { target: { value: 'other' } })
    expect(screen.getByLabelText('Other language')).toBeInTheDocument()
  })

  it('shows invalid-language saves as form-wide errors, not key errors', async () => {
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (url: string, options?: RequestInit) => {
      if (url === '/api/settings/model' && options?.method === 'PUT') return respond({
        base_url: 'https://api.deepseek.com', model_id: 'saved-model',
        key_set: true, api_key_last4: '1234',
      })
      if (url === '/api/settings/preferences' && options?.method === 'PUT') return respond({
        error: { code: 'invalid_language', message: 'Choose a valid language.' },
      }, 422)
      return original(url)
    })
    const { container } = render(<Settings />)
    await screen.findByRole('button', { name: 'Save' })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Choose a valid language.')
    expect(screen.getByLabelText('API key')).not.toHaveAttribute('aria-invalid')
    expect(screen.getByLabelText('API key')).toHaveAttribute('aria-describedby', 'key-saved key-hint')
    await expectAccessible(container)
  })

  it('shows load failures even after the loading state ends', async () => {
    fetchMock.mockImplementation(async (url: string) => url === '/api/settings/model'
      ? respond({ error: { code: 'request_failed', message: 'Could not load settings.' } }, 503)
      : respond({ digest_language: 'en', youtube_captions: false, youtube_skip_shorts: true }))
    const { container } = render(<Settings />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load settings.')
    expect(screen.queryByText('Loading settings…')).toBeNull()
    expect(screen.getByLabelText('API key')).not.toHaveAttribute('aria-invalid')
    await expectAccessible(container)
  })

  it('shows the first-run key hint and saves preferences without exposing the key', async () => {
    const calls: string[] = []
    fetchMock.mockImplementation(async (url: string, options?: RequestInit) => {
      if (options?.method === 'PUT') {
        calls.push(url)
        return respond(url === '/api/settings/model'
          ? { base_url: 'https://api.deepseek.com', model_id: 'live-a', key_set: true, api_key_last4: '3f9a' }
          : { digest_language: 'en', youtube_captions: true, youtube_skip_shorts: false })
      }
      if (url === '/api/settings/model/test') return respond({ ok: true, models: ['live-a'] })
      if (url === '/api/settings/model') return respond({
        base_url: 'https://api.deepseek.com', model_id: '', key_set: false, api_key_last4: null,
      })
      return respond({ digest_language: 'en', youtube_captions: false, youtube_skip_shorts: true })
    })
    const { container } = render(<Settings />)
    const key = await screen.findByLabelText('API key')
    expect(key).toHaveValue('')
    expect(key).toHaveAttribute('aria-describedby', 'key-hint')
    expect(screen.getByLabelText('Model')).toBeDisabled()
    await expectAccessible(container)
    fireEvent.change(key, { target: { value: 'secret-3f9a' } })
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    expect(await screen.findByRole('option', { name: 'live-a' })).toBeInTheDocument()
    await expectAccessible(container)
    fireEvent.click(screen.getByRole('switch', { name: 'Fetch captions locally' }))
    fireEvent.click(screen.getByRole('switch', { name: 'Skip Shorts' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText('Settings saved.')).toBeInTheDocument()
    expect(calls).toEqual(['/api/settings/model', '/api/settings/preferences'])
    expect(key).toHaveValue('')
    expect(key).not.toHaveAttribute('placeholder', expect.stringContaining('3f9a'))
  })
})
