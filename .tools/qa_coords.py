#!/usr/bin/env python3
"""QA v2: compare regenerated coords against old coords + emblems.
Checks:
1. Cardinal rule: on a verse's emblem line, no rect extends LEFT of the emblem.
2. Coverage: every OLD text rect (ground truth of where text is) must be
   covered by some NEW rect (y-band overlap + x overlap at the rect's center).
3. No NEW rect should sit on a line where the OLD data had no rect at all
   (unless it's a legitimate line the old data missed — reported, not fatal).
Usage: python qa_coords.py <page.jpg> <new.json> <old.json>
"""
import sys, json, os
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from detect_emblems import load_templates, detect_emblem_matches, nms

def main():
    page_path, new_path, old_path = sys.argv[1], sys.argv[2], sys.argv[3]
    img = cv2.imread(page_path)
    H, W = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    new = json.load(open(new_path))
    old = json.load(open(old_path))
    new_verses, old_verses = new['verses'], old['verses']
    keys = list(new_verses.keys())

    # --- emblems: use the ones the build actually assigned (from the JSON) ---
    emblems = []
    for key in keys:
        e = new.get('emblems', {}).get(key)
        if e:
            emblems.append({'x': e[0], 'y': e[1], 'w': e[2], 'h': e[3]})

    problems = []
    if len(emblems) != len(keys):
        problems.append(f'emblem count {len(emblems)} != verse count {len(keys)}')

    all_new = []
    for key in keys:
        for r in new_verses[key]:
            all_new.append(tuple(r) + (key,))
    for key in keys:
        for r in old_verses.get(key, []):
            all_new  # noop
    # --- check 1: cardinal rule ---
    for i, key in enumerate(keys):
        if i >= len(emblems):
            break
        e = emblems[i]
        e_cy = e['y'] + e['h'] / 2
        for (x, y, w, h) in new_verses[key]:
            r_cy = y + h / 2
            if abs(r_cy - e_cy) < 0.55 * e['h'] and x < e['x'] - 3:
                problems.append(f'{key}: rect x={x} extends LEFT of emblem x={e["x"]} (same line y={y})')

    # --- check 2: old rects covered by new rects ---
    old_rects = [tuple(r) + (k,) for k, rs in old_verses.items() for r in rs]
    uncovered = []
    for (ox, oy, ow, oh, ok) in old_rects:
        oy_c = oy + oh / 2
        ox_c = ox + ow / 2
        covered = False
        for (nx, ny, nw, nh, nk) in all_new:
            if ny <= oy_c <= ny + nh and nx <= ox_c <= nx + nw:
                covered = True
                break
        if not covered:
            uncovered.append((ok, ox, oy, ow, oh))
    if uncovered:
        problems.append(f'{len(uncovered)} old rects NOT covered by new rects:')
        for (ok, ox, oy, ow, oh) in uncovered[:15]:
            problems.append(f'  {ok}: old rect ({ox},{oy},{ow},{oh})')

    # --- check 3: new rects with no old rect on the same line (potential overreach) ---
    old_y_lines = sorted({r[1] for r in old_rects})
    new_y_lines = sorted({r[1] for r in all_new})
    extras = []
    for (nx, ny, nw, nh, nk) in all_new:
        if not any(abs(ny - oy) < 8 for oy in old_y_lines):
            extras.append((nk, nx, ny, nw, nh))
    if extras:
        problems.append(f'{len(extras)} new rects on lines absent from old data (may be OK):')
        for (nk, nx, ny, nw, nh) in extras[:10]:
            problems.append(f'  {nk}: new rect ({nx},{ny},{nw},{nh})')

    if problems:
        print('PROBLEMS:')
        for p in problems[:40]:
            print(' -', p)
        print(f'({len(problems)} issues)')
    else:
        print('OK: all checks passed')

if __name__ == '__main__':
    main()
