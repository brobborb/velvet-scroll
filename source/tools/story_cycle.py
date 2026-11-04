#!/usr/bin/env python3
"""Four extra phone layouts for a Story mode theme, made from its finished landscape stencils:

    python3 story_cycle.py NAME [NAME ...] [--dir ../../story]

Reads NAME-land-light.webp and NAME-land-dark.webp and writes, for each tone:
  NAME-d1-*.webp   top-left scene as a header, bottom-right scene as a footer
  NAME-ct-*.webp   the top centre ornament alone as a header
  NAME-d2-*.webp   top-right scene as a header, bottom-left scene as a footer
  NAME-cb-*.webp   the bottom centre ornament alone as a footer
The reader shows them in that order, one per chapter. Pieces are found on the light drawing; the dark drawing's
pieces are cut from the same places. Prints the header and footer heights the reader needs, as JSON.
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from story_theme import W, H, K, Pen, side, flourish, save

CORNER_H = .135    # a corner scene is at most this share of the page height ...
CORNER_W = .56     # ... and this share of its width
CENTRE_H = .11     # a centre ornament on its own page

def alpha(path):
    return np.asarray(Image.open(path).convert('RGBA').split()[3]).astype(np.float32) / 255

def find_pieces(a):
    """The six pieces of a landscape stencil: four corner scenes and the top and bottom centre ornaments.
    Side rules and other tall, narrow strips at the edges are left out."""
    Hh, Ww = a.shape; on = a > .2
    lab, n = ndimage.label(ndimage.binary_dilation(on, iterations=4))
    boxes = ndimage.find_objects(lab)
    def kind(b):
        h, w = b[0].stop - b[0].start, b[1].stop - b[1].start
        cx, cy = (b[1].start + b[1].stop) / 2, (b[0].start + b[0].stop) / 2
        if w < Ww*.06 and (cx < Ww*.1 or cx > Ww*.9) and (h > Hh*.08 or Hh*.3 < cy < Hh*.7): return None   # a side rule, sprig or its middle star
        if h*w < Ww*Hh*.002: return 'small'
        if Ww*.3 < cx < Ww*.7: return 'ct' if cy < Hh/2 else 'cb'
        return ('tl' if cy < Hh/2 else 'bl') if cx < Ww/2 else ('tr' if cy < Hh/2 else 'br')
    groups = {}
    for i, b in enumerate(boxes):
        if b is None: continue
        k = kind(b)
        if k and k != 'small': groups.setdefault(k, []).append(i + 1)
    pieces = {}
    for k, ids in groups.items():
        bs = [boxes[i - 1] for i in ids]
        y0, y1 = min(b[0].start for b in bs), max(b[0].stop for b in bs)
        if y1 - y0 < Hh*.035: continue                    # only a thin line: no piece
        x0, x1 = min(b[1].start for b in bs), max(b[1].stop for b in bs)
        # small specks (stars, sparks) that sit inside the piece belong to it
        for i, b in enumerate(boxes):
            if b is not None and kind(b) == 'small' and y0 - 20 <= b[0].start and b[0].stop <= y1 + 20 and x0 - 20 <= b[1].start and b[1].stop <= x1 + 20:
                ids.append(i + 1)
        pieces[k] = ((max(y0 - 4, 0), min(y1 + 4, Hh), max(x0 - 4, 0), min(x1 + 4, Ww)), np.isin(lab, ids))
    return pieces

def cut(a, piece, own):
    """This tone's pixels for a piece: its own clusters on the light drawing; on the dark drawing, everything
    near where those clusters are (the night drawing's lines sit in the same places but don't match exactly)."""
    (y0, y1, x0, x1), mask = piece
    if own: return (a * mask)[y0:y1, x0:x1]
    pad = 30; Y0, Y1, X0, X1 = max(y0 - pad, 0), min(y1 + pad, a.shape[0]), max(x0 - pad, 0), min(x1 + pad, a.shape[1])
    near = ndimage.binary_dilation(mask[Y0:Y1, X0:X1], iterations=pad)
    part = a[Y0:Y1, X0:X1] * near
    ys, xs = np.where(part > .05)
    return part[ys.min():ys.max() + 1, xs.min():xs.max() + 1] if len(ys) else part

def scaled(arr, maxw, maxh):
    k = min(maxw / arr.shape[1], maxh / arr.shape[0])
    im = Image.fromarray((arr*255).astype(np.uint8)).resize((max(1, round(arr.shape[1]*k)), max(1, round(arr.shape[0]*k))), Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255

def paste(canvas, o, x, y):
    canvas[y:y + o.shape[0], x:x + o.shape[1]] = np.maximum(canvas[y:y + o.shape[0], x:x + o.shape[1]], o)

def finish(canvas, p):
    drawn = np.asarray(p.im.filter(ImageFilter.GaussianBlur(.5*K/3)).resize((W, H), Image.LANCZOS)).astype(np.float32)/255
    return np.maximum(canvas, drawn)

def diagonal(top, bottom, top_left):
    """One corner scene at the top, the opposite one at the bottom; the side rules run beside the text."""
    canvas = np.zeros((H, W), np.float32); p = Pen()
    t = scaled(top, W*CORNER_W, H*CORNER_H); b = scaled(bottom, W*CORNER_W, H*CORNER_H)
    paste(canvas, t, 0 if top_left else W - t.shape[1], 0)
    paste(canvas, b, W - b.shape[1] if top_left else 0, H - b.shape[0])
    th, bh = t.shape[0], b.shape[0]
    # the side under the top scene starts below it; the other side runs from the top; the same at the bottom
    for x, flip, under_top, over_bottom in ((40, False, top_left, not top_left), (W - 40, True, not top_left, top_left)):
        y0 = th + 40 if under_top else 70; y1 = H - bh - 40 if over_bottom else H - 70
        side(p, x, y0, y1, 'rule', flip)
    return finish(canvas, p), th + 10, bh + 10

def centre_only(orn, at_top):
    canvas = np.zeros((H, W), np.float32); p = Pen()
    o = scaled(orn, W*.72, H*CENTRE_H)
    if at_top: paste(canvas, o, (W - o.shape[1])//2, 30); th, bh = o.shape[0] + 40, 150; fy = H - 70
    else: paste(canvas, o, (W - o.shape[1])//2, H - 30 - o.shape[0]); th, bh = 150, o.shape[0] + 40; fy = 70
    flourish(p, fy, 'none'); p.star4(W/2, fy, 14)          # the plain flourish at the other end, with a small star
    side(p, 40, th + 30, H - bh - 30, 'rule', False); side(p, W - 40, th + 30, H - bh - 30, 'rule', True)
    return finish(canvas, p), th + 10, bh + 10

def main():
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('names', nargs='+')
    ap.add_argument('--dir', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'story'))
    a = ap.parse_args(); out = {}
    for name in a.names:
        light = alpha(f'{a.dir}/{name}-land-light.webp'); dark = alpha(f'{a.dir}/{name}-land-dark.webp')
        if dark.shape != light.shape: dark = np.asarray(Image.fromarray((dark*255).astype(np.uint8)).resize(light.shape[::-1], Image.LANCZOS)).astype(np.float32)/255
        pc = find_pieces(light); cfg = {}
        for tone, arr in (('light', light), ('dark', dark)):
            own = tone == 'light'; g = lambda k: cut(arr, pc[k], own)
            if all(k in pc for k in ('tl', 'br')): img, th, bh = diagonal(g('tl'), g('br'), True); save(img, f'{a.dir}/{name}-d1-{tone}.webp'); cfg['d1'] = [max(th, cfg.get('d1', [0, 0])[0]), max(bh, cfg.get('d1', [0, 0])[1])]
            if all(k in pc for k in ('tr', 'bl')): img, th, bh = diagonal(g('tr'), g('bl'), False); save(img, f'{a.dir}/{name}-d2-{tone}.webp'); cfg['d2'] = [max(th, cfg.get('d2', [0, 0])[0]), max(bh, cfg.get('d2', [0, 0])[1])]
            if 'ct' in pc: img, th, bh = centre_only(g('ct'), True); save(img, f'{a.dir}/{name}-ct-{tone}.webp'); cfg['ct'] = [max(th, cfg.get('ct', [0, 0])[0]), max(bh, cfg.get('ct', [0, 0])[1])]
            if 'cb' in pc: img, th, bh = centre_only(g('cb'), False); save(img, f'{a.dir}/{name}-cb-{tone}.webp'); cfg['cb'] = [max(th, cfg.get('cb', [0, 0])[0]), max(bh, cfg.get('cb', [0, 0])[1])]
        out[name] = cfg; print(name, cfg, file=sys.stderr)
    print(json.dumps(out))

if __name__ == '__main__':
    main()
