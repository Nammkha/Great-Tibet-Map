#!/usr/bin/env python3
"""Build the physical-geography layers (rivers, lakes, ranges, peaks) for the widget.

The widget stores geometry already projected into its 1180x745 viewBox, so this
script does the projecting.  The map uses a Lambert Conformal Conic; the exact
parameters were not recorded anywhere, so they are recovered here by fitting the
ten labelled towns, then checked against the stored graticule -- which reproduces
to 0.00-0.11 px in longitude and 0.17-0.58 px in latitude across 25-40 N, the
band Tibet occupies.

Source data is Natural Earth (public domain), which is what lets the result stay
compatible with the project's CC0 dedication.  Download beside this script:

  ne_10m_rivers_lake_centerlines.geojson
  ne_10m_lakes.geojson
      from https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/

Usage:  python3 tools/build-physical.py  >  physical.json
"""
import json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
WIDGET = os.path.join(HERE, os.pardir, 'tibet-three-regions-map.html')

# ---------------------------------------------------------------- projection

# Towns carried by the widget, with their real-world positions.  These are the
# control points the projection is recovered from.
TOWNS = {
    'Lhasa': (91.140, 29.650), 'Shigatse': (88.885, 29.267),
    'Ngari (Gar)': (80.100, 32.500), 'Chamdo': (97.178, 31.137),
    'Dartsedo': (101.964, 30.050), 'Jyekundo': (97.008, 33.010),
    'Gyalthang': (99.706, 27.826), 'Xining': (101.778, 36.617),
    'Labrang': (102.511, 35.196), 'Golog': (100.243, 34.472),
}


def _lcc(lon, lat, p1, p2, lon0):
    r = math.radians
    f = lambda p: math.tan(math.pi / 4 + r(p) / 2)
    n = (math.sin(r(p1)) if abs(p1 - p2) < 1e-9 else
         math.log(math.cos(r(p1)) / math.cos(r(p2))) / math.log(f(p2) / f(p1)))
    big_f = math.cos(r(p1)) * f(p1) ** n / n
    rho = big_f / f(lat) ** n
    theta = n * r(lon - lon0)
    return rho * math.sin(theta), -rho * math.cos(theta)


def fit_projection(data):
    """Recover the conic and the affine that maps it into the viewBox."""
    ties = [(TOWNS[c['name']][0], TOWNS[c['name']][1], c['p'][0], c['p'][1])
            for c in data['cities']]

    def solve(p1, p2, lon0):
        pts = [_lcc(lo, la, p1, p2, lon0) + (x, y) for lo, la, x, y in ties]

        def axis(i, j):                      # least squares  target = a*src + b
            n = len(pts)
            sx = sum(q[i] for q in pts); sy = sum(q[j] for q in pts)
            sxx = sum(q[i] * q[i] for q in pts); sxy = sum(q[i] * q[j] for q in pts)
            a = (n * sxy - sx * sy) / (n * sxx - sx * sx)
            b = (sy - a * sx) / n
            return a, b, sum((a * q[i] + b - q[j]) ** 2 for q in pts)

        ax, bx, ex = axis(0, 2); ay, by, ey = axis(1, 3)
        return math.sqrt((ex + ey) / len(pts)), (ax, bx, ay, by)

    best = None
    for i in range(240, 300):                # standard parallel 1: 24.0 - 30.0 N
        for j in range(360, 420):            # standard parallel 2: 36.0 - 42.0 N
            for k in range(880, 960):        # central meridian:    88.0 - 96.0 E
                err, aff = solve(i / 10, j / 10, k / 10)
                if best is None or err < best[0]:
                    best = (err, i / 10, j / 10, k / 10, aff)
    return best


# --------------------------------------------------------------- geometry ops

def simplify(pts, tol):
    """Douglas-Peucker."""
    if len(pts) < 3:
        return pts
    first, last = pts[0], pts[-1]
    dx, dy = last[0] - first[0], last[1] - first[1]
    span = math.hypot(dx, dy)
    worst, idx = -1.0, 0
    for i in range(1, len(pts) - 1):
        px, py = pts[i]
        if span == 0:
            d = math.hypot(px - first[0], py - first[1])
        else:
            d = abs(dy * px - dx * py + last[0] * first[1] - last[1] * first[0]) / span
        if d > worst:
            worst, idx = d, i
    if worst <= tol:
        return [first, last]
    return simplify(pts[:idx + 1], tol)[:-1] + simplify(pts[idx:], tol)


