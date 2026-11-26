#!/usr/bin/env python3
"""Fail if the version in sw.js (CACHE) and index.html (APP_VERSION) differ.

Both must be bumped together on every user-facing change, otherwise installed
copies of the app keep serving the old cached shell.
Usage: python .tools/check_version.py   (exit 0 = in sync, 1 = mismatch)
"""
import re, sys, pathlib

root = pathlib.Path(__file__).resolve().parent.parent
sw = (root / 'sw.js').read_text(encoding='utf-8')
html = (root / 'index.html').read_text(encoding='utf-8')

m_sw = re.search(r"const CACHE = 'quran-player-(v\d+)'", sw)
m_html = re.search(r"const APP_VERSION = '(v\d+)'", html)

if not m_sw or not m_html:
    print('check_version: could not find version strings '
          f'(sw.js: {bool(m_sw)}, index.html: {bool(m_html)})')
    sys.exit(1)

if m_sw.group(1) != m_html.group(1):
    print(f'VERSION MISMATCH: sw.js={m_sw.group(1)} index.html={m_html.group(1)}\n'
          'Bump both to the same value.')
    sys.exit(1)

print(f'versions in sync: {m_sw.group(1)}')
