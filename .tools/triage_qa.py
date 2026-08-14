#!/usr/bin/env python3
"""Triage QA coverage misses across all pages: categorize by miss distance.
A miss < ~12px is a phantom (old rects are taller than the true line pitch);
large misses are real problems.
"""
import json, glob, os, sys
import numpy as np

def analyze(p):
    new = json.load(open(f'new/{p}.json'))
    old = json.load(open(f'../page-coords/{p}.json'))
    if new.get('status') != 'ok':
        return None
    all_new = [(k, x, y, w, h) for k, rs in new['verses'].items() for (x, y, w, h) in rs]
    misses = []
    for k, rs in old['verses'].items():
        for (ox, oy, ow, oh) in rs:
            cx, cy = ox + ow / 2, oy + oh / 2
            best = None
            for (nk, nx, ny, nw, nh) in all_new:
                if ny <= cy <= ny + nh and nx <= cx <= nx + nw:
                    best = 0
                    break
                # distance from old rect center to new rect (vertical)
                dy = max(0, ny - cy, cy - (ny + nh))
                if best is None or dy < best:
                    best = dy
            if best is not None and best > 0:
                misses.append((k, ox, oy, ow, oh, best))
    return misses

tot = {'tiny': 0, 'small': 0, 'real': 0}
real_pages = {}
for p in range(1, 605):
    m = analyze(p)
    if m is None:
        continue
    for (k, ox, oy, ow, oh, dy) in m:
        if dy <= 12:
            tot['tiny'] += 1
        elif dy <= 40:
            tot['small'] += 1
        else:
            tot['real'] += 1
            real_pages.setdefault(p, []).append((k, ox, oy, ow, oh, dy))

print('MISS SUMMARY:', tot)
print('pages with REAL (>40px) misses:', len(real_pages))
for p in sorted(real_pages)[:15]:
    print(f'  page {p}:', real_pages[p][:4])
