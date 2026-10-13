# Native TTYD64 badge integration checks

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
identical IDs retain their existing restriction, except for the separately ported
Pity Flower below. This does not add another shop
stock or map reward for Last Stand, or claim other TTYD64 badge effects are ported.

## Pity Flower

The native badge uses item `0x16D`, move `0xB9`, ability `0x38` and message
section `0x2F`. These are appended native IDs, not Star Rod indices. Its cost
is 3 BP per copy. The checked-in C item/move tables are the native build inputs;
the old YAML/Python decomp generators do not contain this addition.

Python 3 is now required by CMake to convert the published indexed PNG and plain
English text under `port/ttyd64/` into resources in `paperboat.o2r`. The converter
uses only the standard library; no new ROM extraction is required. Existing
vanilla IDs and save fields are unchanged. Old builds cannot use this new ID.

`pity_flower_gdb.py` checks resource loading, duplicate acquisition/equipping,
3-BP copy costs, individual menu-row input, native JSON save/load, and the compiled
effect in a real Tubba Blubba demo attack. The writer refuses an existing slot 3
save in this exact disposable directory; preserve previous fixture saves before
clearing only those generated test files for a repeated writer run.

```bash
source /workspace/.paperboat-setup/activate.sh
cd /workspace/PaperBoat/build/ninja-debug
export DISPLAY=:95 SDL_AUDIODRIVER=dummy LIBGL_ALWAYS_SOFTWARE=1
export XDG_CACHE_HOME=/workspace/.paperboat-setup/cache DEBUGINFOD_URLS=
export SHIP_HOME=/workspace/.paperboat-setup/pity-flower/runtime
mkdir -p "$SHIP_HOME"
export PITY_FLOWER_LOAD_ONLY=0
export PITY_FLOWER_BLOCKED=0
export PITY_FLOWER_RESULT=/workspace/.paperboat-setup/pity-flower/writer.json
timeout 90s gdb -q -batch -x /workspace/PaperBoat/tools/porting/pity_flower_gdb.py ./Paperboat

export PITY_FLOWER_LOAD_ONLY=1
export PITY_FLOWER_RESULT=/workspace/.paperboat-setup/pity-flower/fresh-load.json
timeout 90s gdb -q -batch -x /workspace/PaperBoat/tools/porting/pity_flower_gdb.py ./Paperboat
```

The writer passes 38 checks and the fresh reader passes 28. For the blocked
variant, keep `PITY_FLOWER_LOAD_ONLY=1`, set `PITY_FLOWER_BLOCKED=1` and choose a
separate result path. It passes 29 checks and forces `check_block_input` to return
success; this validates the native blocked path, not controller timing.

Start Xvfb first as described above. The attack loads two equipped copies through
`fio_load_game`, applies a controlled six-damage hit from HP 10, then runs the
native RNG with seed 3 (rolls 9 and 91). It restores one FP and leaves HP 4.
Further cases replay only the compiled popup block, forcing RNG returns to check
the 32/33 boundary, independent per-copy rolls, FP caps, high-FP signed overflow,
and upstream exclusions. These are controlled fixtures, not a playthrough or a
probability-distribution test. `rand_int(100) < 33` is preserved exactly; native
`rand_int(100)` is inclusive and biased, so this is not exactly 33%.

Upstream hooks the primary damage popup: zero damage, suppressed popups, multiple
popups/SMASH and non-player targets bypass it. A lethal hit still reaches it.
Positive blocked damage retains that trigger. The native helper uses the existing
flower recovery effect and recovery sound; software rendering/dummy audio do not
verify physical audio output. The initial mechanic commit added no rewards or
shop stock. The acquisition follow-up below adds two experimental field pickups.

Assertions exit nonzero; a timeout, missing report or interrupted run does not
pass. Reports contain numeric results only; fixture saves and screenshots stay
outside version control.

## World acquisition and visual checks

Two one-time Pity Flower pickups appear in Goomba Village, in front of the inn
and southwest of its save block, after meeting the innkeeper. Walk into them and
confirm the ordinary badge popup. Each costs 3 BP to equip; both need 6 BP.
This is an experimental native-port acquisition path, separate from TTYD64's
original Pit floor 40 reward. Vanilla rewards and shop stock are preserved.
Reserved game bits `0x7FE`/`0x7FF` record the copies independently without a save
schema change. A full badge inventory leaves field badges unclaimed until a
slot is available, before touch can consume their pickup flags.

`world_badges_gdb.py` enters the world through native title cleanup, initialized
file-select and the file-load transition. It creates a disposable NoIntro-style
Goomba Village save, tests native map spawning and actual world pickup updates,
then saves/reloads the acquired pair. The automated receipt uses the existing
AUTO_COLLECT flag and A confirmation; independent keyboard-only pickup was also
observed visually. No `add_item` call grants Pity Flower in this fixture.

```bash
# Use the same display/audio/debugger settings as the Pity Flower fixture.
export SHIP_HOME=/workspace/.paperboat-setup/pity-flower/acquisition-runtime
mkdir -p "$SHIP_HOME"
export WORLD_BADGES_VISUAL=0 WORLD_BADGES_LOAD_ONLY=0
export WORLD_BADGES_RESULT=/workspace/.paperboat-setup/pity-flower/acquisition.json
timeout 120s gdb -q -batch -x /workspace/PaperBoat/tools/porting/world_badges_gdb.py ./Paperboat

export WORLD_BADGES_LOAD_ONLY=1
export WORLD_BADGES_RESULT=/workspace/.paperboat-setup/pity-flower/acquisition-fresh.json
timeout 90s gdb -q -batch -x /workspace/PaperBoat/tools/porting/world_badges_gdb.py ./Paperboat
```

The writer passes 16 checks; the fresh reader passes four. As with the other
writers, it refuses an existing fixture slot 3 save. Preserve prior generated
fixture saves before clearing those files for a repeat. Never use user saves.

For a fresh visual session, use `SHIP_HOME` ending in `world-visual-runtime`, set
`WORLD_BADGES_VISUAL=1`, `WORLD_BADGES_LOAD_ONLY=0` and `WORLD_BADGES_PID` to a
local PID-file path. The fixture leaves the native world running with unclaimed
pickups. Use ordinary input (W/A/S/D stick, X A, C B, Space Start), allow pause
animations to finish before choosing tabs, and stop only the recorded process.
Capture its window rather than unrelated windows on the same display.

The original visual fixture skipped title/file-menu cleanup, retaining curtains
and suppressing the description window. The native transition fixture resolves
that limitation: Pity Flower's name, icon, description, pickup popup and normal
pause-menu copy toggles were all visually verified. This does not establish a
complete campaign playthrough or migrate TTYD64's Pit maps.
