// Service worker: tiene in cache la schermata, così lo scanner si apre anche senza rete.
// Le chiamate /api non passano mai dalla cache: se la rete manca falliscono e la pagina le mette in coda.
const CACHE = "wms-scanner-v1";
const SHELL = ["/", "/static/scanner.css", "/static/scanner.js", "/static/manifest.json"];
self.addEventListener("install", (e) => e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())));
self.addEventListener("activate", (e) => e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/api/") || e.request.method !== "GET") return;
  e.respondWith(fetch(e.request).then((r) => { const copy = r.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); return r; })
    .catch(() => caches.match(e.request)));
});
