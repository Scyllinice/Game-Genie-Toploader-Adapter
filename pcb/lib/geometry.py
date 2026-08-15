"""Measured geometry of the Game Genie Toploader Adapter.

Every number here was read out of the released board
("../Game Genie Toploader Adapter.kicad_pcb") rather than invented, and the
generators reproduce it in ABSOLUTE board coordinates — the same X/Y the released
file uses, not a local frame shifted to the origin.

That choice is what makes compare_original.py a real proof. If the rebuild used its
own datum, comparing it to the shipped board would mean fitting one coordinate set
onto the other, and a fit hides exactly the class of error worth catching (a pad
0.05 mm out, a connector 2.5 mm along, a mirrored finger field). Matching absolutes
means the comparison is a subtraction.

KiCad convention: +X right, +Y DOWN. So the card-edge tongue, at the largest Y, is
the bottom of the board as drawn and the part that goes INTO the console.

  y  60.78 ┌──────────────────────────┐  top edge — the Game Genie's own fingers
           │   J1: 72 pads, 2.54 mm   │       enter the connector body soldered here
  y  67.64 ├──┐                    ┌──┤  shoulders step out
           │  │  MOUNT1     MOUNT2 │  │  2.1 mm holes, y 79.45
  y  86.74 ├──┘   ┌──────────┐   └──┤
           │      │ J2: fingers │     │  72 gold fingers, 2.5 mm pitch
  y 101.68 └──────┴──────────┴───────┘  insertion edge — goes into the toploader
"""

# ---------------------------------------------------------------------------
# Stackup
# ---------------------------------------------------------------------------
# 1.2 mm total, NOT the 1.6 mm default: an NES cartridge PCB is 1.2 mm and the
# console's edge connector is sprung for that. The README says the same thing from
# the other end — a 1.6 mm board would splay the contacts. 1.11 mm core plus
# 2 x 0.035 mm copper plus 2 x 0.01 mm mask is exactly 1.2.
BOARD_THICKNESS = 1.2
CORE_THICKNESS = 1.11
COPPER_THICKNESS = 0.035
MASK_THICKNESS = 0.01
COPPER_LAYERS = 2

# ---------------------------------------------------------------------------
# Outline
# ---------------------------------------------------------------------------
# One closed polygon, clockwise from the bottom-left corner of the tongue.
#
# The released file draws this as 15 Edge.Cuts segments, one more than there are
# corners: its right edge is split at y 67.3608 by a vertex that is COLLINEAR with
# its neighbours, so it adds no geometry. Dropped here, and compare_original.py
# compares corner-to-corner after collapsing collinear vertices for that reason.
OUTLINE = [
    (88.5698, 101.6762),   # tongue, bottom-left  (insertion edge)
    (182.0418, 101.6762),  # tongue, bottom-right
    (182.0418, 86.7410),   # tongue root, right
    (185.2422, 86.7410),   # shoulder, right
    (185.2422, 67.6402),   # right edge, up to the connector step
    (183.6420, 67.6402),   # step in, right
    (183.6420, 60.7822),   # top edge, right
    (91.9226, 60.7822),    # top edge, left
    (91.9226, 63.7540),    # step out, left  (asymmetric with the right step)
    (87.0204, 63.7540),
    (87.0204, 70.2818),
    (85.5218, 70.2818),    # shoulder, left
    (85.5218, 86.7410),
    (88.5698, 86.7410),    # tongue root, left
]

# Named features, derived from the polygon so they cannot disagree with it.
BODY_LEFT = min(x for x, _ in OUTLINE)          # 85.5218
BODY_RIGHT = max(x for x, _ in OUTLINE)         # 185.2422
BODY_TOP = min(y for _, y in OUTLINE)           # 60.7822 — Game Genie end
INSERTION_EDGE_Y = max(y for _, y in OUTLINE)   # 101.6762 — goes into the console
TONGUE_ROOT_Y = 86.7410
TONGUE_LEFT = 88.5698
TONGUE_RIGHT = 182.0418

BOARD_W = BODY_RIGHT - BODY_LEFT                # 99.7204
BOARD_H = INSERTION_EDGE_Y - BODY_TOP           # 40.8940
TONGUE_W = TONGUE_RIGHT - TONGUE_LEFT           # 93.4720

