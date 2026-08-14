#!/usr/bin/env python3
"""Extract emblem center crops into labeled contact sheets for digit ground-truth.
Usage: python extract_centers.py <page.jpg> <detections.json> <sheet_out.png> [crop_dir]
"""
import sys, os, json, subprocess
import cv2
import numpy as np

def get_detections(page_path, thr=0.6):
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'detect_emblems.py'),
                        page_path, '--thr', str(thr)], capture_output=True, text=True)
    return json.loads(r.stdout)

def main():
    page_path = sys.argv[1]
    sheet_out = sys.argv[2]
    crop_dir = sys.argv[3] if len(sys.argv) > 3 else ''
    det = get_detections(page_path)
    img = cv2.imread(page_path)
    crops = []
    labels = []
    for i, d in enumerate(det['detections']):
        x, y, w, h = d['x'], d['y'], d['w'], d['h']
        # center 55% box
        cx, cy = x + int(w * 0.225), y + int(h * 0.225)
        cw, ch = max(8, int(w * 0.55)), max(8, int(h * 0.55))
        crop = img[cy:cy + ch, cx:cx + cw]
        if crop.size == 0:
            continue
        crop = cv2.resize(crop, (64, 64), interpolation=cv2.INTER_AREA)
        crops.append(crop)
        labels.append(f'{os.path.basename(page_path)[:-4]}.{i}')
        if crop_dir:
            os.makedirs(crop_dir, exist_ok=True)
            cv2.imwrite(os.path.join(crop_dir, f'{labels[-1]}.png'), crop)
    # contact sheet 5 per row with index labels
    cols = 5
    rows = (len(crops) + cols - 1) // cols
    cell = 96
    sheet = np.full((rows * (cell + 20), cols * cell, 3), 255, np.uint8)
    for i, (c, lab) in enumerate(zip(crops, labels)):
        r, col = divmod(i, cols)
        y0, x0 = r * (cell + 20), col * cell
        c = cv2.resize(c, (cell, cell), interpolation=cv2.INTER_AREA)
        sheet[y0:y0 + cell, x0:x0 + cell] = c
        cv2.putText(sheet, lab, (x0, y0 + cell + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    cv2.imwrite(sheet_out, sheet)
    print(f'{len(crops)} crops -> {sheet_out}')

if __name__ == '__main__':
    main()
