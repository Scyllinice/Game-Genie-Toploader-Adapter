#!/usr/bin/env python3
"""Generate the board — gg_toploader.kicad_pcb, placed and netted but UNROUTED.

  python3 gen_board.py [-o FILE]

Produces:
  * the measured Edge.Cuts outline
  * a 2-layer, 1.2 mm stack (cartridge thickness, not KiCad's 1.6 mm default)
  * J2, the board's own gold fingers, and J1, the Game Genie connector land
  * both mounting holes and all three silkscreen texts
  * 72 nets, each landing on exactly two pads — J1 pin N and J2 pin N

Copper between those pads is route.py's job, and it is a separate step because this
generator builds the board FROM SCRATCH every time — so running it discards routing.
The Makefile keeps the order straight; guard_routed.py refuses to overwrite a routed
board by accident.

The pass-through is 1:1 BY CONSTRUCTION. Both connectors take their nets from
pinout.NETS keyed on pin number, so there is no table of "J1 pin 5 goes to J2 pin 5"
that could be mistyped — the two pads get the same net object because they look it up
with the same key.
"""

import argparse
import os
import sys

import pcbnew

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import geometry as G      # noqa: E402
import pinout as P        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
EDGE_LIB = os.path.join(HERE, "lib", "gg_adapter.pretty")
STOCK = "/usr/share/kicad/footprints"

MM = pcbnew.FromMM


def V(x, y):
    """Absolute board coordinates — see the note in geometry.py about the datum."""
    return pcbnew.VECTOR2I(MM(x), MM(y))


def load_fp(board, libpath, name):
    fp = pcbnew.FootprintLoad(libpath, name)
    if fp is None:
        raise RuntimeError(f"could not load footprint {name} from {libpath}")
    board.Add(fp)
    return fp


def add_outline(board):
    for (x1, y1, x2, y2) in G.outline_segments():
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(V(x1, y1))
        seg.SetEnd(V(x2, y2))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(MM(0.1))
        board.Add(seg)


H_JUSTIFY = {"left": pcbnew.GR_TEXT_H_ALIGN_LEFT,
             "right": pcbnew.GR_TEXT_H_ALIGN_RIGHT,
             "center": pcbnew.GR_TEXT_H_ALIGN_CENTER}
V_JUSTIFY = {"top": pcbnew.GR_TEXT_V_ALIGN_TOP,
             "bottom": pcbnew.GR_TEXT_V_ALIGN_BOTTOM,
             "center": pcbnew.GR_TEXT_V_ALIGN_CENTER}


def add_silk(board):
    for (text, x, y, angle, size_a, size_b, thick, justify) in G.SILK:
        t = pcbnew.PCB_TEXT(board)
        t.SetText(text)
        t.SetLayer(pcbnew.F_SilkS)
        t.SetPosition(V(x, y))
        t.SetTextAngleDegrees(angle)
        # TWO ORDERING TRAPS IN THREE LINES.
        #
        # VECTOR2I takes the two text dimensions in the OPPOSITE order to the one the
        # .kicad_pcb writes them in, so copying `(size 1.5 0.9)` straight out of the
        # released file transposes the text: the long designation string is condensed
        # to fit along the left edge, and transposed it comes out short and fat and
        # overruns the board — which DRC reports as "silkscreen clipped by board edge"
        # rather than as the transposition it is.
        #
        # SetBold() RECOMPUTES thickness from the size, so it has to come FIRST.
        # Called afterwards it replaced the measured 0.125 mm with KiCad's 0.18 mm.
        t.SetBold(True)
        t.SetTextSize(pcbnew.VECTOR2I(MM(size_b), MM(size_a)))
        t.SetTextThickness(MM(thick))
        parts = justify.split()
        t.SetHorizJustify(H_JUSTIFY.get(parts[0], pcbnew.GR_TEXT_H_ALIGN_CENTER))
        t.SetVertJustify(V_JUSTIFY[parts[-1]])
        board.Add(t)


