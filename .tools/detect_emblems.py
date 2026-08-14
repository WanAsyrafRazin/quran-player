#!/usr/bin/env python3
"""Emblem detector: find verse-end emblems (white + yellow variants) on a mushaf page.
Usage: python detect_emblems.py <page.jpg> [--out crops_dir] [--debug]
Outputs: JSON of detections to stdout, crops saved to crops_dir.
"""
import sys, os, json, argparse
import cv2
import numpy as np

REFS = {
    'white':  os.path.join(os.path.dirname(__file__), 'refs', 'emblem_white.jpg'),
    'yellow': os.path.join(os.path.dirname(__file__), 'refs', 'emblem_yellow.jpg'),
}

def load_templates():
    tmpls = {}
    for name, path in REFS.items():
        t = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if t is None:
            raise SystemExit(f'Cannot load template {path}')
        tmpls[name] = t
    return tmpls

def detect_emblem_matches(img_gray, tmpl, scales=None, thr=0.45):
    """Multi-scale template matching; returns list of (x,y,w,h,score) in img coords."""
    if scales is None:
        scales = np.linspace(0.7, 3.0, 24)
    H, W = img_gray.shape
    th, tw = tmpl.shape
    results = []
    for s in scales:
        wt, ht = max(8, int(round(tw * s))), max(8, int(round(th * s)))
        if wt >= W or ht >= H:
            continue
        t = cv2.resize(tmpl, (wt, ht), interpolation=cv2.INTER_AREA)
        res = cv2.matchTemplate(img_gray, t, cv2.TM_CCOEFF_NORMED)
        ys, xs = np.where(res >= thr)
        for y, x in zip(ys, xs):
            results.append((x, y, wt, ht, float(res[y, x])))
    return results

def nms(results, iou_thr=0.35):
    """Greedy non-max suppression by IoU on (x,y,w,h,score)."""
    if not results:
        return []
    boxes = np.array([[r[0], r[1], r[2], r[3]] for r in results], dtype=float)
    scores = np.array([r[4] for r in results])
    order = scores.argsort()[::-1]
    keep = []
    while order.size:
        i = order[0]
        keep.append(results[int(i)])
        xx1 = np.maximum(boxes[i, 0], boxes[order[1:], 0])
        yy1 = np.maximum(boxes[i, 1], boxes[order[1:], 1])
        xx2 = np.minimum(boxes[i, 0] + boxes[i, 2], boxes[order[1:], 0] + boxes[order[1:], 2])
        yy2 = np.minimum(boxes[i, 1] + boxes[i, 3], boxes[order[1:], 1] + boxes[order[1:], 3])
        inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
        area_i = boxes[i, 2] * boxes[i, 3]
        area_o = boxes[order[1:], 2] * boxes[order[1:], 3]
        union = area_i + area_o - inter
        ovr = np.where(union > 0, inter / np.maximum(union, 1e-6), 0)
        order = order[1:][ovr <= iou_thr]
    return keep

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('page')
    ap.add_argument('--out', default='')
    ap.add_argument('--thr', type=float, default=0.45)
    args = ap.parse_args()

    img = cv2.imread(args.page)
    if img is None:
        raise SystemExit(f'Cannot read {args.page}')
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    H, W = gray.shape
    tmpls = load_templates()

    all_dets = []
    for name, t in tmpls.items():
        dets = detect_emblem_matches(gray, t, thr=args.thr)
        kept = nms(dets)
        for (x, y, w, h, sc) in kept:
            all_dets.append({'type': name, 'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h), 'score': round(sc, 3)})

    # merge near-duplicates from both template types (keep higher score)
    all_dets.sort(key=lambda d: -d['score'])
    merged = []
    for d in all_dets:
        dup = False
        for m in merged:
            dx = min(d['x'] + d['w'], m['x'] + m['w']) - max(d['x'], m['x'])
            dy = min(d['y'] + d['h'], m['y'] + m['h']) - max(d['y'], m['y'])
            if dx > 0.5 * min(d['w'], m['w']) and dy > 0.5 * min(d['h'], m['h']):
                dup = True
                break
        if not dup:
            merged.append(d)
    # Reading order: top→bottom; within the same line band, right→left.
    # Cluster by y-center into bands (tolerance ~12px) so slight y-jitter
    # on the same line doesn't break the order.
    merged.sort(key=lambda d: (d['y'] + d['h'] / 2, d['x']))
    banded = []
    for d in merged:
        cy = d['y'] + d['h'] / 2
        placed = False
        for band in banded:
            if abs(band['cy'] - cy) <= 14:
                band['items'].append(d)
                placed = True
                break
        if not placed:
            banded.append({'cy': cy, 'items': [d]})
    out = []
    for band in sorted(banded, key=lambda b: b['cy']):
        band['items'].sort(key=lambda d: -d['x'])  # right→left within a line
        out.extend(band['items'])
    merged = out

    print(json.dumps({'page': os.path.basename(args.page), 'w': W, 'h': H,
                      'count': len(merged), 'detections': merged}))

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        color = cv2.imread(args.page)
        for i, d in enumerate(merged):
            x, y, w, h = d['x'], d['y'], d['w'], d['h']
            crop = color[max(0, y - 8):y + h + 8, max(0, x - 8):x + w + 8]
            cv2.imwrite(os.path.join(args.out, f"{i:03d}_{d['type']}_{d['score']:.2f}.png"), crop)

if __name__ == '__main__':
    main()
