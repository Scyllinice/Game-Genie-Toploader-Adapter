#!/usr/bin/env python3
"""Route the 72 pass-through conductors. Deterministic — no autorouter.

  python3 route.py [BOARD] [--force]

This board does not need a router, and running one would be a step backwards: an
autorouted result is a different shape every time, cannot be reviewed as a diff, and
has to be re-run and re-checked after any change. The routing problem here is one
sentence long — every conductor goes from J2 pin N straight to J1 pin N, and the two
pad fields are on 2.50 and 2.54 mm pitch, so each one shifts sideways by 1.67 to
3.07 mm on the way. So it is solved in closed form and checked.

THE SHAPE

  J2 pad (2.50 mm pitch)
        |            vertical, in its own pad column
        \\           45 deg jog, all in one band so the jogs stay parallel
         |           vertical, in the destination column
  J1 pad (2.54 mm pitch)

Parallel jogs never converge, and adjacent conductors stay at least 2.5 mm apart
everywhere — the pitch itself is the clearance. That is why one band works for all 72.

THE MOUNTING HOLES ARE THE WHOLE DIFFICULTY

MOUNT1 and MOUNT2 sit in the middle of the routing corridor, and eight conductors pass
within a track's clearance of one of them (four at each hole — the ones whose source
column is close on one side and whose destination column is close on the other). For
those, WHERE the jog happens decides whether the trace clears the hole:

  jog EARLY  and the trace passes the hole in its DESTINATION column
  jog LATE   and it passes in its SOURCE column
  jog TWICE  when neither column clears — it holds a safe X past the hole, then
             finishes the move in the short window between the hole and J1's pads

The released board does exactly this by hand, including the double jog on CPU A8 and
CPU D7. Here it falls out of one rule: pick the X the trace will hold while it passes
the hole, preferring the one that needs the least copper, and reject any choice that
does not fit in the window that is left.

Every segment is then re-measured against every pad, hole, board edge and every other
net's copper before the board is saved. KiCad's own DRC runs after that (`make drc`)
and is the independent check — but a router that only finds out from DRC cannot say
WHY it failed, and this one can.
"""

import argparse
import os
import sys

import pcbnew

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import geometry as G      # noqa: E402
import pinout as P        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MM = pcbnew.FromMM

# Keep-out radius around a mounting hole, measured to a TRACK CENTRELINE: the hole
# radius, plus the hole-to-copper rule, plus half a track, plus 0.05 mm so a trace
# that is placed exactly on the limit is not a DRC coin-flip.
HOLE_R = G.MOUNT_DRILL / 2 + G.HOLE_CLEARANCE + G.TRACK_W / 2 + 0.05

# The jog bands. EARLY starts 0.8 mm clear of J2's pad ends; LATE has to finish
# before J1's pads begin, which is the tight one — 78.0 down to 75.2498 is all the
# room there is between the hole keep-out and the pad field.
EARLY_Y = G.FINGER_PAD_TOP - 0.8
LATE_Y = min(hy for _, _, hy in G.MOUNT_HOLES) - HOLE_R
EARLY_MAX = EARLY_Y - (max(hy for _, _, hy in G.MOUNT_HOLES) + HOLE_R)
LATE_MAX = LATE_Y - G.GG_PAD_BOTTOM


def hole_conflict(x: float) -> bool:
    """Would a trace held at this X pass too close to a mounting hole?

    The epsilon is not decoration. The escape columns offered to choose_mid() are
    hx +/- HOLE_R, and `(hx - HOLE_R) - hx` does not come back as exactly -HOLE_R in
    binary floating point — so an exact-fit candidate rejects itself, and the only
    two conductors that need one (CPU A8 and CPU D7, at MOUNT2) fail to route with a
    message about there being no room. There is room; it is 1e-13 mm short.
    """
    return any(abs(x - hx) < HOLE_R - 1e-9 for _, hx, _ in G.MOUNT_HOLES)


def choose_mid(x_src: float, x_dst: float):
    """The X a conductor holds while it passes the mounting holes.

    Candidates are the two pad columns and the two safe offsets beside each hole.
    Preference is least copper: hold the destination column if it is clear (one jog,
    taken early), otherwise the source column, otherwise squeeze past the hole.
    """
    cands = [(0, x_dst), (1, x_src)]
    for _, hx, _ in G.MOUNT_HOLES:
        cands += [(2, hx - HOLE_R), (2, hx + HOLE_R)]
    ok = [(rank, x) for rank, x in cands
          if not hole_conflict(x)
          and abs(x - x_dst) <= LATE_MAX
          and abs(x - x_src) <= EARLY_MAX]
    if not ok:
        return None
    # Rank first, THEN distance: a pad column costs one jog, an escape column costs
    # two. Ranking on distance alone picked an escape column 0.34 mm nearer J1 over
    # the source column that would have done, and turned two clean 3-segment routes
    # into 5-segment ones for nothing.
    return min(ok, key=lambda rx: (rx[0], abs(rx[1] - x_dst)))[1]


