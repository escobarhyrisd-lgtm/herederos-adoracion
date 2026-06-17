const CACHE_NAME = 'herederos-adoracion-v3';

// Recursos a cachear al instalar
const urlsToCache = [
  '/',
  '/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png'
];

// Instalación
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Cache abierto');
        return cache.addAll(urlsToCache);
      })
  );
});

// Activar y limpiar cachés viejos
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Estrategia de fetch: Network-first para todo
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Si es petición a Supabase, NO usar caché (siempre red)
  if (url.hostname.includes('supabase.co')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Si es petición a la API de Streamlit, NO usar caché
  if (url.pathname.startsWith('/_stcore/')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Para el resto: Network first con fallback a caché
  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Clonar la respuesta para cachear
        const responseClone = response.clone();
        caches.open(CACHE_NAME).then(cache => {
          cache.put(event.request, responseClone);
        });
        return response;
      })
      .catch(() => {
        return caches.match(event.request);
      })
  );
});