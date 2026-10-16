# Native TTYD64 integration checks

Run capture/controller fixtures serially on one display; parallel runtime
fixtures need separate displays to preserve window focus.

## Goombario subsystem batch

Branch `port/ttyd64-goombario-playable-slice` groups pause Party HP,
pause/world ownership, battle swap HP, world shroom recipients and ordinary
contact/flee/menu recovery. The shared `partner_playable_slice_gdb.py` driver
reuses one native lifecycle/input/capture implementation. Select a targeted
phase with `PARTNER_SLICE_PHASES=pause`, `world-items`, `battle` or `team`;
default remains the original three UI/encounter phases. `battle,team` shares
the full lifecycle for affected battle regression and new team acceptance. Recruitment, inventory, ranks/wounds and map/progression setup are
controlled. Battle contact, swap menus and flee outcome use actual keyboard
input. The guarded flag remains off in normal play.

The [isolated developer playtest launcher](GOOMBARIO_PLAYTEST.md) prepares a fresh
private session and hands the native game to the tester after detaching GDB.
It requires this prepared Linux environment and a viewable display; it is not a
packaged release or desktop stream. Its `--verify` mode checks startup/input and
closes. The guarded team phase implements basic Goomba front/back targeting,
explicit Z position swaps, front-first rounds, dead-target fallback and no-item
death/Mario-front movement. Other partners/enemy AI remain pending. The phase
observes native AI rolls/hits/death/Life Shroom with controlled initial wounds
and inventory. It caught and fixes a zero-HP fresh-round menu/transfer loop.
Shared captures now wait for animated HP to settle before final status frames.

World source permits healing zero HP; battle food does not. Private script
LVarE carries the recipient and is explicitly initialized for Mario. Native
inventory-slot ownership and exactly-once consumption remain intact. Active
Goombario effects follow the NPC; inactive-recipient effects use Mario. Full
source choreography/heart artwork remains pending. Battle ranks are hidden in
the guarded width181 list; native/off ranks and typed rank data are retained.

Commands for the strict acceptance runtime, with activation, owned display,
audio/cache prerequisites and native build-directory cwd:

```bash
export SHIP_HOME=/workspace/.paperboat-setup/partner-playable-slice/runtime
mkdir -p "$SHIP_HOME/saves"
cp -n /workspace/.paperboat-setup/fp-drain/runtime/saves/file3.json "$SHIP_HOME/saves/file3.json"
cp -n /workspace/.paperboat-setup/partner-combat/runtime/paperboat.cfg.json "$SHIP_HOME/paperboat.cfg.json"
export PARTNER_SLICE_RESULT=/workspace/.paperboat-setup/partner-playable-slice/combined.json
timeout 900s gdb -q -batch -x /workspace/PaperBoat/tools/porting/partner_playable_slice_gdb.py ./Paperboat
```

## Guarded Goombario world swap list

`partner_world_swap_gdb.py` translates the world list geometry/HP consumer in
active `PartnersHP.patch` (window hook DE428, scissor 8D020, row HP 8D284 and
rank/arrow placement). Native `PopupMenu.userIndex` identifies Goombario;
`value` remains the native rank. Only his row receives HP, under the existing
default-off flag. Battle/upgrade/pause lists and other partner HP rows are
separate migrations. No new save fields, HUD handles, settings or assets.

```bash
source /workspace/.paperboat-setup/activate.sh
cd /workspace/PaperBoat/build/ninja-debug
export DISPLAY=:97 SDL_AUDIODRIVER=dummy LIBGL_ALWAYS_SOFTWARE=1
export XDG_CACHE_HOME=/workspace/.paperboat-setup/cache DEBUGINFOD_URLS=
export SHIP_HOME=/workspace/.paperboat-setup/partner-world-swap/runtime
mkdir -p "$SHIP_HOME/saves"
cp -n /workspace/.paperboat-setup/fp-drain/runtime/saves/file3.json "$SHIP_HOME/saves/file3.json"
cp -n /workspace/.paperboat-setup/partner-combat/runtime/paperboat.cfg.json "$SHIP_HOME/paperboat.cfg.json"
export WORLD_SWAP_RESULT=/workspace/.paperboat-setup/partner-world-swap/acceptance.json
timeout 300s gdb -q -batch -x /workspace/PaperBoat/tools/porting/partner_world_swap_gdb.py ./Paperboat
```

The strict disposable save copy is checked and never written. Recruitment,
ranks and wounds are setup; C-right (Right arrow), stick (W/S), A (X), B (C)
and C-left (Left arrow) drive the native world menus and swaps. Input holds
span native UI passes to let SDL poll the events. Run alone on its display.
Inspect wounded/zero/ultra, eight-partner top/bottom, inventory and off-state
captures independently. All eight list identities are exercised, but only
Goombario HP is claimed. Software rendering/dummy audio retain their limits.
Captures run while the game thread draws freely, before an ignored native
popup breakpoint returns control; timing is asserted. Pausing inside graphics
construction can otherwise leave partial/interpolated frames on screen.
Numeric telemetry records rank data/alpha, scroll offset and blinking arrows.
Partner-rank handles are read only while the partner popup owns them. Guarded
rank icons initialize their own HUD state instead of depending on HP text.

Acceptance: **22 world-menu checks**, **44 battle-healing regressions**,
**67 foundation/save/layout checks**, and **431 utility tests** pass. The
shared coordination handoff records rendered evidence, diagnostic corrections
and the remaining pause/battle-list/recipient work.

