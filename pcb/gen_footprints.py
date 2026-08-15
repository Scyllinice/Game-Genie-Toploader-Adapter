#!/usr/bin/env python3
"""Generate the two 72-way pad fields as .kicad_mod files.

  python3 gen_footprints.py [-o OUTDIR]

Writes lib/gg_adapter.pretty/
  NES_CART_FINGERS.kicad_mod      the board's own gold fingers, 2.50 mm pitch
  GG_2x36_2.54mm_Edge.kicad_mod   land pattern for the TE 5530843-8 edge connector

Written as TEXT rather than through pcbnew. The .kicad_mod S-expression schema is
stable and small, and a text generator stays readable and diffs cleanly; pcbnew earns
its keep in gen_board.py, where nets and connectivity need a real board model.

Pad type is `connect`, not `smd`: connector pads take no solder paste. On the fingers
that is the difference between a plated edge and a stencil aperture over the contact
surface; on J1 the pins are hand-soldered. Neither field belongs on a paste layer.

The two footprints differ in exactly one number — the pitch — so they are emitted by
one function. That is the point of generating them: the released library has them as
two hand-drawn files, and nothing kept the 144 pads in step.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import geometry as G      # noqa: E402
import pinout as P        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "lib", "gg_adapter.pretty")


def fmt(v: float) -> str:
    return f"{v:.4f}".rstrip("0").rstrip(".") or "0"


def generate(name: str, descr: str, tags: str, pin1_x: float, pitch: float) -> str:
    out = []
    a = out.append

    a(f'(footprint "{name}"')
    a("  (version 20240108)")
    a('  (generator "gen_footprints.py")')
    a('  (generator_version "9.0")')
    a('  (layer "F.Cu")')
    a("  (attr smd)")
    a(f'  (descr "{descr}")')
    a(f'  (tags "{tags}")')

    # Reference and value clear of the pad field on both sides (the field is 14 mm
    # tall and centred on the origin, so anything inside it lands on copper).
    a('  (property "Reference" "REF**"')
    a(f"    (at 0 {fmt(-G.PAD_H / 2 - 1.6)} 0)")
    a('    (layer "F.SilkS")')
    a("    (effects (font (size 1.2 1.2) (thickness 0.2)))")
    a("  )")
    a(f'  (property "Value" "{name}"')
    a(f"    (at 0 {fmt(G.PAD_H / 2 + 1.6)} 0)")
    a('    (layer "F.Fab")')
    a("    (effects (font (size 1 1) (thickness 0.15)))")
    a("  )")

    # ---- pads --------------------------------------------------------------
    # 36 front, 36 back, pin N+36 directly behind pin N. Each pad opens its own
    # mask window, the way the released board does it. The alternative — one aperture
    # over the whole field, bare copper between the fingers, which is what a real
    # cartridge has — buys nothing here and costs a solder_mask_bridge violation per
    # finger pair: the mask webs left between fingers sit where the console's contacts
    # never touch.
    for pin in P.PIN_NUMBERS:
        layer = G.layer_of(pin)
        mask = layer.replace(".Cu", ".Mask")
        x = pin1_x - pitch * ((pin - 1) % 36)
        a(f'  (pad "{pin}" connect rect')
        a(f"    (at {fmt(x)} 0)")
        a(f"    (size {fmt(G.PAD_W)} {fmt(G.PAD_H)})")
        a(f'    (layers "{layer}" "{mask}")')
        a("  )")

    # ---- courtyard ---------------------------------------------------------
    # Not in the released footprints, and the one thing added here. It is invisible
    # to the fab (no gerber carries F.CrtYd) but it gives check_placement-style
    # checks and KiCad's own courtyard DRC something to measure, and it is how
    # gen_board.py can assert the two fields do not overlap.
    x0 = pin1_x - pitch * 35 - G.PAD_W / 2
    x1 = pin1_x + G.PAD_W / 2
    y0, y1 = -G.PAD_H / 2, G.PAD_H / 2
    for layer in ("F.CrtYd", "B.CrtYd"):
        a(f"  (fp_rect (start {fmt(x0)} {fmt(y0)}) (end {fmt(x1)} {fmt(y1)})")
        a(f'    (stroke (width 0.05) (type solid)) (fill none) (layer "{layer}"))')

    a(")")
    return "\n".join(out) + "\n"


def fingers() -> str:
    return generate(
        G.FP_FINGERS,
        "NES 72-pin cartridge edge fingers, 2.50 mm pitch. The board's own card "
        "edge — goes into the console. Specify gold fingers (bevel + hard gold).",
        "NES cartridge card-edge gold fingers 72-pin",
        G.FINGER_PIN1_X, G.FINGER_PITCH)


def gg_connector() -> str:
    return generate(
        G.FP_GG,
        f"Land pattern for a 2x36 2.54 mm card-edge connector ({G.GG_PART} or "
        "equivalent), pins bent over and lap-soldered to a 1.2 mm board.",
        "edge connector 2x36 72-pin 2.54mm TE 5530843-8",
        G.GG_PIN1_X, G.GG_PITCH)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--outdir", default=DEFAULT_OUT)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    for name, text in ((G.FP_FINGERS, fingers()), (G.FP_GG, gg_connector())):
        path = os.path.join(args.outdir, f"{name}.kicad_mod")
        with open(path, "w") as f:
            f.write(text)
        pads = text.count("(pad ")
        print(f"wrote {path}  ({pads} pads)")


if __name__ == "__main__":
    main()
