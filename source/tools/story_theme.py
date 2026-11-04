#!/usr/bin/env python3
"""Make a Story mode theme from ONE landscape drawing (16:9, ideally 2560 x 1440, pencil or pen on plain light paper).

    python3 story_theme.py NAME drawing.png --border braid --motif star [--out ../../story]

Writes four stencils to the output folder and prints the numbers the reader needs:
  NAME-land-light.webp / NAME-land-dark.webp   the whole drawing, for computers and tablets held sideways
  NAME-slim-light.webp / NAME-slim-dark.webp   for phones and upright tablets: the drawing's top strip, plus
                                               slim side borders and a small bottom flourish drawn here
Light versions are the pencil lines; dark versions thin broad shading so it doesn't glow on dark pages.
Borders: thorn, braid, rope, stars.  Motifs: quatrefoil, star, anchor, moon.
"""
import math, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H, K = 1440, 2560, 3                       # 9:16 canvas; K = supersampling for smooth lines
BX = 40                                        # border centre, from each edge (2.8% of the width)
INK = 215                                      # drawn lines a little lighter than solid, to sit with pencil
PHONE_SIDES = False                            # phone layouts have no side borders (wide screens keep the drawing's own)


def stencil(img):
    a = np.asarray(img).astype(np.float32)
    paper = np.asarray(img.filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(40))).astype(np.float32)
    ink = np.clip((paper - a) / np.maximum(paper - 30, 1), 0, 1)
    return np.clip((ink - 0.06) / 0.94, 0, 1) ** 0.8

class Pen:
    def __init__(s): s.im = Image.new('L', (W*K, H*K), 0); s.d = ImageDraw.Draw(s.im)
    def P(s, x, y): return (x*K, y*K)
    def line(s, pts, w, a=INK):
        s.d.line([s.P(*p) for p in pts], fill=a, width=max(1, round(w*K)), joint='curve')
    def dot(s, x, y, r, a=INK): s.d.ellipse([s.P(x-r, y-r), s.P(x+r, y+r)], fill=a)
    def circle(s, x, y, r, w, a=INK): s.d.ellipse([s.P(x-r, y-r), s.P(x+r, y+r)], outline=a, width=max(1, round(w*K)))
    def poly(s, pts, a=INK): s.d.polygon([s.P(*p) for p in pts], fill=a)
    def taper(s, pts, w0, w1, a=INK):
        for i in range(len(pts)-1):
            w = w0 + (w1-w0)*i/(len(pts)-1); s.line([pts[i], pts[i+1]], w, a); s.dot(*pts[i+1], w/2, a)
    def star4(s, x, y, r, a=INK):
        s.poly([(x, y-r), (x+r*.22, y-r*.22), (x+r, y), (x+r*.22, y+r*.22), (x, y+r), (x-r*.22, y+r*.22), (x-r, y), (x-r*.22, y-r*.22)], a)

