// Service Worker for Voicebot AI PWA
// Version 1.0.0

const CACHE_VERSION = 'voicebot-v1.0.0';
const CACHE_NAME = `${CACHE_VERSION}`;

// Assets to cache on install
const STATIC_ASSETS = [
    '/chat/',
    '/calendar/',
    '/static/manifest.json',
    '/static/offline.html'
];

// API endpoints to handle with network-first strategy
const API_ROUTES = [
    '/api/voice/auth/',
    '/api/voice/chat/',
    '/api/voice/calendar/'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('[SW] Installing service worker...');

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS.map(url => new Request(url, { credentials: 'same-origin' })));
            })
            .catch((error) => {
                console.error('[SW] Cache installation failed:', error);
            })
    );

    // Activate immediately
    self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating service worker...');

    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME && cacheName.startsWith('voicebot-')) {
                        console.log('[SW] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );

    // Take control immediately
    return self.clients.claim();
});

// Fetch event - handle requests with appropriate strategies
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }

    // Skip chrome extensions and other protocols
    if (!url.protocol.startsWith('http')) {
        return;
    }

    // Skip media files entirely - let browser handle them with range requests
    if (isMediaFile(url.pathname)) {
        return;
    }

    // Determine strategy based on request type
    if (isAPIRequest(url.pathname)) {
        // API requests: Network first, fall back to cache
        event.respondWith(networkFirst(request));
    } else if (isStaticAsset(url.pathname)) {
        // Static assets: Cache first, fall back to network
        event.respondWith(cacheFirst(request));
    } else {
        // Pages: Network first with offline fallback
        event.respondWith(networkFirstWithOffline(request));
    }
});

// Network first strategy (for API calls)
async function networkFirst(request) {
    try {
        const response = await fetch(request);

        // Cache successful responses
        if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }

        return response;
    } catch (error) {
        console.log('[SW] Network failed, trying cache:', request.url);

        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }

        // Return offline response for API calls
        return new Response(JSON.stringify({
            error: 'You are offline. Please check your internet connection.',
            offline: true
        }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}

// Cache first strategy (for static assets)
async function cacheFirst(request) {
    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
        // Update cache in background
        fetch(request).then((response) => {
            if (response.ok) {
                caches.open(CACHE_NAME).then((cache) => {
                    cache.put(request, response);
                });
            }
        }).catch(() => {
            // Ignore network errors for background updates
        });

        return cachedResponse;
    }

    try {
        const response = await fetch(request);

        if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }

        return response;
    } catch (error) {
        console.error('[SW] Failed to fetch asset:', request.url);

        // Return a basic fallback for images
        if (request.destination === 'image') {
            return new Response('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect fill="#ddd" width="200" height="200"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="#999">Offline</text></svg>', {
                headers: { 'Content-Type': 'image/svg+xml' }
            });
        }

        return new Response('Offline', { status: 503 });
    }
}

// Network first with offline fallback (for pages)
async function networkFirstWithOffline(request) {
    try {
        const response = await fetch(request);

        // Cache successful page responses (but not partial content like media)
        if (response.ok && response.status !== 206) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }

        return response;
    } catch (error) {
        console.log('[SW] Network failed for page, checking cache:', request.url);

        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }

        // Return offline page
        const offlinePage = await caches.match('/static/offline.html');
        if (offlinePage) {
            return offlinePage;
        }

        // Fallback offline HTML
        return new Response(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Offline - Voicebot AI</title>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        min-height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        text-align: center;
                        padding: 20px;
                    }
                    .container {
                        max-width: 400px;
                    }
                    .icon {
                        font-size: 80px;
                        margin-bottom: 20px;
                    }
                    h1 {
                        font-size: 28px;
                        margin-bottom: 10px;
                    }
                    p {
                        font-size: 16px;
                        opacity: 0.9;
                        line-height: 1.6;
                    }
                    button {
                        margin-top: 20px;
                        padding: 12px 24px;
                        font-size: 16px;
                        background: white;
                        color: #667eea;
                        border: none;
                        border-radius: 8px;
                        cursor: pointer;
                        font-weight: 600;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="icon">📡</div>
                    <h1>You're Offline</h1>
                    <p>Please check your internet connection and try again.</p>
                    <button onclick="window.location.reload()">Retry</button>
                </div>
            </body>
            </html>
        `, {
            status: 503,
            headers: { 'Content-Type': 'text/html' }
        });
    }
}

// Helper functions
function isAPIRequest(pathname) {
    return API_ROUTES.some(route => pathname.startsWith(route));
}

function isMediaFile(pathname) {
    return pathname.endsWith('.webm') ||
           pathname.endsWith('.mp3') ||
           pathname.endsWith('.mp4') ||
           pathname.endsWith('.wav') ||
           pathname.endsWith('.ogg') ||
           pathname.includes('/media/');
}

function isStaticAsset(pathname) {
    // Exclude media files from static asset caching
    if (isMediaFile(pathname)) {
        return false;
    }
    return pathname.startsWith('/static/') ||
           pathname.endsWith('.js') ||
           pathname.endsWith('.css') ||
           pathname.endsWith('.png') ||
           pathname.endsWith('.jpg') ||
           pathname.endsWith('.svg') ||
           pathname.endsWith('.woff') ||
           pathname.endsWith('.woff2');
}

// Background sync for offline actions
self.addEventListener('sync', (event) => {
    console.log('[SW] Background sync triggered:', event.tag);

    if (event.tag === 'sync-messages') {
        event.waitUntil(syncMessages());
    }
});

async function syncMessages() {
    // Placeholder for syncing offline messages when back online
    console.log('[SW] Syncing offline messages...');
    // Implementation would go here
}

// Push notifications
self.addEventListener('push', (event) => {
    console.log('[SW] Push notification received');

    const data = event.data ? event.data.json() : {};
    const title = data.title || 'Voicebot AI';
    const options = {
        body: data.body || 'You have a new notification',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/badge-72x72.png',
        vibrate: [200, 100, 200],
        tag: data.tag || 'default',
        requireInteraction: data.requireInteraction || false,
        data: data.data || {},
        actions: data.actions || []
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification clicked:', event.notification.tag);

    event.notification.close();

    const urlToOpen = event.notification.data?.url || '/chat/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                // Focus existing window if available
                for (const client of clientList) {
                    if (client.url.includes(urlToOpen) && 'focus' in client) {
                        return client.focus();
                    }
                }

                // Open new window
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});

// Message handler for communication with main app
self.addEventListener('message', (event) => {
    console.log('[SW] Message received:', event.data);

    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }

    if (event.data && event.data.type === 'CACHE_URLS') {
        const urls = event.data.urls || [];
        event.waitUntil(
            caches.open(CACHE_NAME).then((cache) => {
                return cache.addAll(urls);
            })
        );
    }
});

console.log('[SW] Service worker loaded successfully');