## Native battle return and partner HP

`partner_battle_return_gdb.py` uses a regular Goomba Road encounter, preserving
native world backups, end-battle cleanup, NPC/script restoration and input
release. It does not use `load_demo_battle`, which clears world heaps and cannot
prove a normal return path. Existing enemy AI ownership supplies native
`start_battle`; HP wounds and the fled outcome/end-battle state are controlled.
Victory/run-away input, escape timing and choreography are not claimed.

```bash
source /workspace/.paperboat-setup/activate.sh
cd /workspace/PaperBoat/build/ninja-debug
export DISPLAY=:97 SDL_AUDIODRIVER=dummy LIBGL_ALWAYS_SOFTWARE=1
export XDG_CACHE_HOME=/workspace/.paperboat-setup/cache DEBUGINFOD_URLS=
export SHIP_HOME=/workspace/.paperboat-setup/partner-battle-return/runtime
mkdir -p "$SHIP_HOME/saves"
cp -n /workspace/.paperboat-setup/fp-drain/runtime/saves/file3.json "$SHIP_HOME/saves/file3.json"
cp -n /workspace/.paperboat-setup/partner-combat/runtime/paperboat.cfg.json "$SHIP_HOME/paperboat.cfg.json"
export BATTLE_RETURN_BASELINE=0
export BATTLE_RETURN_RESULT=/workspace/.paperboat-setup/partner-battle-return/acceptance.json
timeout 300s gdb -q -batch -x /workspace/PaperBoat/tools/porting/partner_battle_return_gdb.py ./Paperboat
```

The exact disposable save copy is checked; wounded/zero FIO checks restore bytes
with finally. Debug cant-touch suppresses unrelated automatic encounters during
setup, while native StartBattle runs the selected existing encounter. The guard
is enabled only in this fixture; the final full entry/return runs with it off.
Native HUD passes are used for independently inspected local captures. The
fixture waits for full extension (the default -100 → +18 takes twelve +10
updates), submits the completed frame, verifies focus and records HUD state.

Final acceptance passes **32 checks** across three guarded and one prototype-off
native entries/returns. Wounded/zero HP persist through FIO and re-entry; flag-off
entry retains native 99-HP actors and turn availability despite zero passive HP.
25 world ownership, 67 foundation and all 431 utility regressions pass. Numeric
results and limits: coordination `docs/handoffs/2026-10-14-goombario-battle-return.md`
and `results/partner-battle-return/`.

On the matching preceding world-HUD executable
`77f7e17f8deea59a167dc3e0b59645ef66d90a31`, `BATTLE_RETURN_BASELINE=1` passed eight
observations and reproduced persistent HP 3/world control returning with the
partner row missing. The NPC pool is restored rather than recreated, so resume
must rebind world HP. Do not use baseline mode on the corrected executable.

## Guarded Goombario world HP

`partner_world_hud_gdb.py` extends the existing battle HP row into the world for
Goombario only, under the same default-off development flag. Active source:
`NewStatsMenu.patch` hook 81C9C ($PartnerHP_AnimationTimer) and
`PartnersHP.patch` hook 83DF0 (snap displayed HP on partner creation). The full
source stats layout and other partners' UI remain later work.

```bash
source /workspace/.paperboat-setup/activate.sh
cd /workspace/PaperBoat/build/ninja-debug
export DISPLAY=:97 SDL_AUDIODRIVER=dummy LIBGL_ALWAYS_SOFTWARE=1
export XDG_CACHE_HOME=/workspace/.paperboat-setup/cache DEBUGINFOD_URLS=
export SHIP_HOME=/workspace/.paperboat-setup/partner-world-hud/runtime
mkdir -p "$SHIP_HOME/saves"
cp -n /workspace/.paperboat-setup/fp-drain/runtime/saves/file3.json "$SHIP_HOME/saves/file3.json"
cp -n /workspace/.paperboat-setup/partner-combat/runtime/paperboat.cfg.json "$SHIP_HOME/paperboat.cfg.json"
export WORLD_HUD_RESULT=/workspace/.paperboat-setup/partner-world-hud/acceptance.json
timeout 300s gdb -q -batch -x /workspace/PaperBoat/tools/porting/partner_world_hud_gdb.py ./Paperboat
```

The strict disposable copy is checked and restored after FIO. Native world
switch APIs choose Goombario/Kooper/none; full stock animation scripts run.
Map-change APIs exercise actual teardown/reset/recreation. API setup supplies
wounds/ranks and full-rest; Peach/demo/context checks are synthetic guard
branches. Rendering stays free in non-stop GDB; independently inspect captures.
This is not partner-popup input, a normal upgrade or natural battle-exit test.
World ownership is invalidated by NPC clear/reset/free and recreated at native
spawn. The row follows current Goombario, animates recovery, supports zero HP,
and remains hidden when put away, another partner is current, the context is
ineligible or the flag is off. No new save/layout fields or HUD assets.

Final world acceptance passes **25 checks**, with 51 lethal-combat, 67 foundation
and all 431 utility checks passing. Cadence is measured in native UI passes,
which may be fewer than simulation steps when GDB causes frame skipping.
Fixture recruitment grants occur after end-file-select restores PlayerData.
Evidence: coordination `docs/handoffs/2026-10-14-goombario-world-hp.md` and
`results/partner-world-hud/`.

## World full recovery and Heart Blocks

