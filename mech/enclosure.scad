// Game Genie Toploader Adapter — two-part printed shell.
//
//   make            front.stl + back.stl
//   make render     PNGs of both halves and the assembly
//   openscad enclosure.scad            preview (part = "assembly")
//
// The board stands up in use: gold fingers down into the console, the 2x36 edge
// connector on top with the Game Genie plugged into it.
//
// THE CONSOLE END IS BUILT LIKE A CARTRIDGE'S, from measured cart geometry (see the
// block below). The shell does not stop at the fingers and let them hang out in the
// air — it carries on past them as a skirt, and the fingers sit recessed 7 mm up
// inside a MOUTH that the console's 72-pin connector body rises into. Outer size is
// the cart's too: 106.1 mm across the connector end, 16.8 mm thick.
//
// WHAT HOLDS THE BOARD, in order of how much load each part takes:
//
//   the BULKHEAD   The wall that closes the mouth off from the cavity above it. The
//                  board's shoulders — where the 93.5 mm tongue widens to the 99.7 mm
//                  body — seat on its top face, which is also what stops the board
//                  being pushed further into the console. Pushing a Game Genie in
//                  presses the board DOWN onto it, so insertion force goes into a
//                  2.2 mm plastic shelf and not into the screws. A real cart does the
//                  same thing with a 1.4 mm bulkhead per half.
//   the PILLARS    Two internal posts per half, on the board's own 2.1 mm mounting
//                  holes. They set the board on the centre plane and clamp it.
//   the SCREWS     Two M2, front to back, through those same holes. They hold the
//                  halves together; they are not carrying the board.
//
// The pillar faces are plastic bearing on soldermask over copper — several traces
// pass within 1.5 mm of each hole (route.py steers them around it). Plastic is the
// right material for that: a bare metal screw head torqued onto soldermask over a
// trace can abrade through it over time, which is the reason fibre washers get
// specified under screw heads on boards like this. Here the pillar IS the washer.
// Do not counterbore the head down onto the board.
//
// DIMENSIONS YOU MUST CHECK BEFORE PRINTING are collected under "edge connector"
// below. Everything about the BOARD is generated from the PCB source
// (board.scad <- mech/gen_params.py <- pcb/lib/geometry.py) and needs no checking;
// the connector is a bought part nobody here has measured. Print the fit gauge
// (part = "gauge") first — it is 8 grams and it answers the same questions the full
// shell does, an hour sooner.

include <board.scad>

/* [What to build] */
// front = the half you see, back = the half with the screw threads
part = "assembly";  // [front, back, parts, assembly, section, gauge]

/* [Fit] */
// Clearance around the board inside its slot, per side. 0.25 suits a well-tuned
// FDM printer at 0.2 mm layers; go to 0.35 if your first layer squishes wide.
FIT = 0.25;
// Wall thickness. 2.0 is four perimeters at 0.5 mm and is stiff enough at this size.
WALL = 2.0;
// Outer corner rounding.
CORNER_R = 2.5;

/* [Edge connector — MEASURE YOUR PART] */
// A TE 5530843-8 (or the AliExpress equivalents the README lists). These are the
// numbers to caliper: the shell's whole upper half is built from them, and they are
// the only figures in this model that were not taken from the board.
//
// CONN_L/CONN_D are the BODY, not the pin span. CONN_H is measured from where the
// body sits on the board's top edge to the top of the plastic.
CONN_L = 95.0;    // along the board
CONN_D = 11.0;    // across the board — this sets how thick the whole shell is
CONN_H = 12.0;    // above the board's top edge
// How far the connector body reaches DOWN past the board's top edge, if it does.
CONN_OVERLAP = 0.0;
// Gap between the connector and the shell around it.
CONN_CLR = 0.6;
// The shell stops this far below the top of the connector, so the shell can never
// be what a Game Genie lands on — it has to seat on the connector itself.
HOOD_DROP = 1.5;

/* [Fasteners] */
SCREW_CLR_D = 2.2;   // through the front half
SCREW_HEAD_D = 4.0;  // counterbore in the front face
SCREW_HEAD_H = 1.8;
PILOT_D = 1.65;      // back half: thread-forming M2 bites into this
PILLAR_D = 5.5;
PILOT_SKIN = 0.8;    // plastic left at the bottom of the blind pilot hole

