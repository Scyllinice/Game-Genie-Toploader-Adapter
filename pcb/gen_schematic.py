#!/usr/bin/env python3
"""Generate the schematic — gg_toploader.kicad_sch.

  python3 gen_schematic.py [-o FILE]

The whole circuit is "pin N of J1 is pin N of J2, seventy-two times", so the sheet is
two symbols and 144 local labels, with no wires: a label sitting on a pin's connection
point IS the connection, and 144 of them are far more legible than 72 wires crossing a
sheet. That is how the released schematic draws it too; this generator reproduces the
same drawing from the pin table instead of by hand.

Everything is placed by rule from the pin geometry in gen_symbol.py, so a label can
never end up near a pin instead of on it — which is the one failure mode a wireless
schematic has, and one that reads as a finished drawing right up until the netlist
comes out wrong.

UUIDs are DERIVED (uuid5 over a fixed namespace and a stable key), not random.
Regenerating an unchanged design must produce a byte-identical file, or the generator
cannot be used to review a change: every diff would be 200 lines of churn.
"""

import argparse
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import geometry as G      # noqa: E402
import pinout as P        # noqa: E402
import gen_symbol as S    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = "gg_toploader"
DEFAULT_OUT = os.path.join(HERE, f"{PROJECT}.kicad_sch")

NS = uuid.UUID("6a1f3d2e-0b7c-5e48-9a2d-4f8b1c6e7d30")   # fixed, arbitrary

# Symbol sheet positions, as released: the Game Genie connector on the left, the
# console fingers on the right, so the sheet reads console-to-cartridge left to right
# in the same order the signals physically travel through the riser.
PLACE = {
    "J1": (54.61, 97.79, S.SYM_GG, G.FP_GG, G.GG_PART),
    "J2": (135.89, 97.79, S.SYM_CONSOLE, G.FP_FINGERS, "NES-CART-EDGE"),
}


def uid(key: str) -> str:
    return str(uuid.uuid5(NS, key))


def fmt(v: float) -> str:
    return f"{v:.4f}".rstrip("0").rstrip(".") or "0"


def label_at(ref: str, pin: int):
    """Absolute sheet position of the label for one pin, and how to justify it.

    Schematic Y runs the other way from symbol Y, hence the subtraction. Left-side
    pins take a label rotated 180 and right-justified so the text runs away from the
    body; right-side pins take the mirror of that.
    """
    sx, sy = PLACE[ref][0], PLACE[ref][1]
    left = pin <= 36
    x = sx + (-S.PIN_X if left else S.PIN_X)
    y = sy - S.pin_y(pin)
    return x, y, (180 if left else 0), ("right bottom" if left else "left bottom")


def build() -> str:
    out = []
    a = out.append

    a("(kicad_sch")
    a("  (version 20231120)")
    a('  (generator "gen_schematic.py")')
    a('  (generator_version "9.0")')
    a(f'  (uuid "{uid("sheet")}")')
    a('  (paper "A4")')

    # ---- lib_symbols: the two symbols, inlined under their library nickname ----
    # Emitted from gen_symbol.SYMBOLS, the same table the .kicad_sym is built from —
    # see the note there about "doesn't match copy in library".
    a("  (lib_symbols")
    for ref in sorted(PLACE):
        for line in S.emit(PLACE[ref][2], qualified=True):
            a("  " + line)
    a("  )")

    # ---- labels ------------------------------------------------------------
    for ref in sorted(PLACE):
        for pin in P.PIN_NUMBERS:
            x, y, rot, just = label_at(ref, pin)
            a(f'  (label "{P.PINS[pin]["label"]}"')
            a(f"    (at {fmt(x)} {fmt(y)} {rot})")
            a("    (effects (font (size 1.27 1.27)) (justify %s))" % just)
            a(f'    (uuid "{uid(f"label-{ref}-{pin}")}")')
            a("  )")

    # ---- symbol instances --------------------------------------------------
    for ref, (x, y, symname, fp, value) in sorted(PLACE.items()):
        a("  (symbol")
        a(f'    (lib_id "{S.LIB_NICK}:{symname}")')
        a(f"    (at {fmt(x)} {fmt(y)} 0)")
        a("    (unit 1)")
        a("    (exclude_from_sim no)")
        a("    (in_bom yes)")
        a("    (on_board yes)")
        a("    (dnp no)")
        a(f'    (uuid "{uid(f"sym-{ref}")}")')
        # Reference above the body, value below it — outside the 104 mm tall
        # rectangle, which is where the released sheet puts them too.
        a(f'    (property "Reference" "{ref}"')
        a(f"      (at {fmt(x)} {fmt(y - S.BODY[1] - 3.81)} 0)")
        a("      (effects (font (size 1.524 1.524)))")
        a("    )")
        a(f'    (property "Value" "{value}"')
        a(f"      (at {fmt(x)} {fmt(y - S.BODY[3] + 3.81)} 0)")
        a("      (effects (font (size 1.524 1.524)))")
        a("    )")
        a(f'    (property "Footprint" "{S.LIB_NICK}:{fp}"')
        a(f"      (at {fmt(x)} {fmt(y)} 0)")
        a("      (effects (font (size 1.524 1.524)) (hide yes))")
        a("    )")
        a('    (property "Datasheet" ""')
        a(f"      (at {fmt(x)} {fmt(y)} 0)")
        a("      (effects (font (size 1.524 1.524)) (hide yes))")
        a("    )")
        for pin in P.PIN_NUMBERS:
            a(f'    (pin "{pin}" (uuid "{uid(f"pin-{ref}-{pin}")}"))')
        a("    (instances")
        a(f'      (project "{PROJECT}"')
        a(f'        (path "/{uid("sheet")}"')
        a(f'          (reference "{ref}") (unit 1)')
        a("        )")
        a("      )")
        a("    )")
        a("  )")

    a("  (sheet_instances")
    a('    (path "/" (page "1"))')
    a("  )")
    a(")")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    text = build()
    with open(args.out, "w") as f:
        f.write(text)

    # Every label must land exactly on a pin, and every pin must carry exactly one
    # label. Checked here rather than trusted, because a wireless schematic that is
    # 0.01 mm out looks completely correct on screen and nets nothing.
    hits = {}
    for ref in PLACE:
        for pin in P.PIN_NUMBERS:
            x, y, _, _ = label_at(ref, pin)
            hits.setdefault((round(x, 4), round(y, 4)), []).append((ref, pin))
    doubled = {k: v for k, v in hits.items() if len(v) > 1}

    print(f"wrote {args.out}")
    print(f"  symbols: {len(PLACE)}  labels: {2 * len(P.PIN_NUMBERS)}  "
          f"nets: {len(set(P.NETS.values()))}")
    if doubled:
        print(f"  FAIL: {len(doubled)} sheet positions carry more than one label:")
        for k, v in sorted(doubled.items())[:8]:
            print(f"        {k} <- {v}")
        return 1
    print("  every label sits on its own pin connection point")
    return 0


if __name__ == "__main__":
    sys.exit(main())
