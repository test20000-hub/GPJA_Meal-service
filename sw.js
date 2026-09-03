const CACHE_NAME = 'gpja-meal-v4';
const APP_SHELL = [
  './',
  './index.html',
  './style.css',
  './app.js?v=20260903-3',
  './manifest.webmanifest?v=20260903-3',
  './1788425827851.png?v=20260903-3'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
    ))
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  if (url.pathname.endsWith('/data/meals.json')) {
    event.respondWith(fetch(event.request, { cache: 'no-store' }).catch(() => caches.match(event.request)));
    return;
  }

  // HTML/JS/CSS는 최신 배포본을 우선 사용하고, 오프라인일 때만 캐시를 사용합니다.
  if (event.request.destination === 'document' || ['script', 'style'].includes(event.request.destination)) {
    event.respondWith(
      fetch(event.request).then(response => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
        return response;
      }).catch(() => caches.match(event.request))
    );
    return;
  }

  event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request)));
});
