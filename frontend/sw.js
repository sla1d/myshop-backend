const CACHE_NAME = 'myshop-v1';
const STATIC_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/css/themes/midnight.css',
  '/static/js/app.js',
  '/static/js/i18n.js',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws/')) return;
  event.respondWith(
    caches.match(event.request).then(cached => {
      const fetched = fetch(event.request).then(response => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => cached);
      return cached || fetched;
    })
  );
});

self.addEventListener('push', event => {
  const data = event.data?.json() || { title: 'MyShop', body: 'Новое уведомление' };
  event.waitUntil(self.registration.showNotification(data.title, {
    body: data.body,
    icon: '/static/favicon.png',
    badge: '/static/favicon.png',
  }));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(clients.openWindow('/'));
});