# ---------- side patterns: all centred on BX, about 22 px wide, with a hairline rule just inside ----------
def side(p, x, y0, y1, kind, flip):
    inward = 1 if flip else -1          # which way is the page centre
    if kind == 'rule':                  # the plain standard: a fine rule with a small diamond at its middle
        ym = (y0 + y1) / 2
        p.line([(x, y0 + 26), (x, ym - 30)], 1.3); p.line([(x, ym + 30), (x, y1 - 26)], 1.3)
        p.dot(x, ym - 22, 2); p.dot(x, ym + 22, 2)
        p.poly([(x, ym - 15), (x + 3.5, ym - 3.5), (x + 9, ym), (x + 3.5, ym + 3.5), (x, ym + 15), (x - 3.5, ym + 3.5), (x - 9, ym), (x - 3.5, ym - 3.5)])
    else: p.line([(x - inward*17, y0 + 30), (x - inward*17, y1 - 30)], .9, 120)      # the shared hairline rule
    if kind == 'thorn':
        pts = [(x + 4*math.sin(y/38), y) for y in range(int(y0), int(y1), 4)]
        p.taper(pts, 2.2, 2.2)
        for i, y in enumerate(range(int(y0)+20, int(y1)-20, 26)):
            sx = x + 4*math.sin(y/38); d = 1 if i % 2 else -1
            p.taper([(sx, y), (sx + d*7, y - 6), (sx + d*10, y - 11)], 1.6, .3)
        for i, y in enumerate(range(int(y0)+120, int(y1)-120, 210)):   # a small ivy leaf now and then
            sx = x + 4*math.sin(y/38); d = 1 if i % 2 else -1; cx, cy = sx + d*11, y + 4
            leaf = [(cx + math.cos(t)*7*(.55 + .45*abs(math.cos(1.5*t))), cy + math.sin(t)*7*(.55 + .45*abs(math.cos(1.5*t)))) for t in [k/24*2*math.pi for k in range(25)]]
            p.line(leaf, 1.2); p.line([(sx, y), (cx, cy)], 1.1)
    elif kind == 'braid':
        for ph in (0, math.pi):
            pts = [(x + 7*math.sin(y/22 + ph), y) for y in range(int(y0), int(y1), 3)]
            p.taper(pts, 2.0, 2.0)
        for y in range(int(y0) + 35, int(y1) - 20, int(math.pi*22)):        # a bead at every other crossing
            p.dot(x, y, 2.4)
    elif kind == 'rope':
        p.line([(x - 7, y0), (x - 7, y1)], 1.3); p.line([(x + 7, y0), (x + 7, y1)], 1.3)
        for y in range(int(y0) + 4, int(y1) - 4, 9):
            p.taper([(x - 6, y + 5), (x, y + 1), (x + 6, y - 3)], 1.5, 1.1)
    elif kind == 'stars':
        for i, y in enumerate(range(int(y0) + 10, int(y1) - 10, 15)):
            jitter = 3*math.sin(i*1.7)
            if i % 12 == 6: p.star4(x + jitter, y, 9 if i % 24 == 6 else 6)
            else: p.dot(x + jitter, y, 1.5 if i % 3 else 2.1)
    # shared end-caps: a small diamond and a dot at each end
    for (yy, d) in ((y0, -1), (y1, 1)):
        p.poly([(x, yy - 9), (x + 6, yy), (x, yy + 9), (x - 6, yy)]); p.dot(x, yy + d*18, 2.2)

# ---------- the shared bottom flourish, with each theme's motif in the middle ----------
def flourish(p, cy, motif, gap=46):
    cx = W/2
    for m in (1, -1):
        pts = []
        for k in range(120):
            t = k/119; x = cx + m*(gap + t*330); y = cy + math.sin(t*math.pi*2)*7*(1 - t*.5)
            pts.append((x, y))
        p.taper(pts, 3.4, .9)
        ex, ey = pts[-1]; curl = []                       # a curl at the tip
        for k in range(30):
            a = k/29*math.pi*1.6; r = 11*(1 - k/40)
            curl.append((ex + m*(r*math.sin(a)), ey - 11 + r*math.cos(a)))
        p.taper(curl, 1.4, .6)
        for j, dx in enumerate((gap + 349, gap + 366, gap + 380)): p.dot(cx + m*dx, cy + 1, 2.2 - j*.5)
    if motif == 'quatrefoil':
        for dx, dy in ((0, -11), (0, 11), (-11, 0), (11, 0)): p.circle(cx + dx, cy + dy, 11, 1.8)
        p.dot(cx, cy, 3.2)
        p.poly([(cx, cy - 34), (cx + 4, cy - 24), (cx - 4, cy - 24)]); p.poly([(cx, cy + 34), (cx + 4, cy + 24), (cx - 4, cy + 24)])
    elif motif == 'star':
        r1, r2 = 28, 9
        pts = [(cx + math.cos(k*math.pi/4 - math.pi/2)*(r1 if k % 2 == 0 else r2), cy + math.sin(k*math.pi/4 - math.pi/2)*(r1 if k % 2 == 0 else r2)) for k in range(9)]
        p.line(pts, 1.8); p.circle(cx, cy, 33, 1.0, 150); p.dot(cx, cy, 3)
    elif motif == 'anchor':
        p.circle(cx, cy - 26, 6, 1.8)
        p.line([(cx, cy - 20), (cx, cy + 26)], 2.6)
        p.line([(cx - 14, cy - 10), (cx + 14, cy - 10)], 2.2)
        arc = [(cx + math.sin(a)*22, cy + 6 + math.cos(a)*20) for a in [(-1.3 + k*2.6/30) for k in range(31)]]
        p.taper(arc, 2.4, 2.4)
        p.poly([(cx - 22, cy + 6), (cx - 28, cy + 2), (cx - 22, cy - 2)]); p.poly([(cx + 22, cy + 6), (cx + 28, cy + 2), (cx + 22, cy - 2)])
    elif motif == 'moon':
        outer = [(cx - 4 + math.cos(a)*22, cy + math.sin(a)*22) for a in [k/60*2*math.pi for k in range(61)]]
        p.line(outer, 1.8)
        # fill the crescent by painting a disc and carving the inner one
        p.d.ellipse([p.P(cx - 26, cy - 22), p.P(cx + 18, cy + 22)], fill=INK)
        p.d.ellipse([p.P(cx - 16, cy - 22), p.P(cx + 26, cy + 20)], fill=0)
        p.star4(cx + 22, cy - 18, 8); p.star4(cx + 30, cy + 6, 5); p.dot(cx + 14, cy + 20, 1.8)


