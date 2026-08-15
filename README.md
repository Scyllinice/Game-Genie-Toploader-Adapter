# Game Genie Toploader Adapter

<p xmlns:cc="http://creativecommons.org/ns#" >This work by <span property="cc:attributionName">Scyllinice</span> is licensed under <a href="https://creativecommons.org/licenses/by-nc/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Creative Commons Attribution-NonCommercial 4.0 International<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1" alt=""><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1" alt=""><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/nc.svg?ref=chooser-v1" alt=""></a></p>

<a href='https://ko-fi.com/scyllinice' target='_blank'><img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi2.png?v=3' border='0' alt='Support me on ko-fi.com' /></a>

<a href="https://www.pcbway.com/project/shareproject/Game_Genie_Toploader_Adapter_25efb8dd.html"><img src="https://www.pcbway.com/project/img/images/frompcbway-1220.png" alt="PCB from PCBWay" /></a>


![Render](<Game Genie Toploader Adapter.png>)

This is a adapter/riser PCB for using an original Game Genie on your top loading NES. It also works for clone NES systems that load directly from the cart instead of using emulation (a Retron 5, for example, will not work).

The only component needed to build this PCB into a functioning unit would be a 2.54mm pitch 2x36 pin (72 pin total) edge connector. You can search **5530843-8** for a part number as well.

I have had success using the following edge connectors:

* [Edge connector 1](https://www.aliexpress.us/item/3256802817047324.html)
* [Edge connector 2](https://www.aliexpress.us/item/2251832843397196.html)
* [DigiKey](https://www.digikey.com/en/products/detail/te-connectivity-amp-connectors/5530843-8/770547)

When soldering the edge connector to the top of the board, you will need to bend in the pins a bit as the board is only 1.2mm thick to match the original thickness of a NES retail cartridge. This helps preserve the NES cartridge connector. 

For longevity, it is recommended to use an ENIG finish with gold fingers. HASL (or Lead Free HASL) will still work, but it's more fragile and can fail over time.

[JLCPCB](https://jlcpcb.com/) is generally better priced for ENIG gold fingers than PCBWay. As the time of this writing, you can get 5 of these boards for about $20 US at JLCPCB.

## 3D printed enclosure — [`mech/`](mech/README.md)

![both halves, laid out as they print](mech/render_parts.png)

A two-part shell, **106.1 × 16.8 × 58.4 mm**, held together by two M2 screws through
the board's own mounting holes. Prints without supports; `mech/front.stl` and
`mech/back.stl` are ready to slice.

## The KiCad project lives in [`pcb/`](pcb/README.md)

The board is now **generated from source rather than drawn**: a 72-pin pinout table and
a set of measured dimensions, from which the footprints, symbols, schematic, board,
copper and fab outputs are all produced by `make rebuild`.

```
cd pcb
make            check what is committed — DRC, ERC, card-edge rules, and the
                comparison against the board that was released
make rebuild    regenerate everything from the two source tables
make fab        gerbers, drill, position file, BOM
```

Regenerating wants the pinned toolchain — `./dc bash -c "cd pcb && make rebuild"` runs
it in a container with KiCad 10 and OpenSCAD, which is what the committed files were
built with. See [`.devcontainer/`](.devcontainer/README.md). Checking works with
whatever KiCad you have.

It is the same board. The hand-drawn files this project shipped with are frozen in
[`pcb/reference/`](pcb/reference/README.md), and every run subtracts the generated
board from them — 144 pads, 72 nets, 14 outline corners, both holes, all three silk
texts, to within 1 µm. Nothing about the physical board, the pinout or the fab package
has changed.

What the rebuild adds: a schematic that passes ERC (the drawn one reports 54 direction
conflicts, because one symbol was used for both ends of a pass-through), card-edge
checks KiCad's DRC does not have (finger pitch, front/back registration, the bevel
zone, the contact wipe path), ENIG and the 1.2 mm stackup declared in the gerber job
file rather than only in this README, and a rebuild that is byte-identical run to run.
