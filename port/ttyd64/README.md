Pity Flower, Jumpman, Hammerman and FP Drain icons/message wording are from eldexterr/ttyd64 at
`b8d2058ea057b2dfc168f2d909a2a2ea0927ce17`:
`image/assets/item/new/badge/{pityflower,jumpman,hammerman,fpdrain}.png` and patched string sections
23/25/26.
These PNGs are published source artwork, not extracted ROM data.

`tools/porting/build_badge_assets.py` converts these indexed PNGs to native CI4
textures and the plain English strings to PM64 message bytes during the archive
build. Generated resources live only in the build staging directory. The disabled
palette is derived as grayscale; the enabled artwork is preserved.

The FP Drain end-turn label is the published `res/misc/fp_drain.png` from the
same revision, copied as `fp_drain_label.png`. It is a 40x16 indexed Adam7 PNG;
the converter decodes its interlacing without altering the artwork. Native
CI4/palette resources use the existing UI HUD path and are generated only in
build staging.

Courage Shell, Power Punch, Mini Mr. Mini and Mr. Softener artwork comes from
`image/assets/item/new/item/{courageshell,powerpunch,minimrmini,mrsoftener}.png`
at the same reference revision; names/descriptions from string sections23/26.
These are published source assets. The same converter generates native item
textures/palettes and messages; no ROM-derived resource is committed.

Slow Shroom, Gradual Syrup, Couple's Cake and Meteor Meal use the same source
revision's published item PNGs `{slowshroom,gradualsyrup,couplescake,meteormeal}`
and patched 23/26 strings. Only their guarded battle consumers are ported here;
world use, recipes and acquisition remain unfinished. No ROM-derived data.
