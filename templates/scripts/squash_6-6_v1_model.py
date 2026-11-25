"""squash_6-6_v1: parametric model of the 6'6" squash-tail board (flat bottom).
Design units are INCHES; the STEP is exported in mm (x25.4) like the other files in this repo.
Needs: pip install cadquery scipy numpy
Run:   python3 squash_6-6_v1_model.py <outdir>
Writes: squash_6-6_v1_flat.step, squash_6-6_v1_outline.npy, squash_6-6_v1_fins.json (inputs for gen.py)
Edit the tables below (W = full width, T = thickness, rocker, CONCAVE) and rerun to make a new version."""
import numpy as np, cadquery as cq
from scipy.interpolate import PchipInterpolator as P

L = 78.0
# full widths along length (from tail), inches
W = [(0,5.4),(1,8.2),(3,10.9),(6,13.0),(12,16.5),(18,19.0),(24,20.3),(30,20.7),(36,21.0),(40.5,21.1),(48,20.8),
     (54,20.3),(60,19.0),(66,16.8),(70,14.4),(73,10.4),(75.5,6.6),(77,3.2),(78,1.0)]
# centerline thickness (deck height above bottom at stringer)
T = [(0,0.45),(3,0.95),(6,1.4),(12,2.1),(20,2.52),(30,2.72),(40,2.75),(50,2.70),(58,2.58),(66,2.15),(72,1.55),(75,1.15),(78,0.5)]
NOSE_ROCKER, TAIL_ROCKER = 4.25, 2.0
CONCAVE = 0.0       # bottom: 0 = flat. Set 0.125 for a subtle single concave
VEE = 0.125         # tail vee depth

def interp(pts): 
    a=np.array(pts); return P(a[:,0],a[:,1])
WS, TS = 1.018, 1.07   # width / thickness scale (max ~21.5" x 2 15/16")
W = [(x, w*WS if 6<x<72 else w) for x,w in W]
hw_f = lambda x: float(interp(W)(x))/2
# Fair the nose: the piecewise width table leaves a wobble around 70-75" from the tail, so the last 22" use a smoothing spline
# (max change 0.07"). Widths at 12" from the nose and at 72" are unchanged to within 1/16".
from scipy.interpolate import UnivariateSpline as _US
_raw_hw = hw_f
_xn = np.arange(56.0, L+1e-9, 0.1)
_nose = _US(_xn, np.array([_raw_hw(x) for x in _xn]), s=0.2, k=4)
hw_f = lambda x: float(_nose(x)) if x >= 56.0 else _raw_hw(x)
th_f = interp(T)
def rocker(x):
    sn = max(0,(x-30)/(L-30)); st = max(0,(28-x)/28)
    return NOSE_ROCKER*sn**2.3 + TAIL_ROCKER*st**2.0
def smooth(e0,e1,x):
    t=min(1,max(0,(x-e0)/(e1-e0))); return t*t*(3-2*t)
def section(x, tscale=TS, dc=CONCAVE, dv=VEE):
    w=hw_f(x); t=float(th_f(x))*tscale; b=rocker(x)
    cfade = smooth(14,30,x)*(1-smooth(52,68,x))       # concave through the middle
    vfade = 1-smooth(6,34,x)                           # vee out the tail
    off = lambda y: dc*cfade*max(0,1-(y/(0.6*w))**2)**1.0 - dv*vfade*(1-y/w)
    tf = 1-smooth(2,26,x)
    a = 0.42-0.10*tf
    za = b+a*t; u=(1-a)*t
    pts=[(0,b+off(0)),(0.45*w,b+off(0.45*w)),(0.80*w,b+0.03+off(0.80*w)*0.3),
         ((0.955-0.025*tf)*w,b+0.40*a*t),(w,za),(0.955*w,za+0.28*u),(0.80*w,za+0.62*u),(0.45*w,za+0.90*u),(0,b+t)]
    R=[cq.Vector(x,y,z) for y,z in pts]
    Lp=[cq.Vector(x,-y,z) for y,z in reversed(pts)]
    e1=cq.Edge.makeSpline(R,tangents=[cq.Vector(0,1,0),cq.Vector(0,-1,0)])
    e2=cq.Edge.makeSpline(Lp,tangents=[cq.Vector(0,-1,0),cq.Vector(0,1,0)])
    return cq.Wire.assembleEdges([e1,e2])
XS=[0,1,2.5,4,6,9,12,16,20,25,30,35,40,45,50,55,60,64,68,71,73.5,75.5,77,78]
def build(tscale=TS, **kw):
    return cq.Solid.makeLoft([section(x,tscale,**kw) for x in XS], True)


def marks(out):
    """Numbers the Staples template prints along the stringer: rocker gap, thickness, bottom and rail zones."""
    import json, os
    def off0(x):
        return CONCAVE*smooth(14,30,x)*(1-smooth(52,68,x)) - VEE*(1-smooth(6,34,x))
    xs = [round(i*0.25, 2) for i in range(int(L/0.25)+1)]
    m = {
      "rocker": [[x, rocker(x)+off0(x)] for x in xs],            # gap under the stringer, bottom-down on a flat floor
      "thick":  [[x, float(th_f(x))*TS - off0(x)] for x in xs],  # deck to bottom on the stringer
      "tail_rocker_from": 28.0, "nose_rocker_from": 30.0,        # where the bottom starts curving up (from tail / from tail)
      "vee": VEE, "vee_to": 34.0, "concave": CONCAVE,
      "rail_zones": [[0, 8, "red"], [8, 26, "orange"], [26, 66, "green"], [66, L, "blue"]],
    }
    json.dump(m, open(os.path.join(out, "squash_6-6_v1_marks.json"), "w"))

def main(out):
    import json, math, os
    os.makedirs(out, exist_ok=True)
    solid = build()
    litres = solid.Volume()*0.016387064
    print("volume %.2f L, valid=%s" % (litres, solid.isValid()))
    big = solid.scale(25.4)                      # inches -> mm for the STEP
    cq.exporters.export(cq.Workplane().add(big), os.path.join(out, "squash_6-6_v1_flat.step"))
    # outline (half width) every 0.1" along the length; columns: index, x_mm, y_mm
    xs = np.arange(0, L+1e-9, 0.1)
    rows = [[i, x*25.4, hw_f(x)*25.4] for i, x in enumerate(xs)]
    np.save(os.path.join(out, "squash_6-6_v1_outline.npy"), np.array(rows))
    # glass-on thruster: center fin on stringer, side fins toed-in 3/16" over the base
    base0, base1, thick = 6.55, 11.0, 0.43
    xm = (base0+base1)/2
    ym = hw_f(xm) - 1.25                          # base midpoint 1 1/4" in from rail
    toe = 0.1875
    yb, yf = ym+toe/2, ym-toe/2                   # back, front (front toward stringer)
    d = np.array([base1-base0, yf-yb]); d /= np.linalg.norm(d); n = np.array([-d[1], d[0]])*thick/2
    A, B = np.array([base0, yb]), np.array([base1, yf])
    side = [list(A-n), list(A+n), list(B-n), list(B+n)]
    ctr = [[3.25,-0.215],[3.25,0.215],[7.6875,-0.215],[7.6875,0.215]]
    marks(out)
    json.dump({"fins":[ctr, side, [[p[0],-p[1]] for p in side]], "leash":{"x":2.5,"y":0.0,"r":0.5}},
              open(os.path.join(out, "squash_6-6_v1_fins.json"), "w"), indent=1)

if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
