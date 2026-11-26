# Handoff — Quran Player

Last rewritten for **v84** (2026-11-26). The older handoff described v24–v35
and a "plain mode" that no longer exists.

## 1. Release rule (do this every time)
- `sw.js` `CACHE = 'quran-player-vNN'` and `index.html` `APP_VERSION = 'vNN'`
  **must be bumped together** on every user-facing change, or installed copies
  keep the old cached shell.
- Check with `python3 .tools/check_version.py` (exit 1 on mismatch).
- Optional pre-commit hook, once per clone: `git config core.hooksPath .githooks`

## 2. Coordination
- Several agents (PC + VPS Hermes) may work on this repo: `git pull` before
  committing, keep commits small, push promptly.
- **The task channel is private.** Never put VPS→PC task docs in this PUBLIC
  repo (GitHub Pages). Tasks live in the private `server-tools/tasks/`.

## 3. Architecture (current)
- Single-file PWA: `index.html` (HTML+CSS+JS) + `sw.js`. No build step.
- Audio: gapless per-verse playback driven by `murattal_timestamps.json` and
  `mujawwad_timestamps.json`; structure in `surah_structure.json`. Audio files
  are stored permanently in IndexedDB by the page (SW caches are wiped per
  version, so the SW never handles audio).
- Mushaf viewer: two scanned-page editions defined in `MUSHAF_SETS`
  (`index.html`): `madani` → `pages-madani_1421/` + `page-coords-madani_1421/`,
  `tajweed` → `pages-tajweed/` + `page-coords-tajweed/`. 604 pages each.
  Coords files hold per-verse geometry used for cloze/reveal.
- Plain (text) mode was removed in v60. `loadMushafFont()` returns null — do
  NOT re-enable QCF font loading.
- Page 604 has a known irregular-layout quirk (~20px cover, acceptable).

## 4. Decisions already made (don't redo)
- QCF fonts in `quran/quran.com-images` are sanitized stubs (hollow glyphs,
  scrambled cmap); the real fonts are not usable from that repo.
- A web-rendered tajweed prototype (imlaei text + tajweed JSON + UthmanicHafs
  font) was reviewed by the owner and **rejected**. Mushaf stays on scanned
  page images + precomputed coords.

## 5. External dependencies
- Audio: `mirrors.quranicaudio.com`, `download.quranicaudio.com`,
  `server12.mp3quran.net`.
- Words API (`MUSHAF_WORDS_API`): `api.qurancdn.com`.
- Page scans/geometry originate from third-party projects; check licences
  before wider distribution.

## 6. Tooling (`.tools/`) — LEGACY coordinate pipeline
`detect_emblems.py`, `build_coords.py`, `qa_coords.py`, `triage_qa.py`,
`deploy.py`, `full_run.sh` were built for the old single `page-coords/` set
(QuranHub tajweed JPGs). That folder was removed from the repo; it is still in
git history before the cleanup commit if the pipeline is ever revived, and the
scripts need their `--old`/`DST` paths pointed at an existing coords folder.
`full_run.sh` also has a hardcoded Windows path. The current app does not use
any of this at runtime.
`check_version.py` is current and in use.
