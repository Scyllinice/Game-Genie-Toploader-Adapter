#!/usr/bin/env python3
"""Card-edge checks KiCad's DRC does not do.

  python3 check_fingers.py [BOARD]

DRC grades copper against copper. A card edge fails in ways that are all legal by
those rules: fingers on the wrong pitch still clear each other, copper in the bevel
zone still clears the outline, silk in the contact path still clears the mask. This
measures the things that are specific to a board whose edge IS a connector.

  pitch / width      every finger identical and evenly spaced, both fields
  registration       finger N and finger N+36 share an X, front to back
  bevel zone         no copper within reach of the chamfer at the insertion edge
  wipe path          nothing between the finger ends and the insertion edge —
                     the console's contacts sweep that strip on every insertion
  silk               no silkscreen on the insertion surface, for the same reason
  mask               every finger opens its own mask window
  edge clearance     fingers to the sides of the tongue, and — the one KiCad drops —
                     every pad to the milled board edge

Warnings are printed and counted; the exit code is non-zero only for hard failures,
so this can run in the default `make` without blocking on advisory notes.
"""

import argparse
import os
import sys

import pcbnew

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import geometry as G      # noqa: E402
import pinout as P        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# How far a gold-finger bevel reaches back from the edge on each face. A 45 degree
# chamfer to half thickness on a 1.2 mm board takes 0.6 mm; fabs quote 0.3-0.9 mm
# depending on angle and how much land they leave. 0.6 mm is the working number and
# the one that decides whether this board's 0.62 mm finger setback is a margin or a
# coincidence — it is a 0.02 mm margin, which is worth knowing before ordering.
BEVEL_REACH = 0.6

