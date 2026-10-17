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
