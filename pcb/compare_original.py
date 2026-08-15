#!/usr/bin/env python3
"""Prove the generated board is the released board.

  python3 compare_original.py [GENERATED] [ORIGINAL]

This is the point of the whole exercise. A rebuild that merely looks right is a new
board with an old board's name on it — and this one has been fabricated, sold and
plugged into people's consoles, so "looks right" is not the bar. Every pad, hole, net
and outline corner is subtracted from the released file and the differences printed.

Both boards are loaded through pcbnew rather than parsed as text: the released file is
KiCad 8 and the generated one is KiCad 9, so a textual diff would report the format
change and nothing useful. Comparing loaded models compares the geometry.

WHAT IS COMPARED FOR EQUALITY

  outline      corner for corner, after collapsing collinear vertices
  pads         144 pads: position, size, layer, net, on BOTH connectors
  holes        position and drill
  nets         name for name, and which pads each one lands on
  silk         text, position, angle, size, thickness

WHAT IS REPORTED BUT NOT REQUIRED TO MATCH

  copper       the tracks are re-derived by route.py, not copied. Same endpoints,
               different path — reported as counts and total length so a change in
               the routing rule is visible.
  stackup      the rebuild declares ENIG; the released file declares no finish.
  designators  hidden on both, but the generated board also carries a title block.

Exit code is 0 only if every equality check passes.
"""

import argparse
import os
import sys

import pcbnew

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import geometry as G      # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
# reference/ is the released design, frozen at the point the generated board took
# over as the project of record — see reference/README.md. It is not a build input
# and nothing regenerates it; it is the thing being compared against, so it has to
# stay exactly as it shipped.
ORIGINAL = os.path.join(HERE, "reference", "Game Genie Toploader Adapter.kicad_pcb")
GENERATED = os.path.join(HERE, "gg_toploader.kicad_pcb")

# 1 um. Two orders of magnitude below anything a fab can hold, and three below the
# 0.1 mm features on this board — but tight enough that a pad on the wrong pitch or a
# connector one step along shows up immediately.
TOL = 0.001


def mm(v):
    return pcbnew.ToMM(v)


def collapse(points):
    """Drop vertices that lie on the line between their neighbours."""
    out = []
    n = len(points)
    for i, p in enumerate(points):
        a, b = points[i - 1], points[(i + 1) % n]
        cross = ((p[0] - a[0]) * (b[1] - a[1])) - ((p[1] - a[1]) * (b[0] - a[0]))
        if abs(cross) > 1e-6:
            out.append(p)
    return out


def outline_corners(board):
    """Edge.Cuts segment endpoints, deduplicated and ordered around the loop."""
    segs = []
    for d in board.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts:
            continue
        if d.GetShape() != pcbnew.SHAPE_T_SEGMENT:
            raise SystemExit(f"outline has a {d.GetShape()} shape — extend this check")
        segs.append(((round(mm(d.GetStart().x), 4), round(mm(d.GetStart().y), 4)),
                     (round(mm(d.GetEnd().x), 4), round(mm(d.GetEnd().y), 4))))
    # Walk the loop so the comparison is of a POLYGON, not of a segment list whose
    # order and direction are an artefact of how the file was written.
    adj = {}
    for a, b in segs:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    if any(len(v) != 2 for v in adj.values()):
        raise SystemExit("outline is not a single closed loop")
    start = min(adj)
    loop = [start]
    prev, cur = None, start
    while True:
        nxt = [p for p in adj[cur] if p != prev]
        if not nxt or nxt[0] == start:
            break
        prev, cur = cur, nxt[0]
        loop.append(cur)
    return collapse(loop)


def pad_table(board):
    out = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            num = pad.GetNumber()
            if not num.isdigit():
                continue
            pos, size = pad.GetPosition(), pad.GetSize()
            layers = [n for n, bit in (("F.Cu", pcbnew.F_Cu), ("B.Cu", pcbnew.B_Cu))
                      if pad.IsOnLayer(bit)]
            out[(fp.GetReference(), int(num))] = {
                "x": mm(pos.x), "y": mm(pos.y),
                "w": mm(size.x), "h": mm(size.y),
                "layers": tuple(layers), "net": pad.GetNetname(),
            }
    return out


def hole_table(board):
    out = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetDrillSizeX() <= 0:
                continue
            pos = pad.GetPosition()
            out[(round(mm(pos.x), 3), round(mm(pos.y), 3))] = round(
                mm(pad.GetDrillSizeX()), 3)
    return out


def silk_table(board):
    out = {}
    for d in board.GetDrawings():
        if not isinstance(d, pcbnew.PCB_TEXT):
            continue
        out[d.GetText()] = {
            "layer": board.GetLayerName(d.GetLayer()),
            "x": mm(d.GetPosition().x), "y": mm(d.GetPosition().y),
            "angle": d.GetTextAngleDegrees(),
            "sx": mm(d.GetTextSize().x), "sy": mm(d.GetTextSize().y),
            "th": mm(d.GetTextThickness()),
        }
    return out


def track_stats(board):
    total, per_layer = 0.0, {}
    for t in board.GetTracks():
        L = mm(t.GetLength())
        total += L
        per_layer[board.GetLayerName(t.GetLayer())] = \
            per_layer.get(board.GetLayerName(t.GetLayer()), 0) + 1
    return len(board.GetTracks()), total, per_layer


