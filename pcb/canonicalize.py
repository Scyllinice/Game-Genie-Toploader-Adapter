#!/usr/bin/env python3
"""Make the generated .kicad_pcb byte-reproducible.

  python3 canonicalize.py [BOARD]

THE PROBLEM. Regenerating this board from the same source produces an equivalent file
that is not an identical one, for two reasons that are really one reason:

  1. pcbnew mints a fresh random UUID for every item it creates — 380-odd here.
  2. Item ORDER in the written file follows iteration over containers keyed on those
     UUIDs, so it moves run to run as well.

The result is that a rebuild with no design change shows up as a large diff, and a
rebuild WITH a change hides that change inside it. Reviewing "what did this edit
actually do to the board" is the main thing a generated board is supposed to make
possible, so this is worth a post-pass.

WHY A POST-PASS. `m_Uuid` is read-only in the Python bindings and the only related
method regenerates them, so identifiers cannot be chosen while the board is built.
They can only be rewritten in the file afterwards.

WHAT IT DOES. Each top-level item gets a UUID derived from a hash of its own content
with the UUIDs stripped out — identity from what the item IS, not from when it was
made — plus an occurrence index so identical twins stay distinct. Items are then
sorted by that content. Structural blocks (version, generator, general, paper,
layers, setup, net) keep their positions; only items move.

It never touches geometry, nets or layers. Two properties are asserted by --check:
DETERMINISTIC (same input content, same bytes) and IDEMPOTENT (running it twice
changes nothing). The Makefile runs it as the last step of `rebuild`, and `make drc`
after it is what proves the board still means the same thing.
"""

import argparse
import hashlib
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
NS = uuid.UUID("2f5c9e14-8a3b-52d7-b6c1-9e0d4a7f2b58")

# Top-level tags that are ITEMS (movable). Everything else keeps its place.
ITEM_TAGS = {"footprint", "gr_line", "gr_rect", "gr_circle", "gr_arc", "gr_poly",
             "gr_text", "gr_curve", "segment", "arc", "via", "zone", "dimension",
             "image", "group", "target"}

UUID_RE = re.compile(r'\(uuid "([0-9a-fA-F-]{36})"\)')


def split_blocks(body: str):
    """Split the top level of a .kicad_pcb into (tag, text) chunks, in order.

    Text between blocks (indentation, newlines) is attached to the following block so
    reassembly is exact.
    """
    out = []
    i, n = 0, len(body)
    while i < n:
        j = body.find("(", i)
        if j < 0:
            out.append((None, body[i:]))
            break
        lead = body[i:j]
        depth, k, in_str = 0, j, False
        while k < n:
            c = body[k]
            if in_str:
                if c == '"' and body[k - 1] != "\\":
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        block = body[j:k + 1]
        tag = re.match(r"\(([\w_]+)", block).group(1)
        out.append((tag, lead + block))
        i = k + 1
    return out


def canonicalize(text: str) -> str:
    head_end = text.index("\n") + 1                    # "(kicad_pcb\n"
    head, body = text[:head_end], text[head_end:]
    tail = ""
    if body.rstrip().endswith(")"):
        cut = body.rstrip().rfind(")")
        tail = body[cut:]
        body = body[:cut]

    blocks = split_blocks(body)
    items, fixed = [], []
    for idx, (tag, chunk) in enumerate(blocks):
        (items if tag in ITEM_TAGS else fixed).append((idx, tag, chunk))

    # Content identity: the block with every UUID blanked out.
    seen = {}
    rewritten = []
    for idx, tag, chunk in items:
        stripped = UUID_RE.sub('(uuid "")', chunk)
        digest = hashlib.sha1(stripped.encode()).hexdigest()
        occ = seen.get(digest, 0)
        seen[digest] = occ + 1
        counter = [0]

        def replace(_m, digest=digest, occ=occ, counter=counter):
            counter[0] += 1
            return '(uuid "%s")' % uuid.uuid5(NS, f"{digest}:{occ}:{counter[0]}")

        rewritten.append((tag, stripped, UUID_RE.sub(replace, chunk)))

    # Sort by what the item IS. The stripped text is the sort key so two runs that
    # produced the same items in different orders come out the same way round.
    rewritten.sort(key=lambda t: (t[0], t[1]))

    out = [head]
    item_slot = min((i for i, _, _ in items), default=len(blocks))
    for idx, tag, chunk in fixed:
        if idx > item_slot and rewritten:
            out += [c for _, _, c in rewritten]
            rewritten = []
        out.append(chunk)
    out += [c for _, _, c in rewritten]
    out.append(tail)
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("board", nargs="?",
                    default=os.path.join(HERE, "gg_toploader.kicad_pcb"))
    ap.add_argument("--check", action="store_true",
                    help="verify idempotence instead of writing")
    args = ap.parse_args()

    with open(args.board) as f:
        text = f.read()
    once = canonicalize(text)
    twice = canonicalize(once)

    if once != twice:
        print("FAIL: canonicalize is not idempotent — a second pass changes the file")
        return 1
    if args.check:
        print("canonical" if text == once else "NOT canonical (run without --check)")
        return 0 if text == once else 1

    with open(args.board, "w") as f:
        f.write(once)
    n = len(UUID_RE.findall(once))
    print(f"canonicalized {os.path.basename(args.board)}  ({n} uuids derived from "
          f"item content, items sorted)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
