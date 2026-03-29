const CACHE_NAME = "leazy-jinn-empire-v21";
const SHELL = [
  "/login",
  "/company/portal",
  "/manifest.json",
  "/service-worker.js",
  "/frontend-assets/agent.css",
  "/frontend-assets/agent.js",
  "/frontend-assets/empire-pages.css",
  "/frontend-assets/empire-pages.js",
  "/frontend-assets/login.css",
  "/frontend-assets/login.js",
  "/frontend-assets/leazy.css",
  "/frontend-assets/leazy.js",
  "/frontend-assets/techbuzz-systems.html",
  "/frontend-assets/network.html",
  "/frontend-assets/ats.html",
  "/frontend-assets/leazy-icon.svg",
  "/media",
  "/frontend-assets/neural-panel.js",
  "/neural",
  "/frontend-assets/intel-panel.js",
  "/frontend-assets/accounts-command.js",
  "/frontend-assets/brain-accounts.css",
  "/frontend-assets/brain-hierarchy.js",
  "/frontend-assets/art/core-sigil.svg",
  "/frontend-assets/art/brain-expand.svg",
  "/frontend-assets/art/brain-grow.svg",
  "/frontend-assets/art/brain-develop.svg",
  "/frontend-assets/art/brain-protect.svg",
  "/frontend-assets/media/nebula-crown.mp4",
  "/frontend-assets/media/nebula-orbit.mp4",
  "/frontend-assets/media/nebula-sanctum.mp4",
];

function isProtectedPage(url) {
  const path = new URL(url).pathname;
  return ["/leazy", "/agent", "/network", "/ats"].some(prefix => path === prefix || path.startsWith(prefix + "/"));
}

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  if (event.request.method !== "GET") return;
  if (isProtectedPage(event.request.url)) {
    event.respondWith(
      fetch(event.request).catch(() => caches.match("/login"))
    );
    return;
  }
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy)).catch(() => {});
        return response;
      }).catch(() => caches.match("/leazy"));
    })
  );
});
