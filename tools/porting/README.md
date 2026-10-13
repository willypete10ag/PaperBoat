# Last Stand native integration check

`last_stand_gdb.py` runs the compiled defensive-badge block in a real Tubba
Blubba demo-battle attack. It checks eleven cases, then lets a controlled hit
apply damage to Mario and verifies both actor HP and `gPlayerData.curHP`.
It does not add a gameplay test mode or write a save.

Prerequisites: a Debug build with symbols, GDB with Python support, a working
display, and the user's generated game archives. For the prepared cloud
environment, source `/workspace/.paperboat-setup/activate.sh`; GDB was installed
from verified Debian packages under that dependency prefix. Start Xvfb on a free
display as described in the environment startup instructions.

Run from the asset directory (adjust paths/display for other environments):

```bash
source /workspace/.paperboat-setup/activate.sh
cd /workspace/PaperBoat/build/ninja-debug
mkdir -p /workspace/.paperboat-setup/last-stand/runtime
export DISPLAY=:93 SDL_AUDIODRIVER=dummy LIBGL_ALWAYS_SOFTWARE=1
export XDG_CACHE_HOME=/workspace/.paperboat-setup/cache
export SHIP_HOME=/workspace/.paperboat-setup/last-stand/runtime
export DEBUGINFOD_URLS=
export LAST_STAND_VARIANT=stacking
export LAST_STAND_SOURCE=/workspace/PaperBoat/src/battle/1A5830.c
export LAST_STAND_RESULT=/workspace/.paperboat-setup/last-stand/stacking.json
export LAST_STAND_BLOCKED=0
timeout 90s gdb -q -batch -x /workspace/PaperBoat/tools/porting/last_stand_gdb.py ./Paperboat
```

Set `LAST_STAND_BLOCKED=1` and choose another result path to verify mitigation
followed by a successful native block. The fixture forces the return value of
`check_block_input`; it does not test controller timing.

For a baseline comparison, preserve the unmodified executable before rebuilding
and extract its matching source with `git show <baseline-sha>:src/battle/1A5830.c`.
Use `LAST_STAND_VARIANT=baseline`, set `LAST_STAND_SOURCE` to that source file,
and pass the preserved executable to GDB. Matching source is required because
breakpoint line numbers are derived from it. The current cloud debugger source
path is `/workspace/PaperBoat/src/battle/1A5830.c`.

A passing run emits `LAST_STAND_RESULT=...`, writes the requested JSON report,
kills its disposable game process, and exits zero. Assertion failures exit
nonzero. A timeout or missing report is not a passing check.

## What this proves

The fixture replays only the defensive-badge block with controlled HP, equipped
badge entries, incoming damage, and target class. The table checks execute native
code and real ability counting, not a duplicate Python implementation. The final
hit resumes the real enemy-damage function through HP application. The class
case is a synthetic branch check, not a separate enemy-targeted battle.

The fixture bypasses normal badge acquisition/equipping and controls damage at
the point after defense. It does not validate duplicate badge UI, BP accounting,
save persistence, the enemy's original attack strength, hardware audio/graphics,
or a full playthrough. All test state remains in the temporary process and
isolated runtime directory.

## Duplicate badge inventory, menu and save check

`duplicate_badges_gdb.py` grants copies through `add_item`, uses the real badge
menu input handler, and checks ownership/BP limits, independent All/Active row
toggles, removal, pagination, sparse arrays, capacity and existing distinct-ID
stacks. It saves three owned and two equipped Last Stand copies through the native
JSON save writer, clears memory, and loads them through `fio_load_game`.

Use the same display/audio/debugger prerequisites above. The fixture intentionally
requires this exact disposable runtime path and refuses to overwrite an existing
`saves/file3.json`. Preserve earlier fixture results before explicitly clearing
that generated test file for another write run; do not point it at user saves.

```bash
cd /workspace/PaperBoat/build/ninja-debug
export SHIP_HOME=/workspace/.paperboat-setup/duplicate-badges/runtime
mkdir -p "$SHIP_HOME"
export DUPLICATE_BADGES_LOAD_ONLY=0
export DUPLICATE_BADGES_RESULT=/workspace/.paperboat-setup/duplicate-badges/result.json
timeout 90s gdb -q -batch -x /workspace/PaperBoat/tools/porting/duplicate_badges_gdb.py ./Paperboat

export DUPLICATE_BADGES_LOAD_ONLY=1
export DUPLICATE_BADGES_RESULT=/workspace/.paperboat-setup/duplicate-badges/fresh-load-battle.json
timeout 90s gdb -q -batch -x /workspace/PaperBoat/tools/porting/duplicate_badges_gdb.py ./Paperboat
```

The first process checks 35 cases. The second checks eight cases: it loads the
saved copies in a fresh game process, reconstructs the copy rows, equips the
remaining owned copy, and then enters the Tubba Blubba demo battle. During the
attack it reloads the saved pair through `fio_load_game`, controls HP and incoming
attack damage, and verifies the saved copies reduce a six-damage hit to two.
That battle check does not directly write equipped badge entries.

The native save schema is unchanged. Identical copies are interchangeable across
reloads: the menu reconstructs the first N copies as equipped. Within one open
menu, slot mapping keeps the specific selected rows independent across tab
switches. Duplicate equipping is currently enabled only for Last Stand; other
identical IDs retain their existing restriction. This does not add another shop
stock or map reward for Last Stand, or claim other TTYD64 badge effects are ported.
