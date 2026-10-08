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
    throw new Error(`Unexpected request: ${url}`)
  })
})
afterEach(() => {
  vi.unstubAllGlobals()
  fetchMock.mockReset()
})

describe('model settings', () => {
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