def clip_runs(pts, box):
    """Split a polyline into the runs that fall inside box, keeping one vertex
    of slack either side so lines leave the frame cleanly."""
    x0, y0, x1, y1 = box
    inside = lambda p: x0 <= p[0] <= x1 and y0 <= p[1] <= y1
    runs, cur = [], []
    for i, p in enumerate(pts):
        if inside(p):
            if not cur and i:
                cur.append(pts[i - 1])
            cur.append(p)
        elif cur:
            cur.append(p); runs.append(cur); cur = []
    if cur:
        runs.append(cur)
    return [r for r in runs if len(r) > 1]


def label_anchor(runs, frac=0.45, core=(120.0, 60.0, 1060.0, 700.0)):
    """A point and tangent angle partway along the longest run, for placing the
    feature's name.  Preference is given to the part of the course that falls in
    the middle of the frame, so labels do not end up jammed against an edge."""
    x0, y0, x1, y1 = core
    inner = [r for r in runs
             if any(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for p in r)] or runs
    run = max(inner, key=lambda r: sum(math.hypot(b[0] - a[0], b[1] - a[1])
                                       for a, b in zip(r, r[1:])))
    seg = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(run, run[1:])]
    total = sum(seg)
    if total <= 0:
        return None
    want, acc = total * frac, 0.0
    for i, d in enumerate(seg):
        if acc + d >= want:
            t = (want - acc) / d if d else 0
            a, b = run[i], run[i + 1]
            ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
            if ang > 90:
                ang -= 180
            if ang < -90:
                ang += 180
            # A name set along a steep crest is barely readable -- the gang of
            # Kham run nearly north-south and were coming out at 70-80 degrees.
            # Lean it towards the crest without following it all the way.
            ang = max(-MAX_TILT, min(MAX_TILT, ang))
            return {'p': [round(a[0] + t * (b[0] - a[0]), 1),
                          round(a[1] + t * (b[1] - a[1]), 1)],
                    'a': round(ang, 1)}
        acc += d
    return None


def rings_of(dstr):
    out = []
    for sub in dstr.split('M')[1:]:
        v = [float(t) for t in re.findall(r'-?\d+\.?\d*', sub)]
        out.append(list(zip(v[0::2], v[1::2])))
    return out


def inside(rings, x, y):
    hit = False
    for ring in rings:
        for i in range(len(ring)):
            x1, y1 = ring[i]; x2, y2 = ring[(i + 1) % len(ring)]
            if (y1 > y) != (y2 > y) and x < x1 + (y - y1) / (y2 - y1) * (x2 - x1):
                hit = not hit
    return hit


def near_edge(rings, x, y, tol=7.0):
    """Inside, or within tol of the boundary.  Chomolungma stands on the
    Tibet-Nepal line and a strict inside-test drops it."""
    if inside(rings, x, y):
        return True
    for ring in rings:
        for i in range(len(ring)):
            ax_, ay_ = ring[i]; bx_, by_ = ring[(i + 1) % len(ring)]
            vx, vy = bx_ - ax_, by_ - ay_
            L = vx * vx + vy * vy
            t = 0.0 if L == 0 else max(0.0, min(1.0, ((x - ax_) * vx + (y - ay_) * vy) / L))
            if math.hypot(ax_ + t * vx - x, ay_ + t * vy - y) <= tol:
                return True
    return False


def clip_to_tibet(runs, tibet):
    """Keep only the parts of each run that fall inside Tibet.  The map is about
    the three regions, so a river is drawn where it runs through them and not
    across the whole frame; the render also clips to the same outline, which
    tidies the cut ends this leaves at vertex granularity."""
    out = []
    for run in runs:
        cur = []
        for i, p in enumerate(run):
            if inside(tibet, p[0], p[1]):
                if not cur and i:
                    cur.append(run[i - 1])
                cur.append(p)
            elif cur:
                cur.append(p); out.append(cur); cur = []
        if len(cur) > 1:
            out.append(cur)
    return [r for r in out if len(r) > 1]


def to_path(runs, closed=False):
    out = []
    for r in runs:
        out.append('M' + 'L'.join('%.1f %.1f' % (x, y) for x, y in r) + ('Z' if closed else ''))
    return ''.join(out)


# ------------------------------------------------------------------ features

