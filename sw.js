// sw.js
const CACHE = 'ayurvani-tts-v1';
const ASSETS = ['/models/sanskrit-vits-int8.onnx', '/js/phonemizer.js', '/js/tts-engine.js'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
});
self.addEventListener('fetch', e => {
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
