#!/usr/bin/env python3
"""Assert the project file still carries the rules gen_project.py wrote.

  python3 verify_rules.py

pcbnew.SaveBoard() REWRITES the sibling .kicad_pro. If a board is saved after the
project is generated, the generated net class is replaced by KiCad's stock defaults —
0.2 mm clearance becomes whatever KiCad ships with, and nothing says so. The board
then gets checked against rules nobody chose.

That is not hypothetical — it is why this check exists. Where an autorouter is in
play the wrong clearance reaches it through the exported DSN and comes back as copper.
Here the router is deterministic and reads geometry.py directly, so the blast radius is
smaller: DRC grades the board against rules nobody chose, which is quieter and arguably
worse for it.

The Makefile runs gen_project.py after gen_board.py and route.py for this reason, and
runs this check after all three.
"""

import json
import os
import sys

import gen_project

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, f"{gen_project.PROJECT}.kicad_pro")


def dig(d, path):
    for key in path:
        if not isinstance(d, dict) or key not in d:
            return None
        d = d[key]
    return d


def main():
    if not os.path.exists(PATH):
        print(f"missing {PATH} — run gen_project.py")
        return 1
    with open(PATH) as f:
        on_disk = json.load(f)
    expected = gen_project.build()

    bad = []

    want = {c["name"]: c for c in dig(expected, ("net_settings", "classes")) or []}
    have = {c["name"]: c for c in dig(on_disk, ("net_settings", "classes")) or []}
    for name, cls in want.items():
        if name not in have:
            bad.append(f"net class {name!r} is gone from the project file")
            continue
        for key in ("clearance", "track_width", "via_diameter", "via_drill"):
            if abs(have[name].get(key, -1) - cls[key]) > 1e-9:
                bad.append(f"{name}.{key}: {have[name].get(key)} on disk, "
                           f"{cls[key]} generated")
    for name in have:
        if name not in want:
            bad.append(f"net class {name!r} appeared from somewhere")

    wr = dig(expected, ("board", "design_settings", "rules")) or {}
    hr = dig(on_disk, ("board", "design_settings", "rules")) or {}
    for key, val in wr.items():
        if key not in hr or abs(hr[key] - val) > 1e-9:
            bad.append(f"rule {key}: {hr.get(key)} on disk, {val} generated")

    if bad:
        print(f"FAIL: {os.path.basename(PATH)} does not match gen_project.py")
        for b in bad:
            print("   ", b)
        print("   (SaveBoard() rewrites this file — run gen_project.py last)")
        return 1

    cls = have["Default"]
    print(f"rules verified: {cls['track_width']} mm track, {cls['clearance']} mm "
          f"clearance, {hr['min_copper_edge_clearance']} mm to the edge")
    return 0


if __name__ == "__main__":
    sys.exit(main())
