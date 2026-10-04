import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Settings from './Settings'

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
    if (url === '/api/settings/preferences') return respond({ digest_language: 'en' })
    throw new Error(`Unexpected request: ${url}`)
  })
})
afterEach(() => {
  vi.unstubAllGlobals()
  fetchMock.mockReset()
})

describe('model settings', () => {
  it('loads provider settings without revealing the key', async () => {
    render(<Settings />)
    expect(await screen.findByDisplayValue('https://api.deepseek.com')).toBeInTheDocument()
    expect(screen.getByLabelText('API key')).toHaveAttribute('type', 'password')
    expect(screen.getByLabelText('API key')).toHaveAttribute('placeholder', '•••• 1234')
    expect(screen.getByDisplayValue('saved-model')).toBeInTheDocument()
  })

  it('fills model options from a successful provider test', async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url === '/api/settings/model/test') return respond({ ok: true, models: ['live-a', 'live-b'] })
      if (url === '/api/settings/model') return respond({
        base_url: 'https://api.deepseek.com', model_id: '',
        key_set: false, api_key_last4: null,
      })
      return respond({ digest_language: 'en' })
    })
    render(<Settings />)
    await screen.findByRole('button', { name: 'Test connection' })
    await waitFor(() => expect(screen.getByLabelText('Model')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    expect(await screen.findByRole('option', { name: 'live-b' })).toBeInTheDocument()
    expect(screen.getByLabelText('Model')).toHaveValue('live-a')
  })

  it('explains authentication errors', async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url === '/api/settings/model/test')
        return respond({ error: { code: 'auth_failed', message: 'Rejected' } }, 401)
      if (url === '/api/settings/model') return respond({
        base_url: 'https://api.deepseek.com', model_id: 'saved-model',
        key_set: true, api_key_last4: '1234',
      })
      return respond({ digest_language: 'en' })
    })
    render(<Settings />)
    await screen.findByLabelText('API key')
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('rejected the API key')
  })

  it('shows an input when another language is chosen', async () => {
    render(<Settings />)
    await screen.findByLabelText('Digest language')
    fireEvent.change(screen.getByLabelText('Digest language'), { target: { value: 'other' } })
    expect(screen.getByLabelText('Other language')).toBeInTheDocument()
  })
})
