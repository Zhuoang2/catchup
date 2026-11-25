import { act, render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Settings from './Settings'
import { expectAccessible } from '../test/accessibility'

const fetchMock = vi.fn()

function respond(data: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => data }
}

type ModelBody = { base_url: string; model_id: string; api_key: string; provider: string; reasoning: string }

function mockModelProvider({
  saved = { base_url: 'https://api.deepseek.com', model_id: 'saved-model',
    key_set: true, api_key_last4: '1234' as string | null },
  test = () => respond({ ok: true, models: ['live-a', 'live-b'] }),
  put,
}: {
  saved?: { base_url: string; model_id: string; key_set: boolean; api_key_last4: string | null; provider?: string; reasoning?: string }
  test?: () => ReturnType<typeof respond> | Promise<ReturnType<typeof respond>>
  put?: (body: ModelBody) => ReturnType<typeof respond> | Promise<ReturnType<typeof respond>>
} = {}) {
  const original = fetchMock.getMockImplementation()!
  fetchMock.mockImplementation(async (url: string, options?: RequestInit) => {
    if (url === '/api/settings/model' && options?.method === 'PUT') {
      const body = JSON.parse(options.body as string) as ModelBody
      return put ? put(body) : respond({ base_url: body.base_url, model_id: body.model_id,
        reasoning: body.reasoning,
        key_set: true, api_key_last4: body.api_key ? body.api_key.slice(-4) : saved.api_key_last4 })
    }
    if (url === '/api/settings/model' && !options?.method) return respond(saved)
    if (url === '/api/settings/model/test' && options?.method === 'POST') return test()
    return original(url, options)
  })
}

function modelPuts(): ModelBody[] {
  return fetchMock.mock.calls.filter(([url, options]) =>
    url === '/api/settings/model' && options?.method === 'PUT')
    .map(([, options]) => JSON.parse(options.body as string) as ModelBody)
}

function modelSection() {
  return screen.getByRole('heading', { name: 'Step 1: Model provider' }).closest('section')!
}

function expectNoBottomAlert() {
  const xSection = screen.getByRole('heading', { name: 'Step 5: X accounts' }).closest('section')!
  for (const alert of screen.queryAllByRole('alert')) {
    expect(xSection.compareDocumentPosition(alert) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(0)
  }
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
    if (url === '/api/settings/x') return respond({ token_set: false, token_last4: null })
    throw new Error(`Unexpected request: ${url}`)
  })
})
afterEach(() => {
  vi.unstubAllGlobals()
  fetchMock.mockReset()
})

