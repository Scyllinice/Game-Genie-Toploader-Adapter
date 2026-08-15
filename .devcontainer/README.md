# Dev container — the pinned toolchain

Everything in this repository is generated, so the versions of the tools that generate
it are part of the design. This pins them.

```
./dc bash -c "cd pcb && make rebuild"     regenerate the board
./dc bash -c "cd mech && make"            regenerate the STLs
./dc                                      interactive shell
./dc --build                              rebuild the image
```

Or open the folder in VS Code and reopen in the container.

## What's inside

| tool | version | used by |
|---|---|---|
| **KiCad** (`kicad-cli` + `pcbnew` python + libraries) | 10.0.x | everything in `pcb/` |
| **OpenSCAD** (+ xvfb for PNG export) | 2021.01 | `mech/` |
| **Pillow** | distro | `pcb/gen_render.py`, which crops renders on the alpha channel |

Base is `ubuntu:24.04` with KiCad from the official PPA — `kicad-cli` and the `pcbnew`
module come from the same package, so they cannot drift apart. About 4 GB built, most
of which is `kicad-packages3d`; that is not optional, because without it every
`kicad-cli pcb render` draws a bare board and the README image comes out of that
renderer.

## Why KiCad 10 when the host has 9

**To match the desktop install.** The generators themselves do not care — the whole
`pcb/` pipeline runs unchanged on 9.0.8 and 10.0.5 and produces a board that passes
`compare_original.py` either way, verified both ways. What differs is the file they
write: 2465 lines of schema between them, none of it geometry. So regenerating on the
wrong version rewrites the committed board without changing it, and the next real
change would be invisible inside that diff.

It matters in the other direction too, and this one has actually happened: keep the
headless toolchain on 9.x, open the board once in a KiCad 10 desktop, and the desktop
upgrades the file in place — after which 9's `pcbnew` cannot load it at all
(`LoadBoard` returns `None`).

`pcb/check_toolchain.py` prints which KiCad is about to run and warns if it is not
10.x. It warns rather than fails: checking a board on whatever you have is reasonable,
and `make drc` on 9.x is perfectly valid. It is *regenerating* that costs you a diff.

## Why it is this small

A PCB toolchain will happily grow to tens of gigabytes — vendor FPGA suites, firmware
SDKs, simulators, autorouters. None of that applies to a board with no active
components on it, so none of it is here. The one omission that is a design decision
rather than a size decision is the autorouter: `pcb/route.py` solves all 72 conductors
in closed form and audits every segment before writing, and an autorouted board is a
different shape every run and cannot be reviewed as a diff.

## Not in here

Interactive GUIs: the KiCad editor and the OpenSCAD preview. Run those on the host.

## Notes

`dc` passes `--user $(id -u):$(id -g)` so files created on the bind mount stay yours,
and `PYTHONDONTWRITEBYTECODE=1` because a `.pyc` written by the container is validated
against a source mtime written by the host, and those are not the same clock. Measured
on an earlier project: an edited pin table kept importing its previous definitions from
a cached `.pyc`. Editing `pcb/lib/pinout.py`, regenerating, and getting the old nets on
a board that passes every check is the exact failure that costs a board.