/* [Assembly aids] */
// A LAP JOINT AROUND THE WALL, not locating pegs.
//
// Pegs were the first attempt and there is nowhere to put them: the interior width
// IS the board width plus the fit, by construction, so the board fills the shell
// wall to wall and any peg inside the body lands on it. There is a little room in
// the floor beside the tongue and a little beside the connector, but both are ~2 mm
// and a 2 mm printed peg in a 2 mm pocket is a coin toss.
//
// The lap is better anyway, because the problem is not really alignment — the board
// itself aligns the halves, sitting in a slot in both. The problem is that the only
// screws are at z=22.2 (the board's holes are where they are) and the shell carries
// on for another 29 mm above them with nothing holding the two sides together. A
// step around the wall means the top of the seam cannot open even though nothing
// clamps it there.
LAP_W = WALL / 2;    // how much of the wall thickness the step takes
LAP_H = 1.2;         // how far it crosses the parting plane
LAP_CLR = 0.15;      // groove is this much looser than the tongue

/* [The console end — MEASURED FROM A REAL NES CARTRIDGE] */
// These are not guesses. Every number in this block is mesh-measured off a real NES
// cartridge and dry-fit verified in a console; they are the reason this end is
// cartridge-shaped rather than a flat slab with the fingers hanging out of it.
//
// AND YES, THEY APPLY TO A TOP LOADER. The obvious objection to cart geometry in a
// NES-101 adapter is that it might have been taken against a front loader — it was.
// It does not matter: the two consoles take the same 72-pin connector and the same
// cartridge, by design. One cart fits both, so the cart's own mouth clears both
// connectors, and every dimension here is a dimension OF THE CARTRIDGE rather than
// of either console.
//
// What does NOT transfer is anything describing contact with a console's SHELL —
// front-loader tray posts, guide ribs, clamp pads, the thumb-pocket dish a tray post
// lands in. None of that is in this model; there is nothing here but the mouth.
//
// A real cart does NOT expose its fingers. The shell continues past them as a skirt,
// the fingers sit recessed up inside a MOUTH, and the console's 72-pin connector body
// rises into that mouth as the cart seats. Plastic below, above and beside the card
// edge — which is why you can drop a cartridge on the floor and still play it.
//
// The chain that has to hold, or the board never seats:
//   the mouth must clear the CONNECTOR BODY (~100 x 10 mm), not just the fingers
//   the mouth must stay open far enough up for the connector to reach the fingers
//   the bulkhead behind it is the hard stop, and the card edge seats against it
CART_T       = 16.8;   // real cart assembled thickness — this sets the shell's depth
CART_NOSE_W  = 106.1;  // real cart width AT THE CONNECTOR END (the body is 119.3 and
                       //   steps in to this over the bottom 24.3 mm; we are already
                       //   narrower than the body, so we are all nose)
EDGE_RECESS  = 7.0;    // how far the fingers recess UP inside the mouth. Caliper on a
                       //   real cart: 7.08. Interference-scanning a cart through an
                       //   assembled shell bounds it to 6.64..7.02. A guess of 1 mm
                       //   failed the dry fit, which is how it came to be measured.
MOUTH_W      = 101.3;  // mouth width — ~0.65 mm/side over a 100 mm connector body
MOUTH_H      = 10.4;   // mouth opening in the thickness direction
MOUTH_LIP_BOT = 3.4;   // material below the mouth on the back face (top lip = 3.0)
MOUTH_OPEN   = 19.7;   // mouth stays open this far up from the bottom face; above it
                       //   the bulkhead closes the cavity down to the board slot
EDGE_CHAMF   = 1.0;    // 45-degree lead-in chamfer around the bottom face

$fa = 2;
$fs = 0.4;

// ---------------------------------------------------------------------------
// Derived
// ---------------------------------------------------------------------------
SLOT_T   = BOARD_T + 2 * FIT;                     // board slot thickness