describe('model settings', () => {
  it('shows the saved provider as the first field of the Model provider group', async () => {
    mockModelProvider({ saved: { provider: 'anthropic', base_url: 'https://api.anthropic.com',
      model_id: 'claude-opus-5-5', key_set: true, api_key_last4: '1234' } })
    render(<Settings/>)
    const provider = await screen.findByLabelText('Provider')
    expect(provider).toHaveValue('anthropic')
    expect(within(provider).getByRole('option', { name: 'Anthropic', selected: true })).toBeInTheDocument()
    expect(modelSection()).toContainElement(provider)
    expect(modelSection().querySelector('input, select')).toBe(provider)
    expect(provider.compareDocumentPosition(screen.getByLabelText('Base URL'))
      & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('fills in the Anthropic address and empties the model list when Anthropic is chosen', async () => {
    mockModelProvider()
    render(<Settings/>)
    fireEvent.change(await screen.findByLabelText('Provider'), { target: { value: 'anthropic' } })
    expect(screen.getByLabelText('Base URL')).toHaveValue('https://api.anthropic.com')
    const model = screen.getByLabelText('Model')
    expect(within(model).getAllByRole('option').map(option => option.textContent))
      .toEqual(['Test the connection to list models'])
    expect(model).toHaveValue('')
    expect(model).toBeDisabled()
    expect(screen.queryByText(/Saved key ending in/)).toBeNull()
    expect(screen.getByLabelText('API key')).toHaveAccessibleDescription('Enter an API key for this provider.')
  })

  it('restores the saved configuration when the saved provider is chosen again', async () => {
    mockModelProvider({
      saved: { base_url: 'https://custom.example', model_id: 'saved-model', key_set: true, api_key_last4: '1234' },
      test: () => respond({ ok: true, models: ['saved-model', 'another-model'] }),
    })
    render(<Settings/>)
    const provider = await screen.findByLabelText('Provider')
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    await screen.findByText('Connection succeeded. Saved model saved-model.')
    fireEvent.change(provider, { target: { value: 'anthropic' } })
    fireEvent.change(provider, { target: { value: 'openai_compatible' } })
    expect(screen.getByLabelText('Base URL')).toHaveValue('https://custom.example')
    expect(screen.getByLabelText('Model')).toHaveValue('saved-model')
    expect(within(screen.getByLabelText('Model')).getAllByRole('option').map(option => option.textContent))
      .toEqual(['saved-model', 'another-model'])
    expect(screen.getByText(/Saved key ending in/)).toHaveTextContent('Saved key ending in 1234')
  })

  it('tests and saves a new provider with its key', async () => {
    mockModelProvider({
      test: () => respond({ ok: true, models: ['claude-opus-5-5', 'claude-sonnet-5-5'] }),
      put: body => respond({ provider: body.provider, base_url: body.base_url, model_id: body.model_id,
        key_set: true, api_key_last4: '7d2e' }),
    })
    render(<Settings/>)
    fireEvent.change(await screen.findByLabelText('Provider'), { target: { value: 'anthropic' } })
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'key-7d2e' } })
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    await waitFor(() => expect(modelPuts()).toEqual([{
      base_url: 'https://api.anthropic.com', model_id: 'claude-opus-5-5',
      api_key: 'key-7d2e', provider: 'anthropic', reasoning: 'default',
    }]))
    const testCall = fetchMock.mock.calls.find(([url]) => url === '/api/settings/model/test')!
    expect(JSON.parse(testCall[1].body as string)).toEqual({
      base_url: 'https://api.anthropic.com', api_key: 'key-7d2e', provider: 'anthropic',
    })
    await waitFor(() => expect(within(modelSection()).getByRole('status').textContent).toBe(
      'Connection succeeded. Saved key ending in 7d2e with model claude-opus-5-5. Choose another model to change it.'))
    expect(screen.getByLabelText('API key')).toHaveValue('')
    expect(document.getElementById('key-saved')).toHaveTextContent('Saved key ending in 7d2e')
  })

  it('restores the saved model after switching providers without a test', async () => {
    mockModelProvider()
    render(<Settings/>)
    const provider = await screen.findByLabelText('Provider')
    fireEvent.change(provider, { target: { value: 'anthropic' } })
    fireEvent.change(provider, { target: { value: 'openai_compatible' } })
    expect(screen.getByLabelText('Base URL')).toHaveValue('https://api.deepseek.com')
    expect(screen.getByLabelText('Model')).toHaveValue('saved-model')
    expect(within(screen.getByLabelText('Model')).getAllByRole('option').map(option => option.textContent))
      .toEqual(['saved-model'])
    expect(document.getElementById('key-saved')).toHaveTextContent('Saved key ending in 1234')
  })

  it('lists the tested models of a saved Anthropic provider', async () => {
    mockModelProvider({
      saved: { provider: 'anthropic', base_url: 'https://api.anthropic.com',
        model_id: 'claude-opus-5-5', key_set: true, api_key_last4: '1234' },
      test: () => respond({ ok: true, models: ['claude-opus-5-5', 'claude-sonnet-5-5'] }),
    })
    render(<Settings/>)
    await screen.findByLabelText('Provider')
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    await screen.findByText('Connection succeeded. Saved model claude-opus-5-5.')
    expect(within(screen.getByLabelText('Model')).getAllByRole('option').map(option => option.textContent))
      .toEqual(['claude-opus-5-5', 'claude-sonnet-5-5'])
  })

  it("keeps the tested models out of the other provider's list", async () => {
    let finishTest!: (response: ReturnType<typeof respond>) => void
    const pending = new Promise<ReturnType<typeof respond>>(resolve => { finishTest = resolve })
    mockModelProvider({
      test: () => pending,
      put: body => respond({ provider: body.provider, base_url: body.base_url, model_id: body.model_id,
        key_set: true, api_key_last4: '7d2e' }),
    })
    render(<Settings/>)
    const provider = await screen.findByLabelText('Provider')
    fireEvent.change(provider, { target: { value: 'anthropic' } })
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'key-7d2e' } })
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    fireEvent.change(provider, { target: { value: 'openai_compatible' } })
    await act(async () => {
      finishTest(respond({ ok: true, models: ['claude-opus-5-5', 'claude-sonnet-5-5'] }))
    })
    await waitFor(() => expect(modelPuts()).toEqual([{
      base_url: 'https://api.anthropic.com', model_id: 'claude-opus-5-5',
      api_key: 'key-7d2e', provider: 'anthropic', reasoning: 'default',
    }]))
    expect(provider).toHaveValue('openai_compatible')
    expect(screen.getByLabelText('Base URL')).toHaveValue('https://api.deepseek.com')
    expect(within(screen.getByLabelText('Model')).getAllByRole('option').map(option => option.textContent))
      .toEqual(['saved-model'])
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(modelPuts()).toHaveLength(2))
    expect(modelPuts()[1]).toEqual({
      base_url: 'https://api.deepseek.com', model_id: 'saved-model',
      api_key: '', provider: 'openai_compatible', reasoning: 'default',
    })
  })

  it('names the Anthropic address in the invalid-URL message', async () => {
    mockModelProvider({
      saved: { provider: 'anthropic', base_url: 'https://api.anthropic.com',
        model_id: 'claude-opus-5-5', key_set: true, api_key_last4: '1234' },
      put: () => respond({ error: { code: 'invalid_model_config', message: 'Invalid configuration.' } }, 422),
    })
    render(<Settings/>)
    expect(await screen.findByLabelText('Provider')).toHaveValue('anthropic')
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toBe('Enter a valid provider URL, such as https://api.anthropic.com.')
    expect(screen.getByLabelText('Base URL')).toHaveAttribute('aria-describedby', alert.id)
  })

  it('sends the provider with Save', async () => {
    mockModelProvider({ saved: { provider: 'anthropic', base_url: 'https://api.anthropic.com',
      model_id: 'claude-opus-5-5', key_set: true, api_key_last4: '1234' } })
    render(<Settings/>)
    expect(await screen.findByLabelText('Provider')).toHaveValue('anthropic')
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(modelPuts()).toEqual([{
      provider: 'anthropic', reasoning: 'default', base_url: 'https://api.anthropic.com', model_id: 'claude-opus-5-5', api_key: '',
    }]))
  })

  it('has no accessibility violations with Anthropic chosen', async () => {
    const { container } = render(<Settings/>)
    fireEvent.change(await screen.findByLabelText('Provider'), { target: { value: 'anthropic' } })
    await expectAccessible(container)
  })

  it('describes the extension as optional for a first-run model', async () => {
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (url: string) => url === '/api/settings/model'
      ? respond({ base_url: 'https://api.deepseek.com', model_id: '', key_set: false, api_key_last4: null })
      : original(url))
    const { container } = render(<Settings/>)
    await screen.findByLabelText('API key')
    expect(container.querySelector('.lede')?.textContent)
      .toBe('Three quick steps, plus optional X accounts and a browser extension. Your key stays on this computer, encrypted.')
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
    mockModelProvider({
      saved: {
        base_url: 'https://api.deepseek.com', model_id: '',
        key_set: false, api_key_last4: null,
      },
    })
    const { container } = render(<Settings />)
    await screen.findByRole('button', { name: 'Test connection' })
    await waitFor(() => expect(screen.getByLabelText('Model')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    expect(await screen.findByRole('option', { name: 'live-b' })).toBeInTheDocument()
    expect(screen.getByLabelText('Model')).toHaveValue('live-a')
    expect(screen.getByLabelText('API key')).toHaveValue('')
    expect(await screen.findByText('Connection succeeded. Saved model live-a. Choose another model to change it.'))
      .toBeInTheDocument()
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

  it('links invalid-language saves to Other language with the partial-save result at Save', async () => {
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
    fireEvent.change(screen.getByLabelText('Digest language'), { target: { value: 'other' } })
    fireEvent.change(screen.getByLabelText('Other language'), { target: { value: '   ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Choose a valid language.')
    expect(screen.getByLabelText('Other language')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('Other language')).toHaveAttribute('aria-describedby', alert.id)
    expect(screen.getAllByText('Choose a valid language.')).toHaveLength(1)
    expect(within(container.querySelector('.save-bar')!).getByRole('status')).toHaveTextContent(
      'The model settings were saved, but the Digest and YouTube settings were not. Check the Other language field.')
    expect(screen.getByLabelText('API key')).not.toHaveAttribute('aria-invalid')
    expect(screen.getByLabelText('API key')).toHaveAttribute('aria-describedby', 'key-saved key-hint')
    await expectAccessible(container)
  })

  it('shows load failures above the Model provider heading', async () => {
    fetchMock.mockImplementation(async (url: string) => url === '/api/settings/model'
      ? respond({ error: { code: 'request_failed', message: 'Could not load settings.' } }, 503)
      : respond({ digest_language: 'en', youtube_captions: false, youtube_skip_shorts: true }))
    const { container } = render(<Settings />)
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Could not load settings')
    expect(within(alert).queryByText('Could not load settings', { selector: 'strong' })).toBeInTheDocument()
    expect(alert.compareDocumentPosition(screen.getByRole('heading', { name: 'Step 1: Model provider' }))
      & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
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
    expect(calls).toEqual(['/api/settings/model', '/api/settings/model', '/api/settings/preferences'])
    expect(key).toHaveValue('')
    expect(key).not.toHaveAttribute('placeholder', expect.stringContaining('3f9a'))
  })
})

describe('Settings results and focus', () => {
  function saveBar() {
    return screen.getByRole('button', { name: 'Save' }).closest<HTMLElement>('.save-bar')!
  }

  it.each([
    ['', 'Model', 'Test the connection, then choose a model.'],
    ['saved-model', 'Base URL', 'Enter a valid provider URL, such as https://api.deepseek.com.'],
  ])('links invalid model configuration %s to %s', async (model, label, message) => {
    mockModelProvider({
      saved: { base_url: 'https://api.deepseek.com', model_id: model, key_set: true, api_key_last4: '1234' },
      put: () => respond({ error: { code: 'invalid_model_config', message: 'Invalid model configuration.' } }, 422),
    })
    const { container } = render(<Settings/>)
    await screen.findByLabelText('API key')
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    const alert = await screen.findByRole('alert')
    expect(screen.getByLabelText(label)).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText(label)).toHaveAttribute('aria-describedby', alert.id)
    expect(alert).toHaveTextContent(message)
    expect(screen.getAllByText(message)).toHaveLength(1)
    expect(screen.getByLabelText('API key')).not.toHaveAttribute('aria-invalid')
    expect(within(saveBar()).getByRole('status')).toHaveTextContent(
      `Settings were not saved. Check the ${label} field.`)
    await expectAccessible(container)
  })

  it('shows the missing instance secret once in the save bar without marking a field', async () => {
    mockModelProvider({ put: () => respond({ error: { code: 'secret_not_configured', message: 'No secret.' } }, 400) })
    const { container } = render(<Settings/>)
    fireEvent.change(await screen.findByLabelText('API key'), { target: { value: 'fake-3f9a' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    const alert = await screen.findByRole('alert')
    expect(saveBar()).toContainElement(alert)
    expect(alert).toHaveTextContent('Set CATCHUP_SECRET_KEY on the server before saving an API key.')
    expect(screen.getAllByText('Set CATCHUP_SECRET_KEY on the server before saving an API key.')).toHaveLength(1)
    expect(container.querySelector('[aria-invalid="true"]')).toBeNull()
    await expectAccessible(container)
  })

  it('announces Settings saved in the status region present before Save', async () => {
    mockModelProvider()
    render(<Settings/>)
    await screen.findByLabelText('API key')
    const status = saveBar().querySelector('[role="status"]')
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await screen.findByText('Settings saved.')
    expect(within(saveBar()).getByRole('status')).toBe(status)
    expect(status).toHaveTextContent('Settings saved.')
  })

  it('shows the newly saved key and partial save when preferences cannot connect', async () => {
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (url: string, options?: RequestInit) => {
      if (url === '/api/settings/preferences' && options?.method === 'PUT') throw new Error('Offline')
      return original(url, options)
    })
    mockModelProvider()
    render(<Settings/>)
    const key = await screen.findByLabelText('API key')
    fireEvent.change(key, { target: { value: 'fake-3f9a' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await screen.findByRole('alert')
    expect(saveBar()).toHaveTextContent(
      'The model settings were saved, but the Digest and YouTube settings were not. Could not connect to CatchUp.')
    expect(screen.getByText(/Saved key ending in/)).toHaveTextContent('Saved key ending in 3f9a')
    expect(key).toHaveValue('')
  })

  it.each(['field', 'form'])('Test connection clears the save bar after a %s error', async kind => {
    mockModelProvider({ put: () => respond({ error: {
      code: kind === 'field' ? 'auth_failed' : 'secret_not_configured', message: 'Refused.',
    } }, 400) })
    render(<Settings/>)
    await screen.findByLabelText('API key')
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await screen.findByRole('alert')
    expect(saveBar().textContent).not.toBe('Save')
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    expect(within(saveBar()).getByRole('status')).toBeEmptyDOMElement()
    expect(within(saveBar()).queryByRole('alert')).toBeNull()
  })

  it('clears the save bar on a model choice but keeps the key error from a test', async () => {
    mockModelProvider({ put: () => respond({ error: { code: 'secret_not_configured', message: 'No secret.' } }, 400),
      test: () => respond({ error: { code: 'auth_failed', message: 'Rejected' } }, 401) })
    render(<Settings/>)
    await screen.findByLabelText('API key')
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await within(saveBar()).findByRole('alert')
    fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'saved-model' } })
    expect(within(saveBar()).getByRole('status')).toBeEmptyDOMElement()
    expect(within(saveBar()).queryByRole('alert')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    await screen.findByText('The provider rejected the API key.')
    fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'saved-model' } })
    await waitFor(() => expect(modelPuts()).toHaveLength(3))
    expect(screen.getByText('The provider rejected the API key.')).toBeInTheDocument()
    expect(screen.getByLabelText('API key')).toHaveAttribute('aria-invalid', 'true')
  })

  it('removes the old save-bar alert when the next Save succeeds', async () => {
    let refuse = true
    mockModelProvider({ put: body => refuse
      ? respond({ error: { code: 'secret_not_configured', message: 'No secret.' } }, 400)
      : respond({ base_url: body.base_url, model_id: body.model_id, key_set: true, api_key_last4: '1234' }) })
    render(<Settings/>)
    await screen.findByLabelText('API key')
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await within(saveBar()).findByRole('alert')
    refuse = false
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await within(saveBar()).findByText('Settings saved.')
    expect(within(saveBar()).queryByRole('alert')).toBeNull()
  })

  it('keeps empty save, browser, and X status regions on the page without child nodes', async () => {
    render(<Settings/>)
    await screen.findByLabelText('X API token')
    const browser = screen.getByRole('heading', { name: 'Step 4: Browser extension' }).closest('section')!
    const x = screen.getByRole('heading', { name: 'Step 5: X accounts' }).closest('section')!
    const statuses = [
      saveBar().querySelector('[role="status"]'),
      [...browser.querySelectorAll('[role="status"]')].find(node => !node.hasAttribute('aria-label')),
      x.querySelector('[role="status"]'),
    ]
    for (const status of statuses) {
      expect(status).toBeInTheDocument()
      expect(status!.childNodes).toHaveLength(0)
    }
  })

  it('moves focus through X deletion and announces counts in the existing status region', async () => {
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (url: string, options?: RequestInit) =>
      url === '/api/settings/x/delete-all'
        ? respond({ digest_items: 3, digests: 1, accounts: 2 }) : original(url, options))
    render(<Settings/>)
    await screen.findByLabelText('X API token')
    const heading = screen.getByRole('heading', { name: 'Step 5: X accounts' })
    const status = heading.closest('section')!.querySelector('[role="status"]')
    screen.getByRole('button', { name: 'Delete all X data' }).focus()
    fireEvent.click(document.activeElement!)
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.getByRole('button', { name: 'Delete all X data' })).toHaveFocus()
    fireEvent.click(screen.getByRole('button', { name: 'Delete all X data' }))
    const confirm = screen.getByRole('button', { name: 'Delete X data' })
    confirm.focus()
    fireEvent.click(confirm)
    await screen.findByText('Deleted 3 X digest items, 1 digest, and 2 X accounts.')
    expect(heading).toHaveFocus()
    expect(within(heading.closest('section')!).getByRole('status')).toBe(status)
  })

  it('focuses Connected browsers after Disconnect and keeps the browser status region', async () => {
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (url: string, options?: RequestInit) => {
      if (url === '/api/settings/extension-tokens/1') return respond(null, 204)
      if (url === '/api/settings/extension-tokens') return respond([{
        id: 1, name: 'Chrome', created_at: '2026-10-21T12:00:00Z', last_used_at: null,
      }])
      return original(url, options)
    })
    render(<Settings/>)
    const disconnect = await screen.findByRole('button', { name: 'Disconnect Chrome' })
    const heading = screen.getByRole('heading', { name: 'Connected browsers' })
    const section = heading.closest('section')!
    const status = [...section.querySelectorAll('[role="status"]')].find(node => !node.hasAttribute('aria-label'))
    disconnect.focus()
    fireEvent.click(disconnect)
    await screen.findByText('Chrome disconnected.')
    expect(heading).toHaveFocus()
    expect(within(section).getAllByRole('status').find(node => !node.hasAttribute('aria-label'))).toBe(status)
  })

  it('announces X token saved in the existing X status region', async () => {
    render(<Settings/>)
    const input = await screen.findByLabelText('X API token')
    const section = input.closest('section')!
    const status = section.querySelector('[role="status"]')
    fireEvent.change(input, { target: { value: 'fake-token' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save X token' }))
    await screen.findByText('X token saved.')
    expect(within(section).getByRole('status')).toBe(status)
  })
})

describe('saving after a model test', () => {
  it('does not save a failed test and links the rejection to the key', async () => {
    mockModelProvider({ test: () => respond({ error: { code: 'auth_failed', message: 'Rejected' } }, 401) })
    render(<Settings/>)
    await screen.findByLabelText('API key')
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    expect(await within(modelSection()).findByRole('alert')).toHaveTextContent('The provider rejected the API key.')
    expect(modelPuts()).toEqual([])
    expect(screen.getByLabelText('API key')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('API key')).toHaveAttribute('aria-describedby', 'key-saved key-hint key-error')
  })

  it('saves first setup with the fallback model without saving preferences', async () => {
    mockModelProvider({ saved: { base_url: 'https://api.deepseek.com', model_id: '',
      key_set: false, api_key_last4: null } })
    const { container } = render(<Settings/>)
    const key = await screen.findByLabelText('API key')
    fireEvent.change(key, { target: { value: 'secret-3f9a' } })
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    await waitFor(() => expect(modelPuts()).toEqual([{
      provider: 'openai_compatible', reasoning: 'default',
      base_url: 'https://api.deepseek.com', model_id: 'live-a', api_key: 'secret-3f9a',
    }]))
    expect(await within(modelSection()).findByRole('status')).toHaveTextContent(
      'Connection succeeded. Saved key ending in 3f9a with model live-a. Choose another model to change it.')
    expect(fetchMock.mock.calls.filter(([url, options]) =>
      url === '/api/settings/preferences' && options?.method === 'PUT')).toEqual([])
    expect(key).toHaveValue('')
    expect(document.getElementById('key-saved')).toHaveTextContent('Saved key ending in 3f9a')
    expect(screen.getByLabelText('Model')).toHaveValue('live-a')
    await expectAccessible(container)
  })

  it('replaces the saved key while keeping a listed selected model', async () => {
    mockModelProvider({ test: () => respond({ ok: true, models: ['other', 'saved-model'] }) })
    render(<Settings/>)
    fireEvent.change(await screen.findByLabelText('API key'), { target: { value: 'new-key-9999' } })
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    await waitFor(() => expect(modelPuts()).toEqual([{
      provider: 'openai_compatible', reasoning: 'default',
      base_url: 'https://api.deepseek.com', model_id: 'saved-model', api_key: 'new-key-9999',
    }]))
    await waitFor(() => expect(within(modelSection()).getByRole('status').textContent)
      .toBe('Connection succeeded. Saved key ending in 9999 with model saved-model.'))
    expect(document.getElementById('key-saved')).toHaveTextContent('Saved key ending in 9999')
  })

  it('keeps the saved key when testing with an empty key field', async () => {
    mockModelProvider({ test: () => respond({ ok: true, models: ['saved-model'] }) })
    render(<Settings/>)
    await screen.findByLabelText('API key')
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    await waitFor(() => expect(modelPuts()).toEqual([{
      provider: 'openai_compatible', reasoning: 'default',
      base_url: 'https://api.deepseek.com', model_id: 'saved-model', api_key: '',
    }]))
    await waitFor(() => expect(within(modelSection()).getByRole('status').textContent)
      .toBe('Connection succeeded. Saved model saved-model.'))
  })

  it('does not offer another model when the fallback is the only listed model', async () => {
    mockModelProvider({ test: () => respond({ ok: true, models: ['only-model'] }) })
    render(<Settings/>)
    await screen.findByLabelText('API key')
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    await waitFor(() => expect(within(modelSection()).getByRole('status').textContent)
      .toBe('Connection succeeded. Saved model only-model.'))
  })

  it('saves nothing and explains when the provider lists no models', async () => {
    mockModelProvider({ test: () => respond({ ok: true, models: [] }) })
    render(<Settings/>)
    await screen.findByLabelText('API key')
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    await waitFor(() => expect(within(modelSection()).getByRole('status').textContent)
      .toBe('Connection succeeded, but the provider listed no models. Nothing was saved.'))
    expect(modelPuts()).toEqual([])
    expect(screen.getByLabelText('Model')).toBeDisabled()
  })

  it('reports a save failure in the model group and keeps the entered key', async () => {
    mockModelProvider({ put: () => respond({ error: { code: 'secret_not_configured', message: 'No secret' } }, 400) })
    render(<Settings/>)
    const key = await screen.findByLabelText('API key')
    fireEvent.change(key, { target: { value: 'secret-3f9a' } })
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    expect(await within(modelSection()).findByRole('alert')).toHaveTextContent(
      'Connection succeeded, but nothing was saved. Set CATCHUP_SECRET_KEY on the server before saving an API key.')
    expectNoBottomAlert()
    expect(key).toHaveValue('secret-3f9a')
    expect(key).not.toHaveAttribute('aria-invalid')
  })

  it('saves the tested values without clearing a key typed while testing', async () => {
    let finishTest!: (response: ReturnType<typeof respond>) => void
    const pending = new Promise<ReturnType<typeof respond>>(resolve => { finishTest = resolve })
    mockModelProvider({ test: () => pending })
    render(<Settings/>)
    const key = await screen.findByLabelText('API key')
    fireEvent.change(key, { target: { value: 'tested-key-1111' } })
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    fireEvent.change(key, { target: { value: 'typed-later' } })
    fireEvent.change(screen.getByLabelText('Base URL'), { target: { value: 'https://later.example' } })
    await act(async () => { finishTest(respond({ ok: true, models: ['live-a', 'live-b'] })) })
    await waitFor(() => expect(modelPuts()).toEqual([{
      provider: 'openai_compatible', reasoning: 'default',
      base_url: 'https://api.deepseek.com', model_id: 'live-a', api_key: 'tested-key-1111',
    }]))
    expect(key).toHaveValue('typed-later')
  })

  it('shows test errors without a field in the model group, not at the bottom', async () => {
    mockModelProvider({ test: () => respond({ error: { code: 'rate_limited', message: 'Slow down' } }, 429) })
    render(<Settings/>)
    await screen.findByLabelText('API key')
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    expect(await within(modelSection()).findByRole('alert')).toHaveTextContent(
      'The provider is rate limiting requests. Try again later.')
    expectNoBottomAlert()
  })

  it('explains that testing a new key saves it in the saved-key hint', async () => {
    mockModelProvider()
    render(<Settings/>)
    await screen.findByLabelText('API key')
    expect(document.getElementById('key-hint')).toHaveTextContent(
      'Leave empty to keep the saved key. Testing a new key saves it.')
  })

  it('keeps the same status region mounted before and after a test', async () => {
    mockModelProvider()
    render(<Settings/>)
    await screen.findByLabelText('API key')
    const status = within(modelSection()).getByRole('status')
    expect(status).toBeEmptyDOMElement()
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    await waitFor(() => expect(status).toHaveTextContent(
      'Connection succeeded. Saved model live-a. Choose another model to change it.'))
    expect(within(modelSection()).getByRole('status')).toBe(status)
  })
})

describe('reasoning settings', () => {
  it('shows the saved Reasoning after the Model select with its hint', async () => {
    mockModelProvider({ saved: { base_url: 'https://api.deepseek.com', model_id: 'saved-model',
      key_set: true, api_key_last4: '1234', reasoning: 'off' } })
    render(<Settings/>)
    const reasoning = await screen.findByRole('combobox', { name: 'Reasoning' })
    expect(reasoning).toHaveValue('off')
    expect(within(reasoning).getByRole('option', { selected: true })).toHaveTextContent('Off')
    expect(within(reasoning).getAllByRole('option').map(option => option.textContent))
      .toEqual(['Provider default', 'Low', 'Off'])
    expect(modelSection()).toContainElement(reasoning)
    expect(screen.getByLabelText('Model').compareDocumentPosition(reasoning)
      & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(reasoning).toHaveAccessibleDescription(
      'Less reasoning makes digests faster and cheaper. Summaries and topics may be less careful.')
  })

  it('offers no Off for Anthropic and restores the saved choice', async () => {
    mockModelProvider({ saved: { base_url: 'https://api.deepseek.com', model_id: 'saved-model',
      key_set: true, api_key_last4: '1234', reasoning: 'off' } })
    render(<Settings/>)
    const reasoning = await screen.findByLabelText('Reasoning')
    const provider = screen.getByLabelText('Provider')
    fireEvent.change(provider, { target: { value: 'anthropic' } })
    expect(reasoning).toHaveValue('default')
    expect(within(reasoning).getAllByRole('option').map(option => option.textContent))
      .toEqual(['Provider default', 'Low'])
    fireEvent.change(provider, { target: { value: 'openai_compatible' } })
    expect(reasoning).toHaveValue('off')
    fireEvent.change(provider, { target: { value: 'anthropic' } })
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'new-key-7777' } })
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    await waitFor(() => expect(modelPuts()).toEqual([{
      base_url: 'https://api.anthropic.com', model_id: 'live-a', api_key: 'new-key-7777',
      provider: 'anthropic', reasoning: 'default',
    }]))
  })

  it('saves a Reasoning choice right away', async () => {
    mockModelProvider()
    render(<Settings/>)
    const reasoning = await screen.findByLabelText('Reasoning')
    fireEvent.change(reasoning, { target: { value: 'low' } })
    await waitFor(() => expect(modelPuts()).toEqual([{
      base_url: 'https://api.deepseek.com', model_id: 'saved-model', api_key: '',
      provider: 'openai_compatible', reasoning: 'low',
    }]))
    await waitFor(() => expect(within(modelSection()).getByRole('status').textContent)
      .toBe('Saved reasoning: Low.'))
    const provider = screen.getByLabelText('Provider')
    fireEvent.change(provider, { target: { value: 'anthropic' } })
    fireEvent.change(provider, { target: { value: 'openai_compatible' } })
    expect(reasoning).toHaveValue('low')
  })

  it('waits to save a Reasoning choice when the key was edited', async () => {
    mockModelProvider()
    render(<Settings/>)
    const reasoning = await screen.findByLabelText('Reasoning')
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'new-key-7777' } })
    await act(async () => { fireEvent.change(reasoning, { target: { value: 'low' } }) })
    expect(modelPuts()).toEqual([])
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    await waitFor(() => expect(modelPuts()).toEqual([{
      base_url: 'https://api.deepseek.com', model_id: 'live-a', api_key: 'new-key-7777',
      provider: 'openai_compatible', reasoning: 'low',
    }]))
  })

  it('sends the shown Reasoning with Save', async () => {
    mockModelProvider()
    render(<Settings/>)
    const reasoning = await screen.findByLabelText('Reasoning')
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'new-key-7777' } })
    await act(async () => { fireEvent.change(reasoning, { target: { value: 'off' } }) })
    expect(modelPuts()).toEqual([])
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await screen.findByText('Settings saved.')
    expect(modelPuts()).toEqual([{
      base_url: 'https://api.deepseek.com', model_id: 'saved-model', api_key: 'new-key-7777',
      provider: 'openai_compatible', reasoning: 'off',
    }])
    const provider = screen.getByLabelText('Provider')
    fireEvent.change(provider, { target: { value: 'anthropic' } })
    fireEvent.change(provider, { target: { value: 'openai_compatible' } })
    expect(reasoning).toHaveValue('off')
  })

  it('reports a failed Reasoning save in the model group', async () => {
    mockModelProvider({ put: () => respond({ error: { code: 'invalid_reasoning',
      message: 'Choose a Reasoning setting that this provider supports.' } }, 422) })
    render(<Settings/>)
    fireEvent.change(await screen.findByLabelText('Reasoning'), { target: { value: 'low' } })
    expect((await within(modelSection()).findByRole('alert')).textContent).toBe(
      'The reasoning setting was not saved. Choose a Reasoning setting that this provider supports.')
    expectNoBottomAlert()
  })

  it('has no accessibility violations with the Reasoning select', async () => {
    mockModelProvider()
    const { container } = render(<Settings/>)
    await screen.findByLabelText('Reasoning')
    await expectAccessible(container)
  })
})