`partner_world_heal_gdb.py` checks the passive partner HP model through native
world recovery while combat activation stays **off**. Active source is
`PartnersHP.patch` FullyRestoreHPandFP hook F6880 / $Function_HealPartners and
Heart Block hook 106848. At least one unlocked combat partner enables recovery
of all eight compatible health records (including dead/locked ones), without
recruiting partners. Heart Blocks also refill source Star Power. The full-rest
HP/FP API itself leaves SP to the separate existing FullyRestoreSP call.

```bash
source /workspace/.paperboat-setup/activate.sh
cd /workspace/PaperBoat/build/ninja-debug
export DISPLAY=:97 SDL_AUDIODRIVER=dummy LIBGL_ALWAYS_SOFTWARE=1
export XDG_CACHE_HOME=/workspace/.paperboat-setup/cache DEBUGINFOD_URLS=
export SHIP_HOME=/workspace/.paperboat-setup/partner-world-heal/runtime
mkdir -p "$SHIP_HOME/saves"
cp -n /workspace/.paperboat-setup/fp-drain/runtime/saves/file3.json "$SHIP_HOME/saves/file3.json"
cp -n /workspace/.paperboat-setup/partner-combat/runtime/paperboat.cfg.json "$SHIP_HOME/paperboat.cfg.json"
export WORLD_HEAL_BASELINE=0
export WORLD_HEAL_RESULT=/workspace/.paperboat-setup/partner-world-heal/acceptance.json
timeout 300s gdb -q -batch -x /workspace/PaperBoat/tools/porting/partner_world_heal_gdb.py ./Paperboat
```

The strict runtime must contain exactly the disposable FP Drain writer bytes;
FIO checks restore them. Native title/file-select enters Mario's house, skipping
an already-seen Luigi scene. The fixture grants wounds/ranks/unlocks and starts
the stock bed entry script; native keyboard input chooses the rest dialogue.
Native world switching selects Goombario, map-bound door triggers run the stock
room entry/exit scripts, and a fixture-spawned Heart Block is hit by a keyboard
jump in the same world. Rendering stays
free in non-stop GDB; inspect local captures independently. No recursive event
updates. Normal completion kills only the owned game process.

Final acceptance passes **47 checks**: eight partners at all three ranks,
unlock/no-unlock gates, dead HP recovery, full native bed/door lifecycle, real
Heart Block recovery and native FIO. The block accepts up to three ordinary
keyboard jump attempts; the final run needed two under non-stop GDB. This is
not a controller timing test; no damage/healing/collision result is injected.
67 foundation and all 431 utility regressions also pass. Shared evidence:
coordination `docs/handoffs/2026-10-14-world-full-heal.md` and
`results/partner-world-heal/`.

`WORLD_HEAL_BASELINE=1` is only for the matching preceding healing executable
`9db3e1d22a9cbacc2c5cebcad4dc49ac0aab192c`: five observations reproduce full-rest
leaving Goombario at 3 HP while Mario HP/FP restore. Do not run baseline mode on
the updated executable. Native/source rest-need checks select dialogue rather
than rejecting sleep; those checks are unchanged. General world healing-item
recipient menus, dropped hearts, world partner HP UI and all-partner combat
remain separate consumers.

## Goombario healing and battle HP row (guarded)

`partner_healing_gdb.py` exercises Mario's four shroom-family items and the first
battle HP readout for bound Goombario. Normal activation stays **off**. The
fixture's committed item use follows real keyboard input through the native
command wheel, item popup, target cancellation/reselection and item script.
Additional cap/guard/persistence/display checks use native APIs between ticks.
Final acceptance passes **44 checks**: Mushroom 3 → 8, one-of-two consumption,
Mario turn spent and partner menu reached, used-turn preservation, four native
target lists, dead/off exclusion, cap bounds, native FIO and display cadence.
Numeric evidence and exact scope: coordination repository
`docs/handoffs/2026-10-14-goombario-healing.md` and `results/partner-healing/`.

Prepare this exact disposable runtime from the established FP Drain fixture;
never copy user saves. The fixture requires slot3 bytes to match that writer
and restores them after its FIO save/load round trip. The copied test controller
profile uses Ship's **LUS** scancodes: A is X, B is C, stick is W/A/S/D. They are
not raw SDL scancode numbers.

```bash
source /workspace/.paperboat-setup/activate.sh
cd /workspace/PaperBoat/build/ninja-debug
export DISPLAY=:97 SDL_AUDIODRIVER=dummy LIBGL_ALWAYS_SOFTWARE=1
export XDG_CACHE_HOME=/workspace/.paperboat-setup/cache DEBUGINFOD_URLS=
export SHIP_HOME=/workspace/.paperboat-setup/partner-healing/runtime
mkdir -p "$SHIP_HOME/saves"
cp -n /workspace/.paperboat-setup/fp-drain/runtime/saves/file3.json "$SHIP_HOME/saves/file3.json"
cp -n /workspace/.paperboat-setup/partner-combat/runtime/paperboat.cfg.json "$SHIP_HOME/paperboat.cfg.json"
export PARTNER_HEALING_RESULT=/workspace/.paperboat-setup/partner-healing/acceptance.json
timeout 300s gdb -q -batch -x /workspace/PaperBoat/tools/porting/partner_healing_gdb.py ./Paperboat
```

