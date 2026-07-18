// sw.js
// Bump this string on every deploy where cached files changed.
const CACHE = 'ayurvani-v8';

// Only long-lived, rarely-changing assets go here — safe to cache-first.
const STATIC_ASSETS = [
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
  '/icon-512-maskable.png'
];

self.addEventListener('install', e => {
  self.skipWaiting(); // Force active immediately
  e.waitUntil(
    caches.open(CACHE).then(c => {
      return Promise.all(
        STATIC_ASSETS.map(url =>
          c.add(url).catch(err => console.warn(`SW: Failed to cache asset ${url}`, err))
        )
      );
    })
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          if (key !== CACHE) {
            console.log('SW: Removing old cache', key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim()) // Claim control of active pages immediately
  );
});

// Anything that represents "the app" (markup, scripts, data) must always be
// checked against the network first. Cache is only a fallback for offline use.
// This is what actually changes on every deploy — treating it cache-first was
// the reason updates (and hard refreshes) weren't reliably showing up.
function isNetworkFirst(pathname) {
  return (
    pathname === '/' ||
    pathname === '/index.html' ||
    pathname.endsWith('.js') ||
    pathname.endsWith('.css')
  );
}

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;

  const url = new URL(e.request.url);

  // Completely bypass Service Worker cache for Vercel API, Hugging Face, and database JSON files
  if (
    url.pathname.startsWith('/api/') || 
    url.hostname.includes('hf.space') || 
    url.hostname.includes('huggingface') ||
    url.pathname.endsWith('.json')
  ) {
    return;
  }

  if (isNetworkFirst(url.pathname)) {
    e.respondWith(
      fetch(e.request)
        .then(res => {
          const resClone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, resClone));
          return res;
        })
        .catch(() => caches.match(e.request)) // offline fallback only
    );
    return;
  }

  // Cache-first for large binary assets (images, audio, fonts) that don't
  // change once uploaded — safe and keeps the site fast/offline-capable.
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(res => {
        const resClone = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, resClone));
        return res;
      });
    }).catch(() => fetch(e.request))
  );
});
