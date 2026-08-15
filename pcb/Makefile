# Scripted rebuild of the Game Genie Toploader Adapter.
#
#   make           check the files as they stand — DRC, ERC, card edge, and the
#                  comparison against the released board. Regenerates NOTHING.
#   make rebuild   the whole pipeline, from the pin table to a routed board
#   make compare   prove the result is the released board, pad for pad
#   make fab       gerbers, drill, position file, BOM
#
# Nothing here needs a container: KiCad 9's kicad-cli and its pcbnew Python module do
# all of it, and both are on the host. Boards are written in KiCad 9 format while the
# released files are KiCad 8 — which is why compare_original.py compares loaded
# models and not text.

BOARD   := gg_toploader.kicad_pcb
SCH     := gg_toploader.kicad_sch
PRO     := gg_toploader.kicad_pro
FABDIR  := fab
ORIGINAL := reference/Game Genie Toploader Adapter.kicad_pcb

.PHONY: all rebuild footprints symbol sch board route project canonical rules \
        toolchain drc erc fingers compare render fab bom clean

# The default target REGENERATES NOTHING, and neither does `make fab`. A fab target
# that depends on the generators will quietly rebuild an UNROUTED board and export
# gerbers of it — every target here consumes $(BOARD) as it stands.
all: toolchain drc erc fingers canonical compare

# ---- generation --------------------------------------------------------------
# ORDER MATTERS TWICE OVER:
#
#   route.py after gen_board.py   the board is built from scratch, so generating it
#                                 discards routing. guard_routed.py refuses to do
#                                 that to a routed board unless FORCE=1.
#   gen_project.py LAST           pcbnew.SaveBoard() rewrites the sibling .kicad_pro
#                                 and resets the net classes to KiCad's defaults.
#                                 verify_rules.py is what catches it if this slips.
rebuild:
	@python3 check_toolchain.py
	@python3 guard_routed.py $(BOARD)
	python3 lib/pinout.py > /dev/null
	python3 lib/geometry.py > /dev/null
	python3 gen_footprints.py
	python3 gen_symbol.py
	python3 gen_schematic.py
	python3 gen_board.py
	python3 route.py
	python3 canonicalize.py
	python3 gen_project.py
	@python3 verify_rules.py
	@$(MAKE) --no-print-directory all

footprints:
	python3 gen_footprints.py

symbol:
	python3 gen_symbol.py

sch: symbol
	python3 gen_schematic.py

board: footprints
	@python3 guard_routed.py $(BOARD)
	python3 gen_board.py
	python3 gen_project.py

route: $(BOARD)
	python3 route.py --force
	python3 canonicalize.py
	python3 gen_project.py

project:
	python3 gen_project.py

# UUIDs and item order out of pcbnew are random, which makes a no-op rebuild look
# like a large diff. canonicalize.py derives both from item content instead.
canonical: $(BOARD)
	@python3 canonicalize.py --check $(BOARD)

rules:
	@python3 verify_rules.py

# Which KiCad is about to write the board — the committed file's FORMAT is whichever
# one generated it. Warns, never fails. See check_toolchain.py.
toolchain:
	@python3 check_toolchain.py

# ---- checks ------------------------------------------------------------------
drc: $(BOARD)
	kicad-cli pcb drc --exit-code-violations -o $(BOARD:.kicad_pcb=-drc.rpt) $(BOARD)

erc: $(SCH)
	kicad-cli sch erc --exit-code-violations -o $(SCH:.kicad_sch=-erc.rpt) $(SCH)

# Card-edge rules KiCad has no check for — pitch, the bevel zone, the contact wipe
# path. See check_fingers.py.
fingers: $(BOARD)
	@python3 check_fingers.py $(BOARD) 2>/dev/null

# The equivalence proof. This is the target that says the rebuild is the same board.
compare: $(BOARD)
	@python3 compare_original.py $(BOARD) "$(ORIGINAL)" 2>/dev/null

# ---- outputs -----------------------------------------------------------------
# NOT part of `rebuild`, deliberately. This target rewrites the README's image,
# which is tracked, and the raytracer is not bit-exact run to run (~400 pixels of
# sampling noise at a delta of 3/255). Folding it into every rebuild would dirty a
# binary file for nothing. Refresh it when the board changes.
render: $(BOARD)
	python3 gen_render.py

bom: $(BOARD)
	@python3 gen_bom.py $(BOARD) 2>/dev/null

fab: $(BOARD)
	mkdir -p $(FABDIR)
	kicad-cli pcb export gerbers -o $(FABDIR)/ $(BOARD)
	kicad-cli pcb export drill   -o $(FABDIR)/ $(BOARD)
	kicad-cli pcb export pos     -o $(FABDIR)/pos.csv --format csv --units mm $(BOARD)
	@python3 gen_bom.py $(BOARD) 2>/dev/null

clean:
	rm -f $(BOARD) $(SCH) $(PRO) sym-lib-table fp-lib-table \
	      gg_toploader-drc.rpt gg_toploader-erc.rpt render_*.png
	rm -rf $(FABDIR) lib/gg_adapter.pretty lib/gg_adapter.kicad_sym lib/__pycache__
