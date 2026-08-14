// Quran Player Service Worker — offline support
const CACHE = 'quran-player-v10';
const SHELL = [
  './',
  './index.html',
  './manifest.json',
  './surah_structure.json',
  './murattal_timestamps.json',
  './mujawwad_timestamps.json',
  './icon-192-v2.png',
  './icon-512-v2.png'
];
const AUDIO_RE = /mirrors\.quranicaudio\.com|server12\.mp3quran\.net|download\.quranicaudio\.com/;

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => c.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function isAudioRequest(url) {
  return AUDIO_RE.test(url);
}

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = req.url;

  // Audio: cache-first, fill cache on first fetch (playing a surah caches it automatically)
  if (isAudioRequest(url)) {
    e.respondWith(
      caches.match(req).then((cached) => {
        if (cached) return cached;
        return fetch(req).then((res) => {
          if (res && res.status === 200) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy));
          }
          return res;
        });
      })
    );
    return;
  }

  // Navigation: network-first, offline fallback to cached shell
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put('./index.html', copy));
          return res;
        })
        .catch(() => caches.match('./index.html'))
    );
    return;
  }

  // App shell & data: network-first (so updates flow), cache fallback offline
  e.respondWith(
    fetch(req)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      })
      .catch(() => caches.match(req))
  );
});

// Bulk pre-cache of a recitation's audio (from the page UI)
self.addEventListener('message', (e) => {
  const data = e.data || {};
  if (data.type !== 'CACHE_AUDIOS') return;
  const urls = data.urls || [];
  const total = urls.length;
  let done = 0;

  const next = (i) => {
    if (i >= urls.length) {
      e.source.postMessage({ type: 'CACHE_DONE', total, done });
      return;
    }
    const u = urls[i];
    caches.match(u)
      .then((cached) => {
        if (cached) return null;
        return fetch(u).then((res) => {
          if (res && res.status === 200) {
            const copy = res.clone();
            return caches.open(CACHE).then((c) => c.put(u, copy));
          }
          return null;
        });
      })
      .catch(() => null)
      .then(() => {
        done++;
        if (done % 5 === 0 || done === total) {
          e.source.postMessage({ type: 'CACHE_PROGRESS', total, done, current: u });
        }
        next(i + 1);
      });
  };
  next(0);
});