# The hard floor for copper to a ROUTED edge — below this a fab either refuses the
# board or trims copper. It is deliberately not the project's own 0.5 mm rule: the
# released connector land sits at 0.37 mm and has been fabricated and sold, so 0.5 is
# the aspiration and this is the line that actually means "do not build it".
FAB_EDGE_FLOOR = 0.20


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board", nargs="?",
                    default=os.path.join(HERE, "gg_toploader.kicad_pcb"))
    args = ap.parse_args()
    board = pcbnew.LoadBoard(args.board)

    fails, warns, notes = [], [], []

    pads = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        for pad in fp.Pads():
            if pad.GetNumber().isdigit():
                pads[(ref, int(pad.GetNumber()))] = pad

    # ---- pitch, width, alignment ------------------------------------------
    for ref, pitch, label in ((G.REF_FINGERS, G.FINGER_PITCH, "fingers"),
                              (G.REF_GG, G.GG_PITCH, "connector land")):
        for lo, hi in ((1, 36), (37, 72)):
            xs = [pcbnew.ToMM(pads[(ref, n)].GetPosition().x) for n in range(lo, hi + 1)]
            steps = {round(xs[i] - xs[i + 1], 4) for i in range(len(xs) - 1)}
            if steps != {pitch}:
                fails.append(f"{ref} pins {lo}-{hi}: pitch is {sorted(steps)}, "
                             f"expected {pitch}")
            ys = {round(pcbnew.ToMM(pads[(ref, n)].GetPosition().y), 4)
                  for n in range(lo, hi + 1)}
            if len(ys) != 1:
                fails.append(f"{ref} pins {lo}-{hi}: not on one line, y = {sorted(ys)}")
            sizes = {(round(pcbnew.ToMM(pads[(ref, n)].GetSize().x), 4),
                      round(pcbnew.ToMM(pads[(ref, n)].GetSize().y), 4))
                     for n in range(lo, hi + 1)}
            if len(sizes) != 1:
                fails.append(f"{ref} pins {lo}-{hi}: mixed pad sizes {sorted(sizes)}")
        # Front to back registration.
        off = {round(pcbnew.ToMM(pads[(ref, n)].GetPosition().x)
                     - pcbnew.ToMM(pads[(ref, n + 36)].GetPosition().x), 4)
               for n in range(1, 37)}
        if off != {0.0}:
            fails.append(f"{ref}: front and back rows are offset by {sorted(off)} mm")
        else:
            notes.append(f"{ref} {label}: 72 pads, {pitch} mm pitch, front/back "
                         f"registered")

    # ---- layers ------------------------------------------------------------
    for (ref, n), pad in pads.items():
        want = pcbnew.F_Cu if n <= 36 else pcbnew.B_Cu
        other = pcbnew.B_Cu if n <= 36 else pcbnew.F_Cu
        if not pad.IsOnLayer(want) or pad.IsOnLayer(other):
            fails.append(f"{ref}.{n} is not on {G.layer_of(n)} alone")
        mask = pcbnew.F_Mask if n <= 36 else pcbnew.B_Mask
        if not pad.IsOnLayer(mask):
            fails.append(f"{ref}.{n} has no solder mask opening — a finger under "
                         f"mask is a finger that does not connect")

    # ---- the insertion edge -----------------------------------------------
    tip = max(pcbnew.ToMM(pads[(G.REF_FINGERS, n)].GetPosition().y)
              + pcbnew.ToMM(pads[(G.REF_FINGERS, n)].GetSize().y) / 2
              for n in range(1, 73))
    setback = G.INSERTION_EDGE_Y - tip
    notes.append(f"finger ends sit {setback:.3f} mm back from the insertion edge; "
                 f"a {BEVEL_REACH} mm bevel reaches "
                 f"{abs(BEVEL_REACH - setback):.3f} mm "
                 f"{'past them' if BEVEL_REACH > setback else 'short of them'}")
    if setback < BEVEL_REACH:
        warns.append(f"the bevel may cut into the finger ends "
                     f"({setback:.3f} mm setback vs {BEVEL_REACH} mm reach) — tell "
                     f"the fab the fingers are {setback:.2f} mm short of the edge")

    # ---- the wipe path -----------------------------------------------------
    # The strip between the finger ends and the board edge is swept by every contact
    # on every insertion. Copper there shorts to each contact as it passes; silk
    # there wears off and, on the way, holds the contact off the finger.
    wipe_y = tip
    for t in board.GetTracks():
        for pt in (t.GetStart(), t.GetEnd()):
            if pcbnew.ToMM(pt.y) > wipe_y + 1e-6:
                fails.append(f"track on net {t.GetNetname()} enters the wipe path at "
                             f"y {pcbnew.ToMM(pt.y):.3f} (edge is "
                             f"{G.INSERTION_EDGE_Y})")
                break
    for d in board.GetDrawings():
        if not isinstance(d, pcbnew.PCB_TEXT):
            continue
        if d.GetLayer() not in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            continue
        box = d.GetBoundingBox()
        if pcbnew.ToMM(box.GetBottom()) > G.TONGUE_ROOT_Y + 1e-6:
            warns.append(f"silk {d.GetText()!r} reaches y "
                         f"{pcbnew.ToMM(box.GetBottom()):.3f}, past the tongue root "
                         f"at {G.TONGUE_ROOT_Y} — that is the insertion surface")

    # ---- fingers to the sides of the tongue -------------------------------
    left = min(pcbnew.ToMM(pads[(G.REF_FINGERS, n)].GetPosition().x)
               - pcbnew.ToMM(pads[(G.REF_FINGERS, n)].GetSize().x) / 2
               for n in range(1, 73)) - G.TONGUE_LEFT
    right = G.TONGUE_RIGHT - max(
        pcbnew.ToMM(pads[(G.REF_FINGERS, n)].GetPosition().x)
        + pcbnew.ToMM(pads[(G.REF_FINGERS, n)].GetSize().x) / 2
        for n in range(1, 73))
    notes.append(f"outer fingers clear the tongue sides by {left:.3f} mm (left) and "
                 f"{right:.3f} mm (right)")
    for side, v in (("left", left), ("right", right)):
        if v < G.EDGE_CLEARANCE:
            warns.append(f"outer finger is {v:.3f} mm from the {side} tongue edge, "
                         f"inside the {G.EDGE_CLEARANCE} mm rule")

    # ---- pad to board edge, because KiCad will not -------------------------
    #
    # THE COPPER-TO-EDGE CHECK IN DRC DOES NOT LOOK AT PADS. Measured on this board:
    # set min_copper_edge_clearance to 5 mm — far enough that all 144 pads are inside
    # it — and the violation list comes back with 16 items, every one of them a TRACK.
    # Not one pad, at any setting. On an ordinary board that is a curiosity; on a card
    # edge, the pads ARE the thing nearest the milled edge, so the check that matters
    # is the one that does not run.
    #
    # The rule areas gen_board.py writes cannot cover this either — a keepout stops
    # tracks and vias, and permits pads. So it is measured here.
    edges = G.outline_segments()

    def pt_seg(px, py, ax, ay, bx, by):
        vx, vy = bx - ax, by - ay
        L = vx * vx + vy * vy
        t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L))
        return ((px - (ax + t * vx)) ** 2 + (py - (ay + t * vy)) ** 2) ** 0.5

    def pad_edge_gap(pad):
        cx, cy = pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)
        w, h = pcbnew.ToMM(pad.GetSize().x), pcbnew.ToMM(pad.GetSize().y)
        x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
        best = 9e9
        for (ax, ay, bx, by) in edges:
            for i in range(21):
                f = i / 20.0
                for (px, py) in ((x0 + f * (x1 - x0), y0), (x0 + f * (x1 - x0), y1),
                                 (x0, y0 + f * (y1 - y0)), (x1, y0 + f * (y1 - y0))):
                    best = min(best, pt_seg(px, py, ax, ay, bx, by))
        return best

    gaps = sorted((pad_edge_gap(p), ref, n) for (ref, n), p in pads.items())
    worst, wref, wnum = gaps[0]
    tight = [f"{r}.{n}" for g, r, n in gaps if g < G.EDGE_CLEARANCE - 1e-6]
    notes.append(f"closest pad to a board edge: {wref}.{wnum} at {worst:.4f} mm "
                 f"(DRC does not check this — see the comment in this file)")
    if tight:
        notes.append(f"{len(tight)} pads sit inside the {G.EDGE_CLEARANCE} mm "
                     f"copper-to-edge rule: {', '.join(tight[:6])}"
                     + (" ..." if len(tight) > 6 else ""))
        notes.append("  as released, and as fabricated and sold — the connector land "
                     "is where it has to be for the part to fit. Noted, not changed.")
    if worst < FAB_EDGE_FLOOR:
        fails.append(f"{wref}.{wnum} is {worst:.4f} mm from the board edge, under the "
                     f"{FAB_EDGE_FLOOR} mm a fab can hold on a routed edge")

    # ---- the Game Genie end ------------------------------------------------
    top = min(pcbnew.ToMM(pads[(G.REF_GG, n)].GetPosition().y)
              - pcbnew.ToMM(pads[(G.REF_GG, n)].GetSize().y) / 2
              for n in range(1, 73))
    notes.append(f"connector pads start {top - G.BODY_TOP:.3f} mm from the top edge, "
                 f"{len(P.PIN_NUMBERS)} of them at {G.GG_PITCH} mm")

    print(f"card-edge check: {os.path.basename(args.board)}")
    for n in notes:
        print(f"  note  {n}")
    for w in warns:
        print(f"  WARN  {w}")
    for f in fails:
        print(f"  FAIL  {f}")
    print(f"  {len(fails)} failures, {len(warns)} warnings")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