# ---------------------------------------------------------------------------
# The two 72-way pad fields
# ---------------------------------------------------------------------------
# Both are plain rectangular SMD pads on one copper layer each, 36 on the front and
# 36 directly behind them on the back — the same construction, at two different
# pitches, because they mate with two different things:
#
#   J2  the board's OWN gold fingers, 2.50 mm — the NES cartridge pitch. This edge
#       is milled into the console's connector, so its pitch is not negotiable.
#   J1  a land pattern for a TE 5530843-8 (or equivalent) 2x36 2.54 mm edge
#       connector, soldered on top. 2.54 mm because that is the pitch the part is
#       made in. The 0.04 mm/pin difference between the two is the whole reason this
#       board needs routing at all instead of straight-through copper.
#
# 14 mm pads are long for a soldered connector, and deliberately so on both fields:
# the fingers need the length the console's contacts wipe over, and J1's pins are
# BENT OVER and lap-soldered (README: "you will need to bend in the pins a bit as the
# board is only 1.2 mm thick"), which needs land, not a hole.
PAD_W = 2.0
PAD_H = 14.0

FINGER_PITCH = 2.50
FINGER_PIN1_X = 43.75          # relative to the footprint origin
FINGER_ORIGIN = (135.3696, 94.0562)

GG_PITCH = 2.54
GG_PIN1_X = 43.18
GG_ORIGIN = (139.0142, 68.2498)

REF_FINGERS = "J2"
REF_GG = "J1"

FP_FINGERS = "NES_CART_FINGERS"
FP_GG = "GG_2x36_2.54mm_Edge"

# The Game Genie connector is the only part on the BOM.
GG_PART = "5530843-8"


def _field_x(pin: int, pin1_x: float, pitch: float) -> float:
    """Pad X within a 72-way field: pins count DOWN in X, back row behind the front."""
    return pin1_x - pitch * ((pin - 1) % 36)


def finger_x(pin: int) -> float:
    """Absolute X of finger `pin` (1..72)."""
    return FINGER_ORIGIN[0] + _field_x(pin, FINGER_PIN1_X, FINGER_PITCH)


def gg_x(pin: int) -> float:
    """Absolute X of Game Genie connector pad `pin` (1..72)."""
    return GG_ORIGIN[0] + _field_x(pin, GG_PIN1_X, GG_PITCH)


def layer_of(pin: int) -> str:
    return "F.Cu" if pin <= 36 else "B.Cu"


FINGER_Y = FINGER_ORIGIN[1]                     # 94.0562, pad centre line
GG_Y = GG_ORIGIN[1]                             # 68.2498
FINGER_PAD_TOP = FINGER_Y - PAD_H / 2           # 87.0562 — end nearest J1
FINGER_PAD_TIP = FINGER_Y + PAD_H / 2           # 101.0562
GG_PAD_BOTTOM = GG_Y + PAD_H / 2                # 75.2498 — end nearest J2
GG_PAD_TOP = GG_Y - PAD_H / 2                   # 61.2498

# The fingers stop 0.62 mm short of the insertion edge, and J1's pads 0.4672 mm short
# of the top edge. Both are as-released. The finger setback is the one that matters
# electrically: copper running off the milled edge is copper the bevel cuts through.
FINGER_TIP_SETBACK = INSERTION_EDGE_Y - FINGER_PAD_TIP
GG_TOP_SETBACK = GG_PAD_TOP - BODY_TOP

# ---------------------------------------------------------------------------
# Mounting holes
# ---------------------------------------------------------------------------
# Two 2.1 mm NPTH, no annular ring, on the tongue-root centreline. They sit IN THE
# ROUTING CORRIDOR — the 11.8 mm band between the two pad fields is the only place
# tracks can run — so route.py has to steer eight conductors around them rather than
# treat them as decoration. Their positions are not symmetric about the board centre
# (they are 70.4342 mm apart, centred 0.7358 mm right of the outline's centre).
MOUNT_DRILL = 2.1
MOUNT_HOLES = [
    ("MOUNT1", 100.9142, 79.4512),
    ("MOUNT2", 171.3484, 79.4512),
]