describe('saving model choices', () => {
  async function testAndSave() {
    render(<Settings/>)
    await screen.findByLabelText('API key')
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    await screen.findByText('Connection succeeded. Saved model live-a. Choose another model to change it.')
  }

  it('saves a Reasoning choice and a model choice in order', async () => {
    let finishChoice!: (response: ReturnType<typeof respond>) => void
    const pending = new Promise<ReturnType<typeof respond>>(resolve => { finishChoice = resolve })
    mockModelProvider({ put: body => body.model_id === 'live-a' && body.reasoning === 'low'
      ? pending : respond({ base_url: body.base_url, model_id: body.model_id,
        reasoning: body.reasoning, key_set: true, api_key_last4: '1234' }) })
    await testAndSave()
    fireEvent.change(screen.getByLabelText('Reasoning'), { target: { value: 'low' } })
    await waitFor(() => expect(modelPuts()).toHaveLength(2))
    await act(async () => {
      fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'live-b' } })
    })
    expect(modelPuts()).toHaveLength(2)
    await act(async () => {
      finishChoice(respond({ base_url: 'https://api.deepseek.com', model_id: 'live-a',
        reasoning: 'low', key_set: true, api_key_last4: '1234' }))
    })
    await waitFor(() => expect(modelPuts()).toEqual([
      { base_url: 'https://api.deepseek.com', model_id: 'live-a', api_key: '',
        provider: 'openai_compatible', reasoning: 'default' },
      { base_url: 'https://api.deepseek.com', model_id: 'live-a', api_key: '',
        provider: 'openai_compatible', reasoning: 'low' },
      { base_url: 'https://api.deepseek.com', model_id: 'live-b', api_key: '',
        provider: 'openai_compatible', reasoning: 'low' },
    ]))
    await screen.findByText('Saved model live-b.')
  })

  it('saves a model choice and then a Reasoning choice in order', async () => {
    let finishChoice!: (response: ReturnType<typeof respond>) => void
    const pending = new Promise<ReturnType<typeof respond>>(resolve => { finishChoice = resolve })
    mockModelProvider({ put: body => body.model_id === 'live-b' && body.reasoning === 'default'
      ? pending : respond({ base_url: body.base_url, model_id: body.model_id,
        reasoning: body.reasoning, key_set: true, api_key_last4: '1234' }) })
    await testAndSave()
    await act(async () => {
      fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'live-b' } })
    })
    fireEvent.change(screen.getByLabelText('Reasoning'), { target: { value: 'low' } })
    expect(modelPuts()).toHaveLength(2)
    await act(async () => {
      finishChoice(respond({ base_url: 'https://api.deepseek.com', model_id: 'live-b',
        reasoning: 'default', key_set: true, api_key_last4: '1234' }))
    })
    await waitFor(() => expect(modelPuts().map(body => [body.model_id, body.reasoning])).toEqual([
      ['live-a', 'default'], ['live-b', 'default'], ['live-b', 'low'],
    ]))
    await screen.findByText('Saved reasoning: Low.')
  })

  it('waits to save a model choice when the key was edited', async () => {
    mockModelProvider()
    await testAndSave()
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'untested-key' } })
    await act(async () => {
      fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'live-b' } })
    })
    expect(modelPuts()).toEqual([{
      provider: 'openai_compatible', reasoning: 'default',
      base_url: 'https://api.deepseek.com', model_id: 'live-a', api_key: '',
    }])
    expect(screen.getByLabelText('Model')).toHaveValue('live-b')
  })

  it('waits to save a model choice when the base URL was edited', async () => {
    mockModelProvider()
    await testAndSave()
    fireEvent.change(screen.getByLabelText('Base URL'), { target: { value: 'https://untested.example' } })
    await act(async () => {
      fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'live-b' } })
    })
    expect(modelPuts()).toEqual([{
      provider: 'openai_compatible', reasoning: 'default',
      base_url: 'https://api.deepseek.com', model_id: 'live-a', api_key: '',
    }])
    expect(screen.getByLabelText('Model')).toHaveValue('live-b')
  })

  it('does not save a choice when no configuration has ever been saved', async () => {
    mockModelProvider({
      saved: { base_url: 'https://api.deepseek.com', model_id: '', key_set: false, api_key_last4: null },
      put: () => respond({ error: { code: 'secret_not_configured', message: 'No secret' } }, 400),
    })
    render(<Settings/>)
    const key = await screen.findByLabelText('API key')
    fireEvent.change(key, { target: { value: 'secret-3f9a' } })
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    await within(modelSection()).findByRole('alert')
    expect(key).toHaveValue('secret-3f9a')
    fireEvent.change(key, { target: { value: '' } })
    await act(async () => {
      fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'live-b' } })
    })
    expect(modelPuts()).toEqual([{
      provider: 'openai_compatible', reasoning: 'default',
      base_url: 'https://api.deepseek.com', model_id: 'live-a', api_key: 'secret-3f9a',
    }])
    expect(screen.getByLabelText('Model')).toHaveValue('live-b')
  })

  it('saves another model choice immediately after a test', async () => {
    mockModelProvider()
    await testAndSave()
    fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'live-b' } })
    await waitFor(() => expect(modelPuts()).toEqual([
      { base_url: 'https://api.deepseek.com', model_id: 'live-a', api_key: '', provider: 'openai_compatible', reasoning: 'default' },
      { base_url: 'https://api.deepseek.com', model_id: 'live-b', api_key: '', provider: 'openai_compatible', reasoning: 'default' },
    ]))
    await waitFor(() => expect(within(modelSection()).getByRole('status').textContent)
      .toBe('Saved model live-b.'))
  })

  it('saves a model choice after a first-setup test', async () => {
    mockModelProvider({ saved: { base_url: 'https://api.deepseek.com', model_id: '', key_set: false, api_key_last4: null } })
    render(<Settings/>)
    fireEvent.change(await screen.findByLabelText('API key'), { target: { value: 'secret-3f9a' } })
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    await waitFor(() => expect(screen.getByLabelText('API key')).toHaveValue(''))
    fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'live-b' } })
    await waitFor(() => expect(modelPuts()[1]).toEqual(
      { base_url: 'https://api.deepseek.com', model_id: 'live-b', api_key: '', provider: 'openai_compatible', reasoning: 'default' }))
  })

  it('saves quick successive model choices in order', async () => {
    let finishChoice!: (response: ReturnType<typeof respond>) => void
    const pending = new Promise<ReturnType<typeof respond>>(resolve => { finishChoice = resolve })
    mockModelProvider({
      test: () => respond({ ok: true, models: ['live-a', 'live-b', 'live-c'] }),
      put: body => body.model_id === 'live-b' ? pending : respond({
        base_url: body.base_url, model_id: body.model_id, key_set: true,
        api_key_last4: body.api_key ? body.api_key.slice(-4) : '1234',
      }),
    })
    await testAndSave()
    fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'live-b' } })
    await waitFor(() => expect(modelPuts().map(body => body.model_id)).toEqual(['live-a', 'live-b']))
    await act(async () => {
      fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'live-c' } })
    })
    expect(modelPuts().map(body => body.model_id)).toEqual(['live-a', 'live-b'])
    await act(async () => {
      finishChoice(respond({ base_url: 'https://api.deepseek.com', model_id: 'live-b',
        key_set: true, api_key_last4: '1234' }))
    })
    await waitFor(() => expect(modelPuts()).toEqual([
      { base_url: 'https://api.deepseek.com', model_id: 'live-a', api_key: '', provider: 'openai_compatible', reasoning: 'default' },
      { base_url: 'https://api.deepseek.com', model_id: 'live-b', api_key: '', provider: 'openai_compatible', reasoning: 'default' },
      { base_url: 'https://api.deepseek.com', model_id: 'live-c', api_key: '', provider: 'openai_compatible', reasoning: 'default' },
    ]))
    await waitFor(() => expect(within(modelSection()).getByRole('status').textContent)
      .toBe('Saved model live-c.'))
  })

  it('keeps a failed model choice and saves a later choice after a rejected fetch', async () => {
    mockModelProvider({
      test: () => respond({ ok: true, models: ['live-a', 'live-b', 'live-c'] }),
      put: body => {
        if (body.model_id === 'live-b') return Promise.reject(new Error('Offline'))
        return respond({ base_url: body.base_url, model_id: body.model_id, key_set: true,
          api_key_last4: body.api_key ? body.api_key.slice(-4) : '1234' })
      },
    })
    await testAndSave()
    fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'live-b' } })
    expect(await within(modelSection()).findByRole('alert')).toHaveTextContent(
      'The model was not saved. Could not connect to CatchUp.')
    expect(within(modelSection()).getByRole('status')).toBeEmptyDOMElement()
    expect(screen.getByLabelText('Model')).toHaveValue('live-b')
    fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'live-c' } })
    await waitFor(() => expect(within(modelSection()).getByRole('status').textContent)
      .toBe('Saved model live-c.'))
    expect(modelPuts()).toEqual([
      { base_url: 'https://api.deepseek.com', model_id: 'live-a', api_key: '', provider: 'openai_compatible', reasoning: 'default' },
      { base_url: 'https://api.deepseek.com', model_id: 'live-b', api_key: '', provider: 'openai_compatible', reasoning: 'default' },
      { base_url: 'https://api.deepseek.com', model_id: 'live-c', api_key: '', provider: 'openai_compatible', reasoning: 'default' },
    ])
    expect(within(modelSection()).queryByRole('alert')).toBeNull()
  })
})

