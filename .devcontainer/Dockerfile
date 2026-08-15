# Game Genie Toploader Adapter — reproducible headless CLI toolchain.
#
# Deliberately small: this repository is one passive two-layer board and a printed
# shell, so it needs a PCB toolchain, a CAD toolchain, and nothing else. It builds in
# a few minutes.
#
# INCLUDED
#   KiCad (kicad-cli + the pcbnew Python module + footprint/symbol/3D libraries)
#   OpenSCAD (CLI) + xvfb — mech/ STL export, and PNG export which needs a display
#   Python 3 + Pillow — pcb/gen_render.py crops the renders on the alpha channel
#   git, make
#
# DELIBERATELY NOT INCLUDED
#   An autorouter, or the Java runtime one would need. There is none in this project
#     and there should not be: route.py solves all 72 conductors in closed form and
#     audits them (see pcb/route.py). An autorouted board is a different shape every
#     run and cannot be reviewed as a diff.
#   Interactive GUIs — KiCad editor, OpenSCAD preview. Host side.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

# --- KiCad from the official PPA -------------------------------------------------------------
# 10.0.x TO MATCH THE DESKTOP. The alternative was 9.0.x to match this host's kicad-cli, and
# an earlier project settled that argument the expensive way: with the headless toolchain on
# 9.x, opening a board in the desktop upgraded its file format in place and 9's pcbnew could
# no longer load it at all (LoadBoard returned None). Matching the desktop removes the churn.
#
# kicad-cli and the pcbnew Python module ship in the SAME package, so they cannot drift apart.
# kicad-footprints is not optional here: gen_board.py loads MountingHole_2.1mm from
# /usr/share/kicad/footprints.
ARG KICAD_PPA=kicad/kicad-10.0-releases
RUN apt-get update && apt-get install -y --no-install-recommends \
      software-properties-common gnupg ca-certificates curl \
 && add-apt-repository -y "ppa:${KICAD_PPA}" \
 && apt-get update && apt-get install -y --no-install-recommends \
      kicad kicad-footprints kicad-symbols kicad-packages3d \
 && rm -rf /var/lib/apt/lists/*
# kicad-packages3d is ~1.5 GB and is the largest thing in this image by far. It stays because
# `kicad-cli pcb render` draws BARE boards without it — footprints reference
# ${KICAD10_3DMODEL_DIR}/*.step and nothing resolves them. The README image comes out of that
# renderer (pcb/gen_render.py), so a bare-board render is a wrong picture on the front page.

# --- mech + the render pipeline ----------------------------------------------------------------
# xvfb: OpenSCAD's PNG export needs a display even though the STL export does not, so
# `openscad -o thing.png` fails on a headless box without `xvfb-run`. mech/Makefile wraps it.
# python3-pil: pcb/gen_render.py crops each render to the board using the alpha channel.
# From apt, not pip — Ubuntu 24.04's Python is externally managed and pip refuses without
# --break-system-packages, and the distro package is the same library.
RUN apt-get update && apt-get install -y --no-install-recommends \
      openscad xvfb \
      python3 python3-pil \
      git make \
 && rm -rf /var/lib/apt/lists/*

# non-root dev user = the stock ubuntu:24.04 uid-1000 user, so files created on the bind
# mount are not root-owned (devcontainer.json's updateRemoteUserUID maps it to your host uid;
# `dc` passes --user explicitly for the same reason).
RUN mkdir -p /work && chown ubuntu:ubuntu /work
USER ubuntu
WORKDIR /work
CMD ["/bin/bash"]
