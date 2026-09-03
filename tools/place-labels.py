#!/usr/bin/env python3
"""Choose where each river and range name sits on its own line.

Eleven names competing with the towns, the region titles and each other is not
something to place by eye, so it is searched: for every feature, how far along
its line the name sits and how far it is pushed off it.

Labels are rotated, so they are compared as oriented rectangles rather than by
their axis-aligned bounds -- an angled name's bounding box is several times its
real footprint, and using it rejects placements that are in fact clear.

Run tools/measure-labels.py first; it writes measured.json with each name's true
size and every obstacle, read from the rendered widget in SVG user units.

    python3 tools/measure-labels.py
    python3 tools/place-labels.py      # writes placement.json

The chosen numbers go back into the RANGES and RIVERS tables in
tools/build-physical.py.
"""
import json, math, os, re, sys, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('bp', os.path.join(HERE, 'build-physical.py'))
bp = importlib.util.module_from_spec(spec); spec.loader.exec_module(bp)

src = open(os.path.join(HERE, os.pardir, 'tibet-three-regions-map.html'), encoding='utf-8').read()
DATA = json.loads(re.search(r'var DATA = (\{.*?\});\n', src, re.S).group(1))
M = json.load(open(os.path.join(HERE, 'measured.json'))); SIZE = M['labels']

GANG = {'Duldza Zalmo gang', 'Tshawa gang', 'Markham gang',
        'Pobar gang', 'Mardza gang', 'Minya gang'}
TIBET = bp.rings_of(DATA['outline'])
KHAM = bp.rings_of(DATA['regions']['kham']['d'])
PAD = 2.5
FRACS = [i / 100 for i in range(4, 97, 2)]
DYS = list(range(-34, -5, 3)) + list(range(8, 35, 3))


def corners(cx, cy, w, h, ang):
    a = math.radians(ang); c, s = math.cos(a), math.sin(a)
    return [(cx + dx * c - dy * s, cy + dx * s + dy * c)
            for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]


def label_quad(anchor, ang, w, h, dy):
    a = math.radians(ang)
    cx = anchor[0] - dy * math.sin(a) + (h * 0.30) * math.sin(a)
    cy = anchor[1] + dy * math.cos(a) - (h * 0.30) * math.cos(a)
    return corners(cx, cy, w + PAD * 2, h + PAD * 2, ang)


def overlap(A, B):
    """Separating-axis test; 0 when the two quads do not touch."""
    for P, Q in ((A, B), (B, A)):
        for i in range(len(P)):
            ex, ey = P[(i + 1) % len(P)][0] - P[i][0], P[(i + 1) % len(P)][1] - P[i][1]
            nx, ny = -ey, ex
            n = math.hypot(nx, ny) or 1; nx, ny = nx / n, ny / n
            pa = [x * nx + y * ny for x, y in P]; pb = [x * nx + y * ny for x, y in Q]
            if max(pa) < min(pb) or max(pb) < min(pa):
                return 0.0
    depth = 1e9
    for P, Q in ((A, B), (B, A)):
        for i in range(len(P)):
            ex, ey = P[(i + 1) % len(P)][0] - P[i][0], P[(i + 1) % len(P)][1] - P[i][1]
            nx, ny = -ey, ex
            n = math.hypot(nx, ny) or 1; nx, ny = nx / n, ny / n
            pa = [x * nx + y * ny for x, y in P]; pb = [x * nx + y * ny for x, y in Q]
            depth = min(depth, min(max(pa) - min(pb), max(pb) - min(pa)))
    return depth * depth


OB = [(o, corners(o['x'] + o['w'] / 2, o['y'] + o['h'] / 2, o['w'], o['h'], 0))
      for o in M['obstacles']]

FEATURES = ([(g['en'], 'range', bp.rings_of(g['d'])) for g in DATA['ranges']] +
            [(r['en'], 'river', bp.rings_of(r['d'])) for r in DATA['rivers']])

placed, chosen = [], {}
for name, kind, runs in sorted(FEATURES, key=lambda r: -SIZE.get(r[0], {'w': 0})['w']):
    if name not in SIZE:
        sys.stderr.write('no measurement for %r, skipped\n' % name); continue
    runs = [r for r in runs if len(r) > 1]
    w, h = SIZE[name]['w'], SIZE[name]['h']
    best = None
    for dy in DYS:
        for f in FRACS:
            lab = bp.label_anchor(runs, f)
            if not lab:
                continue
            Q = label_quad(lab['p'], lab['a'], w, h, dy)
            cost = sum(overlap(Q, q) for _, q in OB) + sum(overlap(Q, q) for q in placed)
            xs = [p[0] for p in Q]; ys = [p[1] for p in Q]
            cx, cy = sum(xs) / 4, sum(ys) / 4
            # the layers are clipped to Tibet, so the names belong inside it too
            if not bp.inside(TIBET, cx, cy):
                cost += 4000
            if name in GANG and not bp.inside(KHAM, cx, cy):
                cost += 150
            cost += abs(f - 0.5) * 25 + abs(abs(dy) - 9) * 4
            if best is None or cost < best[0]:
                best = (cost, f, dy, Q)
    if best is None:
        sys.stderr.write('nowhere to put %r\n' % name); continue
    cost, f, dy, Q = best
    resid = sum(overlap(Q, q) for _, q in OB) + sum(overlap(Q, q) for q in placed)
    placed.append(Q); chosen[name] = [f, dy]
    hits = [o['t'][:16] for o, q in OB if overlap(Q, q) > 0]
    print('  %-20s %-6s frac %.2f  dy %+3d   overlap %6.1f  %s'
          % (name, kind, f, dy, resid, ('hits: ' + ', '.join(hits)) if hits else 'clear'))
json.dump(chosen, open(os.path.join(HERE, 'placement.json'), 'w'))