Use a running, free Xvfb display. Non-stop mode leaves rendering threads free;
inspect the local PNGs independently. Normal completion kills the owned game.
The fixture converts native Tubba demo formation 4 into a controlled interactive
battle: clears playback flags and its persistent WaitForState gate, balances
its one status-bar-disable count, and restores viewport/curtain presentation.
It does not change the production demo or claim ordinary enemy-AI targeting.
No recursive event updates or direct popup-selection writes advance item use.

Active source: `PartnersHP.patch` create_target_list hook 8026240C rejects zero
HP; `PartnersItems.patch` $Heal_PlayerTeam/$heal_actor cap HP;
`battle/item/patch/Item_Shroom.bpat` selects the healed recipient;
`NewStatsMenu.patch` $PartnerHP_AnimationTimer changes displayed HP by one every
four updates. Native item flight/shimmers are reused for this first consumer;
full source item choreography and the complete stats-menu layout remain later.

Mushroom, Super Shroom, Ultra Shroom and Dried Shroom are admitted only for living,
bound Goombario under the guard. Existing Mario item potency and consumption
stay native. Ordinary food does not revive dead partners or return used turns.
No partner item command, other foods/FP items, world healing/UI or other partner
combat is enabled by this milestone. The readout uses a native portrait and
current/max numbers below the native HUD, separate unsaved display state and
existing scaling; the original save/status-bar layouts stay unchanged.


## Goombario combat (guarded acceptance)

`goombario_combat_gdb.py` validates the bound Goombario prototype in a disposable
native Tubba Blubba battle. Keep `gTtyd64PartnerHPPrototypeEnabled` **off in normal
play**. Other partners' combat, healing/UI, source positioning, Refund and
simultaneous Mario/partner revival remain outside this milestone.

Start from the existing FP Drain writer fixture, copied to this exact runtime.
The combat fixture checks the copy's bytes against that known disposable writer,
loads before Goombario creation and restores slot3 bytes after save/load checks.
Never substitute a user save. Retain the activation/display/audio/cache setup
below; use a free Xvfb display (this acceptance used `:96`).

```bash
source /workspace/.paperboat-setup/activate.sh
cd /workspace/PaperBoat/build/ninja-debug
export DISPLAY=:96 SDL_AUDIODRIVER=dummy LIBGL_ALWAYS_SOFTWARE=1
export XDG_CACHE_HOME=/workspace/.paperboat-setup/cache DEBUGINFOD_URLS=
export SHIP_HOME=/workspace/.paperboat-setup/partner-combat/runtime
mkdir -p "$SHIP_HOME/saves"
cp -n /workspace/.paperboat-setup/fp-drain/runtime/saves/file3.json "$SHIP_HOME/saves/file3.json"
export GOOMBARIO_RESULT=/workspace/.paperboat-setup/partner-combat/acceptance.json
export GOOMBARIO_VISUAL=0 GOOMBARIO_LETHAL=0
timeout 300s gdb -q -batch -x /workspace/PaperBoat/tools/porting/goombario_combat_gdb.py ./Paperboat

export GOOMBARIO_LETHAL=1 GOOMBARIO_VISUAL=1
export GOOMBARIO_RESULT=/workspace/.paperboat-setup/partner-combat/lethal.json
timeout 300s gdb -q -batch -x /workspace/PaperBoat/tools/porting/goombario_combat_gdb.py ./Paperboat
```

Run these sequentially; they share only this fixture's slot3. Visual mode uses
non-stop GDB, pauses only the game-tick thread and captures local PNGs while
rendering continues. Inspect them; a capture being written is not visual proof.
The fixture kills its own process on completion, including visual mode.

The default case redirects a real enemy script's test/damage target to Goombario:
3 damage changes actor/model HP 10 → 7. Lethal mode uses 12 damage, observes
native defeat completion and Mario's next command menu with Goombario dead.
Further checks use compiled damage/script/state APIs between engine ticks;
`continue` alone advances event scripts. Guard forces the input function's
success, testing the minus-one branch rather than controller timing. Native
full put-away/bring-out scripts execute for dead swap-away/back; revived command
routing is exercised through native Prepare Menu with controlled state/flags.
These are not a full controller-driven encounter or broad enemy-AI targeting
acceptance. Model/API fixture resets do not claim general healing presentation.

Final runs pass **49 nonlethal / 51 lethal checks**.
Coverage includes zero/immune/suppressed enemy and item damage, shock backfire
and no-contact suppression, negative contact clamps, no KO turns, script HP APIs,
lethal collapse/status/charge cleanup, active death/revival event protection,
zero-HP poison/shrink turn rejection, repeat-hit rejection, native dead save/load,
full same-battle dead swap-back, exact one-of-two Life Shroom consumption,
ten-HP recovery at ranks 0/1, pose/idle/turn restoration, shroud/item/energy
cleanup, native partner menu entry and prototype-off sentinel/KO behavior.

The expanded fixture caught a real reveal lifetime bug: the death parent killed
its reveal child with shroud tint 48. Revival now tracks and waits for the
20-frame reveal; accepted completion requires tint zero and no leaked item or
energy effect. The contact KO bypass and secondary dispatcher's death tracking
are also fixed. Numeric reports and scope are in the coordination repository's
`docs/handoffs/2026-10-14-goombario-combat.md` and `results/goombario-combat/`.

## Partner HP foundation (guarded prototype)

