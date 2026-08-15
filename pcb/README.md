# pcb/ — the board

The Game Genie Toploader Adapter, generated from source instead of drawn. Two Python
tables describe the board — a 72-pin pinout and a set of measured dimensions — and
everything else here is produced from them: both footprints, both schematic symbols,
the schematic, the board, the copper, the project rules and the fab outputs.

**This is the project of record.** It replaced the hand-drawn files that used to sit
in the repository root, which are frozen in [`reference/`](reference/README.md) — not
as an archive, but because the check below reads them. The generated board is
subtracted from the released one on every run:

```
  PASS  outline  — 14 corners vs 14
  PASS  pad count  — 144 pads
  PASS  pad positions  — 144 pads within 0.001 mm
  PASS  pad sizes
  PASS  pad layers
  PASS  pad nets  — 72 nets
  PASS  net membership  — 72 nets
  PASS  1:1 pass-through  — 72/72 nets join J1 pin N to J2 pin N
  PASS  mounting holes  — (100.914, 79.451) d2.1, (171.348, 79.451) d2.1
  PASS  silk texts  — 3 texts

  The rebuild is geometrically and electrically identical to the released board.
```

## Running it

```
make            check what is here — DRC, ERC, card-edge rules, byte-canonical
                form, and the comparison above. Regenerates nothing.
make rebuild    the whole pipeline, pin table to routed board (FORCE=1 to overwrite
                a board that already carries routing)
make compare    just the equivalence proof
make fab        gerbers, drill, position file, BOM
make render     top and bottom PNGs, and the repository README's image
```

Needs KiCad 9 on the host — `kicad-cli` and the `pcbnew` Python module, both of which
Debian/Ubuntu's `kicad` package installs. No container. The generated files are KiCad
9 format while the released ones are KiCad 8, which is exactly why the comparison
loads both through pcbnew instead of diffing text.

## What the board is

A passive riser. 72 gold fingers go into a top-loading NES; a 2×36 2.54 mm card-edge
connector soldered to the top takes the Game Genie. Pin N to pin N, seventy-two times,
no components. The one and only complication:

**The two ends are on different pitches.** The console's cartridge slot is 2.50 mm and
the connector part is made in 2.54 mm, so every conductor has to shift sideways
between the two fields — 1.67 mm at one end of the board, 3.07 mm at the other. That
shift is the entire routing problem, and it is why the corridor between the two pad
fields is full of parallel diagonal jogs.

**Two mounting holes sit in that corridor** and four conductors cannot clear them in
either pad column, so they jog twice: once early, hold a safe X past the hole, then
finish the move in the 2.75 mm window between the hole and J1's pads. The released
board does this by hand. `route.py` derives it, and refuses to write a board where it
does not fit.

## The pipeline

```
lib/pinout.py      72 pins: nesdev name, this board's net label, symbol pin, direction
lib/geometry.py    the measured board: outline, both pad fields, holes, silk, rules
      |
      |  gen_footprints.py  -> lib/gg_adapter.pretty/   (2 footprints, 144 pads)
      |  gen_symbol.py      -> lib/gg_adapter.kicad_sym (2 symbols, mirrored)
      |  gen_schematic.py   -> gg_toploader.kicad_sch   (2 symbols, 144 labels)
      |  gen_board.py       -> gg_toploader.kicad_pcb   (placed + netted, unrouted)
      |  route.py           -> + 220 track segments, clearance-audited
      |  canonicalize.py    -> byte-reproducible (content-derived UUIDs, sorted items)
      |  gen_project.py     -> gg_toploader.kicad_pro + both lib tables
      v
   checks: kicad-cli drc (0/0) · kicad-cli erc (0) · check_fingers.py ·
           verify_rules.py · compare_original.py
```

`gen_project.py` runs **last**. `pcbnew.SaveBoard()` rewrites the sibling `.kicad_pro`
and resets the net classes to KiCad's stock defaults; `verify_rules.py` is what catches
it when that ordering slips.

## What the rebuild adds

Everything below is a difference from the released project, and each one is deliberate:

| | released | rebuild |
|---|---|---|
| ERC | 54 violations | **0** |
| symbols | one symbol used twice, all 72 nets output-to-output | two symbols, directions mirrored console↔Game Genie |
| symbol source | `doragasu:NES-CART`, a CERN-OHL-S library | generated from the nesdev wiki pin table |
| stackup finish | `None` | `ENIG` — reaches the fab in the gerber job file instead of living in a README |
| card-edge checks | none | pitch, registration, bevel zone, wipe path, mask, edge clearance |
| keepouts | none | rule areas over the bevel/wipe zone and the top edge |
| fab instructions | in this README | `fab/FABNOTES.txt`, in the zip with the gerbers |
| regeneration | n/a | byte-identical across runs |

DRC was already clean on the released board, and stays clean here: 0 violations,
0 unconnected.

## The card edge, and the check KiCad does not run

**DRC's copper-to-edge test does not look at pads.** Measured here: set
`min_copper_edge_clearance` to 5 mm — far enough that all 144 pads are inside it — and
the violation list comes back with 16 items, every one a *track*. Not one pad, at any
setting. On most boards that is a curiosity. On a card edge the pads are the thing
nearest the milled edge, so the check that matters is the one that does not run.

Two things cover it between them:

