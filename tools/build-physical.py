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
            return {'p': [round(a[0] + t * (b[0] - a[0]), 1),
                          round(a[1] + t * (b[1] - a[1]), 1)],
                    'a': round(ang, 1)}
        acc += d
    return None


def to_path(runs, closed=False):
    out = []
    for r in runs:
        out.append('M' + 'L'.join('%.1f %.1f' % (x, y) for x, y in r) + ('Z' if closed else ''))
    return ''.join(out)


# ------------------------------------------------------------------ features

# Natural Earth splits each great river into locally-named segments; these are
# the segment names that make up one continuous course, upstream first.
RIVERS = [
    ('Yarlung Tsangpo', 'Brahmaputra',  ['Maquan', 'Yarlung', 'Dihang', 'Brahmaputra'], 1),
    ('Ma Chu',          'Yellow River', ['Huang'],                                      1),
    ('Dri Chu',         'Yangtze',      ['Tuotuo', 'Tongtian', 'Jinsha', 'Chang Jiang'],1),
    ('Za Chu',          'Mekong',       ['Za', 'Lancang', 'Mekong'],                    1),
    ('Ngul Chu',        'Salween',      ['Nu', 'Salween'],                              1),
    ('Sengge Khabab',   'Indus',        ['Shiquan', 'Indus'],                           1),
    ('Langchen Khabab', 'Sutlej',       ['Sutlej'],                                     0),
    ('Macha Khabab',    'Karnali',      ['Ghaghara', 'Ghäghara'],                  0),
]

LAKES = [
    ('Tso Ngonpo',   'Qinghai Lake', 'Qinghai Hu'),
    ('Namtso',       'Nam Co',       'Nam Co'),
    ('Siling Tso',   'Siling Co',    'Siling Co'),
    ('Yamdrok Tso',  'Yamdrok',      'Yamzho Yumco'),
    ('Mapham Yutso', 'Manasarovar',  'Mapam Yumco'),
]

# Range spines, west to east (or north to south).  Natural Earth ships no range
# centrelines, so these are drawn by hand from the ranges' mapped crests -- they
# carry the label, they are not a claim about exact extent.
RANGES = [
    ('Himalaya', 0.45, [(74.8,35.2),(76.0,34.0),(77.5,32.8),(79.0,31.6),(80.5,30.8),(82.0,30.2),
                  (84.0,29.5),(86.0,28.6),(87.5,28.1),(89.0,27.9),(90.5,28.0),(92.0,28.3),
                  (93.5,28.8),(95.0,29.3),(95.8,29.6)]),
    ('Karakoram', 0.45, [(74.8,36.0),(75.8,35.9),(76.8,35.7),(77.8,35.5),(78.6,35.2)]),
    ('Kunlun', 0.45, [(76.0,36.4),(78.0,36.2),(80.5,35.9),(83.0,35.7),(85.5,35.9),(88.0,36.2),
                (90.5,36.5),(93.0,36.4),(95.5,36.1),(97.5,35.8)]),
    ('Gangdise', 0.45, [(80.5,31.4),(82.5,31.2),(84.5,31.0),(86.5,30.8),(88.5,30.6),(90.0,30.5)]),
    ('Nyenchen Tanglha', 0.78, [(90.0,30.4),(91.5,30.3),(93.0,30.4),(94.3,30.0),(95.2,29.8)]),
    ('Tanggula', 0.22, [(89.5,33.4),(91.5,33.2),(93.5,32.9),(95.5,32.6),(97.0,32.3)]),
    ('Bayan Har', 0.18, [(96.0,34.7),(97.5,34.5),(99.0,34.3),(100.5,34.1)]),
    ('Amnye Machen', 0.15, [(98.9,35.0),(99.5,34.8),(100.1,34.6)]),
    ('Qilian', 0.45, [(94.5,38.9),(96.5,38.7),(98.5,38.2),(100.5,37.6),(102.0,37.0)]),
    ('Hengduan', 0.72, [(98.6,31.5),(98.9,30.0),(99.2,28.5),(99.6,27.2)]),
]

PEAKS = [
    ('Chomolungma', 'Everest',      86.925, 27.988),
    ('Gang Rinpoche', 'Kailash',    81.312, 31.067),
    ('Namcha Barwa', 'Namcha Barwa',95.055, 29.628),
    ('Amnye Machen', 'Amnye Machen',99.478, 34.828),
]

BOX = (-40.0, -40.0, 1220.0, 785.0)      # viewBox plus a little slack
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

    rivers_src = json.load(open(os.path.join(HERE, 'ne_10m_rivers_lake_centerlines.geojson')))
    lakes_src = json.load(open(os.path.join(HERE, 'ne_10m_lakes.geojson')))

    out = {'rivers': [], 'lakes': [], 'ranges': [], 'peaks': []}

    for bo, en, names, main_stem in RIVERS:
        runs = []
        for feat in rivers_src['features']:
            if feat['properties'].get('name') not in names:
                continue
            geom = feat['geometry']
            parts = [geom['coordinates']] if geom['type'] == 'LineString' else geom['coordinates']
            for part in parts:
                pts = [project(lo, la) for lo, la in part]
                for run in clip_runs(pts, BOX):
                    runs.append(simplify(run, TOL_RIVER))
        if runs:
            out['rivers'].append({'bo': bo, 'en': en, 'main': main_stem,
                                  'd': to_path(runs), 'lab': label_anchor(runs)})

    for bo, en, ne_name in LAKES:
        runs = []
        for feat in lakes_src['features']:
            if feat['properties'].get('name') != ne_name:
                continue
            geom = feat['geometry']
            polys = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
            for poly in polys:
                pts = [project(lo, la) for lo, la in poly[0]]
                runs.append(simplify(pts, TOL_LAKE))
        if runs:
            out['lakes'].append({'bo': bo, 'en': en, 'd': to_path(runs, closed=True)})

    for name, frac, spine in RANGES:
        pts = simplify([project(lo, la) for lo, la in spine], TOL_RANGE)
        out['ranges'].append({'en': name, 'd': to_path([pts]),
                              'lab': label_anchor([pts], frac)})

    for bo, en, lon, lat in PEAKS:
        x, y = project(lon, lat)
        out['peaks'].append({'bo': bo, 'en': en, 'p': [round(x, 1), round(y, 1)]})

    json.dump(out, sys.stdout, ensure_ascii=False, separators=(',', ':'))
    sys.stderr.write('rivers %d  lakes %d  ranges %d  peaks %d\n'
                     % (len(out['rivers']), len(out['lakes']),
                        len(out['ranges']), len(out['peaks'])))


if __name__ == '__main__':
    main()
