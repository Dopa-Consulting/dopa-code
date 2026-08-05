const CACHE_NAME = "dopa-code-v1";
const OFFLINE_URL = "/";

self.addEventListener("install", () => {
  (self as unknown as ServiceWorkerGlobalScope).skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  (self as unknown as ServiceWorkerGlobalScope).clients.claim();
});

self.addEventListener("fetch", (event: FetchEvent) => {
  if (event.request.method !== "GET") return;

  const url = new URL(event.request.url);

  // Never cache API calls
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/ws")) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      const fetched = fetch(event.request).then((response) => {
        if (response.ok && response.type === "basic") {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, clone);
          });
        }
        return response;
      });

      return cached || fetched;
    })
  );
});

// ── Background Sync ──

self.addEventListener("sync", (event) => {
  if (event.tag === "flush-pending") {
    event.waitUntil(flushPendingFromSW());
  }
});

async function flushPendingFromSW() {
  // The SW has no direct access to Dexie, so we ask clients to flush.
  // The main thread listens for this message and calls flushPendingActions().
  const clients = await self.clients.matchAll({ type: "window" });
  for (const client of clients) {
    client.postMessage({ type: "bg-sync", tag: "flush-pending" });
  }
}

// ── Message Channel ──

self.addEventListener("message", (event) => {
  if (event.data?.type === "skip-waiting") {
    self.skipWaiting();
  }
});
