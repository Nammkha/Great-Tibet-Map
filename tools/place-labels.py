"""Choose where each range name sits on its own crest.

Labels are rotated, so they are compared as oriented rectangles (separating-axis
test) rather than by their axis-aligned bounds -- an angled name's bounding box
is several times its real footprint, and using it rejects placements that are
in fact clear."""
import json, math, re, importlib.util
spec=importlib.util.spec_from_file_location('bp','/home/user/Great-Tibet-Map/tools/build-physical.py')
bp=importlib.util.module_from_spec(spec); spec.loader.exec_module(bp)
src=open('/home/user/Great-Tibet-Map/tibet-three-regions-map.html',encoding='utf-8').read()
DATA=json.loads(re.search(r'var DATA = (\{.*?\});\n',src,re.S).group(1))
err,p1,p2,lon0,(ax,bx,ay,by)=bp.fit_projection(DATA)
proj=lambda lo,la:(ax*bp._lcc(lo,la,p1,p2,lon0)[0]+bx, ay*bp._lcc(lo,la,p1,p2,lon0)[1]+by)
M=json.load(open('measured.json')); SIZE=M['labels']

PAD=2.5
def corners(cx,cy,w,h,ang):
    a=math.radians(ang); c,s=math.cos(a),math.sin(a)
    return [(cx+dx*c-dy*s, cy+dx*s+dy*c)
            for dx,dy in ((-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2))]

def label_quad(anchor,ang,w,h,dy):
    a=math.radians(ang)
    cx=anchor[0]-dy*math.sin(a); cy=anchor[1]+dy*math.cos(a)
    # shift from text baseline to the visual centre, along the rotated axis
    cx+= (h*0.30)*math.sin(a); cy-= (h*0.30)*math.cos(a)
    return corners(cx,cy,w+PAD*2,h+PAD*2,ang)

def obst_quad(o):
    return corners(o['x']+o['w']/2,o['y']+o['h']/2,o['w'],o['h'],0)

def sat_overlap(A,B):
    """Approximate intersection area of two convex quads: 0 when separated."""
    for P,Q in ((A,B),(B,A)):
        for i in range(len(P)):
            ex,ey=P[(i+1)%len(P)][0]-P[i][0], P[(i+1)%len(P)][1]-P[i][1]
            nx,ny=-ey,ex
            n=math.hypot(nx,ny) or 1; nx,ny=nx/n,ny/n
            pa=[x*nx+y*ny for x,y in P]; pb=[x*nx+y*ny for x,y in Q]
            if max(pa)<min(pb) or max(pb)<min(pa): return 0.0
    # overlapping: score by how deep, cheap proxy on the minimum penetration
    depth=1e9
    for P,Q in ((A,B),(B,A)):
        for i in range(len(P)):
            ex,ey=P[(i+1)%len(P)][0]-P[i][0], P[(i+1)%len(P)][1]-P[i][1]
            nx,ny=-ey,ex; n=math.hypot(nx,ny) or 1; nx,ny=nx/n,ny/n
            pa=[x*nx+y*ny for x,y in P]; pb=[x*nx+y*ny for x,y in Q]
            depth=min(depth, min(max(pa)-min(pb), max(pb)-min(pa)))
    return depth*depth

OB=[(o,obst_quad(o)) for o in M['obstacles']]
FRACS=[i/100 for i in range(4,97,2)]
DYS=list(range(-34,-5,3))+list(range(8,35,3))
placed=[]; chosen={}
for name,frac0,side0,spine in sorted(bp.RANGES,key=lambda r:-SIZE[r[0]]['w']):
    pts=bp.simplify([proj(lo,la) for lo,la in spine], bp.TOL_RANGE)
    w,h=SIZE[name]['w'],SIZE[name]['h']
    best=None
    for dy in DYS:
        for f in FRACS:
            lab=bp.label_anchor([pts],f)
            if not lab: continue
            Q=label_quad(lab['p'],lab['a'],w,h,dy)
            cost=sum(sat_overlap(Q,q) for _,q in OB)+sum(sat_overlap(Q,q) for q in placed)
            xs=[p[0] for p in Q]; ys=[p[1] for p in Q]
            if min(xs)<4 or min(ys)<4 or max(xs)>1176 or max(ys)>741: cost+=9000
            cost+=abs(f-0.5)*25+abs(abs(dy)-9)*4
            if best is None or cost<best[0]: best=(cost,f,dy,Q)
    cost,f,dy,Q=best
    resid=sum(sat_overlap(Q,q) for _,q in OB)+sum(sat_overlap(Q,q) for q in placed)
    placed.append(Q); chosen[name]=[f,dy]
    hits=[o['t'][:16] for o,q in OB if sat_overlap(Q,q)>0]
    print("  %-20s frac %.2f  dy %+3d   overlap %6.1f  %s"%(name,f,dy,resid,
          ("hits: "+", ".join(hits)) if hits else "clear"))
json.dump(chosen, open('placement.json','w'))