`partner_hp_gdb.py` validates passive native health persistence and an explicitly
enabled actor-binding prototype. **Normal gameplay still uses native KO turns;
guarded Goombario combat plus the bounded shroom/battle-HP consumer above are
validated; other partner combat and broader healing/UI remain unported.**
`gTtyd64PartnerHPPrototypeEnabled` is false at startup/new-game, never saved and
has no product setting. Do not enable it in normal play before those consumers
are migrated.

Health lives in `ShipSaveData`, preserving the original eight-byte PartnerData,
0x428-byte PlayerData and 0x1380-byte vanilla save layout. Optional native JSON
`ship.ttyd64PartnerHP` version 1 stores twelve indexed current/max records. Old
JSON initializes full source rank health; malformed/partial records use safe
defaults and bounded integers. Explicit zero is preserved. Maxima derive from
rank until HP Plus P is translated. Noncombat/no-partner getters return -1.

Use the activation/display/audio/cache prerequisites below and this exact
guarded runtime. Writer refuses existing slot3. Archive only the known fixture
save for an intentional writer rerun; never use real saves.

```bash
source /workspace/.paperboat-setup/activate.sh
cd /workspace/PaperBoat/build/ninja-debug
export DISPLAY=:95 SDL_AUDIODRIVER=dummy LIBGL_ALWAYS_SOFTWARE=1
export XDG_CACHE_HOME=/workspace/.paperboat-setup/cache DEBUGINFOD_URLS=
export SHIP_HOME=/workspace/.paperboat-setup/partner-hp/runtime
mkdir -p "$SHIP_HOME"
export PARTNER_HP_LOAD_ONLY=0
export PARTNER_HP_RESULT=/workspace/.paperboat-setup/partner-hp/writer.json
timeout 180s gdb -q -batch -x /workspace/PaperBoat/tools/porting/partner_hp_gdb.py ./Paperboat

export PARTNER_HP_LOAD_ONLY=1
export PARTNER_HP_RESULT=/workspace/.paperboat-setup/partner-hp/fresh-load.json
timeout 180s gdb -q -batch -x /workspace/PaperBoat/tools/porting/partner_hp_gdb.py ./Paperboat
```

Passed **81 writer / 67 fresh-process checks**: every source rank-table entry,
ID/rank/amount bounds, original layout sizes, new-game defaults, source-style
rank reset, native writer/FIO load, nine legacy/malformed/partial JSON variants,
signed/unsigned integer extremes, explicit zero, unrelated badge/ship/opaque
partner data, and synthetic vanilla-save conversion. JSON variants temporarily
change only this fixture's slot3 and restore exact bytes with `finally`.
Vanilla conversion runs the compiled native converter on a synthetic host-endian
VanillaSaveData; raw flash endianness/file-picker import is not tested here.

The live-battle part loads the saved Bow state before native partner creation.
Default actor HP remains 99 while persistent HP is 4/30. Guard checks exclude
demo/Peach/world contexts. In a controlled battle context, the fixture explicitly
enables and binds the prototype: loaded Bow becomes 4/30; its native health
setter synchronizes 2/30. Another partner's setter cannot change Bow. The actual
change-partner state's LOAD_NEW_PARTNER branch runs native deletion/creation
for Kooper 0/15, Goombario 6/10, and Bow 2/30. This tests spawn and model ownership,
not a full swap animation. Newly created, never-executed init scripts are removed
before the next controlled swap; the paused attack is not resumed recursively.
Deletion clears binding, no-partner creation is safe, and health saves without
a live actor. Source damage/KO/event code remains outside this foundation.

The persistence model owns health. Untranslated direct actor damage/setters do
not write back to it. Rank/recruit resets are hooked into existing native world
paths; their helper behavior is tested, but normal upgrade/recruit animations
are not exercised. HP Plus P, displayed HP, full partner combat and patched
TTYD64 ROM-save import remain separate work. Native old readers can ignore the
optional block but drop it when they save.

## Flower Saver and item-dip FP costs

`flower_saver_gdb.py` checks the existing Mario Flower Saver A/B identities at
4 BP per copy, independent rows, native save/load and shared counted discounts.
Double Dip now costs 4 FP/3 BP and Triple Dip 8 FP/3 BP, matching TTYD64's
`globals/Moves.xml`. The active `Fix_DoubleDip_FlowerSavers.patch` supplies the
item-dip menu minimum: a nonfree move costs at least one FP after discounts,
matching actual native payment. Free ordinary attacks stay free.

Prerequisites and display/audio/cache activation are described below. Run from
`build/ninja-debug` with this exact isolated runtime; writer refuses slot3 if it
exists. Archive the known fixture save before a deliberate writer rerun.

```bash
source /workspace/.paperboat-setup/activate.sh
cd /workspace/PaperBoat/build/ninja-debug
export DISPLAY=:95 SDL_AUDIODRIVER=dummy LIBGL_ALWAYS_SOFTWARE=1
export XDG_CACHE_HOME=/workspace/.paperboat-setup/cache DEBUGINFOD_URLS=
export SHIP_HOME=/workspace/.paperboat-setup/flower-saver/runtime
mkdir -p "$SHIP_HOME"
export FLOWER_SAVER_BASELINE=0 FLOWER_SAVER_LOAD_ONLY=0
export FLOWER_SAVER_RESULT=/workspace/.paperboat-setup/flower-saver/writer.json
timeout 180s gdb -q -batch -x /workspace/PaperBoat/tools/porting/flower_saver_gdb.py ./Paperboat

export FLOWER_SAVER_LOAD_ONLY=1
export FLOWER_SAVER_RESULT=/workspace/.paperboat-setup/flower-saver/fresh-load.json
timeout 180s gdb -q -batch -x /workspace/PaperBoat/tools/porting/flower_saver_gdb.py ./Paperboat
```