def add_keepouts(board):
    """Rule areas over the two milled edges — the bevel zone and the wipe path.

    WHY THIS EXISTS, AND IT IS NOT BELT-AND-BRACES: KiCad's copper-to-edge check does
    not look at pads. Measured on this board with the rule cranked to 5 mm, the
    violation list is TRACKS ONLY — 16 of them, not one pad, on a board where all 144
    pads are inside 5 mm of an edge. So the fingers and the connector land are
    unchecked against the board outline by DRC, at any setting.

    A rule area does not fix that (it also permits pads), but it fixes the part that
    is fixable: nothing may ever be ROUTED into these bands. Two reasons to care,
    both specific to a card edge —

      1. The bevel. A 45-degree gold-finger chamfer takes about 0.6 mm off the top
         surface at the insertion edge. Copper inside that is copper the mill cuts
         through.
      2. The wipe path. The console's contacts enter at the insertion edge and slide
         up the finger on every insertion, sweeping the whole strip. A track crossing
         it shorts to each contact that passes over, and the mask covering it wears.

    The band at the Game Genie end is the same idea without the bevel: it is a milled
    edge, and copper wants to stay off it.

    check_fingers.py measures what the rule areas cannot enforce — how close the PADS
    come to each edge — because that is the half DRC drops.
    """
    def rule_area(name, x0, y0, x1, y1):
        ko = pcbnew.ZONE(board)
        ko.SetIsRuleArea(True)
        ko.SetDoNotAllowTracks(True)
        ko.SetDoNotAllowVias(True)
        # RENAMED IN KICAD 10: SetDoNotAllowCopperPour -> SetDoNotAllowZoneFills.
        # The generators run on 9 and 10 (see check_toolchain.py) and calling the
        # missing one is an AttributeError at generation time, not a warning.
        if hasattr(ko, "SetDoNotAllowZoneFills"):
            ko.SetDoNotAllowZoneFills(True)
        else:
            ko.SetDoNotAllowCopperPour(True)
        ko.SetLayerSet(pcbnew.LSET.AllCuMask())
        ko.SetZoneName(name)
        ko.Outline().NewOutline()
        for (x, y) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            ko.Outline().Append(MM(x), MM(y))
        board.Add(ko)
        return ko

    areas = [
        # Insertion edge: from the finger ends out past the board edge, full tongue.
        rule_area("bevel/wipe zone",
                  G.TONGUE_LEFT, G.FINGER_PAD_TIP,
                  G.TONGUE_RIGHT, G.INSERTION_EDGE_Y + 1.0),
        # Game Genie end: from the connector pads out past the top edge.
        rule_area("top edge",
                  G.BODY_LEFT, G.BODY_TOP - 1.0,
                  G.BODY_RIGHT, G.GG_PAD_TOP),
    ]
    return areas


STACKUP = f"""\t\t(stackup
\t\t\t(layer "F.SilkS" (type "Top Silk Screen"))
\t\t\t(layer "F.Paste" (type "Top Solder Paste"))
\t\t\t(layer "F.Mask" (type "Top Solder Mask") (thickness {G.MASK_THICKNESS}))
\t\t\t(layer "F.Cu" (type "copper") (thickness {G.COPPER_THICKNESS}))
\t\t\t(layer "dielectric 1" (type "core") (thickness {G.CORE_THICKNESS})
\t\t\t\t(material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
\t\t\t(layer "B.Cu" (type "copper") (thickness {G.COPPER_THICKNESS}))
\t\t\t(layer "B.Mask" (type "Bottom Solder Mask") (thickness {G.MASK_THICKNESS}))
\t\t\t(layer "B.Paste" (type "Bottom Solder Paste"))
\t\t\t(layer "B.SilkS" (type "Bottom Silk Screen"))
\t\t\t(copper_finish "ENIG")
\t\t\t(dielectric_constraints no)
\t\t)
"""


