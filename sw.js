// sw.js
const CACHE = 'ayurvani-v6';
const ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
  '/icon-512-maskable.png',
  '/js/vagdhenu-ui.js',
  '/dravyaguna.js',
  '/dravyaguna_data.json',
  '/books.json',
  '/chants.json',
  '/charaka_verse_index.json',
  '/dravyaguna-bg.jpg'
];

self.addEventListener('install', e => {
  self.skipWaiting(); // Force active immediately
  e.waitUntil(
    caches.open(CACHE).then(c => {
      // Add assets one-by-one or fallback to prevent failure if one is missing
      return Promise.all(
        ASSETS.map(url => {
          return c.add(url).catch(err => {
            console.warn(`SW: Failed to cache asset ${url}`, err);
          });
        })
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

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  
  const url = new URL(e.request.url);
  // Completely bypass Service Worker cache for Vercel API and Hugging Face routes
  if (url.pathname.startsWith('/api/') || url.hostname.includes('hf.space') || url.hostname.includes('huggingface')) {
    return;
  }
  
  e.respondWith(
    caches.match(e.request).then(response => {
      return response || fetch(e.request).catch(() => null);
    }).catch(() => {
      return fetch(e.request);
    })
  );
});