Passed **114 writer** and **99 fresh-process** checks. Seven equipment variants
(none, one, pair, mixed A/B, four, nine and Flower Fanatic coexistence) exercise
real item-menu construction, submenu cost/discount data, eligibility just below
and at cost, and actual `deduct_current_move_fp()`. Native Power Jump/Power Smash
menus and payment also agree. The final Double Dip menu/payment loads the saved
pair through FIO, then natively grants/equips the item-dip badges with a test BP
budget: FP 2 → 0. Choosing Items is controlled through the native main-menu
update return, not controller input. This does not play a complete two/three-item
turn or validate partner Flower Saver. Raw equipment in the branch matrix is
controlled state, not normal acquisition or legal loadouts at starting BP.

`FLOWER_SAVER_BASELINE=1`, with load-only zero and a **matching prior FP Drain
executable**, observes pre-change behavior without saving. That preceding build
passed 96 observations and reproduced zero-FP item-dip eligibility despite a
one-FP payment. Do not run baseline mode against the updated executable.

For keyboard pause-menu inspection, copy only the writer's disposable save to
`.paperboat-setup/flower-saver/visual-runtime/saves/file3.json`, preserving an
existing copy. Set `SHIP_HOME` to that strict runtime and run
`flower_saver_visual.gdb`. It performs native title/file-select cleanup, loads
the pair into Goomba Village, records numeric state and a PID, then detaches.
Raise/focus the window belonging to that PID; use Space for pause, A/D for tabs,
X for N64 A and C for B. Capture the full display (`import -window root`), not
only the OpenGL window. Stop only the recorded game PID afterward. Screenshots
and saves stay local. The normal input inspection is separate from menu-choice
control in the cost fixture.

The existing unused X variant remains single-equip. The native ability counter
already counts all same-move variants; the source's explicit Double Dip fix
mentions A/B only. Native Flower Fanatic and unused-X discount behavior are
retained; neither is claimed as newly translated gameplay. Source partner-only
Flower Saver P and the source's removal of Mario discounts from partners are
not yet ported. No new IDs, artwork, rewards or save fields are added. Double
Dip's higher BP cost can make an old native equipped loadout exceed its budget;
remove/re-equip badges under the new cost. Do not regenerate native tables from
the old YAML without preserving all appended TTYD64 entries.

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
`rand_int(100)` spans 0..100; the predicate accepts 0..32. These checks validate
the boundary and controlled seed, rather than measuring a distribution.

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

`pity_flower_animation.gdb` loads the world-acquired pair in a real demo attack
and stops after twelve native flower-animation updates. It asserts HP 4, FP 1,
flower type and popup amount 1, records a numeric report/PID under the local
Pity Flower artifacts directory, then detaches with native game updates slowed
to keep the effect visible for inspection. Set `SHIP_HOME` to
`/workspace/.paperboat-setup/pity-flower/animation-runtime`; copy the generated
`acquisition-runtime/saves/file3.json` into its `saves/` directory first. Do not
use a user save. Run it with the same display/debugger settings:

```bash
timeout 90s gdb -q -batch -x /workspace/PaperBoat/tools/porting/pity_flower_animation.gdb ./Paperboat
```

Native update data showed the floating component rising from Y 0 to about 16.8
over twelve frames at full scale. The rendered green flower and number 1 were
visually confirmed beside the damage popup. This fixture intentionally slows
gameplay after that point; it is not an input-timing or hardware-audio check.
Stop the recorded process when finished.

## Defend Plus

Defend Plus uses its existing native A/X/Y item IDs (`0xFB`, `0x13E`, `0x13F`),
shared move `0x45` and ability `0x1B`. TTYD64's move table charges 5 BP per copy;
the native table now matches that cost. Its defensive damage code already subtracts
the ability count before Last Stand and blocking. The port enables independent
same-ID copies for all three variants using the existing copy-aware menu/save
implementation. Other identical effect IDs remain restricted. Existing IDs,
ownership/save fields, graphics, reward placement and shop prices are unchanged.

`defend_plus_gdb.py` passes 38 writer checks and 15 checks in each fresh-process
variant: unblocked, forced blocked and low incoming damage. It covers variant
identity/counting, same-ID and distinct-ID stacks, 4/5/9/10-BP boundaries, owned
copy limits, native menu input, native JSON save/load, nine compiled defensive
branches and a loaded-copy native HP application. The script supplies inventory
through `add_item`; it does not add normal-game extra-copy rewards.

```bash
export SHIP_HOME=/workspace/.paperboat-setup/defend-plus/runtime
mkdir -p "$SHIP_HOME"
export DEFEND_PLUS_LOAD_ONLY=0 DEFEND_PLUS_BLOCKED=0 DEFEND_PLUS_INPUT=6
export DEFEND_PLUS_RESULT=/workspace/.paperboat-setup/defend-plus/writer.json
timeout 120s gdb -q -batch -x /workspace/PaperBoat/tools/porting/defend_plus_gdb.py ./Paperboat

export DEFEND_PLUS_LOAD_ONLY=1
export DEFEND_PLUS_RESULT=/workspace/.paperboat-setup/defend-plus/fresh-load.json
timeout 90s gdb -q -batch -x /workspace/PaperBoat/tools/porting/defend_plus_gdb.py ./Paperboat
```

