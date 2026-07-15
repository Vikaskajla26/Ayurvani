// sw.js
const CACHE = 'ayurvani-v5';
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
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
