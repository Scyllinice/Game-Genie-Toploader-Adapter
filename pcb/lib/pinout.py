"""The NES 72-pin cartridge pinout — single source of truth for this adapter.

Everything downstream reads this table: both footprints (gen_footprints.py), both
schematic symbols (gen_symbol.py), the schematic netlist (gen_schematic.py) and the
board's net assignment (gen_board.py). Pad numbers, pin names and net labels cannot
drift apart because there is only one place they are written.

THREE NAMES PER PIN, and they are not interchangeable:

  wiki  — the signal as https://www.nesdev.org/wiki/Cartridge_connector writes it.
          The independent reference. compare_original.py never reads it; it exists so
          a human reviewing this file can check it against the wiki page directly, and
          so the fab layer can be labelled in the names the wiki uses.
  label — the net label THIS PROJECT uses, character for character as the shipped
          board spells it ("CPU-R/~{W}", "PPU-VA10", "S0"). Reproduced rather than
          modernised: the net names are the thing compare_original.py diffs against the
          released board, so renaming them would forfeit the equivalence proof.
  pin   — the symbol pin name. The same signal shortened to fit a symbol body, again
          copied from the released project's symbol.

FLOW is the one field that is a JUDGEMENT, not a measurement. It says which end of
the riser drives the conductor, and it exists only to make ERC meaningful:

  "console"  the console drives it (address, clocks, /ROMSEL, PPU strobes, CIC in)
  "cart"     the cartridge drives it (CIRAM A10, CIRAM /CE, CIC toMB)
  "bidir"    data buses
  "od"       /IRQ — open collector, wire-OR
  "passive"  EXP pins, not driven by anything on either side
  "vcc" / "gnd"  the rails

The riser is a plain 1:1 wire, so a single symbol used twice would put two same-
direction pins on every net and ERC would report 72 conflicts. gen_symbol.py instead
emits TWO symbols from this one table and mirrors FLOW between them: whatever is an
output on the console side is an input on the Game Genie side. That is what makes the
generated schematic ERC-clean.

WHERE FLOW DISAGREES WITH THE RELEASED SYMBOL, on purpose, for pins 22 and 57:
nes-cart.kicad_sym marks CIRAM A10 (22, "VA10") and CIRAM /CE (57, "~{VCS}") as
inputs. The wiki has both driven BY the cartridge — mirroring control is the mapper's
job — so they are "cart" here. This changes ERC direction and nothing else: no pad,
net or track moves, and compare_original.py proves it.
"""


def _p(wiki, label, pin, flow):
    return {"wiki": wiki, "label": label, "pin": pin, "flow": flow}