class Report:
    def __init__(self):
        self.fails = []
        self.lines = []

    def check(self, name, ok, detail=""):
        self.lines.append(f"  {'PASS' if ok else 'FAIL'}  {name}"
                          + (f"  — {detail}" if detail else ""))
        if not ok:
            self.fails.append(name)

    def note(self, text):
        self.lines.append(f"  ....  {text}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("generated", nargs="?", default=GENERATED)
    ap.add_argument("original", nargs="?", default=ORIGINAL)
    args = ap.parse_args()

    for p in (args.generated, args.original):
        if not os.path.exists(p):
            print(f"missing: {p}")
            return 1

    new = pcbnew.LoadBoard(args.generated)
    old = pcbnew.LoadBoard(args.original)
    r = Report()

    # ---- outline -----------------------------------------------------------
    a, b = outline_corners(new), outline_corners(old)
    same = len(a) == len(b) and all(
        abs(p[0] - q[0]) < TOL and abs(p[1] - q[1]) < TOL
        for p, q in zip(a, b))
    r.check("outline", same, f"{len(a)} corners vs {len(b)}")
    if not same:
        for p, q in zip(a, b):
            if abs(p[0] - q[0]) >= TOL or abs(p[1] - q[1]) >= TOL:
                r.note(f"corner {p} vs {q}")

    # ---- pads --------------------------------------------------------------
    pa, pb = pad_table(new), pad_table(old)
    missing = sorted(set(pb) - set(pa))
    extra = sorted(set(pa) - set(pb))
    r.check("pad count", not missing and not extra,
            f"{len(pa)} pads")
    for k in missing[:5]:
        r.note(f"missing from the rebuild: {k}")
    for k in extra[:5]:
        r.note(f"only in the rebuild: {k}")

    moved, resized, relayered, renetted = [], [], [], []
    for k in sorted(set(pa) & set(pb)):
        x, y = pa[k], pb[k]
        if abs(x["x"] - y["x"]) >= TOL or abs(x["y"] - y["y"]) >= TOL:
            moved.append((k, (x["x"], x["y"]), (y["x"], y["y"])))
        if abs(x["w"] - y["w"]) >= TOL or abs(x["h"] - y["h"]) >= TOL:
            resized.append(k)
        if x["layers"] != y["layers"]:
            relayered.append(k)
        if x["net"] != y["net"]:
            renetted.append((k, x["net"], y["net"]))

    r.check("pad positions", not moved, f"{len(pa)} pads within {TOL} mm")
    for k, u, v in moved[:6]:
        r.note(f"{k[0]}.{k[1]}  {u}  vs  {v}")
    r.check("pad sizes", not resized)
    r.check("pad layers", not relayered)
    r.check("pad nets", not renetted, f"{len(set(v['net'] for v in pa.values()))} nets")
    for k, u, v in renetted[:6]:
        r.note(f"{k[0]}.{k[1]}  {u}  vs  {v}")

    # ---- connectivity ------------------------------------------------------
    # The nets could match pad for pad and still describe a different circuit if the
    # rebuild grouped them differently, so compare the GROUPS: for each net, the set
    # of pads on it. On a 1:1 riser every group must be exactly {J1.n, J2.n}.
    def groups(tbl):
        out = {}
        for (ref, num), v in tbl.items():
            out.setdefault(v["net"], set()).add((ref, num))
        return out

    ga, gb = groups(pa), groups(pb)
    r.check("net membership", ga == gb, f"{len(ga)} nets")
    for net in sorted(set(ga) | set(gb)):
        if ga.get(net) != gb.get(net):
            r.note(f"{net}: {sorted(ga.get(net, []))} vs {sorted(gb.get(net, []))}")
    straight = {n: v for n, v in ga.items()
                if len(v) == 2 and len({num for _, num in v}) == 1}
    r.check("1:1 pass-through", len(straight) == len(ga),
            f"{len(straight)}/{len(ga)} nets join J1 pin N to J2 pin N")

    # ---- holes -------------------------------------------------------------
    ha, hb = hole_table(new), hole_table(old)
    r.check("mounting holes", ha == hb,
            ", ".join(f"{k} d{v}" for k, v in sorted(ha.items())))
    if ha != hb:
        r.note(f"rebuild: {sorted(ha.items())}")
        r.note(f"released: {sorted(hb.items())}")

    # ---- silkscreen --------------------------------------------------------
    sa, sb = silk_table(new), silk_table(old)
    r.check("silk texts", set(sa) == set(sb), f"{len(sa)} texts")
    for t in sorted(set(sa) & set(sb)):
        u, v = sa[t], sb[t]
        diffs = [k for k in ("x", "y", "angle", "sx", "sy", "th")
                 if abs(u[k] - v[k]) >= TOL]
        if u["layer"] != v["layer"]:
            diffs.append("layer")
        r.check(f"silk {t!r}", not diffs,
                "" if not diffs else f"differs in {', '.join(diffs)}")
        if diffs:
            r.note(f"rebuild {u}")
            r.note(f"released {v}")

    # ---- reported, not required -------------------------------------------
    na, la, pla = track_stats(new)
    nb, lb, plb = track_stats(old)
    r.note(f"copper: rebuild {na} segments / {la:.1f} mm  "
           f"({', '.join(f'{k} {v}' for k, v in sorted(pla.items()))})")
    r.note(f"copper: released {nb} segments / {lb:.1f} mm  "
           f"({', '.join(f'{k} {v}' for k, v in sorted(plb.items()))})"
           "   — re-derived by route.py, not copied")
    r.note(f"thickness: rebuild {mm(new.GetDesignSettings().GetBoardThickness())} mm, "
           f"released {mm(old.GetDesignSettings().GetBoardThickness())} mm")

    print(f"generated : {args.generated}")
    print(f"released  : {args.original}")
    print(f"tolerance : {TOL} mm")
    print()
    for line in r.lines:
        print(line)
    print()
    if r.fails:
        print(f"{len(r.fails)} DIFFERENCE(S): {', '.join(r.fails)}")
        return 1
    print("The rebuild is geometrically and electrically identical to the "
          "released board.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