describe('X accounts settings', () => {
  it('asks before deleting all X data, preserves saved pages, and announces counts', async () => {
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (url: string, options?: RequestInit) => {
      if (url === '/api/settings/x/delete-all' && options?.method === 'POST') return respond({
        digest_items: 3, digests: 1, accounts: 2,
      })
      return original(url)
    })
    const { container } = render(<Settings/>)
    await screen.findByLabelText('X API token')
    fireEvent.click(screen.getByRole('button', { name: 'Delete all X data' }))
    const confirmation = screen.getByRole('group', { name: 'Confirm X data deletion' })
    expect(confirmation).toHaveTextContent(
      'Delete all X data? This removes your X token, followed X accounts, and their items in saved digests.')
    expect(confirmation).toHaveTextContent('Pages saved from X with the extension stay.')
    await expectAccessible(container)
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(fetchMock.mock.calls.filter(([url]) => url === '/api/settings/x/delete-all')).toHaveLength(0)
    fireEvent.click(screen.getByRole('button', { name: 'Delete all X data' }))
    fireEvent.click(screen.getByRole('group', { name: 'Confirm X data deletion' }).querySelector('button')!)
    expect((await screen.findByText('Deleted 3 X digest items, 1 digest, and 2 X accounts.'))
      .closest('[role="status"]')).toBeInTheDocument()
    expect(fetchMock.mock.calls.filter(([url]) => url === '/api/settings/x/delete-all')).toHaveLength(1)
  })

  // Guard: the confirmation already stays mounted when deletion fails.
  it('shows the active-run refusal and keeps the confirmation', async () => {
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (url: string, options?: RequestInit) =>
      url === '/api/settings/x/delete-all' && options?.method === 'POST'
        ? respond({ error: { code: 'run_active',
          message: 'A digest is being made. Try again when it finishes.' } }, 409)
        : original(url))
    const { container } = render(<Settings/>)
    await screen.findByLabelText('X API token')
    fireEvent.click(screen.getByRole('button', { name: 'Delete all X data' }))
    fireEvent.click(screen.getByRole('group', { name: 'Confirm X data deletion' }).querySelector('button')!)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'A digest is being made. Try again when it finishes.')
    expect(screen.getByRole('group', { name: 'Confirm X data deletion' })).toBeInTheDocument()
    await expectAccessible(container)
  })

  it('loads a saved token without putting it in the field', async () => {
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (url: string) =>
      url === '/api/settings/x' ? respond({ token_set: true, token_last4: 'abcd' }) : original(url))
    const { container } = render(<Settings/>)
    expect(await screen.findByText(/Saved token ending in/)).toHaveTextContent('abcd')
    expect(screen.getByLabelText('X API token')).toHaveValue('')
    expect(screen.getByLabelText('X API token')).toHaveAttribute('type', 'password')
    expect(container.querySelector('.lede')?.textContent)
      .toBe('Your model, digest language, YouTube options, browser extension, and X accounts.')
    expect(screen.getByRole('link', { name: /spending limit/i }))
      .toHaveAttribute('href', 'https://github.com/Zhuoang2/catchup#x-accounts')
    // .note is a flex row: the sentence must be one item, not text, link, and period side by side.
    const note = screen.getByRole('link', { name: /spending limit/i }).closest('.note')!
    expect([...note.childNodes].every(node => node.nodeType === Node.ELEMENT_NODE)).toBe(true)
    expect(note.querySelector('span')).toHaveTextContent(
      'X API reads are billed to your X developer account. You can set a spending limit in the X console.')
    await expectAccessible(container)
  })

  it('saves, tests, and removes the token without touching model settings', async () => {
    const original = fetchMock.getMockImplementation()!
    let tokenSet = false
    fetchMock.mockImplementation(async (url: string, options?: RequestInit) => {
      if (url === '/api/settings/x' && !options?.method) {
        return respond({ token_set: tokenSet, token_last4: tokenSet ? 'oken' : null })
      }
      if (url === '/api/settings/x' && options?.method === 'PUT') {
        expect(JSON.parse(options.body as string)).toEqual({ token: 'test-token' })
        tokenSet = true
        return respond({ token_set: true, token_last4: 'oken' })
      }
      if (url === '/api/settings/x/test') return respond({ ok: true })
      if (url === '/api/settings/x' && options?.method === 'DELETE') {
        tokenSet = false
        return respond(null, 204)
      }
      return original(url)
    })
    const { container, unmount } = render(<Settings/>)
    const input = await screen.findByLabelText('X API token')
    fireEvent.change(input, { target: { value: 'test-token' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save X token' }))
    await screen.findByText(/Saved token ending in/)
    expect(input).toHaveValue('')
    fireEvent.click(screen.getByRole('button', { name: 'Test X token' }))
    expect(await screen.findByText('X token works.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Remove X token' }))
    await waitFor(() => expect(screen.queryByText(/Saved token ending in/)).toBeNull())
    expect(fetchMock.mock.calls.filter(([url, options]) => url === '/api/settings/x'
      && (options as RequestInit | undefined)?.method === 'DELETE')).toHaveLength(1)
    expect(screen.getByLabelText('X API token').closest('section')).not.toHaveTextContent('Saved token ending in')
    expect(fetchMock.mock.calls.some(([url, options]) => url === '/api/settings/model'
      && (options as RequestInit | undefined)?.method === 'PUT')).toBe(false)
    await expectAccessible(container)
    unmount()
    render(<Settings/>)
    await screen.findByLabelText('X API token')
    expect(screen.getByLabelText('X API token').closest('section')).not.toHaveTextContent('Saved token ending in')
    expect(fetchMock.mock.calls.filter(([url, options]) => url === '/api/settings/x'
      && !(options as RequestInit | undefined)?.method)).toHaveLength(2)
  })

  it('ties a failed X token save to the token field', async () => {
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (url: string, options?: RequestInit) => {
      if (url === '/api/settings/x' && options?.method === 'PUT') return respond(
        { error: { code: 'invalid_x_token', message: 'Enter a printable ASCII X API token.' } }, 422)
      if (url === '/api/settings/x') return respond({ token_set: true, token_last4: 'abcd' })
      return original(url)
    })
    const { container } = render(<Settings/>)
    const input = await screen.findByLabelText('X API token')
    expect(input).toHaveAccessibleDescription(/Saved token ending in abcd/)
    fireEvent.change(input, { target: { value: 'bad token' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save X token' }))
    expect(await screen.findByText('Enter a printable ASCII X API token.')).toBeInTheDocument()
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAccessibleDescription(/Enter a printable ASCII X API token/)
    await expectAccessible(container)
  })

  it('reports rejected tokens and remains accessible', async () => {
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (url: string, options?: RequestInit) =>
      url === '/api/settings/x/test' && options?.method === 'POST'
        ? respond({ error: { code: 'x_token_rejected', message: 'X rejected the token.' } }, 401)
        : original(url))
    const { container } = render(<Settings/>)
    await screen.findByLabelText('X API token')
    await expectAccessible(container)
    fireEvent.click(screen.getByRole('button', { name: 'Test X token' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('X rejected the token')
    await expectAccessible(container)
  })

  it('keeps model form saves separate from X operations', async () => {
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (url: string, options?: RequestInit) => {
      if (url === '/api/settings/model' && options?.method === 'PUT') return respond({
        base_url: 'https://api.deepseek.com', model_id: 'saved-model', key_set: true, api_key_last4: '1234',
      })
      if (url === '/api/settings/preferences' && options?.method === 'PUT') return respond({
        digest_language: 'en', youtube_captions: false, youtube_skip_shorts: true,
      })
      return original(url)
    })
    render(<Settings/>)
    await screen.findByLabelText('X API token')
    fireEvent.click(screen.getByRole('button', { name: /^Save$/ }))
    await screen.findByText('Settings saved.')
    expect(fetchMock.mock.calls.filter(([url, options]) => url === '/api/settings/x'
      && (options as RequestInit | undefined)?.method)).toEqual([])
  })
})
