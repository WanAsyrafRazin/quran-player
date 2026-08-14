#!/usr/bin/env python3
"""Deploy: copy regenerated coords into page-coords/, stripped to app schema.
Usage: python deploy.py
"""
import json, os, glob

SRC = 'new'
DST = '../page-coords'

def main():
    n = 0
    for f in sorted(glob.glob(os.path.join(SRC, '*.json')), key=lambda x: int(os.path.basename(x)[:-5])):
        p = int(os.path.basename(f)[:-5])
        d = json.load(open(f))
        if d.get('status') != 'ok' or not d.get('verses'):
            print(f'skip page {p}: status={d.get("status")}')
            continue
        out = {'page': p, 'w': d['w'], 'h': d['h'], 'verses': d['verses']}
        json.dump(out, open(os.path.join(DST, f'{p}.json'), 'w'))
        n += 1
    print(f'deployed {n} page-coords files')

if __name__ == '__main__':
    main()