# Pins 1-36 are the front (label) side, 37-72 the back; pin N and pin N+36 sit at the
# same X, one behind the other. Order below is pin order, which is also left-to-right
# on the board with pin 1 at +X (see geometry.py — the fingers count DOWN in X).
PINS = {
     1: _p("GND",        "CPU-GND",      "GND",       "gnd"),
     2: _p("CPU A11",    "CPU-A11",      "A11",       "console"),
     3: _p("CPU A10",    "CPU-A10",      "A10",       "console"),
     4: _p("CPU A9",     "CPU-A9",       "A9",        "console"),
     5: _p("CPU A8",     "CPU-A8",       "A8",        "console"),
     6: _p("CPU A7",     "CPU-A7",       "A7",        "console"),
     7: _p("CPU A6",     "CPU-A6",       "A6",        "console"),
     8: _p("CPU A5",     "CPU-A5",       "A5",        "console"),
     9: _p("CPU A4",     "CPU-A4",       "A4",        "console"),
    10: _p("CPU A3",     "CPU-A3",       "A3",        "console"),
    11: _p("CPU A2",     "CPU-A2",       "A2",        "console"),
    12: _p("CPU A1",     "CPU-A1",       "A1",        "console"),
    13: _p("CPU A0",     "CPU-A0",       "A0",        "console"),
    14: _p("CPU R/W",    "CPU-R/~{W}",   "R/~{W}",    "console"),
    15: _p("/IRQ",       "CPU-~{IRQ}",   "~{IRQ}",    "od"),
    16: _p("EXP 0",      "EXP0",         "EXP0",      "passive"),
    17: _p("EXP 1",      "EXP1",         "EXP1",      "passive"),
    18: _p("EXP 2",      "EXP2",         "EXP2",      "passive"),
    19: _p("EXP 3",      "EXP3",         "EXP3",      "passive"),
    20: _p("EXP 4",      "EXP4",         "EXP4",      "passive"),
    21: _p("PPU /RD",    "PPU-~{R}",     "~{R}",      "console"),
    22: _p("CIRAM A10",  "PPU-VA10",     "VA10",      "cart"),
    23: _p("PPU A6",     "PPU-A6",       "A6",        "console"),
    24: _p("PPU A5",     "PPU-A5",       "A5",        "console"),
    25: _p("PPU A4",     "PPU-A4",       "A4",        "console"),
    26: _p("PPU A3",     "PPU-A3",       "A3",        "console"),
    27: _p("PPU A2",     "PPU-A2",       "A2",        "console"),
    28: _p("PPU A1",     "PPU-A1",       "A1",        "console"),
    29: _p("PPU A0",     "PPU-A0",       "A0",        "console"),
    30: _p("PPU D0",     "PPU-D0",       "D0",        "bidir"),
    31: _p("PPU D1",     "PPU-D1",       "D1",        "bidir"),
    32: _p("PPU D2",     "PPU-D2",       "D2",        "bidir"),
    33: _p("PPU D3",     "PPU-D3",       "D3",        "bidir"),
    34: _p("CIC toPak",  "S0",           "S0",        "console"),
    35: _p("CIC toMB",   "S1",           "S1",        "cart"),
    36: _p("+5V",        "CIC-VCC",      "VCC",       "vcc"),
    37: _p("SYSTEM CLK", "21.48MHz",     "21.48MHz",  "console"),
    38: _p("M2",         "PHI2",         "PHI2",      "console"),
    39: _p("CPU A12",    "CPU-A12",      "A12",       "console"),
    40: _p("CPU A13",    "CPU-A13",      "A13",       "console"),
    41: _p("CPU A14",    "CPU-A14",      "A14",       "console"),
    42: _p("CPU D7",     "CPU-D7",       "D7",        "bidir"),
    43: _p("CPU D6",     "CPU-D6",       "D6",        "bidir"),
    44: _p("CPU D5",     "CPU-D5",       "D5",        "bidir"),
    45: _p("CPU D4",     "CPU-D4",       "D4",        "bidir"),
    46: _p("CPU D3",     "CPU-D3",       "D3",        "bidir"),
    47: _p("CPU D2",     "CPU-D2",       "D2",        "bidir"),
    48: _p("CPU D1",     "CPU-D1",       "D1",        "bidir"),
    49: _p("CPU D0",     "CPU-D0",       "D0",        "bidir"),
    50: _p("/ROMSEL",    "CPU-~{PRG}",   "~{PRG}",    "console"),
    51: _p("EXP 9",      "EXP9",         "EXP9",      "passive"),
    52: _p("EXP 8",      "EXP8",         "EXP8",      "passive"),
    53: _p("EXP 7",      "EXP7",         "EXP7",      "passive"),
    54: _p("EXP 6",      "EXP6",         "EXP6",      "passive"),
    55: _p("EXP 5",      "EXP5",         "EXP5",      "passive"),
    56: _p("PPU /WR",    "PPU-~{W}",     "~{W}",      "console"),
    57: _p("CIRAM /CE",  "PPU-~{VCS}",   "~{VCS}",    "cart"),
    58: _p("PPU /A13",   "PPU-~{A13}",   "~{A13}",    "console"),
    59: _p("PPU A7",     "PPU-A7",       "A7",        "console"),
    60: _p("PPU A8",     "PPU-A8",       "A8",        "console"),
    61: _p("PPU A9",     "PPU-A9",       "A9",        "console"),
    # 62/63 really are A11 then A10 — the PPU address lines are not in order on the
    # connector. Both the wiki and the released board agree; it is not a typo here.
    62: _p("PPU A11",    "PPU-A11",      "A11",       "console"),
    63: _p("PPU A10",    "PPU-A10",      "A10",       "console"),
    64: _p("PPU A12",    "PPU-A12",      "A12",       "console"),
    65: _p("PPU A13",    "PPU-A13",      "A13",       "console"),
    66: _p("PPU D7",     "PPU-D7",       "D7",        "bidir"),
    67: _p("PPU D6",     "PPU-D6",       "D6",        "bidir"),
    68: _p("PPU D5",     "PPU-D5",       "D5",        "bidir"),
    69: _p("PPU D4",     "PPU-D4",       "D4",        "bidir"),
    70: _p("CIC +RST",   "S2",           "S2",        "console"),
    71: _p("CIC CLK",    "4MHz",         "4MHz",      "console"),
    72: _p("GND",        "CIC-GND",      "GND",       "gnd"),
}

