#!/usr/bin/env python3
"""Say which KiCad is about to write the board, and whether it is the pinned one.

  python3 check_toolchain.py        warns; never fails the build

THE COMMITTED BOARD HAS A FILE FORMAT, and it is whichever KiCad generated it. The
generators themselves are version-agnostic — verified, the whole pipeline runs
unchanged on 9.0.8 and 10.0.5 and produces a board that passes compare_original.py
either way — but the two write different files: 2465 differing lines of schema between
them, none of it geometry (`(tenting front back)` becoming a nested block, float
formatting, the format version itself).

So regenerating on the wrong KiCad rewrites the entire committed artifact without
changing the board, and a real change made in the next commit would be invisible
inside that. It also runs the other way, and this one has actually happened: open a
9.x board once in a KiCad 10 desktop and the desktop upgrades the file in place, after
which 9's pcbnew cannot load it at all — `LoadBoard` returns None.

The pin is 10.0.x, matching the desktop install. `./dc` from the repository root runs
the pipeline in a container that has exactly that.

This WARNS rather than fails on purpose: checking a board on whatever KiCad you have
is a reasonable thing to do, and `make drc` on 9.x is perfectly valid. It is
REGENERATING on an unpinned version that costs you a diff.
"""

import re
import sys

import pcbnew

PINNED_MAJOR = 10


def main():
    build = pcbnew.GetBuildVersion()
    m = re.match(r"(\d+)\.(\d+)", build)
    if not m:
        print(f"toolchain: cannot read a version out of {build!r} — proceeding")
        return 0
    major = int(m.group(1))
    if major == PINNED_MAJOR:
        print(f"toolchain: KiCad {build} (pinned {PINNED_MAJOR}.x)")
        return 0

    print(f"toolchain: KiCad {build} — THE PIN IS {PINNED_MAJOR}.x")
    print("  Checks are fine on this version. Regenerating is not: the board will be")
    print("  rewritten in this version's file format, which is a few thousand lines of")
    print("  diff with no change to the board.")
    print("  Run it in the container instead:  ./dc bash -c 'cd pcb && make rebuild'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