Use the same display/audio/debugger prerequisites as above. For blocking, set
`DEFEND_PLUS_BLOCKED=1` with input 6 and a separate result path. For clamping,
set blocked back to 0 and `DEFEND_PLUS_INPUT=1`. The writer refuses an existing
fixture slot 3 save. Two saved copies reduce controlled post-defense damage 6
to 4 (HP 10 → 6), then native blocking reduces it to 3 (HP 10 → 7). A one-damage
input is clamped to zero after mitigation, leaving HP 10. The Last Stand
combination is checked in the compiled branch; non-player class checks are
synthetic. No controller timing or complete playthrough is claimed.

## Jumpman

Jumpman uses appended native item `0x16E`, move `0xBA`, ability `0x39` and message
section `0x2F` indexes 2/3. It costs 2 BP per copy and uses its published source
icon/text. The existing standard-library asset converter now packs both new
badges. Existing IDs and save fields remain stable.

The native battle-start path disables Hammer by clearing `BTL_MENU_ENABLED_SMASH`.
The player attack-badge path adds one power per copy except for
`MOVE_FIRST_STRIKE_HAMMER`, matching active upstream operands. The upstream hook
does not test attack elements: a debugger-forced normal Hammer still receives
the boost, while normal command selection disables Hammer. Scripted command-mask
overrides retain their existing behavior. The paired Hammerman port is described
below; partner badges remain separate migrations. No normal-game Jumpman reward is added in this milestone.

`jumpman_gdb.py` passes 34 writer and 24 fresh-process checks: resource/identity
loading, native duplicate/BP/menu/save handling, seven compiled attack branches,
command-mask initialization, the actual command-wheel consumer and a loaded-copy
enemy HP application. A controlled base-three jump with two saved copies deals
five damage and reduces enemy HP 10 → 5. Hammer first-strike exclusion is checked
in the compiled branch; it is not a separately played first-strike sequence.

```bash
export SHIP_HOME=/workspace/.paperboat-setup/jumpman/runtime
mkdir -p "$SHIP_HOME"
export JUMPMAN_LOAD_ONLY=0
export JUMPMAN_RESULT=/workspace/.paperboat-setup/jumpman/writer.json
timeout 120s gdb -q -batch -x /workspace/PaperBoat/tools/porting/jumpman_gdb.py ./Paperboat

export JUMPMAN_LOAD_ONLY=1
export JUMPMAN_RESULT=/workspace/.paperboat-setup/jumpman/fresh-load.json
timeout 90s gdb -q -batch -x /workspace/PaperBoat/tools/porting/jumpman_gdb.py ./Paperboat
```

Use the same display/debugger settings and exact disposable save safeguards as
the other fixtures. Normal world pause input also visually confirmed the icon,
name, description, 2-BP costs and independent first/third copy highlights. This
visual fixture loaded a prepared save; Jumpman copies were granted for testing.

## Hammerman

Hammerman appends native item `0x16F`, move `0xBB`, ability `0x3A` and message
section `0x2F` indexes 4/5. It uses the published source icon/text and costs 2 BP
per copy. The native start path clears `BTL_MENU_ENABLED_JUMP`; the attack path
adds its copy count except for `MOVE_FIRST_STRIKE_JUMP`. A forced ordinary Jump
still gets the bonus, matching the source hook, while normal Jump selection is
disabled. Equipping both Jumpman and Hammerman disables both commands; both
bonuses add on ordinary forced calculations and each retains its own first-strike
exclusion. Later scripted menu overrides retain native behavior.

`hammerman_gdb.py` passes 45 writer and 35 fresh-process checks covering
resource/identity, copy/BP/menu/save and fresh loading,
eleven compiled attack cases and the actual command-wheel builder. It enters the
native Hammer demo rather than changing a Jump attack into a Hammer calculation.
The final saved-pair hit uses controlled base damage, defense, immunity and enemy
HP for comparison. First strikes are compiled-branch checks, not natural timing
sequences. Paired command-wheel checks reuse the combined mask captured from the
compiled start path in the same initialized battle. Inventory grants are native
fixture grants; no normal Hammerman reward is added.

Use the shared runtime prerequisites above and run from `build/ninja-debug`:

```bash
export SHIP_HOME=/workspace/.paperboat-setup/hammerman/runtime
mkdir -p "$SHIP_HOME"
export HAMMERMAN_LOAD_ONLY=0
export HAMMERMAN_RESULT=/workspace/.paperboat-setup/hammerman/writer.json
timeout 120s gdb -q -batch -x /workspace/PaperBoat/tools/porting/hammerman_gdb.py ./Paperboat

export HAMMERMAN_LOAD_ONLY=1
export HAMMERMAN_RESULT=/workspace/.paperboat-setup/hammerman/fresh-load.json
timeout 120s gdb -q -batch -x /workspace/PaperBoat/tools/porting/hammerman_gdb.py ./Paperboat
```

The exact runtime path is guarded. Writer runs refuse an existing file3 save;
archive/remove only that known disposable fixture file before a deliberate rerun.
Keep normal user saves and other SHIP_HOME paths untouched.

Normal keyboard input in an initialized world/pause menu visually confirmed the
Hammerman icon, name, description and independent two-BP copy toggles, using a
prepared fixture save. Capture the full virtual display if individual OpenGL
window capture returns black. Screenshots and test saves stay local.

