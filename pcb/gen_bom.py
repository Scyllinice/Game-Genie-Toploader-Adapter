#!/usr/bin/env python3
"""BOM and build notes, read off the board.

  python3 gen_bom.py [BOARD] [-o FILE]

Reads the BOARD, not the schematic, because the board is what gets fabricated — and
the value the board carries is what a BOM built from it will say. A footprint whose
value was never set produces a BOM line naming the PACKAGE instead of the PART, which
looks like a BOM right up until someone tries to order from it.

Two things on this board are NOT line items and are filtered out by attribute rather
than by name:
  * J2, the gold fingers — copper on the board itself, nothing to buy
  * the mounting holes — holes
Which leaves exactly one purchasable part, and this file exists to say so precisely.
"""

import argparse
import csv
import os
import sys

import pcbnew

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import geometry as G      # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# THESE NOTES GO IN A FILE, not just to the terminal.
#
# Two of them are fab instructions that no gerber can carry. The gerber job file
# records the surface finish, because the stackup declares ENIG — but there is no
# field anywhere in the format for "bevel the gold fingers", and a fab that is not
# told will send back a board with square-edged contacts that chew the console's
# connector. Printing that to stdout at the end of `make fab` puts it in a terminal
# nobody reads twice; fab/FABNOTES.txt goes in the zip with the gerbers.
FAB_NOTES = f"""\
{'=' * 72}
FABRICATION NOTES — Game Genie Toploader Adapter
{'=' * 72}

1.  GOLD FINGERS, BEVELLED, on the card edge at the bottom of the board (the
    72 contacts on the tongue, both faces). Specify the gold-finger process,
    not just the surface finish — the bevel is a separate operation and it is
    what lets the board enter the console's connector without shaving it.

    The finger ends stop {G.FINGER_TIP_SETBACK:.2f} mm short of the board edge. A 45-degree
    bevel reaches roughly 0.6 mm, so it clears them by about 0.02 mm. If your
    process takes more than that, say so before building.

2.  SURFACE FINISH: ENIG. Declared in the stackup and in the gerber job file.
    HASL works and is cheaper, but it wears off the contacts over time and
    takes the console's connector with it.

3.  BOARD THICKNESS: {G.BOARD_THICKNESS} mm. NOT the 1.6 mm default. This is the NES
    cartridge thickness and the console's edge connector is sprung for it;
    1.6 mm splays the contacts permanently.

4.  LAYERS: {G.COPPER_LAYERS}. Copper {G.COPPER_THICKNESS * 1000:.0f} um, core {G.CORE_THICKNESS} mm.

5.  ASSEMBLY: one part, J1 — a 2x36 2.54 mm card-edge connector ({G.GG_PART} or
    equivalent), hand-soldered to the TOP side. Its pins are bent inward to
    clamp the {G.BOARD_THICKNESS} mm board and lap-soldered to the pads on both faces.
    Not an SMT job; there is no paste layer on this board.

Copper-to-edge on the J1 land is {0.37:.2f} mm at its tightest, which is inside this
project's own 0.5 mm rule and is as-released — the connector has to sit where
it sits. Every board so far has been built this way.
"""

NOTES = FAB_NOTES.strip().splitlines()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board", nargs="?",
                    default=os.path.join(HERE, "gg_toploader.kicad_pcb"))
    ap.add_argument("-o", "--out", default=os.path.join(HERE, "fab", "bom.csv"))
    args = ap.parse_args()

    board = pcbnew.LoadBoard(args.board)
    rows = {}
    skipped = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        pads = list(fp.Pads())
        if all(p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH for p in pads) and pads:
            skipped.append(f"{ref} (hole)")
            continue
        if ref == G.REF_FINGERS:
            skipped.append(f"{ref} (the board's own card edge)")
            continue
        key = (fp.GetValue(), fp.GetFPIDAsString())
        rows.setdefault(key, []).append(ref)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Qty", "Value", "Footprint", "Designators"])
        for (value, fpid), refs in sorted(rows.items()):
            w.writerow([len(refs), value, fpid, " ".join(sorted(refs))])

    print(f"wrote {args.out}")
    for (value, fpid), refs in sorted(rows.items()):
        print(f"  {len(refs)} x {value:<14} {fpid}   [{' '.join(sorted(refs))}]")
    print(f"  not ordered: {', '.join(skipped)}")

    notes_path = os.path.join(os.path.dirname(args.out), "FABNOTES.txt")
    with open(notes_path, "w") as f:
        f.write(FAB_NOTES)
    print(f"wrote {notes_path}")
    print()
    print("  " + "\n  ".join(FAB_NOTES.strip().splitlines()[:6]))
    print("  ...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
