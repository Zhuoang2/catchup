import { fireEvent, screen, waitFor } from '@testing-library/dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { initOptions } from '../options'

const values: Record<string, string> = {}
const storage = { get: vi.fn(async () => ({ ...values })), set: vi.fn(async (next: Record<string, string>) =>
  Object.assign(values, next)) }
const fetchMock = vi.fn()

beforeEach(() => {
  document.body.innerHTML = '<main><h1>CatchUp options</h1><form id="options-form">' +
    '<label for="server">Server address</label><input id="server" required>' +
    '<label for="token">Connection token</label><input id="token" required>' +
    '<button type="submit">Save</button></form>' +
    '<button type="button" id="test-connection">Test connection</button>' +
    '<p id="feedback" role="status" aria-live="polite"></p></main>'
  for (const key of Object.keys(values)) delete values[key]
  storage.get.mockClear(); storage.set.mockClear()
  vi.stubGlobal('chrome', { storage: { local: storage } })
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => { vi.unstubAllGlobals(); fetchMock.mockReset() })

it('loads and saves local address and token, then tests only that address', async () => {
  Object.assign(values, { server: 'http://localhost:8800', token: 'fake-browser-token' })
  fetchMock.mockResolvedValue({ ok: true, json: async () => ({ name: 'Chrome', waiting: 0 }) })
  initOptions()
  await waitFor(() => expect(screen.getByLabelText('Server address')).toHaveValue('http://localhost:8800'))
  fireEvent.change(screen.getByLabelText('Server address'), { target: { value: 'http://127.0.0.1:8000' } })
  fireEvent.submit(document.querySelector('form')!)
  await waitFor(() => expect(storage.set).toHaveBeenCalledWith({
    server: 'http://127.0.0.1:8000', token: 'fake-browser-token',
  }))
  fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
    'http://127.0.0.1:8000/api/extension/status',
    expect.objectContaining({ headers: { Authorization: 'Bearer fake-browser-token' } }),
  ))
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Chrome'))
  expect((await axe(document.body, { rules: { 'color-contrast': { enabled: false } } })).violations).toEqual([])
})

it.each(['http://192.168.1.5:8000', 'https://example.com'])(
  'rejects a server outside the extension host permissions: %s', async server => {
    initOptions()
    await waitFor(() => expect(screen.getByLabelText('Server address')).toHaveValue('http://127.0.0.1:8000'))
    fireEvent.change(screen.getByLabelText('Server address'), { target: { value: server } })
    fireEvent.change(screen.getByLabelText('Connection token'), { target: { value: 'fake-browser-token' } })
    fireEvent.submit(document.querySelector('form')!)
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(/localhost|127\.0\.0\.1/))
    expect(storage.set).not.toHaveBeenCalled()
    expect(fetchMock).not.toHaveBeenCalled()
    expect((await axe(document.body, { rules: { 'color-contrast': { enabled: false } } })).violations).toEqual([])
  },
)
