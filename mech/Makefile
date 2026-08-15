# The printed shell.
#
#   make           front.stl + back.stl
#   make gauge     the fit gauge — print THIS first, it is 8 g and answers the same
#                  tolerance questions the shell does
#   make render    PNGs of both halves and the opened-out assembly
#   make params    re-export board.scad from the PCB source (pcb/lib/geometry.py)
#
# Runs on the host or under ./dc; OpenSCAD is in the container for the same reason
# KiCad is. PNG export needs a display even though STL export does not, hence
# xvfb-run — `openscad -o x.png` on a headless box otherwise fails at GL init.

SCAD    := enclosure.scad
PARAMS  := board.scad
OSCAD   := openscad
XVFB    := xvfb-run -a

.PHONY: all stl gauge render params canonical images clean

# `all` BUILDS EVERYTHING THIS DIRECTORY COMMITS — the STLs and the renders. It used
# to be just the STLs, and the renders are committed too because the READMEs display
# them: so `make clean` followed by `make` left the tree missing five PNGs and both
# READMEs showing broken images. A clean build has to restore the tree it cleaned.
all: stl render images

# board.scad is GENERATED from the PCB. Never edit it; edit pcb/lib/geometry.py.
$(PARAMS): gen_params.py ../pcb/lib/geometry.py
	python3 gen_params.py

params:
	python3 gen_params.py

stl: front.stl back.stl

# Every STL goes through canonical_stl.py — CGAL emits facets in an unstable order,
# so without it a committed STL is modified by every build. See that file.
front.stl: $(SCAD) $(PARAMS)
	$(OSCAD) -o $@ -D 'part="front"' $(SCAD)
	@python3 canonical_stl.py $@

back.stl: $(SCAD) $(PARAMS)
	$(OSCAD) -o $@ -D 'part="back"' $(SCAD)
	@python3 canonical_stl.py $@

gauge: gauge.stl
gauge.stl: $(SCAD) $(PARAMS)
	$(OSCAD) -o $@ -D 'part="gauge"' $(SCAD)
	@python3 canonical_stl.py $@

# --camera=tx,ty,tz,rx,ry,rz,dist. These four angles were picked by looking at the
# output, not by arithmetic: the section is the one that matters, because it is the
# only view where the floor ledge, the pillars and the screw appear together. Look at
# it after changing any fit parameter.
render: $(SCAD) $(PARAMS)
	$(XVFB) $(OSCAD) -o render_parts.png --imgsize=1400,1000 \
	    --camera=0,12,0,58,0,25,330 -D 'part="parts"' $(SCAD)
	$(XVFB) $(OSCAD) -o render_assembly.png --imgsize=1400,1000 \
	    --camera=0,0,22,66,0,212,310 -D 'part="assembly"' $(SCAD)
	$(XVFB) $(OSCAD) -o render_front.png --imgsize=1100,900 \
	    --camera=0,0,22,60,0,20,280 -D 'part="front"' $(SCAD)
	$(XVFB) $(OSCAD) -o render_back.png --imgsize=1100,900 \
	    --camera=0,0,22,60,0,200,280 -D 'part="back"' $(SCAD)
	$(XVFB) $(OSCAD) -o render_section.png --imgsize=1100,900 \
	    --camera=-40,0,8,72,0,128,115 -D 'part="section"' $(SCAD)
	$(XVFB) $(OSCAD) -o render_mouth.png --imgsize=1200,850 \
	    --camera=0,0,-4,142,0,18,190 -D 'part="closed"' $(SCAD)

canonical: front.stl back.stl
	@python3 canonical_stl.py --check front.stl back.stl

# Every image the READMEs point at must exist. GitHub renders a missing image as a
# broken icon and nothing else complains, so this is the only thing that would catch
# a render that was deleted, renamed, or never generated.
images:
	@missing=""; \
	for f in $$(grep -ho 'render_[a-z]*\.png' README.md ../README.md | sort -u); do \
	    [ -f "$$f" ] || missing="$$missing $$f"; \
	done; \
	if [ -n "$$missing" ]; then \
	    echo "MISSING, and the READMEs link to them:$$missing"; exit 1; \
	fi; \
	echo "images: all README references present"

clean:
	rm -f front.stl back.stl gauge.stl render_*.png