PIN_NUMBERS = tuple(range(1, 73))
FRONT = tuple(range(1, 37))     # F.Cu fingers / F.Cu connector pads
BACK = tuple(range(37, 73))     # B.Cu, pin N behind pin N-36


# ---------------------------------------------------------------------------
# Net names
# ---------------------------------------------------------------------------
# KiCad prefixes a net named by a local label on the root sheet with the sheet path,
# so the label "CPU-A11" becomes the net "/CPU-A11" — and it escapes a "/" INSIDE a
# label as "{slash}", which is why pin 14's net is "/CPU-R{slash}~{W}". Both quirks
# are reproduced rather than avoided: these strings are what the released board
# contains, and matching them is what lets compare_original.py diff net for net.
def net_of(pin: int) -> str:
    return "/" + PINS[pin]["label"].replace("/", "{slash}")


NETS = {n: net_of(n) for n in PIN_NUMBERS}


def check() -> list:
    """Self-consistency of the table. Returns a list of complaints, empty if clean."""
    bad = []
    if sorted(PINS) != list(PIN_NUMBERS):
        bad.append("pin numbers are not exactly 1..72")
    labels = [PINS[n]["label"] for n in PIN_NUMBERS]
    if len(set(labels)) != 72:
        dupes = sorted({x for x in labels if labels.count(x) > 1})
        bad.append(f"duplicate net labels: {dupes} — a 1:1 riser has 72 distinct nets")
    # GND appears twice on the connector (1 and 72) and the released board keeps them
    # as SEPARATE nets, CPU-GND and CIC-GND. That is deliberate on a passive riser: no
    # copper joins them here, they meet in the console. Assert it stays that way.
    if PINS[1]["label"] == PINS[72]["label"]:
        bad.append("pins 1 and 72 share a net — the riser must not bridge the grounds")
    for n in PIN_NUMBERS:
        if PINS[n]["flow"] not in ("console", "cart", "bidir", "od", "passive",
                                   "vcc", "gnd"):
            bad.append(f"pin {n}: unknown flow {PINS[n]['flow']!r}")
    return bad


if __name__ == "__main__":
    import sys
    problems = check()
    for p in problems:
        print("FAIL:", p)
    if not problems:
        print(f"pinout: {len(PINS)} pins, {len(set(NETS.values()))} distinct nets, clean")
        for n in PIN_NUMBERS:
            p = PINS[n]
            print(f"  {n:3}  {p['wiki']:<11} {p['label']:<14} {p['flow']}")
    sys.exit(1 if problems else 0)