def add_stackup(path):
    """Write the physical stack into the saved file.

    SetBoardThickness() records 1.2 mm in `(general (thickness ...))`, which is what
    the 3D view and length calculations read. It does NOT produce a stackup block —
    pcbnew only writes one if the board already carries a custom stack, and there is
    no Python binding for the stackup editor. The stackup is what ends up in the
    gerber job file, so without it the fab is told nothing about the board it is
    making. On a cartridge that is not a detail: 1.2 mm is the NES card thickness and
    a 1.6 mm board splays the console's contacts.

    copper_finish is ENIG here where the released board says "None". That is a
    deliberate change, not a transcription error — the README already tells builders
    to order ENIG with gold fingers, and putting it in the stackup is how the
    instruction reaches the fab instead of living in a text file on GitHub.
    """
    with open(path) as f:
        text = f.read()
    anchor = "\t\t(pad_to_mask_clearance"
    if "(stackup" in text or anchor not in text:
        return False
    text = text.replace(anchor, STACKUP + anchor, 1)
    with open(path, "w") as f:
        f.write(text)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=os.path.join(HERE, "gg_toploader.kicad_pcb"))
    args = ap.parse_args()

    problems = G.check() + P.check()
    if problems:
        for p in problems:
            print("FAIL:", p)
        return 1

    board = pcbnew.CreateEmptyBoard()
    board.SetCopperLayerCount(G.COPPER_LAYERS)
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(G.COPPER_LAYERS)
    ds.SetBoardThickness(MM(G.BOARD_THICKNESS))

    add_outline(board)

    # ---- the two 72-way fields --------------------------------------------
    fingers = load_fp(board, EDGE_LIB, G.FP_FINGERS)
    fingers.SetPosition(V(*G.FINGER_ORIGIN))
    fingers.SetReference(G.REF_FINGERS)
    fingers.SetValue(G.FP_FINGERS)

    gg = load_fp(board, EDGE_LIB, G.FP_GG)
    gg.SetPosition(V(*G.GG_ORIGIN))
    gg.SetReference(G.REF_GG)
    # The VALUE is the orderable part number, not the footprint name. gen_bom.py
    # reads the board, and "GG_2x36_2.54mm_Edge" is not something a distributor
    # stocks — this board's entire BOM is this one line.
    gg.SetValue(G.GG_PART)

    # BOTH DESIGNATORS HIDDEN, as on the released board.
    #
    # Tried visible first, and there is nowhere for them to go: each footprint is
    # 89 x 14 mm of pad field, the corridor between them is 11.8 mm of routing, and
    # the three silk texts already occupy the free space. DRC reported the result
    # exactly — J1's label over J1's own mask openings, J2's label on top of the
    # "NES" text. Hiding them costs nothing here: a two-connector board where one
    # connector is the board's own edge cannot be misassembled by designator, and
    # the "Game Genie" / "NES" silk says which end is which, which is the question a
    # builder actually has.
    for fp in (fingers, gg):
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)

    # ---- mounting holes ----------------------------------------------------
    for ref, x, y in G.MOUNT_HOLES:
        mh = load_fp(board, os.path.join(STOCK, "MountingHole.pretty"),
                     "MountingHole_2.1mm")
        mh.SetPosition(V(x, y))
        mh.SetReference(ref)
        mh.Reference().SetVisible(False)
        mh.Value().SetVisible(False)

    add_silk(board)
    keepouts = add_keepouts(board)

    # ---- nets --------------------------------------------------------------
    netmap = {}
    for pin in P.PIN_NUMBERS:
        name = P.NETS[pin]
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netmap[name] = ni

    applied = 0
    for fp in (fingers, gg):
        for pad in fp.Pads():
            pin = int(pad.GetNumber())
            pad.SetNet(netmap[P.NETS[pin]])
            applied += 1

    # Stamp the track count generation itself produced — zero here, but the guard
    # reads it rather than assuming, so it keeps working if this ever fans out.
    board.GetTitleBlock().SetComment(8, f"generated-tracks={len(board.GetTracks())}")
    board.GetTitleBlock().SetTitle("Game Genie Toploader Adapter")
    board.GetTitleBlock().SetComment(1, "generated by pcb/gen_board.py — do not hand-edit")

    pcbnew.SaveBoard(args.out, board)
    stackup_ok = add_stackup(args.out)

    # ---- report ------------------------------------------------------------
    pads = {}
    for fp in (fingers, gg):
        for pad in fp.Pads():
            pads.setdefault(pad.GetNetname(), []).append(fp.GetReference())
    lonely = {n: v for n, v in pads.items() if len(v) != 2}

    print(f"wrote {args.out}")
    print(f"  outline  : {len(G.OUTLINE)} corners, {G.BOARD_W:.3f} x {G.BOARD_H:.3f} mm")
    print(f"  stack    : {G.COPPER_LAYERS} layers, {G.BOARD_THICKNESS} mm"
          f"{'' if stackup_ok else '  (STACKUP PATCH FAILED)'}")
    print(f"  {G.REF_FINGERS}       : {len(fingers.Pads())} fingers @ {G.FINGER_PITCH} mm")
    print(f"  {G.REF_GG}       : {len(gg.Pads())} pads @ {G.GG_PITCH} mm  ({G.GG_PART})")
    print(f"  holes    : {len(G.MOUNT_HOLES)} x {G.MOUNT_DRILL} mm")
    print(f"  silk     : {len(G.SILK)} texts")
    print(f"  keepouts : {len(keepouts)} rule areas — "
          + ", ".join(k.GetZoneName() for k in keepouts))
    print(f"  nets     : {len(netmap)} nets, {applied} pads connected")
    if lonely:
        print(f"  FAIL     : {len(lonely)} nets do not land on exactly two pads")
        for n, v in sorted(lonely.items())[:8]:
            print(f"             {n} -> {v}")
        return 1
    print("  every net lands on exactly one J1 pad and one J2 pad")
    return 0


if __name__ == "__main__":
    sys.exit(main())
