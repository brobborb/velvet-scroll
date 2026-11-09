#!/usr/bin/env python3
"""Make a full-colour Story mode theme from TWO landscape paintings (16:9, ideally 2560 x 1440): one painted on
plain light paper for light pages and one on plain black for dark pages, with the pictures in the corners (and
optionally a small ornament at the top and bottom centre).

    python3 story_colour.py NAME light.png dark.png [--out ../../story]

Unlike pencil themes (story_theme.py), the colours are kept: the plain paper or black is taken out, leaving the
pictures on a see-through background, so they sit on whatever page colour the reader has chosen.
Writes NAME-land-{light,dark}.webp and the phone layouts NAME-{d1,d2,ct,cb}-{light,dark}.webp, and prints the
numbers the reader needs (ST_LAND and ST_CYC), as JSON.
"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from story_theme import W, H, find_layout
from story_cycle import find_pieces, CORNER_W, CORNER_H, CENTRE_H

def load(path):
    img = Image.open(path).convert('RGB')
    if img.size != (2560, 1440): img = img.resize((2560, 1440), Image.LANCZOS)
    return np.asarray(img).astype(np.float32)

def colour_to_alpha(rgb):
    """Take the plain background out: each pixel becomes the colour that, laid over the background at some
    opacity, gives what was painted. Faint paper grain is dropped entirely."""
    h, w, _ = rgb.shape
    bg = np.median(rgb[h//3:2*h//3, w//3:2*w//3].reshape(-1, 3), axis=0)
    d = rgb - bg
    den = np.where(d < 0, np.maximum(bg, 1), np.maximum(255 - bg, 40))
    a = np.clip(np.abs(d) / den, 0, 1).max(axis=2)
    a = np.clip((a - .05) / .95, 0, 1)
    safe = np.maximum(a, 1e-3)[..., None]
    col = np.clip((rgb - bg * (1 - safe)) / safe, 0, 255)
    return np.dstack([col, a * 255]).astype(np.float32), bg

def save_rgba(arr, path):
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA').save(path, quality=86, method=6)

def cut(rgba, box, mask, own):
    y0, y1, x0, x1 = box
    if own:
        part = rgba[y0:y1, x0:x1].copy(); part[..., 3] *= mask[y0:y1, x0:x1]; return part
    pad = 30; Y0, Y1, X0, X1 = max(y0 - pad, 0), min(y1 + pad, rgba.shape[0]), max(x0 - pad, 0), min(x1 + pad, rgba.shape[1])
    near = ndimage.binary_dilation(mask[Y0:Y1, X0:X1], iterations=pad)
    part = rgba[Y0:Y1, X0:X1].copy(); part[..., 3] *= near
    ys, xs = np.where(part[..., 3] > 12)
    return part[ys.min():ys.max() + 1, xs.min():xs.max() + 1] if len(ys) else part

def scaled(arr, maxw, maxh):
    k = min(maxw / arr.shape[1], maxh / arr.shape[0])
    # premultiply so the see-through edges don't pick up a fringe when resized
    pm = arr.copy(); pm[..., :3] *= pm[..., 3:4] / 255
    im = Image.fromarray(np.clip(pm, 0, 255).astype(np.uint8), 'RGBA').resize((max(1, round(arr.shape[1]*k)), max(1, round(arr.shape[0]*k))), Image.LANCZOS)
    o = np.asarray(im).astype(np.float32); al = np.maximum(o[..., 3:4], 1e-3)
    o[..., :3] = np.clip(o[..., :3] * 255 / al, 0, 255); return o

def paste(canvas, o, x, y):
    region = canvas[y:y + o.shape[0], x:x + o.shape[1]]
    a = o[..., 3:4] / 255; b = region[..., 3:4] / 255; out_a = a + b * (1 - a)
    region[..., :3] = (o[..., :3] * a + region[..., :3] * b * (1 - a)) / np.maximum(out_a, 1e-3)
    region[..., 3:4] = out_a * 255

def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('name'); ap.add_argument('light'); ap.add_argument('dark')
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'story'))
    a = ap.parse_args()
    light, bgl = colour_to_alpha(load(a.light)); dark, bgd = colour_to_alpha(load(a.dark))
    save_rgba(light, f'{a.out}/{a.name}-land-light.webp'); save_rgba(dark, f'{a.out}/{a.name}-land-dark.webp')
    al = light[..., 3] / 255
    layout, _ = find_layout(al)
    pc = find_pieces(al); cyc = {}
    for tone, arr in (('light', light), ('dark', dark)):
        own = tone == 'light'
        g = lambda k: cut(arr, pc[k][0], pc[k][1], own)
        def write(v, canvas, th, bh):
            save_rgba(canvas, f'{a.out}/{a.name}-{v}-{tone}.webp')
            old = cyc.get(v, [0, 0]); cyc[v] = [max(th, old[0]), max(bh, old[1])]
        for v, top, bot, tl in (('d1', 'tl', 'br', True), ('d2', 'tr', 'bl', False)):
            if top in pc and bot in pc:
                c = np.zeros((H, W, 4), np.float32)
                t = scaled(g(top), W*CORNER_W, H*CORNER_H); b = scaled(g(bot), W*CORNER_W, H*CORNER_H)
                paste(c, t, 0 if tl else W - t.shape[1], 0); paste(c, b, W - b.shape[1] if tl else 0, H - b.shape[0])
                write(v, c, t.shape[0] + 10, b.shape[0] + 10)
        for v in ('ct', 'cb'):
            if v in pc:
                c = np.zeros((H, W, 4), np.float32); o = scaled(g(v), W*.72, H*CENTRE_H); x = (W - o.shape[1])//2
                if v == 'ct': paste(c, o, x, 30); write(v, c, o.shape[0] + 50, 160)
                else: paste(c, o, x, H - 30 - o.shape[0]); write(v, c, 160, o.shape[0] + 50)
    print(f'backgrounds taken out: light {bgl.round()}, dark {bgd.round()}', file=sys.stderr)
    print(json.dumps({a.name: {'land': layout, 'cyc': cyc}}))

if __name__ == '__main__':
    main()
