import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import { describe, expect, it, vi } from 'vitest'

type Event = {
  request?: { mode: string; url: string }
  waitUntil?: (work: Promise<unknown>) => void
  respondWith?: (response: Promise<unknown>) => void
}

function worker() {
  const handlers: Record<string, (event: Event) => void> = {}
  const add = vi.fn(async (_path: string) => undefined)
  const put = vi.fn()
  const offline = { body: 'Offline' }
  const match = vi.fn(async (_path: string) => offline)
  const open = vi.fn(async (_name: string) => ({ add, put, match }))
  const keys = vi.fn(async () => ['catchup-offline-v0', 'catchup-offline-v1', 'other-cache'])
  const remove = vi.fn(async (_name: string) => true)
  const fetch = vi.fn(async (_request: { url: string }) => ({ status: 200 }))
  const skipWaiting = vi.fn()
  const claim = vi.fn()
  runInNewContext(readFileSync('public/sw.js', 'utf8'), {
    self: {
      addEventListener: (name: string, handler: (event: Event) => void) => { handlers[name] = handler },
      skipWaiting, clients: { claim },
    },
    caches: { open, keys, delete: remove }, fetch, Response,
  })
  return { handlers, add, put, offline, match, open, keys, remove, fetch, skipWaiting, claim }
}

describe('offline-only service worker', () => {
  it('caches only the offline page during install and removes old caches on activate', async () => {
    const w = worker()
    let install: Promise<unknown> | undefined
    w.handlers.install({ waitUntil: work => { install = work } })
    await install
    expect(w.open).toHaveBeenCalledWith('catchup-offline-v1')
    expect(w.add).toHaveBeenCalledExactlyOnceWith('/offline.html')
    expect(w.put).not.toHaveBeenCalled()
    expect(w.skipWaiting).toHaveBeenCalledOnce()
    let activate: Promise<unknown> | undefined
    w.handlers.activate({ waitUntil: work => { activate = work } })
    await activate
    expect(w.remove.mock.calls.map(([name]) => name)).toEqual(['catchup-offline-v0', 'other-cache'])
    expect(w.claim).toHaveBeenCalledOnce()
  })

  it('falls back only when a navigation rejects, not on a 500 response', async () => {
    const w = worker()
    const request = { mode: 'navigate', url: 'http://localhost/history' }
    let response: Promise<unknown> | undefined
    w.fetch.mockRejectedValueOnce(new Error('Network unavailable'))
    w.handlers.fetch({ request, respondWith: work => { response = work } })
    expect(await response).toBe(w.offline)
    expect(w.match).toHaveBeenCalledExactlyOnceWith('/offline.html')
    w.fetch.mockResolvedValueOnce({ status: 500 })
    w.handlers.fetch({ request, respondWith: work => { response = work } })
    expect(await response).toEqual({ status: 500 })
    expect(w.match).toHaveBeenCalledTimes(1)
    expect(w.put).not.toHaveBeenCalled()
  })

  it('does not intercept API, assets, or other non-navigation requests', () => {
    const w = worker()
    const respondWith = vi.fn()
    for (const url of ['/api/digests', '/assets/index.js', '/icon-192.png']) {
      w.handlers.fetch({ request: { mode: 'cors', url }, respondWith })
    }
    expect(respondWith).not.toHaveBeenCalled()
    expect(w.fetch).not.toHaveBeenCalled()
    expect(w.open).not.toHaveBeenCalled()
    expect(w.put).not.toHaveBeenCalled()
  })
})
