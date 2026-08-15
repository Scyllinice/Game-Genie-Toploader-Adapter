#!/usr/bin/env python3
"""Generate the schematic symbols — lib/gg_adapter.kicad_sym.

  python3 gen_symbol.py [-o FILE]

TWO symbols, from the one pin table:

  NES-CART-Console      J2, the board's own gold fingers. What the CONSOLE presents.
  NES-CART-GameGenie    J1, the connector the Game Genie plugs into.

They are pin-for-pin identical and differ only in electrical type: every direction is
mirrored between them (see pinout.py, FLOW). That is not decoration. The released
project uses ONE symbol twice, which puts two outputs on all 72 nets, and ERC on that
schematic reports a conflict for every conductor on the board — so ERC was never
usable as a check there. With the directions mirrored, a 1:1 riser is exactly what
ERC expects to see: one driver, one receiver, per net.

The symbols are also a clean-room rebuild in the licensing sense. The released
schematic still references `doragasu:NES-CART` for J1, from a CERN-OHL-S library;
these are drawn from the pin table in pinout.py, whose source is the nesdev wiki
page cited there.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import geometry as G      # noqa: E402
import pinout as P        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "lib", "gg_adapter.kicad_sym")

LIB_NICK = "gg_adapter"
SYM_CONSOLE = "NES-CART-Console"
SYM_GG = "NES-CART-GameGenie"

# ---------------------------------------------------------------------------
# Sheet layout of the symbol body — copied from the released symbol so the
# generated schematic reads the same as the one people have already seen.
# ---------------------------------------------------------------------------
PIN_LEN = 5.08
SLOT = 2.54
TOP_Y = 48.26                 # y of pin 1 and pin 37
BODY = (-8.89, 50.8, 8.89, -53.34)
PIN_X = 13.97                 # pins reach 5.08 past the body edge

# Blank slots inserted BEFORE these pins, so the functional groups separate visually.
# Same gaps the released symbol has; they are what make the CIC and EXP blocks
# readable on a 72-pin part.
GAPS = {16: 1, 21: 2, 34: 1, 51: 2, 56: 1, 70: 1}

# Group captions inside the body.
CAPTIONS = [("6502", 33.02), ("BUS", 30.48), ("EXP", 2.54),
            ("2C02", -25.4), ("BUS", -27.94), ("CIC", -48.26)]

# FLOW -> KiCad electrical type, per side. The console side is the source of
# everything the console drives and of both rails; the Game Genie side receives it.
ETYPE = {
    #  flow        console side     game genie side
    "console": ("output",        "input"),
    "cart":    ("input",         "output"),
    "bidir":   ("bidirectional", "bidirectional"),
    "od":      ("open_collector", "open_collector"),
    "passive": ("passive",       "passive"),
    "vcc":     ("power_out",     "power_in"),
    "gnd":     ("power_out",     "power_in"),
}


def fmt(v: float) -> str:
    return f"{v:.4f}".rstrip("0").rstrip(".") or "0"


def pin_y(pin: int) -> float:
    """Y of a pin in symbol coordinates, counting slots down each side."""
    first = 1 if pin <= 36 else 37
    slot = 0
    for n in range(first, pin + 1):
        slot += GAPS.get(n, 0)
        if n != first:
            slot += 1
    return TOP_Y - SLOT * slot


def _prop(out, name, value, x, y, size=1.524, hide=False):
    out.append(f'    (property "{name}" "{value}"')
    out.append(f"      (at {fmt(x)} {fmt(y)} 0)")
    out.append("      (effects (font (size %s %s))%s)"
               % (fmt(size), fmt(size), " (hide yes)" if hide else ""))
    out.append("    )")


def symbol(name: str, side: int, ref: str, value: str, footprint: str,
           descr: str, base: str = None) -> list:
    """One symbol. side 0 = console (fingers), side 1 = Game Genie connector.

    `base` names the _0_0 / _0_1 / _1_1 sub-symbols. In a .kicad_sym library that is
    the same as `name`, but inside a schematic's lib_symbols the outer symbol is
    LIBRARY-QUALIFIED ("gg_adapter:NES-CART-Console") while its sub-symbols keep the
    bare name. Getting that wrong does not produce a parse error — KiCad simply
    refuses the whole file with "Failed to load schematic".
    """
    base = base or name
    out = []
    a = out.append

    a(f'  (symbol "{name}"')
    a("    (pin_names (offset 1.016))")
    a("    (exclude_from_sim no)")
    a("    (in_bom yes)")
    a("    (on_board yes)")
    _prop(out, "Reference", ref, -7.62, 52.07)
    _prop(out, "Value", value, -2.54, -54.61)
    _prop(out, "Footprint", footprint, 0, 5.08, hide=True)
    _prop(out, "Datasheet", "", 0, 5.08, hide=True)
    _prop(out, "Description", descr, 0, 0, size=1.27, hide=True)

    # Group captions, then the body outline. KiCad wants these in the _0_0 and
    # _0_1 sub-symbols respectively.
    a(f'    (symbol "{base}_0_0"')
    for text, y in CAPTIONS:
        a(f'      (text "{text}" (at 0 {fmt(y)} 0)')
        a("        (effects (font (size 1.524 1.524))))")
    a("    )")

    a(f'    (symbol "{base}_0_1"')
    a(f"      (rectangle (start {fmt(BODY[0])} {fmt(BODY[1])}) "
      f"(end {fmt(BODY[2])} {fmt(BODY[3])})")
    a("        (stroke (width 0) (type default)) (fill (type none)))")
    a("    )")

    a(f'    (symbol "{base}_1_1"')
    for pin in P.PIN_NUMBERS:
        etype = ETYPE[P.PINS[pin]["flow"]][side]
        left = pin <= 36
        x = -PIN_X if left else PIN_X
        rot = 0 if left else 180
        a(f"      (pin {etype} line")
        a(f"        (at {fmt(x)} {fmt(pin_y(pin))} {rot})")
        a(f"        (length {fmt(PIN_LEN)})")
        a(f'        (name "{P.PINS[pin]["pin"]}" (effects (font (size 1.27 1.27))))')
        a(f'        (number "{pin}" (effects (font (size 1.27 1.27))))')
        a("      )")
    a("    )")
    a("  )")
    return out


# The definition of each symbol, in ONE place. gen_schematic.py inlines a copy of
# every symbol it uses into the .kicad_sch, and KiCad compares that copy against the
# library field by field: a description that differs by a word is reported as
# "Symbol doesn't match copy in library". Both files build from this table so they
# cannot drift.
SYMBOLS = {
    SYM_CONSOLE: {
        "side": 0,
        "ref": "J",
        "value": "NES-CART-EDGE",
        "fp": G.FP_FINGERS,
        "descr": ("NES 72-pin card edge, console side. The board's own gold "
                  "fingers — no part to buy."),
    },
    SYM_GG: {
        "side": 1,
        "ref": "J",
        "value": G.GG_PART,
        "fp": G.FP_GG,
        "descr": ("NES 72-pin edge connector, Game Genie side. TE 5530843-8 or "
                  "equivalent 2x36 2.54 mm card-edge connector."),
    },
}


def emit(name: str, qualified: bool = False) -> list:
    """Lines for one symbol from SYMBOLS, bare or library-qualified."""
    d = SYMBOLS[name]
    outer = f"{LIB_NICK}:{name}" if qualified else name
    return symbol(outer, d["side"], d["ref"], d["value"],
                  f"{LIB_NICK}:{d['fp']}", d["descr"], base=name)


def build() -> str:
    out = ["(kicad_symbol_lib",
           "  (version 20231120)",
           '  (generator "gen_symbol.py")',
           '  (generator_version "9.0")']
    for name in SYMBOLS:
        out += emit(name)
    out.append(")")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    text = build()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write(text)

    # Report the direction split — the whole reason there are two symbols.
    flows = {}
    for pin in P.PIN_NUMBERS:
        flows[P.PINS[pin]["flow"]] = flows.get(P.PINS[pin]["flow"], 0) + 1
    print(f"wrote {args.out}")
    print(f"  {SYM_CONSOLE:<22} 72 pins")
    print(f"  {SYM_GG:<22} 72 pins, directions mirrored")
    print("  flows: " + ", ".join(f"{k}={v}" for k, v in sorted(flows.items())))


if __name__ == "__main__":
    main()
