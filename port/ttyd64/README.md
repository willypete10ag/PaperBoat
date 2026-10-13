Pity Flower icon and message wording are from eldexterr/ttyd64 at
`b8d2058ea057b2dfc168f2d909a2a2ea0927ce17`:
`image/assets/item/new/badge/pityflower.png` and strings/patch sections 23/25/26.
The PNG is published source artwork, not extracted ROM data.

`tools/porting/build_badge_assets.py` converts this indexed PNG to native CI4
textures and the plain English strings to PM64 message bytes during the archive
build. Generated resources live only in the build staging directory. The disabled
palette is derived as grayscale; the enabled artwork is preserved.