def path_for(pin: int):
    """The polyline for one conductor, source pad centre to destination pad centre."""
    x_src, x_dst = G.finger_x(pin), G.gg_x(pin)
    x_mid = choose_mid(x_src, x_dst)
    if x_mid is None:
        return None
    pts = [(x_src, G.FINGER_Y)]
    if abs(x_mid - x_src) > 1e-9:
        pts.append((x_src, EARLY_Y))
        pts.append((x_mid, EARLY_Y - abs(x_mid - x_src)))
    if abs(x_dst - x_mid) > 1e-9:
        pts.append((x_mid, LATE_Y))
        pts.append((x_dst, LATE_Y - abs(x_dst - x_mid)))
    pts.append((x_dst, G.GG_Y))
    # Drop repeats and points that sit on the line between their neighbours.
    out = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - out[-1][0]) < 1e-9 and abs(p[1] - out[-1][1]) < 1e-9:
            continue
        out.append(p)
    return out


# ---------------------------------------------------------------------------
# Clearance measurement
# ---------------------------------------------------------------------------
def seg_dist(px, py, ax, ay, bx, by):
    """Point-to-segment distance."""
    vx, vy = bx - ax, by - ay
    L = vx * vx + vy * vy
    if L == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L))
    dx, dy = px - (ax + t * vx), py - (ay + t * vy)
    return (dx * dx + dy * dy) ** 0.5


def seg_seg_dist(s, t):
    """Distance between two segments, treating a crossing as zero."""
    (ax, ay, bx, by), (cx, cy, dx, dy) = s, t
    d1 = (bx - ax, by - ay)
    d2 = (dx - cx, dy - cy)
    denom = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(denom) > 1e-12:
        t1 = ((cx - ax) * d2[1] - (cy - ay) * d2[0]) / denom
        t2 = ((cx - ax) * d1[1] - (cy - ay) * d1[0]) / denom
        if -1e-9 <= t1 <= 1 + 1e-9 and -1e-9 <= t2 <= 1 + 1e-9:
            return 0.0
    return min(seg_dist(ax, ay, cx, cy, dx, dy), seg_dist(bx, by, cx, cy, dx, dy),
               seg_dist(cx, cy, ax, ay, bx, by), seg_dist(dx, dy, ax, ay, bx, by))


def rect_dist(seg, cx, cy, w, h):
    """Distance from a segment to an axis-aligned rectangle (0 if it enters it)."""
    x0, x1 = cx - w / 2, cx + w / 2
    y0, y1 = cy - h / 2, cy + h / 2
    edges = [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]
    ax, ay, bx, by = seg
    inside = (x0 <= ax <= x1 and y0 <= ay <= y1) or (x0 <= bx <= x1 and y0 <= by <= y1)
    if inside:
        return 0.0
    return min(seg_seg_dist(seg, e) for e in edges)