# Natural Earth splits each great river into locally-named segments; these are
# the segment names that make up one continuous course, upstream first.
# name in Tibetan script, name in Latin letters, the Natural Earth segments that
# make up the course, whether it draws as a main stem, where the label sits.
# Both names come from the author's list; the international names the segments
# carry (Brahmaputra, Mekong, Yangtze ...) are not shown on the map.  The last
# two numbers are where the label sits along the course and how far off it.
RIVERS = [
    ('ཡར་ཀླུང་གཙང་པོ་', 'Yarlung Tsangpo', ['Maquan', 'Yarlung', 'Dihang', 'Brahmaputra'], 1, 0.82, 17),
    ('རྨ་ཆུ་',           'Ma Chu',          ['Huang'],                                     1, 0.48, 8),
    ('འབྲི་ཆུ་',          'Drichu',          ['Tuotuo', 'Tongtian', 'Jinsha', 'Chang Jiang'],1, 0.08, 8),
    ('རྫ་ཆུ་',           'Za Qu',           ['Za', 'Lancang', 'Mekong'],                   1, 0.96, 11),
    ('རྒྱ་མོ་རྔུལ་ཆུ་',    'Gyalmo Ngulchu',  ['Nu', 'Salween'],                             1, 0.52, -7),
    ('སེང་གེ་ཁ་འབབ་',    'Sangge Khabab',   ['Shiquan', 'Indus'],                          1, 0.92, -16),
    ('གླང་ཆེན་ཁ་འབབ་',   'Langchen Khabab', ['Sutlej'],                                    0, 0.82, 8),
    # Macha Khabab is left out: Natural Earth's Ghaghara segment begins at the
    # border, so only about 15 px of it falls inside Tibet -- too little to read
    # as a river, while its name crowded the corner where the Sengge and Langchen
    # Khabab and Gang Rinpoche already compete. Add it back if a source with the
    # Tibetan headwater turns up.
]

LAKES = [
    ('Tso Ngonpo',   'Qinghai Lake', 'Qinghai Hu'),
    ('Namtso',       'Nam Co',       'Nam Co'),
    ('Siling Tso',   'Siling Co',    'Siling Co'),
    ('Yamdrok Tso',  'Yamdrok',      'Yamzho Yumco'),
    ('Mapham Yutso', 'Manasarovar',  'Mapam Yumco'),
]

# Range spines, west to east (or north to south).  The number after the name is
# how far along the spine the label sits, and the next is how far it is pushed
# off the crest, perpendicular to it.  Both are chosen by tools/place-labels.py,
# which tests the rotated name against the towns, the region titles and the
# other names; they are not hand-picked.  Natural Earth ships no range
# centrelines, so these are drawn by hand from the ranges' mapped crests -- they
# carry the label, they are not a claim about exact extent.
RANGES = [
    # The six gang of Kham -- the ridges of "Chushi Gangdruk", four rivers and
    # six ranges -- then the ranges that wall the plateau.  No dataset carries
    # the gang, so these six spines are placed from where each gang sits between
    # its rivers; they carry the name and are the part of this file most in need
    # of a Khampa eye.
    ('', 'Duldza Zalmo gang', 0.04, -34, [(95.8,33.3),(96.7,32.9),(97.6,32.5),(98.4,32.1)]),
    ('', 'Mardza gang',       0.68, -34, [(98.4,32.9),(99.1,32.6),(99.8,32.4),(100.4,32.1)]),
    ('', 'Pobar gang',        0.70, -10, [(94.4,30.3),(95.3,30.0),(96.2,29.9),(97.0,30.0)]),
    ('', 'Tshawa gang',       0.50, 8, [(97.4,30.5),(97.9,29.7),(98.3,28.9),(98.6,28.1)]),
    ('', 'Markham gang',      0.50, 8, [(98.7,30.6),(99.1,29.8),(99.4,29.0),(99.7,28.2)]),
    ('', 'Minya gang',        0.72, 8, [(100.6,30.8),(101.2,30.3),(101.7,29.7),(102.1,29.1)]),

    ('', 'Himalaya', 0.50, 8, [(74.8,35.2),(76.0,34.0),(77.5,32.8),(79.0,31.6),(80.5,30.8),(82.0,30.2),
                  (84.0,29.5),(86.0,28.6),(87.5,28.1),(89.0,27.9),(90.5,28.0),(92.0,28.3),
                  (93.5,28.8),(95.0,29.3),(95.8,29.6)]),
    ('', 'Karakoram', 0.50, -10, [(74.8,36.0),(75.8,35.9),(76.8,35.7),(77.8,35.5),(78.6,35.2)]),
    ('ཁུ་ནུ་རི་རྒྱུད་', 'Kunlun', 0.50, -10, [(76.0,36.4),(78.0,36.2),(80.5,35.9),(83.0,35.7),(85.5,35.9),(88.0,36.2),
                (90.5,36.5),(93.0,36.4),(95.5,36.1),(97.5,35.8)]),
    ('གངས་ཏི་སེ་', 'Gangdise', 0.50, 8, [(80.5,31.4),(82.5,31.2),(84.5,31.0),(86.5,30.8),(88.5,30.6),(90.0,30.5)]),
    ('གཉན་ཆེན་ཐང་ལྷ་', 'Nyenchen Tanglha', 0.50, -10, [(90.0,30.4),(91.5,30.3),(93.0,30.4),(94.3,30.0),(95.2,29.8)]),
]


