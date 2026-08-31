// Quran Player Service Worker — offline support for the app shell only.
// NOTE: audio files are stored PERMANENTLY in IndexedDB by the page (not here),
// because service-worker caches are wiped on every app update. Audio requests
// pass straight through to the network — the page serves blob: URLs from
// IndexedDB when files are saved, so this never blocks offline playback.
const CACHE = 'quran-player-v56';
// All per-ayah page coordinates are precached so classic-mode cloze works offline.
const COORDS = Array.from({ length: 604 }, (_, i) => './page-coords/' + (i + 1) + '.json');
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
// Mushaf page scans: served CACHE-FIRST so classic pages load instantly once
// the user saves them (the OFFLINE MODE button fills the 'quran-pages' cache).
const PAGE_IMG_RE = /raw\.githubusercontent\.com\/QuranHub\/quran-pages-images/;

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => c.addAll(SHELL.concat(COORDS)))
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

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;

  // Audio: pass through untouched (permanent storage lives in IndexedDB, page-side)
  if (AUDIO_RE.test(req.url)) {
    e.respondWith(fetch(req));
    return;
  }

  // Mushaf page scans: cache-first once saved (instant classic-mode loads),
  // network fallback + fill cache when not saved yet.
  if (PAGE_IMG_RE.test(req.url)) {
    e.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open('quran-pages').then((c) => c.put(req, copy));
        return res;
      }))
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
