const CACHE = 'catchup-offline-v1'

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.add('/offline.html')).then(() => self.skipWaiting())
  )
})

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(names => Promise.all(names.filter(name => name !== CACHE).map(name => caches.delete(name))))
      .then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', event => {
  if (event.request.mode !== 'navigate') return
  event.respondWith(
    fetch(event.request).then(response => {
      if (response.ok) refreshOfflinePage(event)
      return response
    }, async () => {
      const cache = await caches.open(CACHE)
      return await cache.match('/offline.html') ?? Response.error()
    })
  )
})

// Keep the cached offline page current without ever replacing a real response.
function refreshOfflinePage(event) {
  try {
    event.waitUntil(
      caches.open(CACHE)
        .then(cache => cache.add(new Request('/offline.html', { cache: 'no-cache' })))
        .catch(() => {})
    )
  } catch {
    // The event can no longer be extended; the previously cached copy stays.
  }
}