# ---------------------------------------------------------------------------
# Silkscreen
# ---------------------------------------------------------------------------
# Text, position, size, angle and justification as released. "Game Genie" and "NES"
# label the two ends so an assembler cannot fit the connector to the wrong edge —
# on a board with no polarised parts that silk is the only thing that says which
# way up it goes.
SILK = [
    # (text, x, y, angle, size_a, size_b, thickness, justify)
    #
    # size_a/size_b are in the order the .kicad_pcb writes them, `(size a b)`, which
    # is the REVERSE of the (width, height) order pcbnew's VECTOR2I takes. They are
    # named neutrally here so the numbers can be checked against the released file by
    # eye; gen_board.py does the swap, with the trap written up where it happens.
    ("Game Genie Top Loader Adapter", 89.8652, 86.3092, 90, 1.5, 0.9, 0.125, "left bottom"),
    ("Game Genie", 129.713915, 77.7240, 0, 1.5, 1.5, 0.300, "left bottom"),
    ("NES", 136.7282, 85.9536, 0, 1.5, 1.5, 0.300, "bottom"),
]

# ---------------------------------------------------------------------------
# Design rules
# ---------------------------------------------------------------------------
# As released: 0.2 mm track, 0.2 mm clearance, one Default net class. Roomy for this
# board — the tightest feature is the 0.54 mm gap between J1's 2 mm pads on 2.54 mm
# pitch, and nothing has to route between them.
TRACK_W = 0.2
CLEARANCE = 0.2
VIA_DIA = 0.6
VIA_DRILL = 0.3
EDGE_CLEARANCE = 0.5
HOLE_CLEARANCE = 0.25


def outline_segments():
    """The closed polygon as (x1, y1, x2, y2) segments."""
    return [(*OUTLINE[i], *OUTLINE[(i + 1) % len(OUTLINE)]) for i in range(len(OUTLINE))]


def check() -> list:
    """Assertions about the measured numbers. Empty list means clean."""
    bad = []
    total = CORE_THICKNESS + 2 * COPPER_THICKNESS + 2 * MASK_THICKNESS
    if abs(total - BOARD_THICKNESS) > 1e-9:
        bad.append(f"stackup sums to {total} mm, not {BOARD_THICKNESS}")
    # The fields must both fit inside the outline, with the fingers on the tongue.
    if finger_x(36) - PAD_W / 2 < TONGUE_LEFT or finger_x(1) + PAD_W / 2 > TONGUE_RIGHT:
        bad.append("finger field runs off the tongue")
    if gg_x(36) - PAD_W / 2 < BODY_LEFT or gg_x(1) + PAD_W / 2 > BODY_RIGHT:
        bad.append("Game Genie field runs off the board")
    # The routing corridor is what is left between the two pad fields.
    corridor = FINGER_PAD_TOP - GG_PAD_BOTTOM
    if corridor < 5:
        bad.append(f"routing corridor is only {corridor:.2f} mm")
    for name, hx, hy in MOUNT_HOLES:
        if not (GG_PAD_BOTTOM < hy < FINGER_PAD_TOP):
            bad.append(f"{name} is not in the corridor — the router assumes it is")
    return bad


if __name__ == "__main__":
    import sys
    problems = check()
    for p in problems:
        print("FAIL:", p)
    if not problems:
        print(f"board      : {BOARD_W:.4f} x {BOARD_H:.4f} mm, "
              f"{COPPER_LAYERS} layers, {BOARD_THICKNESS} mm thick")
        print(f"outline    : {len(OUTLINE)} corners, tongue {TONGUE_W:.4f} mm wide")
        print(f"fingers J2 : pin1 x {finger_x(1):.4f}  pin36 x {finger_x(36):.4f}  "
              f"pitch {FINGER_PITCH}")
        print(f"connector J1: pin1 x {gg_x(1):.4f}  pin36 x {gg_x(36):.4f}  "
              f"pitch {GG_PITCH}")
        print(f"corridor   : {FINGER_PAD_TOP - GG_PAD_BOTTOM:.4f} mm between pad fields, "
              f"{len(MOUNT_HOLES)} holes in it")
        print(f"setback    : fingers {FINGER_TIP_SETBACK:.4f} mm from the insertion edge")
        shift = [gg_x(n) - finger_x(n) for n in range(1, 37)]
        print(f"pitch drift: each conductor moves {min(shift):.4f}..{max(shift):.4f} mm "
              f"between the two fields")
    sys.exit(1 if problems else 0)
