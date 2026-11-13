/* My Songbook service worker: lets the app open with no internet.
   - The page (index.html): try the network for up to 3 s so a new version arrives right away,
     otherwise open the saved copy. Each successful load refreshes the saved copy.
   - Icons and manifest: saved copy first.
   - Everything else (the GitHub API) is never touched here:
     the app keeps its own copy of the songs and queues changes until it is back online. */
const CACHE = 'msb-shell-v2'; // v2: new icons
const SHELL = ['./', 'manifest.webmanifest', 'icons/icon-192.png', 'icons/icon-512.png', 'icons/icon-maskable-512.png', 'icons/apple-touch-icon.png', 'icons/favicon.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('msb-shell-') && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

function fromNetwork(req, ms) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error('slow')), ms);
    fetch(req, { cache: 'no-store' }).then(r => { clearTimeout(t); resolve(r) }, err => { clearTimeout(t); reject(err) });
  });
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  const scope = new URL(self.registration.scope);
  const isPage = req.mode === 'navigate' || url.pathname === scope.pathname || url.pathname.endsWith('/index.html');
  if (isPage) {
    e.respondWith((async () => {
      const cache = await caches.open(CACHE);
      try {
        const r = await fromNetwork(req, 3000);
        if (r.ok) cache.put('./', r.clone());
        return r;
      } catch (err) {
        const saved = await cache.match('./');
        if (saved) return saved;
        throw err;
      }
    })());
    return;
  }
  e.respondWith(caches.match(req).then(hit => hit || fetch(req)));
});
