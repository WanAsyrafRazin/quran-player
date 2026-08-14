#!/usr/bin/env python3
"""Regenerate page-coords JSONs using emblem-anchored verse boundaries.

Layout model (Dar al-Marefa / Madani mushaf):
- Lines flow right-to-left; a verse-end emblem (medallion with ayah number)
  sits at the END of its verse's text ON THE SAME LINE.
- The next verse's text continues to the LEFT of the emblem on that line,
  wrapping to the next line at the right margin.
- Surah headers + basmallah occupy their own ornament lines (skipped).
- Verse N's cloze covers text from after emblem N-1 to emblem N, INCLUDING
  emblem N, and never extends past emblem N's left edge.

Usage: python build_coords.py <page.jpg> [--draw preview.png] [--old old.json]
Output: JSON (same schema as existing page-coords: {page,w,h,verses})
"""
import sys, os, json, argparse
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from detect_emblems import load_templates, detect_emblem_matches, nms

ORNAMENT_REFS = {
    'basmallah': os.path.join(os.path.dirname(__file__), 'refs', 'basmallah.jpg'),
    'heading':   os.path.join(os.path.dirname(__file__), 'refs', 'surah_heading.jpg'),
}

def detect_ornaments(img_gray):
    """Return list of (name, x, y, w, h, score) for basmallah/heading ornaments."""
    found = []
    for name, path in ORNAMENT_REFS.items():
        t = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if t is None:
            continue
        for s in np.linspace(0.6, 2.2, 17):
            wt, ht = max(8, int(t.shape[1] * s)), max(8, int(t.shape[0] * s))
            if wt >= img_gray.shape[1] or ht >= img_gray.shape[0]:
                continue
            tt = cv2.resize(t, (wt, ht), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(img_gray, tt, cv2.TM_CCOEFF_NORMED)
            _, mx, _, mxloc = cv2.minMaxLoc(res)
            if mx >= 0.45:
                found.append((name, mxloc[0], mxloc[1], wt, ht, float(mx)))
    # dedupe by overlap, keep best score per region
    found.sort(key=lambda f: -f[5])
    out = []
    for f in found:
        dup = False
        for g in out:
            dx = min(f[1] + f[3], g[1] + g[3]) - max(f[1], g[1])
            dy = min(f[2] + f[4], g[2] + g[4]) - max(f[2], g[2])
            if dx > 0.4 * min(f[3], g[3]) and dy > 0.4 * min(f[4], g[4]):
                dup = True
                break
        if not dup:
            out.append(f)
    return out

_orn_cache = {}
def ornament_on_line(img_gray, line_cy, pitch):
    """True if a basmallah/surah-heading ornament sits on this line slot."""
    key = id(img_gray)
    if key not in _orn_cache:
        _orn_cache[key] = detect_ornaments(img_gray)
    half = pitch * 0.75
    for (name, x, y, w, h, sc) in _orn_cache[key]:
        ocy = y + h / 2
        if abs(ocy - line_cy) < half:
            return True
    return False

def line_bands_from_old(old_verses, pitch_tol=0.35):
    """Derive line y-bands from existing coords' rect y positions (they're accurate)."""
    ys = set()
    for rects in old_verses.values():
        for (x, y, w, h) in rects:
            ys.add(y)
    ys = sorted(ys)
    bands = [[ys[0], ys[0]]]
    for y in ys[1:]:
        if y - bands[-1][1] <= 6:
            bands[-1][1] = y
        else:
            bands.append([y, y])
    gaps = [bands[i + 1][0] - bands[i][0] for i in range(len(bands) - 1)]
    pitch = float(np.median(gaps)) if gaps else 80.0
    # sanity: gaps shouldn't deviate wildly from pitch
    centers = [ (b[0] + b[1]) / 2 for b in bands ]
    return centers, pitch

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('page')
    ap.add_argument('--old', required=True, help='existing page-coords json')
    ap.add_argument('--draw', default='', help='annotated preview output path')
    ap.add_argument('--thr', type=float, default=0.45)
    args = ap.parse_args()

    img = cv2.imread(args.page)
    if img is None:
        raise SystemExit(f'cannot read {args.page}')
    H, W = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    old = json.load(open(args.old, encoding='utf-8'))
    old_verses = old['verses']

    # margins from old coords (min x and max x+w)
    xs = [x for rects in old_verses.values() for (x, y, w, h) in rects]
    xws = [x + w for rects in old_verses.values() for (x, y, w, h) in rects]
    left_margin, right_margin = min(xs), max(xws)

    # 1) emblems
    tmpls = load_templates()
    dets = []
    for name, t in tmpls.items():
        for (x, y, w, h, sc) in nms(detect_emblem_matches(gray, t, thr=args.thr)):
            dets.append({'type': name, 'x': x, 'y': y, 'w': w, 'h': h, 'score': sc})
    # merge near-duplicates (both types), keep best
    dets.sort(key=lambda d: -d['score'])
    merged = []
    for d in dets:
        if all(not (min(d['x'] + d['w'], m['x'] + m['w']) - max(d['x'], m['x']) > 0.5 * min(d['w'], m['w'])
                    and min(d['y'] + d['h'], m['y'] + m['h']) - max(d['y'], m['y']) > 0.5 * min(d['h'], m['h']))
               for m in merged):
            merged.append(d)
    # reading order: band-cluster by y-center then right->left within band
    merged.sort(key=lambda d: (d['y'] + d['h'] / 2, d['x']))
    banded = []
    for d in merged:
        cy = d['y'] + d['h'] / 2
        for b in banded:
            if abs(b['cy'] - cy) <= 14:
                b['items'].append(d)
                break
        else:
            banded.append({'cy': cy, 'items': [d]})
    emblems = []
    for b in sorted(banded, key=lambda b: b['cy']):
        b['items'].sort(key=lambda d: -d['x'])
        emblems.extend(b['items'])

    keys = list(old_verses.keys())
    nk = len(keys)

    # Note on continuation detection: surah_structure.json maps each verse to
    # ONE page (its start page), so it cannot tell whether a verse spans two
    # pages — the previous structure-based check always returned False.
    # The emblem count itself is the signal: a page whose last verse truly
    # continues has only nk-1 emblems (the last verse's emblem is on the next
    # page). But a MISSING faint emblem (below threshold) also yields nk-1.
    # So prefer nk whenever ANY threshold reaches it (missing-emblem case is
    # far more common than a false positive completing the count); only use
    # nk-1 when no threshold finds all nk emblems (true continuation).

    def detect_all(thr):
        dets = []
        for name, t in tmpls.items():
            for (x, y, w, h, sc) in nms(detect_emblem_matches(gray, t, thr=thr)):
                dets.append({'type': name, 'x': x, 'y': y, 'w': w, 'h': h, 'score': sc})
        # Size filter: real emblems are ~42-55 x 57-79 px at native res.
        # Tiny fragments (21x29) and oversized ornament matches (75x108+)
        # are false positives that corrupt the count.
        dets = [d for d in dets if 28 <= d['w'] <= 70 and 38 <= d['h'] <= 95]
        dets.sort(key=lambda d: -d['score'])
        merged = []
        for d in dets:
            if all(not (min(d['x'] + d['w'], m['x'] + m['w']) - max(d['x'], m['x']) > 0.5 * min(d['w'], m['w'])
                        and min(d['y'] + d['h'], m['y'] + m['h']) - max(d['y'], m['y']) > 0.5 * min(d['h'], m['h']))
                   for m in merged):
                merged.append(d)
        return merged

    # Path A: reading-order ladder — i-th emblem (reading order) ends the
    # i-th verse. Scan ALL thresholds; prefer the first that yields EXACTLY
    # nk (every verse ends on this page). A nk-1 result is ambiguous (true
    # continuation OR a faint missed emblem), so it is kept only as a
    # fallback if no threshold ever reaches nk.
    ladder = None
    ladder_alt = None  # best nk-1 candidate (true continuation fallback)
    for thr in (0.6, 0.55, 0.5, 0.45):
        merged = detect_all(thr)
        merged.sort(key=lambda d: (d['y'] + d['h'] / 2, d['x']))
        banded = []
        for d in merged:
            cy = d['y'] + d['h'] / 2
            for b in banded:
                if abs(b['cy'] - cy) <= 14:
                    b['items'].append(d)
                    break
            else:
                banded.append({'cy': cy, 'items': [d]})
        ordered = []
        for b in sorted(banded, key=lambda b: b['cy']):
            b['items'].sort(key=lambda d: -d['x'])
            ordered.extend(b['items'])
        if len(ordered) == nk and ladder is None:
            ladder = ordered
            break  # exact count found at the highest threshold — done
        if len(ordered) == nk - 1 and ladder_alt is None:
            ladder_alt = ordered
    if ladder is None:
        ladder = ladder_alt

    # Path B: score-ordered positional assignment — for pages where no
    # threshold gives an exact count (missing interior emblems / false
    # positives). Candidates processed by score DESCENDING each claim their
    # nearest unassigned verse within a generous y tolerance.
    ys = sorted({r[1] for rs in old_verses.values() for r in rs})
    pitch_est = float(np.median([ys[i + 1] - ys[i] for i in range(len(ys) - 1)])) if len(ys) > 1 else 80.0
    text_w = right_margin - left_margin
    expected = []
    for key in keys:
        lx, ly, lw, lh = old_verses[key][-1]
        expected.append((key, lx, ly + lh / 2))
    pos = None
    merged = detect_all(0.45)
    assigned = {}
    for d in sorted(merged, key=lambda d: -d['score']):
        dcx, dcy = d['x'] + d['w'] / 2, d['y'] + d['h'] / 2
        best_vi, best_d = None, None
        for vi in range(nk):
            if vi in assigned:
                continue
            _, ex, ey = expected[vi]
            dy = abs(dcy - ey) / pitch_est
            if dy > 2.2:
                continue
            dx = abs(dcx - ex) / text_w
            dist = 3 * dy * dy + dx * dx
            if best_d is None or dist < best_d:
                best_d, best_vi = dist, vi
        if best_vi is not None:
            assigned[best_vi] = d
    unassigned = [i for i in range(nk) if i not in assigned]
    if not unassigned or unassigned == [nk - 1]:
        pos = [assigned[i] for i in range(nk) if i in assigned]

    def validate(cands):
        """Return None if OK, else an error string."""
        prev_cy = -1
        for e in cands:
            cy = e['y'] + e['h'] / 2
            if cy < prev_cy - 20:
                return 'reading-order violation'
            prev_cy = cy
        centers_per_verse = {key: sorted({r[1] + r[3] / 2 for r in rects}) for key, rects in old_verses.items()}
        fails = 0
        for key, e in zip(keys, cands):
            ecy = e['y'] + e['h'] / 2
            if not any(abs(ecy - cy) < 90 for cy in centers_per_verse.get(key, [])):
                fails += 1
        if fails > 2:
            return f'validation fails={fails}/{nk}'
        return None

    emblems, win_banded = None, None
    if ladder is not None and validate(ladder) is None:
        emblems = ladder
    elif pos is not None and validate(pos) is None:
        emblems = pos
    else:
        why = (validate(ladder) if ladder is not None else 'no-count-match')
        return json.dumps({'page': int(os.path.basename(args.page)[:-4]), 'w': W, 'h': H,
                           'status': f'MISMATCH ({why})', 'verses': {}})
    # rebuild bands from the chosen emblems
    banded = []
    for d in emblems:
        cy = d['y'] + d['h'] / 2
        for b in banded:
            if abs(b['cy'] - cy) <= 14:
                b['items'].append(d)
                break
        else:
            banded.append({'cy': cy, 'items': [d]})
    win_banded = banded
    ne = len(emblems)
    has_emblem_all = (ne == nk)

    # 2) line grid from EMBLEM band centers (ground truth). Old coords supply
    # only the verse keys + margins (their y geometry is buggy on some pages).
    banded = []
    for d in emblems:
        cy = d['y'] + d['h'] / 2
        for b in banded:
            if abs(b['cy'] - cy) <= 14:
                b['items'].append(d)
                break
        else:
            banded.append({'cy': cy, 'items': [d]})
    sorted_bands = sorted(banded, key=lambda b: b['cy'])
    band_centers = [b['cy'] for b in sorted_bands]
    band_gaps = [band_centers[i + 1] - band_centers[i] for i in range(len(band_centers) - 1)]
    # Pitch estimate: old-coord line tops give the true line spacing on most
    # pages; emblem band gaps are inflated by multi-line verse spans. Use the
    # old pitch to infer how many lines each emblem gap spans, then take the
    # median of the per-line values (robust to header gaps and bad old data).
    old_ys = sorted({r[1] for rs in old_verses.values() for r in rs})
    old_gaps = [old_ys[i + 1] - old_ys[i] for i in range(len(old_ys) - 1)]
    old_pitch = float(np.median(old_gaps)) if old_gaps else 80.0
    cands = []
    for g in band_gaps:
        k = max(1, int(round(g / old_pitch)))
        cands.append(g / k)
    pitch = float(np.median(cands)) if cands else old_pitch
    if not (25 < pitch < 150):
        pitch = old_pitch
    # build contiguous grid, inserting candidate lines where gaps are large
    grid = {}       # line index -> y center
    orn_idx = set()
    line_idx = 0
    prev_c = band_centers[0]
    grid[0] = prev_c
    band_line = [0]
    for c in band_centers[1:]:
        gap = c - prev_c
        if gap > 1.5 * pitch:
            n_missing = max(1, int(round(gap / pitch)) - 1)
            for k in range(1, n_missing + 1):
                line_idx += 1
                # candidate missing line; decide ornament vs text line by
                # checking the basmallah/surah-heading templates
                cy = prev_c + k * pitch
                if ornament_on_line(gray, cy, pitch):
                    orn_idx.add(line_idx)
        line_idx += 1
        grid[line_idx] = c
        band_line.append(line_idx)
        prev_c = c
    gmin, gmax = min(grid), max(grid)
    # map each emblem to its grid line (via its band)
    band_pos = {}
    for bi, b in enumerate(sorted_bands):
        for d in b['items']:
            band_pos[id(d)] = bi
    for d in emblems:
        d['_line'] = band_line[band_pos[id(d)]]
    def line_top(j):
        # y of the top of line with grid index j
        if j in grid:
            return grid[j] - pitch / 2
        # missing interior line: interpolate from the nearest grid line above
        lo = max((k for k in grid if k < j), default=None)
        if lo is not None:
            return grid[lo] + (j - lo) * pitch - pitch / 2
        if j < gmin:
            return grid[gmin] - pitch / 2 + (j - gmin) * pitch
        return grid[gmax] + pitch / 2 + (j - gmax) * pitch
    def line_span(j):
        return max(0, int(round(line_top(j)))), max(0, int(round(line_top(j) + pitch)))

    # 4) pair emblems with keys; build rects
    verses_out = {}
    for i, key in enumerate(keys):
        surah, ayah = key.split(':')
        prev_surah = keys[i - 1].split(':')[0] if i > 0 else None
        surah_start = (i == 0 and ayah == '1' and surah != '1') or (i > 0 and surah != prev_surah)
        has_emblem = i < ne
        rects = []
        if has_emblem:
            e = emblems[i]
            e_line = e['_line']
        else:
            e = None
            e_line = gmax  # last line (verse continues off-page)

        if surah_start and i > 0:
            # mid-page surah start: the 2 lines right after the previous
            # verse's emblem line are the surah heading + basmallah (ornaments)
            pl = emblems[i - 1]['_line']
            orn_idx.add(pl + 1)
            orn_idx.add(pl + 2)
            start_line = pl + 3
        elif i == 0:
            # page top: text starts at the page's top text line (old coords'
            # smallest rect y is the reliable anchor; negative indices
            # extrapolate above the first emblem band)
            min_old_y = min(r[1] for rs in old_verses.values() for r in rs)
            start_line = int(round((min_old_y + pitch / 2 - band_centers[0]) / pitch))
        else:
            prev_e = emblems[i - 1]
            pl = prev_e['_line']
            if pl < e_line and pl not in orn_idx:
                # piece on prev emblem's line: text continues left of emblem
                y0, y1 = line_span(pl)
                if prev_e['x'] > left_margin + 2:
                    rects.append([left_margin, y0, prev_e['x'] - left_margin, y1 - y0])
            start_line = pl + 1

        # full-width lines strictly between start_line and e_line (skip ornaments)
        for ln in range(start_line, e_line):
            if ln in orn_idx:
                continue
            y0, y1 = line_span(ln)
            rects.append([left_margin, y0, right_margin - left_margin, y1 - y0])

        if has_emblem:
            # piece on emblem line: from emblem left edge to next-emblem-or-margin
            y0, y1 = line_span(e_line)
            # find next emblem to the right on the same line
            right_bound = right_margin
            for d in emblems:
                if d['_line'] == e_line and d['x'] > e['x'] and d['x'] + d['w'] < right_bound:
                    right_bound = d['x'] + d['w']
            rects.append([e['x'], y0, right_bound - e['x'], y1 - y0])
        else:
            # verse continues to next page: cover remaining lines to the
            # bottom of the page's text area (old coords' lowest rect bottom)
            last_old_bottom = max(r[1] + r[3] for rs in old_verses.values() for r in rs)
            n_extra = max(0, int(np.ceil((last_old_bottom - (grid[gmax] + pitch / 2)) / pitch)))
            for ln in range(e_line + 1, gmax + 1 + n_extra):
                if ln in orn_idx:
                    continue
                y0, y1 = line_span(ln)
                rects.append([left_margin, y0, right_margin - left_margin, y1 - y0])

        # merge horizontally-overlapping rects on the same line
        rects.sort(key=lambda r: (r[1], r[0]))
        merged_rects = []
        for r in rects:
            if merged_rects and merged_rects[-1][1] == r[1] and r[0] < merged_rects[-1][0] + merged_rects[-1][2]:
                # extend
                pr = merged_rects[-1]
                new_x = min(pr[0], r[0])
                new_w = max(pr[0] + pr[2], r[0] + r[2]) - new_x
                merged_rects[-1] = [new_x, pr[1], new_w, pr[3]]
            else:
                merged_rects.append(r)
        verses_out[key] = merged_rects

    out = {'page': int(os.path.basename(args.page)[:-4]), 'w': W, 'h': H,
           'status': 'ok',
           'emblems': {key: [e['x'], e['y'], e['w'], e['h']]
                       for key, e in zip(keys, emblems)} if has_emblem_all else {},
           'verses': verses_out}

    if args.draw:
        for (vk, rects) in verses_out.items():
            color = (0, 0, 255)
            for (x, y, w, h) in rects:
                cv2.rectangle(img, (x, y), (x + w, y + h), color, 1)
        for i, d in enumerate(emblems):
            cv2.rectangle(img, (d['x'], d['y']), (d['x'] + d['w'], d['y'] + d['h']), (0, 255, 0), 2)
        cv2.imwrite(args.draw, img)

    return json.dumps(out, default=lambda o: int(o) if isinstance(o, np.integer)
                       else float(o) if isinstance(o, np.floating) else str(o))

if __name__ == '__main__':
    print(main())
