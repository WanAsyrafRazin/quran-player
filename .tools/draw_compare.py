#!/usr/bin/env python3
"""Visual comparison: draw OLD (blue) and NEW (red) verse covers on a page.
Usage: python draw_compare.py <page.jpg> <old.json> <new.json> <out.png>
"""
import sys, json
import cv2

def draw(img, verses, color, label):
    for k, rects in verses.items():
        for (x, y, w, h) in rects:
            cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
    cv2.putText(img, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

def main():
    page, old_p, new_p, out = sys.argv[1:5]
    img = cv2.imread(page)
    old = json.load(open(old_p))
    new = json.load(open(new_p))
    draw(img, old['verses'], (255, 128, 0), 'OLD (orange)')
    draw(img, new['verses'], (0, 0, 255), 'NEW (red)')
    cv2.imwrite(out, img)
    print('saved', out)

if __name__ == '__main__':
    main()