// THE OUTER SIZE IS THE CARTRIDGE'S, NOT THE BOARD'S. Both ends have something that
// must fit inside — the console's connector at the bottom, the Game Genie's at the
// top — and where they disagree the cart dimension wins, because it is the one proven
// to fit a console.
OUTER_D  = max(CART_T, CONN_D + 2 * CONN_CLR + 2 * WALL, SLOT_T + 2 * WALL);
OUTER_W  = max(CART_NOSE_W, MOUTH_W + 2 * WALL, BOARD_W + 2 * (FIT + WALL),
               CONN_L + 2 * (CONN_CLR + WALL));
INNER_D  = OUTER_D - 2 * WALL;
INNER_W  = OUTER_W - 2 * WALL;

// z = 0 is the board's insertion edge. The shell now goes BELOW it: the skirt reaches
// EDGE_RECESS past the card edge, so the fingers sit up inside the mouth.
SHELL_Z0    = -EDGE_RECESS;                       // bottom face of the skirt
MOUTH_TOP   = SHELL_Z0 + MOUTH_OPEN;              // where the bulkhead begins
BULKHEAD_Z1 = TONGUE_ROOT_Z;                      // its top face — the card-edge seat
CONN_Z0     = TOP_EDGE_Z - CONN_OVERLAP;          // underside of the GG connector body
SHELL_Z1    = CONN_Z0 + CONN_H - HOOD_DROP;       // top rim

// Head bottom to the end of the blind pilot: what the screw actually has to span.
SCREW_LEN = (OUTER_D / 2 - SCREW_HEAD_H) + (OUTER_D / 2 - PILOT_SKIN);

echo(str("shell     : ", OUTER_W, " x ", OUTER_D, " x ", SHELL_Z1 - SHELL_Z0, " mm"));
echo(str("mouth     : ", MOUTH_W, " x ", MOUTH_H, ", open ", MOUTH_OPEN,
         " mm up from the bottom face"));
echo(str("fingers   : recessed ", EDGE_RECESS, " mm inside the mouth, ",
         MOUTH_TOP, " mm of card reachable by the console connector"));
echo(str("bulkhead  : ", BULKHEAD_Z1 - MOUTH_TOP, " mm thick, card edge seats on it"));
echo(str("screws    : 2 x M2, ", ceil(SCREW_LEN), " mm long (thread-forming)"));

// 2D profiles live in (x, z) and are extruded across the board — see gen_params.py
// for why z is flipped relative to KiCad.
module extrude_y(depth) {
    rotate([90, 0, 0]) linear_extrude(height = depth, center = true) children();
}

module rrect(w, h, r, z0) {
    translate([0, z0 + h / 2])
        offset(r = r) offset(r = -r) square([w, h], center = true);
}

// ---------------------------------------------------------------------------
// The solid shell, before it is split
// ---------------------------------------------------------------------------
module outer_2d() {
    union() {
        rrect(OUTER_W, SHELL_Z1 - SHELL_Z0, CORNER_R, SHELL_Z0);
        // Square off the bottom two corners. A cartridge's connector end is square in
        // this view and eased by the 45-degree chamfer instead; leaving the 2.5 mm
        // plan radius here would put a mismatched step where the nose meets the body.
        translate([0, SHELL_Z0 + CORNER_R / 2])
            square([OUTER_W, CORNER_R], center = true);
    }
}

// The main cavity, above the bulkhead. Open at the top — it runs 1 mm past the top
// rim so no lid is left behind.
module inner_2d() {
    rrect(INNER_W, SHELL_Z1 - BULKHEAD_Z1 + 1, max(0.1, CORNER_R - WALL), BULKHEAD_Z1);
}

module shell_outer() {
    union() {
        // Body, from the top of the nose chamfer up.
        intersection() {
            extrude_y(OUTER_D) outer_2d();
            translate([0, 0, (SHELL_Z0 + EDGE_CHAMF + SHELL_Z1) / 2])
                cube([OUTER_W + 2, OUTER_D + 2, SHELL_Z1 - SHELL_Z0 - EDGE_CHAMF],
                     center = true);
        }
        // The nose: a 45-degree lead-in all the way round the bottom face, the same
        // chamfer a cartridge has. It is what lets the thing find the slot instead of
        // catching on its own square edge.
        hull() {
            translate([0, 0, SHELL_Z0 + 0.005])
                cube([OUTER_W - 2 * EDGE_CHAMF, OUTER_D - 2 * EDGE_CHAMF, 0.01],
                     center = true);
            translate([0, 0, SHELL_Z0 + EDGE_CHAMF])
                cube([OUTER_W, OUTER_D, 0.01], center = true);
        }
    }
}

