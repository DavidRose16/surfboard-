"""Staples / copy-shop template: ONE 36 x 48 in sheet, board length running down the sheet, cut in two pieces
(A = tail half, B = nose half) that overlap by ~2" and register on four crosses. Includes rocker, bottom and
thickness strips, rail-type colored lines, fins and leash plug. Same layout as hypto_6-6_template_STAPLES_36x48in.pdf.

usage: python3 gen_staples.py outline.npy fins.json marks.json info.json "Board name" outdir fname source_text
  outline.npy / fins.json / info.json  - same inputs gen.py uses (info.json is written by gen.py)
  marks.json                           - rocker / thickness / bottom / rail zones (written by the model script)
"""
import sys, json, math
import numpy as np
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.colors import Color, black, white, HexColor

rfile, ffile, mfile, ifile, NAME, OUT, FNAME, SRC = sys.argv[1:9]
R = np.load(rfile); F = json.load(open(ffile)); M = json.load(open(mfile)); INFO = json.load(open(ifile))
X_ = R[:, 1] / 25.4; Y_ = R[:, 2] / 25.4
L = float(INFO["L"])
hw = lambda x: float(np.interp(x, X_, Y_))
rock = lambda x: float(np.interp(x, [p[0] for p in M["rocker"]], [p[1] for p in M["rocker"]]))
thick = lambda x: float(np.interp(x, [p[0] for p in M["thick"]], [p[1] for p in M["thick"]]))
CENTER = L / 2


def frac(v):
    n = round(v * 16); w, r = divmod(n, 16)
    if r == 0: return f'{w}"'
    g = math.gcd(r, 16); return (f'{w} ' if w else '') + f'{r // g}/{16 // g}"'


def ftxt(v):  # like frac but 0 -> 0"
    return frac(max(v, 0))


RED, ORANGE, GREEN, BLUE = HexColor('#DC1A1A'), HexColor('#F28C00'), HexColor('#009E3D'), HexColor('#0040C8')
ZCOL = {"red": RED, "orange": ORANGE, "green": GREEN, "blue": BLUE}
GRAY, LGRAY = HexColor('#808080'), HexColor('#DDDDDD')
PINK, PURPLE, LGREEN, BAND = HexColor('#FFD9D9'), HexColor('#E6D6FF'), HexColor('#D9FFD9'), HexColor('#FFEBC2')

SW, SH = 36.0, 48.0
PWID, SX = 14.8, 2.7          # piece width, stringer distance from the piece's left border
pieces = [
    dict(k='A', title='PIECE A - TAIL HALF', left=0.6, top=3.5, h=42.0, bx_top=-2.0, other='B ends here'),
    dict(k='B', title='PIECE B - NOSE HALF', left=15.75, top=3.25, h=42.5, bx_top=38.0, other='A ends here'),
]
BAND_FROM, BAND_TO = CENTER - 1.0, CENTER + 1.0   # the ~2" overlap band, centred on the center station

c = canvas.Canvas(f'{OUT}/{FNAME}_template_STAPLES_36x48in.pdf', pagesize=(SW * 72, SH * 72))
c.setTitle(f'{NAME} - 36x48 split template'); c.scale(72, 72)


def Yc(y): return SH - y


def text(X, Y, s, size=0.13, font='Helvetica', color=black, rot=0, anchor='l'):
    c.saveState(); c.translate(X, Yc(Y)); c.rotate(rot); c.setFillColor(color); c.setFont(font, size)
    {'l': c.drawString, 'c': c.drawCentredString, 'r': c.drawRightString}[anchor](0, 0, s); c.restoreState()


def line(x0, y0, x1, y1, w=0.012, color=black, dash=None):
    c.saveState(); c.setStrokeColor(color); c.setLineWidth(w)
    if dash: c.setDash(*dash)
    c.line(x0, Yc(y0), x1, Yc(y1)); c.restoreState()


def poly(pts, fill=None, stroke=black, w=0.012, close=True, dash=None):
    c.saveState(); p = c.beginPath(); p.moveTo(pts[0][0], Yc(pts[0][1]))
    for q in pts[1:]: p.lineTo(q[0], Yc(q[1]))
    if close: p.close()
    if fill is not None: c.setFillColor(fill)
    if stroke is not None: c.setStrokeColor(stroke); c.setLineWidth(w)
    if dash: c.setDash(*dash)
    c.drawPath(p, fill=1 if fill is not None else 0, stroke=1 if stroke is not None else 0); c.restoreState()


