# TASK — Photo album face-sorting script (from VPS Hermes)

Build this on the PC. Self-contained task — the user approved the approach.

## Goal
Sort a large photo album (~20GB, thousands of photos, one folder) into
subfolders by who appears in each photo:

- `me/` — photos containing the user's face
- `wife/` — photos containing the wife's face
- `both/` — photos containing BOTH faces
- `others/` — photos with faces but neither of them (or no faces)

## Approach (use this — it was chosen over vision-LLM sorting)
Use **face recognition**, NOT Qwen2.5VL (too slow at 20GB scale, weaker at
identity matching). Recommended library: `insightface` with `onnxruntime`
(CPU is fine; it's what photo apps use). Fallback: `face_recognition`
(dlib) if insightface install fails on Windows.

## Steps

1. **Install**: `pip install insightface onnxruntime` (on Windows, use the
   PC's Python. If insightface's model download fails, it fetches from
   GitHub — retry or set `INSIGHTFACE_HOME`). If that's painful, try
   `pip install face_recognition` (dlib wheels should work).

2. **Reference faces**: the user will provide 2 reference photos — one of
   his face, one of his wife's face. Prompt them for the paths. Encode each
   reference face (detect face → extract 512-d embedding). If a reference
   photo has multiple faces, take the LARGEST face (closest to camera).

3. **Scan loop** over the album folder:
   - Support common formats: jpg/jpeg/png/webp/heic (heic needs pillow-heif;
     skip gracefully if the lib is missing and the file can't be read)
   - For each image: detect all faces. For each face embedding, compute
     cosine similarity against both reference embeddings.
   - Thresholds: similarity > 0.45 → match (tune: start 0.45, if too many
     false positives raise to 0.55; if it misses people lower to 0.38).
   - Classification per photo:
     - has_me = any face matches reference 1
     - has_wife = any face matches reference 2
     - has_me && has_wife → `both/`
     - has_me → `me/`
     - has_wife → `wife/`
     - faces present but no match, or zero faces → `others/`

4. **Copy, don't move** (safety). Preserve filenames; if a name collides in
   the destination, append `_1`, `_2`, …

5. **Resumable**: keep a state file (e.g. `sorted_state.json`) listing
   processed files so an interrupted run can continue without re-scanning.

6. **Progress output**: print every 100 photos (`1234 / 21300 — me: 512,
   wife: 380, both: 120, others: 322`). Run in background and notify when
   done.

7. **Verify**: after the run, print a summary + list a few sample matches
   per category so the user can spot-check correctness.

## Output
Final folders created inside the album directory (or a `sorted/` subfolder
if the user prefers). Report the summary to the user.

## Notes
- Ask the user for: album folder path, the 2 reference photo paths, and
  copy-vs-move preference (default: copy).
- If a photo is corrupt/unreadable, record it in a `failed.txt` and continue.
- Don't touch subfolders unless the user says the album is flat — ask.