module shell_cavity() { extrude_y(INNER_D) inner_2d(); }

// THE MOUTH: the pocket the console's connector body rises into. Open from the bottom
// face up to the bulkhead, with a lip on each face — 3.4 mm on the back, 3.0 on the
// label side, exactly as the cart carries them. The card edge hangs in the middle of
// it with air all round, which is the point: nothing touches the fingers except the
// console's contacts.
module mouth_void() {
    y0 = -OUTER_D / 2 + MOUTH_LIP_BOT;
    translate([0, y0 + MOUTH_H / 2, (SHELL_Z0 - 1 + MOUTH_TOP) / 2])
        cube([MOUTH_W, MOUTH_H, MOUTH_TOP - SHELL_Z0 + 1], center = true);
}

// The slot the board itself occupies: its own outline, grown by the fit, and run
// out through the bottom of the floor so the tongue has somewhere to go.
module board_slot() {
    extrude_y(SLOT_T)
        offset(r = FIT)
            polygon(BOARD_OUTLINE);
    // Below the board outline there is nothing to offset, so extend the tongue
    // slot downward past the bottom face.
    extrude_y(SLOT_T)
        translate([(TONGUE_LEFT_X + TONGUE_RIGHT_X) / 2, -5])
            square([TONGUE_W + 2 * FIT, 10], center = true);
}

// The connector's own volume, so the hood cannot foul it.
module connector_void() {
    translate([0, 0, CONN_Z0 + (CONN_H + 1) / 2])
        cube([CONN_L + 2 * CONN_CLR, CONN_D + 2 * CONN_CLR, CONN_H + 1], center = true);
}

// One screw column, centred on a board mounting hole and running through the shell.
module pillar(pos) {
    translate([pos[0], 0, pos[1]]) rotate([90, 0, 0])
        cylinder(d = PILLAR_D, h = INNER_D, center = true);
}

module screw_cut_front(pos) {
    translate([pos[0], 0, pos[1]]) rotate([-90, 0, 0]) {
        cylinder(d = SCREW_CLR_D, h = OUTER_D);                       // shank
        translate([0, 0, OUTER_D / 2 - SCREW_HEAD_H])
            cylinder(d = SCREW_HEAD_D, h = SCREW_HEAD_H + 1);         // head
    }
}

module screw_cut_back(pos) {
    // Blind: the pilot stops PILOT_SKIN short of the outer face, so nothing shows
    // on the outside of the finished shell and the screw cannot poke through.
    translate([pos[0], 0, pos[1]]) rotate([90, 0, 0])
        cylinder(d = PILOT_D, h = OUTER_D / 2 - PILOT_SKIN);
}

// The lap: the OUTER part of the wall's cross-section, everywhere the two halves
// actually touch. That is the side walls and the floor — not the top, where the
// cavity runs out through the rim and there is no wall to step.
module lap_2d(clearance = 0) {
    intersection() {
        outer_2d();
        offset(delta = clearance)
            difference() {
                difference() { outer_2d(); inner_2d(); }   // the wall, in section
                offset(delta = -LAP_W) outer_2d();         // minus its inner part
            }
    }
}

// Everything on the front half's side of the parting plane: the y>0 halfspace, plus
// the lap crossing into the back half's side.
module split_volume(clearance = 0) {
    union() {
        translate([0, (OUTER_D + 20) / 2, (SHELL_Z0 + SHELL_Z1) / 2])
            cube([OUTER_W + 20, OUTER_D + 20, SHELL_Z1 - SHELL_Z0 + 20], center = true);
        translate([0, -(LAP_H + clearance) / 2, 0])
            extrude_y(LAP_H + clearance) lap_2d(clearance);
    }
}

module shell_body() {
    difference() {
        union() {
            shell_outer();
            for (p = MOUNT_POS) pillar(p);
        }
        shell_cavity_and_slot();
    }
}

// The cavity, minus the pillars, so hollowing does not eat them.
module shell_cavity_and_slot() {
    difference() {
        union() { shell_cavity(); connector_void(); mouth_void(); }
        for (p = MOUNT_POS) pillar(p);
    }
}

