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
      if (response.ok) {
        event.waitUntil(
          caches.open(CACHE).then(cache => cache.add('/offline.html')).catch(() => {})
        )
      }
      return response
    }).catch(async () => {
      const cache = await caches.open(CACHE)
      return await cache.match('/offline.html') ?? Response.error()
    })
  )
})