def audit(tracks, pads):
    """Measure everything against everything. Returns (findings, worst-case table)."""
    need_copper = G.CLEARANCE + G.TRACK_W / 2          # centreline to other copper
    need_pad = G.CLEARANCE + G.TRACK_W / 2
    need_hole = G.MOUNT_DRILL / 2 + G.HOLE_CLEARANCE + G.TRACK_W / 2
    need_edge = G.EDGE_CLEARANCE + G.TRACK_W / 2

    findings = []
    worst = {"track/track": 9e9, "track/pad": 9e9, "track/hole": 9e9, "track/edge": 9e9}

    by_layer = {}
    for t in tracks:
        by_layer.setdefault(t["layer"], []).append(t)

    for layer, group in by_layer.items():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if a["net"] == b["net"]:
                    continue
                for sa in a["segs"]:
                    for sb in b["segs"]:
                        d = seg_seg_dist(sa, sb)
                        worst["track/track"] = min(worst["track/track"], d)
                        if d < need_copper - 1e-6:
                            findings.append(
                                f"{a['net']} and {b['net']} are {d:.3f} mm apart on "
                                f"{layer} (need {need_copper:.3f})")
        for a in group:
            for pad in pads:
                if pad["layer"] != layer or pad["net"] == a["net"]:
                    continue
                for sa in a["segs"]:
                    d = rect_dist(sa, pad["x"], pad["y"], pad["w"], pad["h"])
                    worst["track/pad"] = min(worst["track/pad"], d)
                    if d < need_pad - 1e-6:
                        findings.append(
                            f"{a['net']} runs {d:.3f} mm from pad {pad['ref']}."
                            f"{pad['num']} [{pad['net']}] (need {need_pad:.3f})")

    for t in tracks:
        for sa in t["segs"]:
            for name, hx, hy in G.MOUNT_HOLES:
                d = seg_dist(hx, hy, *sa)
                worst["track/hole"] = min(worst["track/hole"], d)
                if d < need_hole - 1e-6:
                    findings.append(f"{t['net']} passes {d:.3f} mm from {name}'s "
                                    f"centre (need {need_hole:.3f})")
            for e in G.outline_segments():
                d = seg_seg_dist(sa, e)
                worst["track/edge"] = min(worst["track/edge"], d)
                if d < need_edge - 1e-6:
                    findings.append(f"{t['net']} runs {d:.3f} mm from the board "
                                    f"edge (need {need_edge:.3f})")
    return findings, worst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board", nargs="?",
                    default=os.path.join(HERE, "gg_toploader.kicad_pcb"))
    ap.add_argument("--force", action="store_true",
                    help="route a board that already carries tracks (they are kept)")
    args = ap.parse_args()

    board = pcbnew.LoadBoard(args.board)
    existing = len(board.GetTracks())
    if existing and not args.force:
        print(f"{args.board} already carries {existing} tracks — "
              f"regenerate with `make board`, or pass --force")
        return 1

    # ---- plan ---------------------------------------------------------------
    plan = {}
    for pin in P.PIN_NUMBERS:
        pts = path_for(pin)
        if pts is None:
            print(f"FAIL: no clear path for pin {pin} ({P.NETS[pin]}) — the mounting "
                  f"holes leave no safe column within {LATE_MAX:.2f} mm of J1")
            return 1
        plan[pin] = pts

    tracks = []
    for pin, pts in plan.items():
        tracks.append({
            "net": P.NETS[pin],
            "layer": G.layer_of(pin),
            "segs": [(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
                     for i in range(len(pts) - 1)],
        })

    pads = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if not pad.GetNumber().isdigit():
                continue
            pos = pad.GetPosition()
            size = pad.GetSize()
            pads.append({
                "ref": fp.GetReference(), "num": pad.GetNumber(),
                "net": pad.GetNetname(),
                "x": pcbnew.ToMM(pos.x), "y": pcbnew.ToMM(pos.y),
                "w": pcbnew.ToMM(size.x), "h": pcbnew.ToMM(size.y),
                "layer": "F.Cu" if pad.IsOnLayer(pcbnew.F_Cu) else "B.Cu",
            })

    findings, worst = audit(tracks, pads)
    if findings:
        print(f"FAIL: {len(findings)} clearance problems — nothing written")
        for f in findings[:20]:
            print("   ", f)
        return 1

    # ---- commit -------------------------------------------------------------
    layers = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}
    added = 0
    for t in tracks:
        net = board.FindNet(t["net"])
        if net is None:
            print(f"FAIL: board has no net {t['net']}")
            return 1
        for (x1, y1, x2, y2) in t["segs"]:
            trk = pcbnew.PCB_TRACK(board)
            trk.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1)))
            trk.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
            trk.SetWidth(MM(G.TRACK_W))
            trk.SetLayer(layers[t["layer"]])
            trk.SetNet(net)
            board.Add(trk)
            added += 1
    pcbnew.SaveBoard(args.board, board)

    # ---- report -------------------------------------------------------------
    shapes = {}
    for pin, pts in plan.items():
        shapes[len(pts) - 1] = shapes.get(len(pts) - 1, 0) + 1
    dodged = [pin for pin, pts in plan.items() if len(pts) - 1 > 3]
    length = sum(((s[2] - s[0]) ** 2 + (s[3] - s[1]) ** 2) ** 0.5
                 for t in tracks for s in t["segs"])

    print(f"routed {args.board}")
    print(f"  {len(plan)} conductors, {added} segments, {length:.1f} mm of "
          f"{G.TRACK_W} mm track")
    print("  segments per conductor: "
          + ", ".join(f"{k}x{v}" for k, v in sorted(shapes.items())))
    print(f"  jogged twice to clear a mounting hole: "
          f"{', '.join(f'{p} ({P.PINS[p]['wiki']})' for p in sorted(dodged)) or 'none'}")
    print("  worst clearances (centreline to other copper):")
    for k in ("track/track", "track/pad", "track/hole", "track/edge"):
        print(f"    {k:<12} {worst[k]:.3f} mm")
    return 0


if __name__ == "__main__":
    sys.exit(main())