module shell() {
    difference() {
        shell_body();
        board_slot();
        for (p = MOUNT_POS) { screw_cut_front(p); screw_cut_back(p); }
    }
}

// ---------------------------------------------------------------------------
// Halves. The parting plane is the board's own centre plane, so each half carries
// half the board slot and the board is trapped when they close.
// ---------------------------------------------------------------------------
// The two halves are cut with the SAME volume — one keeps what is inside it, the
// other keeps what is outside. They cannot overlap or leave a gap, whatever the lap
// geometry does, because they are complements of one shape. The back half is cut
// with a slightly grown version so the groove is looser than the tongue.
module front_half() {
    intersection() { shell(); split_volume(0); }
}

module back_half() {
    difference() { shell(); split_volume(LAP_CLR); }
}

// ---------------------------------------------------------------------------
// The fit gauge: the bottom 20 mm of the shell, both halves, printed as one small
// part per side. It carries the floor, the tongue slot, one screw pillar and one
// peg — every tolerance in the design except the connector's — and it prints in
// minutes. Check that the board drops onto the floor without forcing and that the
// halves close with no gap, THEN print the shell.
// ---------------------------------------------------------------------------
// Far enough up to catch a screw pillar as well as the mouth, the bulkhead and the
// card seat — the pillars moved out of range when the shell grew a skirt, and a gauge
// that does not test the screws is not testing the assembly.
GAUGE_Z1 = MOUNT_POS[0][1] + PILLAR_D / 2 + 1;

// A ternary cannot select a MODULE in OpenSCAD — `cond ? a() : b()` is an expression
// and fails to parse, with the error pointing at this line and no hint why.
module gauge_cut() {
    intersection() {
        children();
        translate([0, 0, (SHELL_Z0 + GAUGE_Z1) / 2])
            cube([OUTER_W + 2, OUTER_D * 3, GAUGE_Z1 - SHELL_Z0], center = true);
    }
}

module gauge() {
    gauge_cut() front_half();
    translate([0, -OUTER_D - 4, 0]) gauge_cut() back_half();
}

// ---------------------------------------------------------------------------
module board_mockup() {
    color("#1a6b3c", 0.9)
        extrude_y(BOARD_T) polygon(BOARD_OUTLINE);
    color("#c8a800", 0.9)
        translate([0, 0, CONN_Z0 + CONN_H / 2])
            cube([CONN_L, CONN_D, CONN_H], center = true);
}

// A cut through one of the screws — the only view that shows all three of the things
// that hold the board at once (floor ledge, pillars, screw), and the one to look at
// after changing any fit parameter.
module section() {
    intersection() {
        union() {
            front_half();
            back_half();
            board_mockup();
        }
        translate([MOUNT_POS[0][0] - OUTER_W, 0, (SHELL_Z0 + SHELL_Z1) / 2])
            cube([OUTER_W * 2, OUTER_D * 2, (SHELL_Z1 - SHELL_Z0) * 2 + 20],
                 center = true);
    }
}

// BOTH HALVES LAID OUT AS THEY PRINT — outer face down, interior up, which is also
// the only view that shows the inside of both at once. Sliding them apart along the
// parting plane does not: the two halves open TOWARD each other, so any camera that
// sees into one is looking at the back of the other.
module parts() {
    translate([0, OUTER_D + 6, 0]) rotate([-90, 0, 0]) front_half();
    rotate([90, 0, 0]) back_half();
}

// The finished object, halves closed — for looking at the mouth from below, which is
// the view that says whether the console end is right.
module closed() { front_half(); back_half(); }

if (part == "closed") closed();
else if (part == "parts") parts();
else if (part == "front") front_half();
else if (part == "back") back_half();
else if (part == "gauge") gauge();
else if (part == "section") section();
else {
    // assembly: halves opened out so both insides are visible, board in the middle.
    // The offset has to EXCEED OUTER_D/2 or the halves still overlap and the view
    // looks like one solid block — which is what 6 mm did.
    EXPLODE = OUTER_D;
    translate([0, EXPLODE, 0]) front_half();
    translate([0, -EXPLODE, 0]) back_half();
    %board_mockup();
}
