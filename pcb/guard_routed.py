#!/usr/bin/env python3
"""Refuse to regenerate a board that carries routing.

  python3 guard_routed.py [BOARD]     exit 1 if the board has more copper than
                                      generation itself produces

gen_board.py builds from scratch — it does not patch the board in place — so running
it throws away everything route.py added. That is fine when it is what you meant and
expensive when it is not, which is the definition of a thing to guard rather than to
remember.

The test is not "does the board have any tracks". gen_board.py stamps how many track
segments IT produced into the title block (`generated-tracks=N`, currently zero, but
read rather than assumed so this keeps working if it ever fans out), and anything
beyond that count is routing somebody added.

FORCE=1 make board  to mean it.
"""

import os
import re
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE,
                                                              "gg_toploader.kicad_pcb")
    if not os.path.exists(path):
        return 0                      # nothing to protect yet
    if os.environ.get("FORCE") == "1":
        print("FORCE=1 — regenerating over the existing board")
        return 0

    board = pcbnew.LoadBoard(path)
    tracks = len(board.GetTracks())
    stamp = 0
    for i in range(1, 10):
        m = re.match(r"generated-tracks=(\d+)", board.GetTitleBlock().GetComment(i))
        if m:
            stamp = int(m.group(1))
            break

    if tracks > stamp:
        print(f"{os.path.basename(path)} carries {tracks} track segments and "
              f"generation produces {stamp}.")
        print("Regenerating would discard the routing. Use FORCE=1 make board.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
