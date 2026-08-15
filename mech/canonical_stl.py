#!/usr/bin/env python3
"""Make an OpenSCAD ASCII STL byte-reproducible.

  python3 canonical_stl.py FILE...
  python3 canonical_stl.py --check FILE...

Two runs of the same model produce the same triangles in a DIFFERENT ORDER — measured
on front.stl, 312 of 8486 lines differ between runs while the file length, the
triangle count and the geometry are identical. CGAL emits facets in whatever order it
walks its own structures, and that order is not stable.

The consequence is the same one canonicalize.py fixes for the board: a committed STL
would show up as modified every time anyone ran `make`, and a real change to the model
would be buried in the noise. These files are a deliverable — someone without OpenSCAD
should be able to print the shell straight from the repository — so they are committed,
and that means they have to be diffable.

Sorting is safe. An STL is an unordered triangle soup: nothing reads facet order.
WINDING IS NOT reordered — the vertex list inside each facet is only ROTATED, to start
at its smallest vertex, which leaves the cyclic order and therefore the surface normal
exactly as it was. Reversing it instead would turn the model inside out, and every
slicer would still open it.
"""

import argparse
import re
import sys

FACET = re.compile(
    r"\s*facet normal\s+(\S+)\s+(\S+)\s+(\S+)\s*"
    r"outer loop\s*"
    r"vertex\s+(\S+)\s+(\S+)\s+(\S+)\s*"
    r"vertex\s+(\S+)\s+(\S+)\s+(\S+)\s*"
    r"vertex\s+(\S+)\s+(\S+)\s+(\S+)\s*"
    r"endloop\s*endfacet")


def canonical(text: str) -> str:
    facets = []
    for m in FACET.finditer(text):
        g = m.groups()
        normal = g[0:3]
        verts = [g[3:6], g[6:9], g[9:12]]
        # Rotate — never sort — so the winding survives.
        start = min(range(3), key=lambda i: tuple(float(v) for v in verts[i]))
        verts = verts[start:] + verts[:start]
        facets.append((tuple(float(v) for v in verts[0]),
                       tuple(float(v) for v in verts[1]),
                       tuple(float(v) for v in verts[2]),
                       normal, verts))
    facets.sort(key=lambda f: (f[0], f[1], f[2]))

    out = ["solid OpenSCAD_Model"]
    for _, _, _, normal, verts in facets:
        out.append("  facet normal %s %s %s" % normal)
        out.append("    outer loop")
        for v in verts:
            out.append("      vertex %s %s %s" % v)
        out.append("    endloop")
        out.append("  endfacet")
    out.append("endsolid OpenSCAD_Model")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    bad = 0
    for path in args.files:
        with open(path) as f:
            text = f.read()
        if not text.lstrip().startswith("solid"):
            print(f"{path}: not an ASCII STL — OpenSCAD wrote binary?")
            bad += 1
            continue
        fixed = canonical(text)
        if canonical(fixed) != fixed:
            print(f"{path}: canonical form is not stable")
            bad += 1
            continue
        n = fixed.count("facet normal")
        if args.check:
            state = "canonical" if text == fixed else "NOT canonical"
            print(f"{path}: {state} ({n} facets)")
            if text != fixed:
                bad += 1
        else:
            with open(path, "w") as f:
                f.write(fixed)
            print(f"canonicalized {path} ({n} facets)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
