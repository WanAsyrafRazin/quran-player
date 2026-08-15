# Handoff — from VPS Hermes (Tencent) to PC Hermes (Qwen2.5VL agent)

Date: 2026-08-15. Read this before touching the repo. Pull first!

## 1. IMPORTANT: SW cache is stale
`sw.js` still has `const CACHE = 'quran-player-v24';` but the app is at v35.
Users may be stuck on old cached code. **Bump the cache string on the next
UI change** (e.g. `quran-player-v36`). Every UI change needs a bump.

## 2. Coordination rule
Two Hermes agents now work on this repo (PC agent + VPS agent). Always
`git pull` before committing, keep commits small, and push promptly so the
other agent never builds on a stale tree.

## 3. QCF font finding (verified, binary-level)
The `QCF_P{NNN}.TTF` files in `quran/quran.com-images` (raw.githubusercontent)
are **sanitized/stub fonts**:
- Standard Arabic codepoints (U+0621–U+064A) map to identical hollow
  rectangles (8 points, 0 off-curve).
- The `code_v1`/`code_v2` presentation forms (U+FB50+) map to a SCRAMBLED
  cmap — glyph names like A/B/C (Latin shapes), not Arabic. Rendering
  `code_v1` text with these fonts produces tofu too.
- The repo's real fonts were removed (King Fahd Complex copyright) and
  replaced with placeholders. The morx/just tables survived, which is why
  classic-mode coords still measure correctly.
- quran.com's REAL font is served from their own CDN:
  `https://quran.com/fonts/quran/hafs/uthmanic_hafs/UthmanicHafs1Ver18.woff2`
  (verified: real glyph curves, renders correctly in browser).

## 4. Tajweed web-render prototype — DISCONTINUED (user rejected)
A prototype was built (imlaei text + quran-tajweed JSON + span color
wrapping + UthmanicHafs font, 15-line justify layout, quran.com palette).
The user reviewed pages 1–5 and rejected it ("the result is terrible").
**Do not pursue this approach.** Plain mode stays on the system Arabic font
with fit-to-width; classic stays on scanned page images + precomputed coords.

## 5. Working architecture (current state)
- Plain mode: system Arabic fallback font (v24 decision — the QCF stub
  fonts must never be loaded), fit-to-width loop, edge-pinned justify,
  surah-final lines centered, printed frame (juz/surah/page corners),
  night toggle.
- Classic mode: precomputed `page-coords/{n}.json` (emblem-anchored,
  regenerated in v25), tall pills, tap-anywhere cloze, reveal-one-by-one.
- `loadMushafFont()` returns null — do NOT re-enable QCF font loading.
- Page 604 has a known irregular-layout quirk (~20px cover, acceptable).

## 6. Data sources (verified working)
- Words API: `https://api.qurancdn.com/api/v4/verses/by_page/{N}?words=true&word_fields=text_uthmani,text_imlaei,code_v1,line_number,position,char_type_name`
- Page images: `https://raw.githubusercontent.com/QuranHub/quran-pages-images/main/easyquran.com/hafs-tajweed/{N}.jpg`
- Tajweed JSON (only if ever needed again): `https://raw.githubusercontent.com/quran/quran-tajweed/master/output/tajweed.hafs.uthmani-pause-sajdah.json` — offsets index into Tanzil-format imlaei text (words + Arabic digit).

## 7. Tooling
`.tools/` (detect_emblems.py, build_coords.py, qa_coords.py, deploy.py,
full_run.sh) is clean and works. `refs/` holds the emblem/basmallah/surah
reference crops. Keep tooling here so both agents share it.

— VPS Hermes (DeepSeek main, Groq/Qwen vision fallback, reachable via
Tailscale 100.104.153.112)
