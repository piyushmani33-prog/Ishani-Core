const CACHE_NAME = "leazy-jinn-empire-v46";
const SHELL = [
  "/manifest.json",
  "/service-worker.js",
  "/frontend-assets/agent.css",
  "/frontend-assets/agent.js",
  "/frontend-assets/brain-accounts.css",
  "/frontend-assets/brain-hierarchy.js",
  "/frontend-assets/core.css",
  "/frontend-assets/empire-pages.css",
  "/frontend-assets/empire-pages.js",
  "/frontend-assets/intel-panel.js",
  "/frontend-assets/login.css",
  "/frontend-assets/login.html",
  "/frontend-assets/login.js",
  "/frontend-assets/leazy.css",
  "/frontend-assets/leazy.js",
  "/frontend-assets/navigator.js",
  "/frontend-assets/accounts-command.js",
  "/frontend-assets/public-agent.css",
  "/frontend-assets/public-agent.js",
  "/frontend-assets/ui-auto-repair.js",
  "/frontend-assets/company-portal.html",
  "/frontend-assets/empire-portals.html",
  "/frontend-assets/career.html",
  "/frontend-assets/jobs.html",
  "/frontend-assets/network.html",
  "/frontend-assets/techbuzz-systems.html",
  "/frontend-assets/leazy-icon.svg",
  "/frontend-assets/art/core-sigil.svg",
  "/frontend-assets/art/leazy-icon.svg",
  "/frontend-assets/art/brain-expand.svg",
  "/frontend-assets/art/brain-grow.svg",
  "/frontend-assets/art/brain-develop.svg",
  "/frontend-assets/art/brain-protect.svg",
  "/frontend-assets/visuals/recruitment-intelligence.webp",
  "/frontend-assets/visuals/guardian-battle.webp",
  "/frontend-assets/visuals/guardian-shield.webp",
  "/frontend-assets/visuals/finance-brain.jpg",
  "/frontend-assets/visuals/finance-benefits.jpg",
  "/frontend-assets/visuals/finance-automation.png",
  "/frontend-assets/media/nebula-crown.mp4",
  "/frontend-assets/media/nebula-orbit.mp4",
  "/frontend-assets/media/nebula-sanctum.mp4",
];

function isHtmlNavigation(request) {
  return request.mode === "navigate" || (request.headers.get("accept") || "").includes("text/html");
}

function isProtectedPage(url) {
  const path = new URL(url).pathname;
  const protectedAssets = [
    "/frontend-assets/leazy.html",
    "/frontend-assets/agent.html",
    "/frontend-assets/navigator.html",
    "/frontend-assets/browser.html",
    "/frontend-assets/network-intel.html",
    "/frontend-assets/ats.html",
    "/frontend-assets/hq.html",
    "/frontend-assets/hq-owner.html",
    "/frontend-assets/media.html",
    "/frontend-assets/ide.html",
    "/frontend-assets/mission.html",
    "/frontend-assets/neural.html",
    "/frontend-assets/photon.html",
    "/frontend-assets/research.html",
    "/frontend-assets/spread.html",
  ];
  return protectedAssets.includes(path) || ["/leazy", "/agent/console", "/navigator", "/browser", "/network/intel", "/ats", "/hq", "/ide", "/mission", "/neural", "/photon", "/research", "/spread"].some(prefix => path === prefix || path.startsWith(prefix + "/"));
}

function isLiveDataRequest(url) {
  const path = new URL(url).pathname;
  return path.startsWith("/api/") || path === "/service-worker.js";
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
      fetch(event.request).catch(() => caches.match("/frontend-assets/login.html"))
    );
    return;
  }
  if (isLiveDataRequest(event.request.url)) {
    event.respondWith(fetch(event.request));
    return;
  }
  if (isHtmlNavigation(event.request)) {
    event.respondWith(
      fetch(event.request).then(response => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy)).catch(() => {});
        return response;
      }).catch(() => caches.match(event.request).then(cached => cached || caches.match("/frontend-assets/company-portal.html")))
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
      }).catch(() => caches.match("/frontend-assets/company-portal.html"));
    })
  );
});