def find_layout(ink):
    """Measure the landscape drawing: how far the side art reaches in, and the top and bottom centre ornaments."""
    from scipy import ndimage
    Hh, Ww = ink.shape; on = ink > .2
    # the top strip ends at the first fully empty band of rows below the top ornaments
    rows = on.any(axis=1); top_end = None
    for y in range(int(Hh*.08), int(Hh*.6)):
        if not rows[y:y + int(Hh*.02)].any(): top_end = y; break
    if top_end is None:   # side vines run on: take where the inner columns go quiet
        inner = on[:, int(Ww*.1):int(Ww*.9)].any(axis=1)
        top_end = next(y for y in range(int(Hh*.08), Hh) if not inner[y:y + int(Hh*.02)].any())
    # separate clusters (a small gap is enough), each placed by where its middle is
    lab, n = ndimage.label(ndimage.binary_dilation(on, iterations=4))
    boxes = ndimage.find_objects(lab)
    big = [b for b in boxes if (b[0].stop - b[0].start) * (b[1].stop - b[1].start) > Ww*Hh*.002]
    find_layout.lab = lab; find_layout.ids = {id(b): i + 1 for i, b in enumerate(boxes) if b is not None}
    mid = lambda b: (b[1].start + b[1].stop) / 2
    def centred(b): return Ww*.3 < mid(b) < Ww*.7
    tops = [b for b in big if centred(b) and b[0].stop < Hh*.5]; bots = [b for b in big if centred(b) and b[0].start > Hh*.5]
    sides_l = [b for b in big if not centred(b) and mid(b) < Ww*.5]; sides_r = [b for b in big if not centred(b) and mid(b) >= Ww*.5]
    lw = max([b[1].stop for b in sides_l] or [int(Ww*.2)]); rx = min([b[1].start for b in sides_r] or [int(Ww*.8)])
    tx0 = min([b[1].start for b in tops + bots] or [int(Ww*.3)]); tx1 = max([b[1].stop for b in tops + bots] or [int(Ww*.7)])
    # thin rules either side of a centre ornament are too slight to count as clusters; include any ink in the middle band
    for band in ([0, max([b[0].stop for b in tops] or [0])], [min([b[0].start for b in bots] or [Hh]), Hh]):
        cols = np.where(on[band[0]:band[1], int(Ww*.25):int(Ww*.75)].any(axis=0))[0]
        if len(cols): tx0 = int(min(tx0, int(Ww*.25) + cols[0])); tx1 = int(max(tx1, int(Ww*.25) + cols[-1]))
    th = max([b[0].stop for b in tops] or [int(Hh*.08)]); by = min([b[0].start for b in bots] or [int(Hh*.92)])
    pad = 10
    # top corner scenes: side clusters that start near the top (not the full-height side strips)
    corners = ([b for b in sides_l if b[0].start < top_end and b[0].stop < Hh*.6], [b for b in sides_r if b[0].start < top_end and b[0].stop < Hh*.6])
    union = lambda bs: (min(b[1].start for b in bs), 0, max(b[1].stop for b in bs), min(top_end, max(b[0].stop for b in bs))) if bs else None
    find_layout.corners = (union(corners[0]), union(corners[1]))
    find_layout.corner_ids = [{find_layout.ids[id(b)] for b in c} for c in corners]
    # bottom corner scenes, for themes whose scenes sit along the bottom
    bc = ([b for b in sides_l if b[0].start > Hh*.4], [b for b in sides_r if b[0].start > Hh*.4])
    ubot = lambda bs: (min(b[1].start for b in bs), min(b[0].start for b in bs), max(b[1].stop for b in bs), max(b[0].stop for b in bs)) if bs else None
    find_layout.bcorners = (ubot(bc[0]), ubot(bc[1])); find_layout.bcorner_ids = [{find_layout.ids[id(b)] for b in c} for c in bc]
    find_layout.centre = (max(tx0 - pad, 0), 0, min(tx1 + pad, Ww), min(th + pad, Hh//2)) if tops else None
    find_layout.bcentre = (min(b[1].start for b in bots) - pad, min(b[0].start for b in bots) - pad, max(b[1].stop for b in bots) + pad, Hh) if bots else None
    lw, rx = min(lw + pad, Ww//2 - 20), max(rx - pad, Ww//2 + 20)
    # centre ornaments keep their own width; where they overlap a side piece the soft edge fades blend the two
    return dict(W=Ww, H=Hh, lw=lw, rx=rx, tx=max(tx0 - pad, 0), tw=min(tx1 - tx0 + 2*pad, Ww),
                th=min(th + pad, Hh//2), by=max(by - pad, Hh//2), bh=Hh - max(by - pad, Hh//2)), top_end

def rule_sides(land):
    """Remove the drawing's own side strips (tall, narrow clusters at the edges between the corner scenes)
    and draw the standard fine rule with a middle diamond in their place."""
    lab = getattr(find_layout, 'ref_lab', None)
    boxed = lab is not None          # measured on the matching day drawing: clear each strip's whole box (a little wider)
    if not boxed: lab = find_layout.lab
    Hh, Ww = land.shape; out = land.copy()
    from scipy import ndimage
    strips = [(i + 1, b) for i, b in enumerate(ndimage.find_objects(lab)) if b is not None
              and (b[1].stop - b[1].start) < Ww*.08 and (b[0].stop - b[0].start) > Hh*.3 and ((b[1].start + b[1].stop)/2 < Ww*.1 or (b[1].start + b[1].stop)/2 > Ww*.9)]
    k = 3; im = Image.new('L', (Ww*k, Hh*k), 0); d = ImageDraw.Draw(im)
    for i, b in strips:
        if boxed: out[max(b[0].start - 14, 0):b[0].stop + 14, max(b[1].start - 14, 0):b[1].stop + 14] = 0
        else: out[lab == i] = 0
        x = (b[1].start + b[1].stop) / 2; y0, y1 = b[0].start + 10, b[0].stop - 10; ym = (y0 + y1) / 2
        L = lambda pts, w: d.line([(px*k, py*k) for px, py in pts], fill=215, width=round(w*k))
        L([(x, y0), (x, ym - 34)], 1.6); L([(x, ym + 34), (x, y1)], 1.6)
        for yy in (ym - 25, ym + 25, y0 - 7, y1 + 7): d.ellipse([((x - 2.3)*k, (yy - 2.3)*k), ((x + 2.3)*k, (yy + 2.3)*k)], fill=215)
        d.polygon([(x*k, (ym - 17)*k), ((x + 4)*k, (ym - 4)*k), ((x + 10)*k, ym*k), ((x + 4)*k, (ym + 4)*k), (x*k, (ym + 17)*k), ((x - 4)*k, (ym + 4)*k), ((x - 10)*k, ym*k), ((x - 4)*k, (ym - 4)*k)], fill=215)
    drawn = np.asarray(im.filter(ImageFilter.GaussianBlur(.5)).resize((Ww, Hh), Image.LANCZOS)).astype(np.float32)/255
    print(f'replaced {len(strips)} side strips with a plain rule', file=sys.stderr)
    return np.maximum(out, drawn)

def stencil_light_on_dark(img):
    """A drawing made light-on-black: its brightness is the ink, so lit faces, glows and highlights stay as drawn."""
    a = np.asarray(img).astype(np.float32)
    bg = np.asarray(img.filter(ImageFilter.MinFilter(15)).filter(ImageFilter.GaussianBlur(40))).astype(np.float32)
    ink = np.clip((a - bg) / np.maximum(255 - bg, 1), 0, 1)
    return np.clip((ink - 0.04) / 0.96, 0, 1) ** 0.9

def to_dark(light, r=3):
    """Dark pages: keep the linework and drop the broad shading, so nothing glows like a photo negative.
    The reader shows it as gold or silver foil, like the stamping on a cloth-bound book."""
    blur = np.asarray(Image.fromarray((light*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))).astype(np.float32)/255
    lines = np.clip((light - blur)*2.4, 0, 1); lines = np.clip(lines + .12*light, 0, 1); lines[lines < .06] = 0
    return lines

def save(arr, path):
    st = Image.new('LA', (arr.shape[1], arr.shape[0]), (255, 0)); st.putalpha(Image.fromarray((arr*255).astype(np.uint8)))
    st.convert('RGBA').save(path, quality=84, method=6)

def phone_bottom(a, land, crop, layout):
    """Phone layout with the scenes as a footer: the bottom corner scenes enlarged across the bottom of the page,
    and the drawing's top centre ornament as a small header with the shared flourish."""
    import json
    canvas = np.zeros((H, W), np.float32)
    L, Rc = find_layout.bcorners
    cl, cr = crop(L, find_layout.bcorner_ids[0]), crop(Rc, find_layout.bcorner_ids[1]); gap = 30
    k = min((W - gap) / (cl.shape[1] + cr.shape[1]), H*.16 / max(cl.shape[0], cr.shape[0]))
    def place(arr, x, bottom):
        im = Image.fromarray((arr*255).astype(np.uint8)).resize((max(1, round(arr.shape[1]*k)), max(1, round(arr.shape[0]*k))), Image.LANCZOS)
        a2 = np.asarray(im).astype(np.float32)/255; y = bottom - a2.shape[0]
        canvas[y:bottom, x:x + a2.shape[1]] = np.maximum(canvas[y:bottom, x:x + a2.shape[1]], a2); return a2.shape
    hl = place(cl, 0, H)[0]; wr = round(cr.shape[1]*k); hr = place(cr, W - wr, H)[0]
    band_h = max(hl, hr)
    p = Pen(); top_h = 200
    C = find_layout.centre
    if C:
        orn = crop(C); kk = 130 / orn.shape[0]
        im = Image.fromarray((orn*255).astype(np.uint8)).resize((round(orn.shape[1]*kk), 130), Image.LANCZOS)
        o = np.asarray(im).astype(np.float32)/255; ox = (W - o.shape[1])//2; oy = 40
        if o.shape[1] > W - 80:   # a wide ornament: keep its middle
            cut = (o.shape[1] - (W - 80))//2; o = o[:, cut:cut + W - 80]; ox = 40
        canvas[oy:oy + 130, ox:ox + o.shape[1]] = np.maximum(canvas[oy:oy + 130, ox:ox + o.shape[1]], o)
        if o.shape[1] < W*.6: flourish(p, oy + 65, 'none', gap=o.shape[1]//2 + 14)
    else: flourish(p, 90, a.motif)
    y0, y1 = top_h + 20, H - band_h - 40
    if PHONE_SIDES: side(p, BX, y0, y1, a.border, False); side(p, W - BX, y0, y1, a.border, True)
    drawn = np.asarray(p.im.filter(ImageFilter.GaussianBlur(.5*K/3)).resize((W, H), Image.LANCZOS)).astype(np.float32)/255
    slim = np.maximum(canvas, drawn)
    nm = 'foot' if a.alt else 'slim'
    if a.tone == 'dark': save(slim, f'{a.out}/{a.name}-{nm}-dark.webp')
    else:
        save(slim, f'{a.out}/{a.name}-{nm}-light.webp')
        if a.tone == 'both': save(to_dark(slim), f'{a.out}/{a.name}-{nm}-dark.webp')
    cfg = {'land': layout, 'slim': {'W': W, 'H': H, 'th': top_h, 'bh': band_h + 10, 'scenes': 'bottom'}}
    print(json.dumps({a.name + ('' if a.tone == 'both' else '/' + a.tone): cfg}))
    print(f'portrait footer {round(100*band_h/H,1)}% of the height', file=sys.stderr)

def phone_centre(a, land, crop, layout):
    """Phone layout from the two centre ornaments: the top one enlarged as a header, the bottom one as a footer."""
    import json
    canvas = np.zeros((H, W), np.float32)
    def put(arr, maxw, maxh, y=None, bottom=None):
        k = min(maxw / arr.shape[1], maxh / arr.shape[0])
        im = Image.fromarray((arr*255).astype(np.uint8)).resize((max(1, round(arr.shape[1]*k)), max(1, round(arr.shape[0]*k))), Image.LANCZOS)
        o = np.asarray(im).astype(np.float32)/255; x = (W - o.shape[1])//2
        if y is None: y = bottom - o.shape[0]
        canvas[y:y + o.shape[0], x:x + o.shape[1]] = np.maximum(canvas[y:y + o.shape[0], x:x + o.shape[1]], o); return o.shape[0]
    top_h = 30 + put(crop(find_layout.centre), W*.62, H*.14, y=30)
    bc = find_layout.bcentre
    bot_h = put(crop(bc), W - 120, H*.08, bottom=H - 30) + 30 if bc else 0
    p = Pen()
    if not bc: flourish(p, H - 70, a.motif); bot_h = 150
    y0, y1 = top_h + 40, H - bot_h - 40
    if PHONE_SIDES: side(p, BX, y0, y1, a.border, False); side(p, W - BX, y0, y1, a.border, True)
    drawn = np.asarray(p.im.filter(ImageFilter.GaussianBlur(.5*K/3)).resize((W, H), Image.LANCZOS)).astype(np.float32)/255
    out = np.maximum(canvas, drawn)
    if a.tone == 'dark': save(out, f'{a.out}/{a.name}-mid-dark.webp')
    else:
        save(out, f'{a.out}/{a.name}-mid-light.webp')
        if a.tone == 'both': save(to_dark(out), f'{a.out}/{a.name}-mid-dark.webp')
    print(json.dumps({a.name: {'mid': {'th': top_h + 10, 'bh': bot_h + 10}}}))

def main():
    import argparse, json, os
    ap = argparse.ArgumentParser(); ap.add_argument('name'); ap.add_argument('image')
    ap.add_argument('--border', default='braid', choices=['rule', 'thorn', 'braid', 'rope', 'stars'])
    ap.add_argument('--motif', default='star', choices=['quatrefoil', 'star', 'anchor', 'moon'])
    ap.add_argument('--tone', default='both', choices=['both', 'light', 'dark'],
                    help='both: a dark-on-light drawing, dark files made from it; light: write only the light files; '
                         'dark: the image is drawn light-on-black for dark pages, used as drawn (its own lighting is kept)')
    ap.add_argument('--phone-scenes', default='top', choices=['top', 'bottom', 'centre'],
                    help='which corner scenes make the phone band: top (a header) or bottom (a footer, with the centre ornament as a small header)')
    ap.add_argument('--alt', action='store_true',
                    help='with --phone-scenes bottom: write only the footer layout, as NAME-foot-*, as an alternative to the header layout')
    ap.add_argument('--layout-from', default=None,
                    help='measure pieces on this drawing instead (the matching light version), for a dark drawing whose lines join its scenes')
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'story'))
    a = ap.parse_args()
    img = Image.open(a.image).convert('L')
    if img.size != (2560, 1440): img = img.resize((2560, round(2560 * img.height / img.width)), Image.LANCZOS)
    land = stencil(img) if a.tone != 'dark' else stencil_light_on_dark(img)
    if a.layout_from:
        ref = Image.open(a.layout_from).convert('L')
        if ref.size != (2560, 1440): ref = ref.resize((2560, round(2560 * ref.height / ref.width)), Image.LANCZOS)
        layout, top_end = find_layout(stencil(ref)); find_layout.ref_lab = find_layout.lab
        # the pieces' own pixels come from this drawing: everything inside each measured box
        find_layout.lab = np.ones_like(find_layout.lab); find_layout.corner_ids = [{1}, {1}]; find_layout.bcorner_ids = [{1}, {1}]
    else: layout, top_end = find_layout(land)
    if a.border == 'rule': land = rule_sides(land)
    if a.alt or a.phone_scenes == 'centre': pass
    elif a.tone == 'dark': save(land, f'{a.out}/{a.name}-land-dark.webp')
    else:
        save(land, f'{a.out}/{a.name}-land-light.webp')
        if a.tone == 'both': save(to_dark(land), f'{a.out}/{a.name}-land-dark.webp')
    # portrait: the two top corner scenes, enlarged to fill the page width; the top centre ornament moves to the
    # middle of the bottom flourish, so the drawing's own motif ties top and bottom together
    def crop(box, ids=None):
        x0, y0, x1, y1 = box; part = land[y0:y1, x0:x1]
        if ids: part = part * np.isin(find_layout.lab[y0:y1, x0:x1], list(ids))   # only this scene's own lines
        return part
    if a.phone_scenes == 'bottom': return phone_bottom(a, land, crop, layout)
    if a.phone_scenes == 'centre': return phone_centre(a, land, crop, layout)
    L, Rc = find_layout.corners; canvas = np.zeros((H, W), np.float32)
    if L and Rc:
        cl, cr = crop(L, find_layout.corner_ids[0]), crop(Rc, find_layout.corner_ids[1]); gap = 30
        k = min((W - gap) / (cl.shape[1] + cr.shape[1]), H*.16 / max(cl.shape[0], cr.shape[0]))
        def place(arr, x, y):
            im = Image.fromarray((arr*255).astype(np.uint8)).resize((max(1, round(arr.shape[1]*k)), max(1, round(arr.shape[0]*k))), Image.LANCZOS)
            a2 = np.asarray(im).astype(np.float32)/255; canvas[y:y + a2.shape[0], x:x + a2.shape[1]] = np.maximum(canvas[y:y + a2.shape[0], x:x + a2.shape[1]], a2); return a2.shape
        hl = place(cl, 0, 0)[0]; wr = round(cr.shape[1]*k); hr = place(cr, W - wr, 0)[0]
        band_h = max(hl, hr)
    else:   # no separate corners: use the whole top strip
        strip = land[:top_end]; band = Image.fromarray((strip*255).astype(np.uint8)).resize((W, round(strip.shape[0]*W/strip.shape[1])), Image.LANCZOS)
        canvas[:band.size[1]] = np.asarray(band).astype(np.float32)/255; band_h = band.size[1]
    p = Pen(); y0, y1 = band_h + 40, H - 150
    if PHONE_SIDES: side(p, BX, y0, y1, a.border, False); side(p, W - BX, y0, y1, a.border, True)
    C = find_layout.centre
    if C:
        orn = crop(C); kk = 120 / orn.shape[0]
        im = Image.fromarray((orn*255).astype(np.uint8)).resize((round(orn.shape[1]*kk), 120), Image.LANCZOS)
        o = np.asarray(im).astype(np.float32)/255; ox = (W - o.shape[1])//2; oy = H - 70 - 60
        canvas[oy:oy + 120, ox:ox + o.shape[1]] = np.maximum(canvas[oy:oy + 120, ox:ox + o.shape[1]], o)
        flourish(p, H - 70, 'none', gap=o.shape[1]//2 + 14)
    else: flourish(p, H - 70, a.motif)
    drawn = np.asarray(p.im.filter(ImageFilter.GaussianBlur(.5*K/3)).resize((W, H), Image.LANCZOS)).astype(np.float32)/255
    slim = np.maximum(canvas, drawn)
    if a.tone == 'dark': save(slim, f'{a.out}/{a.name}-slim-dark.webp')
    else:
        save(slim, f'{a.out}/{a.name}-slim-light.webp')
        if a.tone == 'both': save(to_dark(slim), f'{a.out}/{a.name}-slim-dark.webp')
    cfg = {'land': layout, 'slim': {'W': W, 'H': H, 'th': band_h + 10, 'bh': 200}}
    print(json.dumps({a.name + ('' if a.tone == 'both' else '/' + a.tone): cfg}))
    print(f'portrait top band {round(100*band_h/H,1)}% of the height; landscape sides {round(100*layout["lw"]/layout["W"])}% / {round(100*(layout["W"]-layout["rx"])/layout["W"])}%,'
          f' top ornament {round(100*layout["th"]/layout["H"])}%, bottom ornament {round(100*layout["bh"]/layout["H"])}%', file=sys.stderr)

if __name__ == '__main__':
    main()