def rect(X, Y, w, h, fill=None, stroke=black, lw=0.012):
    poly([(X, Y), (X + w, Y), (X + w, Y + h), (X, Y + h)], fill=fill, stroke=stroke, w=lw)


def crossing(arr, val, lo, hi):
    """x between lo..hi where arr (list of [x,y]) crosses val"""
    pts = [p for p in arr if lo <= p[0] <= hi]
    for a, b in zip(pts, pts[1:]):
        if (a[1] - val) * (b[1] - val) <= 0 and a[1] != b[1]:
            return a[0] + (val - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
    return None


# ---------- fins / leash from json ----------
fins = F["fins"]; leash = F["leash"]
side = [p for p in fins if np.mean([q[1] for q in p]) > 1][0]
ctr = [p for p in fins if abs(np.mean([q[1] for q in p])) < 1][0]
quad = lambda pts: [pts[0], pts[1], pts[3], pts[2]]
cx0, cx1 = INFO["ctr"]
sf, sb = INFO["side_front"], INFO["side_back"]


def draw_piece(pc):
    left, top, h = pc['left'], pc['top'], pc['h']; bt = pc['bx_top']
    bx_lo, bx_hi = bt, bt + h
    sx = left + SX
    P = lambda bx, by: (sx + by, top + (bx - bt))           # board coords -> sheet inches (Y down)
    vis = lambda a, b: (max(a, bx_lo), min(b, bx_hi))        # visible part of a bx range

    c.saveState(); p = c.beginPath(); p.rect(left, Yc(top + h), PWID, h); c.clipPath(p, stroke=0, fill=0)

    # overlap band
    y0 = top + (BAND_FROM - bt) if pc['k'] == 'B' else top + (BAND_FROM - bt)
    ya, yb = sorted([top + (max(BAND_FROM, bx_lo) - bt), top + (min(BAND_TO, bx_hi) - bt)])
    rect(left, ya, PWID, yb - ya, fill=BAND, stroke=None)
    ydash = top + ((BAND_FROM if pc['k'] == 'A' else BAND_TO) - bt)
    line(left, ydash, left + PWID, ydash, w=0.014, color=ORANGE, dash=([0.12, 0.06], 0))
    text(left + PWID - 3.2, ydash + (-0.1 if pc['k'] == 'A' else 0.22), pc['other'], 0.14, 'Helvetica-Bold', ORANGE)
    text(left + PWID - 0.2, (ya + yb) / 2 - 0.4 if pc['k'] == 'B' else (ya + yb) / 2 - 0.4, 'OVERLAP', 0.15, 'Helvetica-Bold', ORANGE, rot=-90)

    # ---- strips: THICK numbers / BOTTOM / ROCKER ----
    colT, colB0, colB1, colR0, colR1 = left + 0.30, left + 0.55, left + 0.80, left + 1.15, left + 1.38
    for hx, name in ((colT - 0.08, 'THICK'), (colB0 + 0.07, 'BOTTOM'), (colR0 + 0.07, 'ROCKER')):
        text(hx, top + 0.2, name, 0.12, 'Helvetica-Bold', rot=-90)

    def band_text(x0, x1, bx0, bx1, fill, label, size=0.105):
        a, b = vis(bx0, bx1)
        if b <= a: return
        rect(x0, top + (a - bt), x1 - x0, b - a, fill=fill, stroke=black, lw=0.006)
        text(x0 + 0.04, max(top + (a - bt) + 0.1, top + 1.1), label, size, 'Helvetica-Bold', rot=-90) if (b - a) > 0.6 else None

    tr, nr = M["tail_rocker_from"], M["nose_rocker_from"]
    band_text(colR0, colR1, 0, tr, PINK, f'TAIL ROCKER: bottom starts curving up about {int(tr)}" from the tail')
    band_text(colR0, colR1, tr, nr, LGREEN, 'LOW POINT', 0.09)
    band_text(colR0, colR1, nr, L, PINK, f'NOSE ROCKER: bottom starts curving up about {int(L - nr)}" from the nose ({int(nr)}" from tail)')
    # rocker numbers (gap under the stringer, board bottom-down on a flat floor)
    for bx in [0, 6, 12, 18, 24] + [48, 54, 60, 66, 72, 78]:
        if bx_lo <= bx <= bx_hi:
            Y = top + (bx - bt)
            line(colR0 - 0.1, Y, colR0, Y, w=0.01)
            text(colR0 - 0.16, Y + 0.03 if bx > 0 else Y + 0.03, ftxt(round(rock(bx) * 16) / 16), 0.1, 'Helvetica-Bold', rot=-90)
    vee_to = M["vee_to"]
    if M["vee"] > 0:
        band_text(colB0, colB1, 0, vee_to, PURPLE, f'VEE about {frac(M["vee"])}: stringer a bit lower than the rails, like a flat roof. Through the fins, fades to flat by {int(vee_to)}".')
    band_text(colB0, colB1, vee_to if M["vee"] > 0 else 0, L, HexColor('#F4F4F4'), 'FLAT: keep the bottom dead straight (check with a straightedge)')
    # thickness along the stringer
    tmax_x = max(M["thick"], key=lambda p: p[1])[0]; tmax = max(p[1] for p in M["thick"])
    marks = []
    for val in (1.0, 1.5, 2.0, 2.5):
        a = crossing(M["thick"], val, 0, tmax_x); b = crossing(M["thick"], val, tmax_x, L)
        for bx in (a, b):
            if bx is not None: marks.append((bx, frac(val)))
    marks.append((tmax_x, f'THICKEST {frac(tmax)}'))
    for bx, lab in marks:
        if bx_lo <= bx <= bx_hi:
            Y = top + (bx - bt); line(colT + 0.05, Y, colT + 0.22, Y, w=0.01)
            text(colT - 0.04, Y + 0.03, lab, 0.1, 'Helvetica-Bold', rot=-90)

    # gray notes between strips and stringer
    if pc['k'] == 'A':
        text(left + 1.62, top + 0.15 + 1.9, 'Numbers above the line = inches from TAIL tip. Gray numbers below = inches from NOSE tip.', 0.1, color=GRAY, rot=-90)
        text(left + 1.82, top + 0.15 + 1.9, f'Ends are drawn exactly as in the CAD file: tail end {frac(2 * hw(0))} wide, nose end {frac(2 * hw(L))} wide - round the corners off by hand.', 0.1, color=GRAY, rot=-90)
    text(left + 2.12, top + 0.15 + (1.9 if pc['k'] == 'A' else 0.15), 'STRINGER / CENTERLINE - lay this line exactly on the stringer, trace, then flip the template over and trace the other side', 0.1, 'Helvetica-Bold', rot=-90)

    # ---- stringer, ticks, station numbers ----
    line(sx, top, sx, top + h, w=0.03, color=RED, dash=([0.35, 0.08, 0.03, 0.08], 0))
    for i in range(0, int(L) + 1):
        if bx_lo <= i <= bx_hi:
            Y = top + (i - bt)
            line(sx, Y, sx + (0.4 if i % 6 == 0 else 0.15), Y, w=0.012)
    for k in range(0, int(L / 6) + 1):
        bx = 6 * k
        if bx_lo + 0.5 <= bx <= bx_hi:
            Y = top + (bx - bt)
            text(sx + 0.42, Y + 0.04, str(bx), 0.14, 'Helvetica-Bold', rot=-90)
        nb = L - 6 * k
        if bx_lo + 0.5 <= nb <= bx_hi and nb % 6 == 0 or (nb == L and bx_lo <= 0):
            Y = top + (nb - bt)
            text(sx - 0.28, Y + 0.0 if nb == L else Y - 0.3, f'{int(L - nb)} from nose', 0.1, color=GRAY, rot=-90)

    # ---- station lines with widths ----
    stations = [(6 * k, '') for k in range(1, int(L / 6)) if abs(6 * k - CENTER) > 0.1]
    stations = [(bx, 'TAIL 12" ' if bx == 12 else 'NOSE 12" ' if bx == L - 12 else '') for bx, _ in stations]
    stations.append((CENTER, 'CENTER '))
    for bx, pre in stations:
        if not (bx_lo + 0.3 <= bx <= bx_hi - 0.3): continue
        w = 2 * hw(bx); Y = top + (bx - bt); xo = sx + hw(bx)
        line(sx + 0.45, Y, xo, Y, w=0.008, color=GRAY, dash=([0.12, 0.08], 0))
        text(sx + 0.95, Y - 0.07, f'{pre}W {frac(w)}   (half {frac(hw(bx))})', 0.13, 'Helvetica-Bold' if pre else 'Helvetica')
    # wide point
    wpx, wpw = INFO["wpx"], INFO["wpw"]
    if bx_lo + 0.3 <= wpx <= bx_hi - 0.3:
        Y = top + (wpx - bt)
        line(sx, Y, sx + wpw / 2 + 0.3, Y, w=0.012)
        text(sx + wpw / 2 + 0.42, Y + 0.2, f'WIDE POINT {frac(wpw)} @ {wpx:.1f}" from tail (+{wpx - CENTER:.1f}" from center)', 0.13, 'Helvetica-Bold', BLUE, rot=-90)

    # ---- fins ----
    for pts in (quad(side), quad(ctr)):
        poly([P(bx, by) for bx, by in pts], fill=LGRAY)
    d = np.array([sf[0] - sb[0], sf[1] - sb[1]]); d /= np.linalg.norm(d)
    a = np.array(sb) - d * 0.7; b = np.array(sf) + d * 0.9
    line(*P(*a), *P(*b), w=0.01, dash=([0.1, 0.05], 0))
    toe = math.degrees(math.atan2(sb[1] - sf[1], sf[0] - sb[0]))
    sidelines = ['SIDE FIN BASE (mark both sides - mirror)',
                 f'front of base {frac(sf[0])} from tail, {frac(INFO["side_front_from_rail"])} in from rail edge',
                 f'back of base {frac(sb[0])} from tail, {frac(INFO["side_back_from_rail"])} in from rail edge',
                 f'toe-in {frac(abs(sb[1] - sf[1]))} over the base (front points toward stringer)',
                 'cant 5 deg (fin tip leans out toward rail)',
                 f'use side fins with a base {frac(sf[0] - sb[0])} long or shorter']
    tx0, tby = sx + 7.35, 12.3
    if bx_lo <= tby <= bx_hi - 5:
        for k, t in enumerate(sidelines):
            text(tx0 - k * 0.15, top + (tby - bt) + 0.0, t, 0.11 if k else 0.12, 'Helvetica-Bold' if k == 0 else 'Helvetica', rot=-90)
        fx, fy = P(sf[0] - 1.0, sf[1] + 0.2)
        line(fx, fy, tx0 + 0.07, top + (tby - bt) - 0.1, w=0.008)
    ctext = ['CENTER FIN BASE (on stringer, 0 deg)', f'{frac(cx0)} to {frac(cx1)} from tail']
    cb = 9.0
    if bx_lo <= cb <= bx_hi - 3:
        for k, t in enumerate(ctext):
            text(sx + 1.55 - k * 0.16, top + (cb - bt), t, 0.12 if k == 0 else 0.11, 'Helvetica-Bold' if k == 0 else 'Helvetica', rot=-90)
        line(sx + 1.35, top + (cb - bt) - 0.05, sx + 0.1, top + ((cx0 + cx1) / 2 - bt) + 0.2, w=0.008)
    # leash plug
    lx, lyy = leash["x"], leash["r"]
    if bx_lo <= lx <= bx_hi:
        X, Y = P(lx, 0)
        c.saveState(); c.setStrokeColor(black); c.setLineWidth(0.012); c.circle(X, Yc(Y), lyy); c.restoreState()
        line(X - 0.2, Y, X + 0.2, Y, w=0.012); line(X, Y - 0.2, X, Y + 0.2, w=0.012)
        text(sx + 1.0, top + (lx - bt) + 1.2, 'LEASH PLUG (deck)', 0.11, color=BLUE, rot=-90)
        text(sx + 0.85, top + (lx - bt) + 1.2, f'1" hole, {frac(lx)} from tail', 0.11, color=BLUE, rot=-90)

    # ---- rail zone colors (outside the outline) + notes ----
    zinfo = {
        "red": ('RED = TUCKED EDGE', 'Low rail, tucked slightly under, with a firm edge where the bottom meets the rail.', 'Runs past the fins. Lets the tail release off the wave in turns.'),
        "orange": ('ORANGE = BLEND', 'The tucked tail rail slowly fills out into the full mid-board rail.', None),
        "green": ('GREEN = MEDIUM-FULL ROUND RAIL', f'Rail apex about {frac(0.42 * tmax)} up from the bottom at the thickest point, rounded over, deck gently domed.', 'Forgiving, stable, easy to paddle and still turns.'),
        "blue": ('BLUE = NOSE', 'Thinner, softer rail. Round it off so the nose does not catch.', None),
    }
    for z0, z1, col in M["rail_zones"]:
        a, b = vis(z0, z1)
        if b <= a: continue
        xs = np.linspace(a, b, int((b - a) * 8) + 2); pts = []
        for x in xs:
            h0, h1 = hw(x - 0.05), hw(x + 0.05); slope = (h1 - h0) / 0.1; n = math.hypot(slope, 1)
            pts.append(P(x + 0.12 * (-slope) / n, hw(x) + 0.12 / n))
        c.saveState(); c.setStrokeColor(ZCOL[col]); c.setLineWidth(0.06); c.setLineCap(0)
        p = c.beginPath(); p.moveTo(pts[0][0], Yc(pts[0][1]))
        for q in pts[1:]: p.lineTo(q[0], Yc(q[1]))
        c.drawPath(p, stroke=1, fill=0); c.restoreState()
        title, l1, l2 = zinfo[col]; zr = f'{int(z0)}" to {int(z1)}"' if col not in ('red', 'blue') else (f'tail to {int(z1)}"' if col == 'red' else f'{int(z0)}" to nose')
        mid = (z0 + z1) / 2
        if col == 'green': mid = 53
        if col == 'blue': mid = 72
        if col == 'orange': mid = 17
        if col == 'red': mid = 4.5
        lines_ = [(f'{title} ({zr})', 'Helvetica-Bold', 0.15), (l1, 'Helvetica', 0.105)] + ([(l2, 'Helvetica', 0.105)] if l2 else [])
        span = max(pdfmetrics.stringWidth(t, f, s_) for t, f, s_ in lines_)
        s0, s1 = mid - span / 2, mid + span / 2
        if s0 < bx_lo + 0.3 or s1 > bx_hi - 0.3: continue            # whole note must sit on this piece
        xt = sx + max(hw(x) for x in np.linspace(max(s0, 0), min(s1, L), 40)) + 0.5
        steps_ = [(0.2 if s_ > 0.12 else 0.14) for t, f, s_ in lines_]
        off = sum(steps_) - steps_[-1]                      # title sits right-most, detail lines step left toward the board
        for (t, f, s_), st_ in zip(lines_, steps_):
            text(xt + off, top + (s0 - bt), t, s_, f, ZCOL[col], rot=-90); off -= st_

    # ---- outline (black), tips, labels ----
    out = [P(x, hw(x)) for x in np.arange(0, L + 0.001, 0.1)]
    out = [(sx, P(0, 0)[1])] + out + [(sx, P(L, 0)[1])]
    c.saveState(); c.setStrokeColor(black); c.setLineWidth(0.03)
    pth = c.beginPath(); pth.moveTo(out[0][0], Yc(out[0][1]))
    for q in out[1:]: pth.lineTo(q[0], Yc(q[1]))
    c.drawPath(pth, stroke=1, fill=0); c.restoreState()
    text(sx + hw(4.0) + 0.45, top + (0.6 - bt), 'TAIL', 0.24, 'Helvetica-Bold', rot=-90) if bx_lo <= 0.5 else None
    if bx_hi >= L:
        text(sx + hw(L - 4.6) + 0.4, top + (L - 4.2 - bt), 'NOSE', 0.24, 'Helvetica-Bold', rot=-90)

    # ---- registration crosses X1-X4 on the center station ----
    for i, off in enumerate((0, 3, 6, 9)):
        X, Y = P(CENTER, off)
        c.saveState(); c.setStrokeColor(black); c.setLineWidth(0.012); c.circle(X, Yc(Y), 0.14); c.restoreState()
        line(X - 0.34, Y, X + 0.34, Y, w=0.012); line(X, Y - 0.34, X, Y + 0.34, w=0.012)
        text(X + 0.12, Y + 0.42, f'X{i + 1}', 0.2, 'Helvetica-Bold', RED, rot=-90)
    c.restoreState()
    # border + title
    rect(left, top, PWID, h, fill=None, stroke=black, lw=0.016)
    text(left, top - 0.48, pc['title'], 0.34, 'Helvetica-Bold')
    text(left, top - 0.2, f'{h:.2f}" x {PWID:.2f}"  -  cut on the black border', 0.15)
    text(left, top + h + 0.3, pc['title'].split(' - ')[0], 0.15, 'Helvetica-Bold')


for pc in pieces: draw_piece(pc)

# ---------- scale bars ----------
def bar_h(X, Y, n=12):
    for i in range(n):
        if i % 2 == 0: rect(X + i, Y, 1, 0.35, fill=black, stroke=None)
    rect(X, Y, n, 0.35, fill=None, stroke=black, lw=0.012)
    text(X, Y - 0.15, f'SCALE CHECK: this bar must measure exactly {n}" (each block 1")', 0.14, 'Helvetica-Bold')
    for i in (0, 6, 12): text(X + i, Y + 0.6, str(i), 0.12, anchor='c')
bar_h(15.9, 1.15)
VX, VY0 = 30.95, 33.5
for i in range(12):
    if i % 2 == 0: rect(VX, VY0 + i, 0.3, 1, fill=black, stroke=None)
rect(VX, VY0, 0.3, 12, fill=None, stroke=black, lw=0.012)
text(VX + 0.5, VY0 + 0.1, 'SCALE CHECK: this bar must measure exactly 12"', 0.14, 'Helvetica-Bold', rot=-90)

# ---------- sidebar ----------
SXb = 30.95; y = 3.75
text(SXb, y, NAME, 0.3, 'Helvetica-Bold'); y += 0.45
text(SXb, y, 'Half-outline template, 2 pieces', 0.16); y += 0.25
text(SXb, y, 'FULL SIZE 1:1 on 36 x 48 in sheet', 0.16, 'Helvetica-Bold'); y += 0.6
text(SXb, y, 'PRINT AT 100% / ACTUAL SIZE.', 0.18, 'Helvetica-Bold', RED); y += 0.3
text(SXb, y, 'NO fit-to-page, NO scaling.', 0.18, 'Helvetica-Bold', RED); y += 0.5
text(SXb, y, 'Measure both bars after printing:', 0.14, 'Helvetica-Bold'); y += 0.35
rect(SXb, y, 1, 1, fill=black, stroke=None); text(SXb + 1.15, y + 0.6, '1" x 1" square', 0.18, 'Helvetica-Bold'); y += 1.5
text(SXb, y, '12" bars: top of sheet + right edge.', 0.13); y += 0.55
text(SXb, y, 'HOW TO ASSEMBLE', 0.18, 'Helvetica-Bold'); y += 0.3
steps = ['1. Cut both pieces out on their black border.', '2. Lay piece B flat. Slide piece A over it', '   so the OVERLAP bands stack (~2").',
         '3. Line up the 4 crosses X1-X4 (hold up to', '   light). Red stringer lines must make one', '   straight line - check with a straightedge.',
         '4. A\'s end edge lands on B\'s "A ends here"', '   dashed line, and B\'s edge on "B ends here".', '5. Tape both faces along the seam.',
         f'6. Check: tail tip to nose tip = {int(L)}"', f'   ({int(L // 12)}\'{int(L % 12)}") along the stringer.', '7. Glue to 1/8" hardboard, cut, sand to line.']
for s in steps: text(SXb, y, s, 0.13); y += 0.2
y += 0.3
text(SXb, y, 'SHAPING MARKS', 0.18, 'Helvetica-Bold'); y += 0.3
for s in ['Numbers come from your design file.', 'Colored line outside the rail = rail type:', '  red tucked edge, orange blend, green medium-',
          '  full round rail, blue nose.', 'Strips under the stringer:', '  ROCKER = where the bottom curves up',
          '  BOTTOM = vee / flat zones', '  THICK = thickness on the stringer', 'Order: outline, then rocker + thickness',
          '(planer), then bottom shape, then rails.', 'Trace the zone ends onto the blank.']:
    text(SXb, y, s, 0.13); y += 0.2
y += 0.3
for s in [f'Source: {SRC}', f'Overlap centred on CENTER station ({int(CENTER)}" from tail).']:
    text(SXb, y, s, 0.1, color=GRAY); y += 0.17
c.showPage(); c.save()
