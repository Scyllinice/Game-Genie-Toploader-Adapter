#!/usr/bin/env python3
"""Render the board, and refresh the image the repository's README shows.

  python3 gen_render.py [--width N] [--no-readme]

Writes:
  render_top.png                              full-resolution, cropped to the board
  render_bottom.png
  ../Game Genie Toploader Adapter.png         the README image, at its original width

THE README IMAGE IS A BUILD ARTEFACT, and until now it was the one thing on the page
that still came from the hand-drawn board. Nothing about the copper changed in the
promotion — compare_original.py says so on every run — but a picture that cannot be
regenerated is a picture nobody can check, and it would quietly go stale the first
time the board did change.

WHY THE CROP. kicad-cli fits the board inside the frame it is given and pads the rest,
so asking for the board's own 2.44:1 aspect ratio still leaves margins on the short
axis — the render is fitted, not framed. --zoom only trades one margin for a clipped
edge. So this renders large, then crops to where the board actually is, measured from
the alpha channel rather than guessed.

The alpha test uses a THRESHOLD, not "any non-zero pixel". At high quality the render
carries a soft shadow whose alpha tails off to nothing several pixels out; cropping on
non-zero alpha frames the shadow instead of the board, off-centre, by a different
amount on each side.
"""

import argparse
import os
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(HERE, "gg_toploader.kicad_pcb")
README_IMAGE = os.path.abspath(os.path.join(HERE, "..",
                                            "Game Genie Toploader Adapter.png"))

# Render this many times the delivered width, then downsample. The board is 99.7 mm
# of 2.5 mm-pitch fingers and 0.2 mm tracks; rendered at final size the tracks alias
# into a dotted line, and the finger gaps go grey.
SUPERSAMPLE = 3
ALPHA_FLOOR = 128        # below this is shadow, not board


def render(side: str, path: str, width: int, height: int):
    subprocess.run(
        ["kicad-cli", "pcb", "render", "--side", side,
         "--background", "transparent", "--quality", "high",
         "--width", str(width), "--height", str(height),
         "-o", path, BOARD],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def crop_to_board(path: str) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    alpha = img.getchannel("A").point(lambda v: 255 if v >= ALPHA_FLOOR else 0)
    box = alpha.getbbox()
    if box is None:
        raise SystemExit(f"{path}: nothing opaque in the render")
    return img.crop(box)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=940,
                    help="delivered width of the README image (default: its "
                         "original 940 px)")
    ap.add_argument("--no-readme", action="store_true",
                    help="render only, leave the README image alone")
    args = ap.parse_args()

    # Ask for a frame comfortably larger than the board's aspect ratio in both
    # directions; the crop is what sets the final framing.
    w = args.width * SUPERSAMPLE
    h = int(w / 2.0)

    for side in ("top", "bottom"):
        raw = os.path.join(HERE, f"render_{side}.png")
        render(side, raw, w, h)
        img = crop_to_board(raw)
        img.save(raw)
        print(f"wrote {os.path.basename(raw)}  {img.width} x {img.height}")
        if side == "top" and not args.no_readme:
            scale = args.width / img.width
            small = img.resize((args.width, max(1, round(img.height * scale))),
                               Image.LANCZOS)
            small.save(README_IMAGE)
            print(f"wrote {README_IMAGE}  {small.width} x {small.height}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