## FP Drain

Native item `0x170`, move `0xBC`, ability `0x3B`, message section `0x2F` indexes
6/7; cost 3 BP. Published source icon/text and the 40x16 Adam7 recovery label
(`ttyd64/res/misc/fp_drain.png`) are packed into the existing native archive.
`check_badge_assets.py` compares all five source PNG conversions against
ImageMagick's independent RGBA decoding; no ROM data is involved.

The active source hook applies one flat damage penalty regardless of copies,
counts eligible player damage calculations up to five and includes first strikes.
Counts accrue before final defense/clamping: reaching this hook can earn FP even
when final damage is zero. Early misses/contact hazards that return before the
hook do not reach it. At eligible turn end, positive hit count restores
`hits + copies - 1` FP. No hits means no FP; item-dip, Stone and Outta Sight gates
retain the pending count until eligible recovery. Battle initialization clears
the battle-local counter before first strikes. The counter is not saved.

Native `LVarD` carries this recovery into the existing Happy phase alongside
HP Drain (`A`), Happy Heart (`B`) and Happy Flower (`C`). FP feedback sums `C+D`;
normal one-point increments cap actual FP safely. The distinct FP Drain label is
created/freed in the existing HUD path; all three labels are separated by nine
pixels. Unported partner/status patches are not prerequisites for this badge.

`fp_drain_gdb.py` passed 55 writer, 45 fresh-process, 47 coexistence, 45 FP-cap and
45 zero-damage checks. The saved pair gives controlled damage 3 → 2, enemy HP
10 → 8 and FP 2 → 4 through the actual native turn-end state machine and script.
Base 1 gives zero damage/unchanged enemy HP but still restores FP 2 → 4. FP 98
caps at 99. Coexistence uses additional native test grants/equipping, with 20 test
BP; it deals 1 damage, restores FP 2 → 5 and HP 5 → 7. Compiled branch replay
covers the flat penalty, first-strike flag and seven hit counts ending at five;
it does not play a full first-strike or multi-hit controller sequence.

Use the shared activation/display/audio/cache prerequisites and run from
`build/ninja-debug`. Writer refuses an existing slot3 in its exact runtime.
Only archive/remove that known disposable fixture save for deliberate reruns.

```bash
export SHIP_HOME=/workspace/.paperboat-setup/fp-drain/runtime
mkdir -p "$SHIP_HOME"
export FP_DRAIN_LOAD_ONLY=0 FP_DRAIN_COEXIST=0 FP_DRAIN_FP_START=2 FP_DRAIN_BASE_DAMAGE=3
export FP_DRAIN_RESULT=/workspace/.paperboat-setup/fp-drain/writer.json
timeout 180s gdb -q -batch -x /workspace/PaperBoat/tools/porting/fp_drain_gdb.py ./Paperboat

export FP_DRAIN_LOAD_ONLY=1
export FP_DRAIN_RESULT=/workspace/.paperboat-setup/fp-drain/fresh-load.json
timeout 180s gdb -q -batch -x /workspace/PaperBoat/tools/porting/fp_drain_gdb.py ./Paperboat
```

For each following variant, copy only the writer's disposable `saves/file3.json`
into its distinct runtime first, preserving any existing variant saves. Reset
all other mode variables to their defaults above before selecting a variant.

| Variant | Exact SHIP_HOME suffix under `.paperboat-setup/fp-drain/` | Mode setting |
| --- | --- | --- |
| HP Drain/Happy Heart/Happy Flower coexistence | `coexist-runtime` | `FP_DRAIN_COEXIST=1` |
| Near-full FP | `cap-runtime` | `FP_DRAIN_FP_START=98` |
| Zero final damage | `zero-runtime` | `FP_DRAIN_BASE_DAMAGE=1` |

Keep `FP_DRAIN_LOAD_ONLY=1` and use a separate `FP_DRAIN_RESULT` for each run.
The exact runtime and valid mode combinations are guarded. Debugger scheduling
is locked only for short compiled-block replay; native function calls and whole
attack/recovery progression let rendering/audio threads run. The fixture clears
the demo playback exit flag so the real native player-turn state machine can
reach recovery.

Normal keyboard input visually confirmed the badge's name, artwork, description
and independent 3-BP toggles using a prepared test save. No normal FP Drain reward
is added. Native inventory grants are development fixtures.

For feedback inspection, copy the writer save into
`/workspace/.paperboat-setup/fp-drain/animation-runtime/saves/file3.json`, then:

```bash
export SHIP_HOME=/workspace/.paperboat-setup/fp-drain/animation-runtime
timeout 120s gdb -q -batch -x /workspace/PaperBoat/tools/porting/fp_drain_animation.gdb ./Paperboat
```

This uses the real title/file-select/world lifecycle and native Hammer demo,
then captures the label and green flower/number 2 after eighteen native recovery
updates. GDB non-stop mode pauses only game-tick while rendering threads present
the preceding frame; the script explicitly selects the paused thread. The
capture is timing-controlled, with software rendering/dummy audio. It detaches
and records `animation.pid`; stop only that fixture process when finished.
Screenshots/save files stay local, numeric `animation.json` is publishable.

```bash
BADGE_ASSETS_RESULT=/workspace/.paperboat-setup/fp-drain/assets.json \
  python3 /workspace/PaperBoat/tools/porting/check_badge_assets.py
```
