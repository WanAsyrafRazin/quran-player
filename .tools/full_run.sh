#!/bin/bash
# Full 604-page run: download missing pages (parallel) + build all coords
cd "/c/Users/A/Desktop/Github-Project/quran-player/.tools" || exit 1
mkdir -p pages new

echo "=== Downloading missing pages (8 parallel streams) ==="
seq 1 604 | xargs -P 8 -I{} bash -c '
  if [ ! -s "pages/{}.jpg" ]; then
    curl -sfL --connect-timeout 10 -o "pages/{}.jpg" "https://raw.githubusercontent.com/QuranHub/quran-pages-images/main/easyquran.com/hafs-tajweed/{}.jpg" 2>/dev/null || echo "FAILED {}" >> dl_failures.txt
  fi
'
echo "Downloads done. Failures: $(wc -l < dl_failures.txt 2>/dev/null || echo 0)"

echo "=== Building coords for all pages ==="
: > build_report.txt
for p in $(seq 1 604); do
  if [ ! -s "pages/$p.jpg" ]; then
    echo "page $p: NO IMAGE" >> build_report.txt
    continue
  fi
  env -u PYTHONPATH -u VIRTUAL_ENV .venv/Scripts/python.exe build_coords.py "pages/$p.jpg" --old "../page-coords/$p.json" > "new/$p.json" 2>/dev/null
  st=$(env -u PYTHONPATH -u VIRTUAL_ENV .venv/Scripts/python.exe -c "import json,sys; d=json.load(open('new/$p.json')); print(d.get('status','?'))" 2>/dev/null)
  if [ "$st" != "ok" ]; then
    echo "page $p: $st" >> build_report.txt
  fi
done
echo "=== SUMMARY ==="
echo "ok pages: $(grep -vc ':' build_report.txt 2>/dev/null || echo 604)"
if [ -s build_report.txt ]; then
  echo "NON-OK PAGES:"
  cat build_report.txt
else
  echo "ALL 604 PAGES OK"
fi
echo "RUN COMPLETE"