**Rule areas** (`gen_board.py`) over the bevel/wipe zone at the insertion edge and over
the top edge. Nothing may be *routed* into either band. The insertion-edge one is there
twice over: a 45° gold-finger bevel takes ~0.6 mm off the top surface, so copper inside
it is copper the mill cuts through — and the console's contacts sweep that same strip
on every insertion, so a track crossing it shorts to each contact as it passes. They
are rule areas, not copper: the gerbers are byte-identical with and without them,
verified.

**`check_fingers.py`** measures what a keepout cannot enforce, because keepouts permit
pads. It reports the closest pad to any edge — J1.36 at **0.372 mm** — and fails only
below 0.20 mm, the floor a fab can actually hold on a routed edge. All 72 J1 pads sit
inside this project's own 0.5 mm rule, at 0.468 mm from the top edge. That is
as-released and as-fabricated: the connector land has to be where the connector is.
Noted every run, not changed.

**The bevel itself is not board geometry** — it is a process the fab applies, and
there is no field in any gerber that asks for it. That instruction now ships as
`fab/FABNOTES.txt` inside the fab package rather than living in a README, because a
fab that is not told sends back square-edged contacts that chew the console connector.

## Things worth knowing about this board

* **1.2 mm, not 1.6 mm.** Cartridge thickness. The stackup declares 1.11 mm core plus
  copper and mask to reach it, and the gerber job carries the number.
* **The finger setback is 0.62 mm** and a 45° gold-finger bevel on a 1.2 mm board
  reaches about 0.6 mm. That is a **0.02 mm margin** — `check_fingers.py` prints it
  every run because it is the kind of number you want to have seen before ordering.
* **Pins 1 and 72 are both GND and are NOT joined here.** They are separate nets
  (`CPU-GND`, `CIC-GND`) and meet in the console. `pinout.py` asserts it stays that
  way; bridging them would be a change of circuit, not a cleanup.
* **PPU A11 and A10 really are swapped** at pins 62/63. Wiki and released board agree.
* **CIRAM A10 and CIRAM /CE are driven by the cartridge**, so they are the two signals
  whose direction runs Game-Genie-to-console. The released symbol has them as inputs;
  this is the only place the rebuild's pin table disagrees with it, and it changes
  nothing but ERC.

## Traps this cost, written down where they happened

* `.kicad_pcb` writes text size in the **opposite order** to `VECTOR2I`, and
  `SetBold()` **recomputes thickness**, so it has to be called before setting it.
  Between them, the long silk text came out short, fat and off the edge.
* A schematic's inlined `lib_symbols` copy is **library-qualified**, but its
  `_0_0`/`_1_1` sub-symbols are **not**. Get it wrong and KiCad rejects the whole file
  with "Failed to load schematic" and no line number.
* That inlined copy is compared **field by field** against the library. A description
  that differs by one word is an ERC warning, which is why both files build their
  symbols from one table.
* The escape columns beside a mounting hole are `hx ± R`, and `(hx - R) - hx` is not
  exactly `-R` in floating point, so an exact-fit candidate rejects itself. Two
  conductors failed to route over 1e-13 mm.

## Files

| file | what it makes |
|---|---|
| `lib/pinout.py` | the 72-pin table — run it to print the pinout |
| `lib/geometry.py` | measured geometry — run it to print the dimensions |
| `gen_footprints.py` | `lib/gg_adapter.pretty/` — the fingers and the connector land |
| `gen_symbol.py` | `lib/gg_adapter.kicad_sym` — two direction-mirrored symbols |
| `gen_schematic.py` | the schematic: two symbols, 144 labels, no wires |
| `gen_board.py` | the board: outline, placement, holes, silk, 72 nets |
| `route.py` | the copper, in closed form, clearance-audited before it is written |
| `canonicalize.py` | content-derived UUIDs so a no-op rebuild is a no-op diff |
| `gen_project.py` | net classes, design rules, both library tables |
| `gen_bom.py` | the BOM — one line, plus the fab notes that matter |
| `gen_render.py` | the two renders, and the repository README's image |
| `compare_original.py` | the equivalence proof against the released board |
| `check_fingers.py` | card-edge checks KiCad's DRC does not have |
| `verify_rules.py` | asserts `SaveBoard()` has not eaten the net classes |
| `guard_routed.py` | refuses to regenerate over routing |
| `reference/` | the released design, frozen — what `compare_original.py` reads |

## Changing the board

Edit the table, not the file. A pin's net name lives in `lib/pinout.py`; a dimension
lives in `lib/geometry.py`; where the copper goes is a rule in `route.py`. Then
`make rebuild`, and read the diff — it will be small, because the board is
canonicalised.

Opening `gg_toploader.kicad_pcb` in KiCad and dragging something works, and the next
`make rebuild` discards it. That is not a warning against using the GUI: it is the
fastest way to try a change. Try it there, then fold the numbers back into the table
that owns them.

One consequence of the promotion is worth stating plainly: **`make compare` is now a
regression test, not a migration check.** It answers "does the board still match what
was fabricated and sold", so a deliberate design change is supposed to break it. When
that happens, the fix is to read exactly which of the fourteen lines changed, satisfy
yourself that it is the change you meant, and say so in the commit — not to relax the
check. `reference/` never moves.

`production/` in the repository root is the fab package the released board was ordered
from. It has not been regenerated: it corresponds to the design this board is proven
identical to, and `make fab` produces its replacement when there is a reason to order
again.
