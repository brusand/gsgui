// Service Worker pour Protéodies Player - Cache hors ligne
const CACHE_NAME = 'proteodies-v16-neuro-douleur';
const urlsToCache = [
  '/proteodies/',
  '/proteodies/index.html',
  '/proteodies/manifest.json',
  '.',
  './'
];

// Installation - mise en cache des fichiers
self.addEventListener('install', event => {
  console.log('[SW] 🚀 Installation du Service Worker:', CACHE_NAME);
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[SW] 📦 Cache ouvert, ajout des URLs:', urlsToCache);

        // Ajouter toutes les URLs en parallèle mais continuer même si certaines échouent
        const cachePromises = urlsToCache.map(url => {
          return cache.add(url).then(() => {
            console.log('[SW] ✅ Cached:', url);
          }).catch(err => {
            console.warn('[SW] ⚠️ Failed to cache:', url, err.message);
            // Ne pas bloquer l'installation si une URL échoue
          });
        });

        return Promise.all(cachePromises);
      })
      .then(() => {
        console.log('[SW] ✅ Installation complète, activation immédiate');
        return self.skipWaiting();
      })
      .catch(err => {
        console.error('[SW] ❌ Erreur installation critique:', err);
        throw err;
      })
  );
});

// Activation - nettoyage des anciens caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('Suppression ancien cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Interception des requêtes - stratégie CACHE ONLY pour mode avion complet
self.addEventListener('fetch', event => {
  // Ignorer les requêtes non-HTTP (chrome-extension://, etc.)
  if (!event.request.url.startsWith('http')) {
    return;
  }

  event.respondWith(
    // Stratégie ultra-agressive : CACHE FIRST, NO NETWORK
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.match(event.request)
          .then(cachedResponse => {
            if (cachedResponse) {
              console.log('[SW] ✅ CACHE HIT (offline OK):', event.request.url);
              return cachedResponse;
            }

            // Essayer plusieurs variantes d'URL en cache
            const url = new URL(event.request.url);
            const variants = [
              url.pathname,
              url.pathname + '/',
              url.pathname.replace(/\/$/, ''),
              '/proteodies/',
              '/proteodies/index.html'
            ];

            console.log('[SW] ⚠️ Cache miss, trying variants:', variants);

            return variants.reduce((promise, variant) => {
              return promise.then(response => {
                if (response) return response;
                return cache.match(variant);
              });
            }, Promise.resolve(null))
            .then(variantResponse => {
              if (variantResponse) {
                console.log('[SW] ✅ VARIANT HIT (offline OK)');
                return variantResponse;
              }

              // Aucun cache trouvé - essayer le réseau en dernier recours
              console.log('[SW] 🌐 Trying network as last resort:', event.request.url);

              return fetch(event.request, {
                mode: 'cors',
                credentials: 'omit'
              })
              .then(networkResponse => {
                if (networkResponse && networkResponse.status === 200) {
                  console.log('[SW] ✅ Network success, caching:', event.request.url);
                  cache.put(event.request, networkResponse.clone());
                  return networkResponse;
                }
                throw new Error('Network response invalid');
              })
              .catch(err => {
                console.error('[SW] ❌ TOTAL FAILURE (mode avion complet?):', err.message);

                // Mode avion complet - retourner une réponse offline
                return cache.match('/proteodies/index.html')
                  .then(fallback => {
                    if (fallback) {
                      console.log('[SW] ✅ Returning index.html fallback');
                      return fallback;
                    }

                    // Vraiment rien dans le cache
                    return new Response(
                      '<!DOCTYPE html><html><body><h1>Mode Offline</h1><p>Cache non disponible. Veuillez ouvrir l\'app avec connexion une première fois.</p></body></html>',
                      {
                        status: 503,
                        statusText: 'Service Unavailable',
                        headers: { 'Content-Type': 'text/html' }
                      }
                    );
                  });
              });
            });
          });
      })
  );
});