# Namcha Barwa and Amnye Machen are not on the author's list, so they carry the
# Latin name only and are marked as having no Tibetan yet.
PEAKS = [                                     # last field: label below (1) or above (-1)
    ('ཇོ་མོ་གླང་མ་',   'Chomo lungma', 86.925, 27.988, -1),
    ('གངས་རིན་པོ་ཆེ་', 'Gang Rinpoche',81.312, 31.067,  1),
    ('',              'Namcha Barwa', 95.055, 29.628,  1),
    ('',              'Amnye Machen', 99.478, 34.828, -1),
]

BOX = (-40.0, -40.0, 1220.0, 785.0)      # viewBox plus a little slack
MAX_TILT = 34.0                          # degrees; steeper names stop reading
TOL_RIVER, TOL_LAKE, TOL_RANGE = 0.8, 0.4, 0.5


def main():
    src = open(WIDGET, encoding='utf-8').read()
    data = json.loads(re.search(r'var DATA = (\{.*?\});\n', src, re.S).group(1))
    err, p1, p2, lon0, (ax, bx, ay, by) = fit_projection(data)
    sys.stderr.write('projection: parallels %.1f/%.1f N, meridian %.1f E, '
                     'town residual %.2f px\n' % (p1, p2, lon0, err))

    def project(lon, lat):
        x, y = _lcc(lon, lat, p1, p2, lon0)
        return ax * x + bx, ay * y + by

    tibet = rings_of(data['outline'])

    rivers_src = json.load(open(os.path.join(HERE, 'ne_10m_rivers_lake_centerlines.geojson')))
    lakes_src = json.load(open(os.path.join(HERE, 'ne_10m_lakes.geojson')))

    out = {'rivers': [], 'lakes': [], 'ranges': [], 'peaks': []}

    for bo, en, names, main_stem, frac, dy in RIVERS:
        runs = []
        for feat in rivers_src['features']:
            if feat['properties'].get('name') not in names:
                continue
            geom = feat['geometry']
            parts = [geom['coordinates']] if geom['type'] == 'LineString' else geom['coordinates']
            for part in parts:
                pts = [project(lo, la) for lo, la in part]
                for run in clip_to_tibet(clip_runs(pts, BOX), tibet):
                    runs.append(simplify(run, TOL_RIVER))
        if runs:
            out['rivers'].append({'bo': bo, 'en': en, 'main': main_stem, 'dy': dy,
                                  'd': to_path(runs), 'lab': label_anchor(runs, frac)})

    for bo, en, ne_name in LAKES:
        runs = []
        for feat in lakes_src['features']:
            if feat['properties'].get('name') != ne_name:
                continue
            geom = feat['geometry']
            polys = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
            for poly in polys:
                pts = [project(lo, la) for lo, la in poly[0]]
                if not any(inside(tibet, x, y) for x, y in pts):
                    continue
                runs.append(simplify(pts, TOL_LAKE))
        if runs:
            out['lakes'].append({'bo': bo, 'en': en, 'd': to_path(runs, closed=True)})

    for bo, name, frac, dy, spine in RANGES:
        pts = simplify([project(lo, la) for lo, la in spine], TOL_RANGE)
        runs = clip_to_tibet([pts], tibet)
        if not runs:
            continue
        out['ranges'].append({'bo': bo, 'en': name, 'd': to_path(runs), 'dy': dy,
                              'lab': label_anchor(runs, frac)})

    for bo, en, lon, lat, side in PEAKS:
        x, y = project(lon, lat)
        if not near_edge(tibet, x, y):
            continue
        out['peaks'].append({'bo': bo, 'en': en, 'p': [round(x, 1), round(y, 1)],
                             'side': side})

    json.dump(out, sys.stdout, ensure_ascii=False, separators=(',', ':'))
    sys.stderr.write('rivers %d  lakes %d  ranges %d  peaks %d\n'
                     % (len(out['rivers']), len(out['lakes']),
                        len(out['ranges']), len(out['peaks'])))


if __name__ == '__main__':
    main()
