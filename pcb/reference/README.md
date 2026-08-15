# reference/ — the released design, frozen

These are the hand-drawn KiCad files this project shipped with: the board that was
fabricated, sold, listed on PCBWay and plugged into people's consoles. They lived in
the repository root until the generated project in `../` took over as the project of
record.

**Nothing builds from this directory and nothing regenerates it.** It is here for one
reason: `../compare_original.py` loads `Game Genie Toploader Adapter.kicad_pcb` on
every run and subtracts it from the generated board — 14 outline corners, 144 pads,
72 net groups, 2 holes, 3 silk texts, all to 1 µm. Delete this and that proof becomes
an assertion.

Kept complete rather than just the one file the check reads, so the released design
can still be opened and looked at:

| | |
|---|---|
| `Game Genie Toploader Adapter.kicad_pcb` | the released board — **what the comparison reads** |
| `Game Genie Toploader Adapter.kicad_sch` | the released schematic (ERC: 54 direction conflicts, see `../README.md`) |
| `Game Genie Toploader Adapter.kicad_pro` | its project settings |
| `nes-cart.kicad_sym` | its symbol library |
| `NES.pretty/`, `Game Genie.pretty/` | its two hand-drawn footprints |
| `fp-lib-table`, `sym-lib-table` | library tables, `${KIPRJMOD}`-relative, so they still resolve here |
| `fabrication-toolkit-options.json` | config for the Fabrication Toolkit plugin it was ordered with |

If you edit anything in here, the comparison stops meaning what it says.
