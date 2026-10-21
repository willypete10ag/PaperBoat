# Reproducible native TTYD64 checks

> **Policy supersession:** prior off/unsaved/reset activation policy below is superseded by [ADR 0007](https://github.com/willypete10ag/ttyd64-port/blob/main/docs/decisions/0007-per-save-ttyd64-mode.md). Historical code/results keep their original scope. This branch implements the saved-mode contract below; acceptance/CI status is recorded in its milestone PR.

New files offer **Vanilla** (default) or **TTYD64 (experimental)**. Existing saves
remain Vanilla. These checks are not full-mod or campaign acceptance. All runtime fixtures use debugger
setup, except the native-launch checks described below; several use injected damage/forced guard/RNG returns. Per-check method
records and complete logs identify those cases. Capturing a frame does not
prove anyone inspected it. Software rendering and dummy audio do not validate
hardware rendering or audible output.

## Native guard input and Piranha status attacks (R1-M5)

`--only native-guard-1,native-guard-2,native-guard-3` runs ordinary Road Goomba
attacks on each supported ground partner and Mario. X is scheduled through
xdotool/SDL during the native attack; the fixture never overwrites the input
ring, block result, damage or RNG. Timed taps require successful guards on both
teammates; every attempted tap/hit remains in the trace. Early and no-input
controls check native EARLY/FAIL results and unguarded damage. A brief real-time
hold allows SDL polling; this is instrument-timed keyboard input, not a human
reaction-time test. Initial map/recruitment/rank/stats/stock and between-turn HP
refills are controlled, as is the shared file-select startup return.

`native-status-1/2/3` selects actual Putrid/Frost Piranha formations1501/1d07 in
disposable Road encounters, then uses keyboard contact, Z order, Do Nothing and
flee. Native enemy scripts choose attacks/RNG/status/damage; no status, cure,
immunity, attack branch or result is injected. This tests real enemy scripts,
not their natural Jungle/Snow map acquisition. Partner-front attacks, poison
HP ticks, native durations, freeze turn blocking/expiry, same-battle Vanilla and
dead-partner fallback boundaries are observed. Mode/dead boundaries and refills
are explicit injected comparisons. `PORTING_STATUS_BASELINE=1` expects the old
Mario-only target and is pre-fix reproduction only. Baseline and failed attempts
retain their own game/fixture identities. Captures remain private for inspection.

Putrid/Frost Piranhas now use the source SetTargetActorInFront rule; Frost reads
its selected target's frozen state. First-strike camera positions also use that
target. Vanilla and unsupported partners retain Mario targeting without extra
RNG. Native attack damage/chances/durations are retained; this does not port all
source move values, status enemies, flying partners, or campaign content.

## World item-description layout (PT-UI-001)

The eight appended status/regeneration descriptions use one newline between
text lines, matching the native two-line world popup. The window/font geometry
and original item messages are unchanged.

Add `--descriptions` to `check_native_playtest.py` for the grouped UI cohort.
It runs the native developer healing/status profiles, navigates every item with
real keyboard input and records loaded message controls, native font pitch,
width, actual popup dimensions and private capture hashes. For the Vanilla
comparison it explicitly edits only the disposable file's saved mode, uses
native FIO load and reuses its inventory; this is not normal Vanilla acquisition
of appended items. Original save bytes are restored before process cleanup.
The cohort stops after menu checks; later swap/healing/battle acceptance is not
included. Captures stay private and require inspection.

`--descriptions --description-baseline` expects the old blank-line overflow and
is only for pinned pre-fix reproduction. `get_msg_lines` ignores blank lines;
the observer therefore counts loaded ENDL controls and records that helper's
nonempty-line count separately. A passing baseline report means the old defect
was reproduced, not that the UI fits. No Windows rendering claim follows from
a Linux run or a green platform build.

## Per-save mode and shared acceptance

ADR0007 is implemented by the new-file rules screen. Choice is fixed for the
file; no normal menu/CVar changes an existing campaign. The optional native JSON
is `ship.ttyd64Mode = {"version": 1, "rules": "vanilla" | "ttyd64"}`. Missing,
invalid or unknown data defaults to Vanilla, including old native saves and
vanilla imports. HP/inventory/proof flags never infer the choice. The legacy
player/partner structs and save prefix stay fixed. Unrelated JSON keys survive
save/copy. Runtime mode belongs to the loaded file; summary previews and file
copy do not select a file. The normal maps contain neither proof Pity Flower.

After a clean committed build (the full runner below creates its matching
`porting-build.json` receipt), run the grouped Linux acceptance:

```bash
python3 tools/porting/check_save_modes.py --source "$PAPERBOAT_SOURCE_DIR" \
  --executable "$PAPERBOAT_EXECUTABLE" --package "$PAPERBOAT_BUILD_DIR" \
  --archive "$PAPERBOAT_ROM_ARCHIVE" --output "$PORTING_WORK_DIR/save-modes-new-run"
```

The output must be new. Real keyboard-only creation makes both file modes;
separate processes use title/file selection to resume TTYD64 and a mode-less old
file. The lifecycle group uses native CLI setup, harmless injected JSON probes,
native copy/preview/erase APIs and controlled route/1HP/empty items, followed by
real encounter/Do Nothing/native fatal damage/game-over/title/keyboard continue.
Every group writes its own full log, timestamps, source/fixture commits and
binary/fixture hashes. GDB observes creation/continuation without injecting their input/state;
subsequent Heart Block comparisons inject wounds, position and the test block. There is no forced guard/RNG or injected reset/game-over API.
This supplements the shared healing/status/badge fixtures; passing one group
is not a full-suite result. Old proof-acquisition fixtures now first check native
absence, then explicitly inject disposable test entities for pickup/capacity.

## Current-partner recovery hooks

`--only partner-recovery-hooks-1,partner-recovery-hooks-2,partner-recovery-hooks-3`
extends the existing shared partner route. The world-heart matrix injects current
partner/rank/wounds and an entity's touch state, then runs the native collectable
callback. It covers all eight compatible HP records, zero/wounded/full HP,
Vanilla/TTYD64, Mario already full and unchanged inactive partners. Only the three
ground partners have native actor acceptance: real keyboard Road contact creates
their actors; injected reward substate/timer and wounds run the native celebration
callback, checking HP/actor synchronization and inactive records across all ranks.
This callback matrix does not prove earning a level-up or its stat-choice UI. The
separate `partner-level-up-1/2/3` scenarios grant a disposable heart and99 star
points, then use real walking/pickup, Road encounter, attacks, native victory,
earned level-up/stat choice, world return and Save Block/save reload. Recruitment,
wounds, progression and maps are controlled as in the shared route; rewards and
level-up state are not forced in these three scenarios.
`PORTING_RECOVERY_BASELINE=1` records expected missing hooks on a pinned pre-fix
executable; use it only for bug reproduction, never fixed-game acceptance. Both
modes and the baseline flag appear in each result's configuration/full log.

## Double Dip and BP-budget checks

In TTYD64 files Double Dip costs3 BP per copy: one copy offers Double Dip,
two offer one Double Dip and one Triple Dip, and extra copies add no menu rows.
A standalone Triple Dip shares its row. FP costs remain4/8 before Flower Saver;
the native item scripts pay once per sequence. Vanilla retains single-equip and
its original menu/cost behavior. Loading an over-budget TTYD64 file unequips from
the end until affordable, preserving owned badges and the original file until
its next normal save. Invalid equipped item IDs are cleared in that mode only.
No legacy save structs or JSON fields change. A running injected over-budget
state displays zero available BP and a bounded budget-orb loop.

`--only dip-menu,bp-render,dip-native,flower-saver-writer,flower-saver,flower-saver-vanilla`
uses existing shared badge and partner drivers. `dip-menu` injects inventory /
budget and calls native pause/FIO/menu APIs, including forced demo/menu returns;
it covers copy rows, save migration, both modes, mixed standalone Triple Dip and
64 injected copies. `bp-render` injects an over-budget world loadout, uses keyboard
pause input, and observes native numeric/budget-orb calls. `dip-native` controls
stock/wounds/FP and equips through the native pause API, then uses real keyboard
contact, Double/Triple Dip menus, cancellations, Mario/partner recipients, item
scripts/payment, stock exhaustion and turn scheduling. Common startup uses a
forced file-select return; Dip selections, guards, RNG and outcomes are not
forced. Only selected IDs run. `PORTING_DIP_BASELINE=1` expects the old defects
for pinned pre-fix reproduction; never use that setting as fix acceptance.

## Source rules and costs

TTYD64 mode now uses the182 matching semantic Moves.xml identities for FP/BP
prices. Twenty remaining differences are corrected through the saved-mode
getters; the static Vanilla table stays intact. Seven reused/relocated source
indices are explicitly excluded. Price parity does not port a move's mechanics,
stacking, availability or distribution; Charge behavior remains separate.

The ROM-free `ttyd64_source_rules` CTest parses committed original public source
XML and the active partner-HP table excerpt, then calls the compiled pure
functions. It preserves185 original Vanilla rows, compares182 semantic TTYD64
FP/BP rows and33 partner/rank HP cells. See tests/reference/README.md for pinned
source/provenance; no ROM, generated archive, assets or save is included.
Linux CI runs both gameplay and source-rule CTests.

`--only source-costs` extends the shared Flower Saver driver:365 matrix checks
parse the local pinned source XML independently of port constants. Fixed-game
checks additionally exercise native7BP Quick Change/Double Dip budget rejection,
load-budget trimming/owned counts and the three changed FP payments through
native APIs. Inventory/mode/state and demo actors are controlled, including a
forced demo return; no actual move scripts or real input are claimed here.
`PORTING_SOURCE_COSTS_BASELINE=1` expects the old20 differences for pinned
before-fix reproduction only. It is never fix acceptance.

## Windows playtest and native startup checks

The Windows CI ZIP now includes an explicit isolated developer-session launcher.
See [WINDOWS-PLAYTEST.md](WINDOWS-PLAYTEST.md) for local-ROM setup, controls,
profiles, saves and logs. Normal launches use the selected file's saved mode; the launcher creates an explicitly TTYD64 developer file.
The launcher creates new-game state natively; no GDB or private seed is needed.

Linux and packaged Windows CI run `check_playtest_preflight.py` with a synthetic
text archive. This exercises actual process/path setup and failure diagnostics,
including the Windows PowerShell launcher, without loading any ROM data or
initializing graphics. CI artifacts preserve full logs/hashes/times. It does not
validate real Windows rendering, input or gameplay.

For a committed Linux build with the extraction assets in its output directory:

```bash
cp tools/porting/fixtures/keyboard.json "$PAPERBOAT_BUILD_DIR/playtest-keyboard.json"
python3 tools/porting/check_native_playtest.py \
  --executable "$PAPERBOAT_EXECUTABLE" --package "$PAPERBOAT_BUILD_DIR" \
  --archive "$PAPERBOAT_ROM_ARCHIVE" --output "$PORTING_WORK_DIR/native-playtest-new-run"
```

Install Xvfb, GDB and xdotool as in the full Linux recipe. The output path must
not exist. This check owns its Xvfb server, launches each profile through the
native CLI, observes state with GDB, and uses real keyboard movement/menus/swap/
pause/healing. Recruitment, wounds/items/progression are native developer setup,
not debugger writes. A final reset-boundary check explicitly calls the native
startup API from GDB; methods disclose it. Result JSONs contain commit, executable/
fixture/archive hashes, UTC times, per-check methods, full logs and skips. Copy
only result JSONs into the coordination repository, never the session/save/
archive files. This targeted group does not rerun all older gameplay fixtures.

## ROM-free gameplay tests (Linux, no game installation)

On Ubuntu 24.04, from a clean checkout:

```bash
sudo apt-get update
sudo apt-get install -y git cmake ninja-build g++ python3 nlohmann-json3-dev
git clone --branch ttyd64/main https://github.com/willypete10ag/PaperBoat.git
cd PaperBoat
cmake -S . -B build/logic -G Ninja -DPAPERBOAT_LOGIC_TESTS_ONLY=ON
cmake --build build/logic
ctest --test-dir build/logic --output-on-failure
```

This builds the same pure functions called by gameplay and SaveManager, with
no engine, ROM, extracted assets, SDL or display. Assertions stay enabled in
Release. Coverage: all partner HP/rank table entries, normalization, real JSON
serialization/parsing with missing/invalid/out-of-range values, BP accumulation,
move FP reductions/floor, the complete stack allowlist (including the current
Double/Triple Dip non-stacking limitation), Last Stand, FP Drain, and Pity Flower
with boundary rolls and a reproducible seeded RNG stream. A passing test of the
current allowlist does not claim source Double Dip parity.

## Full Linux acceptance from a clean checkout

This is a separate recipe; if you used the ROM-free recipe above, reuse that
checkout and omit the clone/`cd` commands.

Use Ubuntu 24.04 or equivalent with GCC 14, CMake >=3.28 and Python >=3.10.
The commands below also need Internet access for source dependencies. ROM data
never goes into Git or CI. Supply your own unmodified supported US Paper Mario
ROM; extraction validates the ROM. Historical onboarding used US SHA-1
`3837f44cda784b466c9a2d99df70d77c322b97a0`.

```bash
sudo apt-get update
sudo apt-get install -y gcc-14 g++-14 git cmake ninja-build lsb-release file \
  curl wget build-essential pkg-config python3 gdb xvfb xdotool x11-utils imagemagick \
  libsdl2-dev libsdl2-net-dev libpng-dev libzip-dev zipcmp zipmerge ziptool \
  nlohmann-json3-dev libtinyxml2-dev libspdlog-dev libfmt-dev libboost-dev \
  libopengl-dev libgl1-mesa-dev libgl1-mesa-dri libogg-dev libvorbis-dev zlib1g-dev libbz2-dev \
  libvulkan-dev libshaderc-dev glslang-dev spirv-tools

git clone --branch ttyd64/main https://github.com/willypete10ag/PaperBoat.git
cd PaperBoat
git submodule update --init --recursive
export CC=gcc-14 CXX=g++-14
# Match the dependency versions used by .github/workflows/build.yml.
mkdir -p ../paperboat-deps
cd ../paperboat-deps
wget https://www.libsdl.org/release/SDL2-2.30.3.tar.gz
tar -xzf SDL2-2.30.3.tar.gz
(cd SDL2-2.30.3 && ./configure --enable-hidapi-libusb && make -j4)
sudo make -C SDL2-2.30.3 install
wget -O tinyxml2-10.0.0.tar.gz https://github.com/leethomason/tinyxml2/archive/refs/tags/10.0.0.tar.gz
tar -xzf tinyxml2-10.0.0.tar.gz
cmake -S tinyxml2-10.0.0 -B tinyxml2-10.0.0/build
cmake --build tinyxml2-10.0.0/build -j4
sudo cmake --install tinyxml2-10.0.0/build
wget https://github.com/nih-at/libzip/releases/download/v1.10.1/libzip-1.10.1.tar.gz
tar -xzf libzip-1.10.1.tar.gz
cmake -S libzip-1.10.1 -B libzip-1.10.1/build \
  -DENABLE_COMMONCRYPTO=OFF -DENABLE_GNUTLS=OFF -DENABLE_MBEDTLS=OFF -DENABLE_OPENSSL=OFF
cmake --build libzip-1.10.1/build -j4
sudo cmake --install libzip-1.10.1/build
sudo ldconfig
cd ../PaperBoat

git clone https://github.com/eldexterr/ttyd64.git ../ttyd64-reference
git -C ../ttyd64-reference checkout b8d2058ea057b2dfc168f2d909a2a2ea0927ce17
export PAPERBOAT_SOURCE_DIR="$PWD"
export PAPERBOAT_BUILD_DIR="$PWD/build/acceptance"
export PAPERBOAT_EXECUTABLE="$PAPERBOAT_BUILD_DIR/Paperboat"
export TTYD64_REFERENCE_DIR="$(realpath ../ttyd64-reference)"
# EDIT to your own ROM location. Do not copy it into a tracked directory.
export PAPERBOAT_ROM="/absolute/path/to/papermario.us.z64"
# Choose fresh private output locations; archives and runtime saves are local.
export PAPERBOAT_ROM_ARCHIVE="$(realpath ..)/paperboat-private/pm64.o2r"
export PAPERBOAT_PORT_ARCHIVE="$PAPERBOAT_BUILD_DIR/paperboat.o2r"
export PORTING_WORK_DIR="$(realpath ..)/paperboat-private/run-001"
export PORTING_RESULTS_DIR="$(realpath ..)/paperboat-evidence/run-001"
bash tools/porting/run_acceptance.sh
ctest --test-dir "$PAPERBOAT_BUILD_DIR" --output-on-failure
```

Run serially; the runner owns a fresh Xvfb display and disposable process groups.
A container must permit tracing its own child (`ptrace`); sandbox rejection is a
failed run, not a gameplay result. Do not run as root. ImageMagick must permit
local PNG captures. Default timeout is 1800 seconds **per fixture**; the full
suite can take much longer. Set `PORTING_BUILD_JOBS` (default 4) or
`PORTING_FIXTURE_TIMEOUT` to adjust local resources. Missing environment variables
or inputs produce explicit errors. The runner refuses tracked source edits,
existing work/results directories and unmatched build receipts. Use new output
paths for each attempt, including failed attempts.

The runner configures/builds Debug, writes a commit/binary build receipt, invokes
`Paperboat --extract-rom ROM SOURCE_DIR OUTPUT_DIR` to produce `pm64.o2r` without
SDL/UI, copies the executable beside the supplied archives (Linux resource discovery uses
`/proc/self/exe`, so a symlink or cwd alone is insufficient), starts Xvfb, generates the seed and runs
all committed runtime fixture scripts. The port archive comes from the native
build. No original private directory or prior save is required. All executable,
ROM, archive, reference, working and result paths are supplied above. The runner
provides per-process `SHIP_HOME`, `PORTING_SAVE_DIR`, `PORTING_SEED_SAVE`,
`PORTING_FIXTURE_DIR` and `PORTING_CHECK_METHODS`; they are never normal saves.

To run a subset, use for example:

```bash
bash tools/porting/run_acceptance.sh --only combat,foundation,healing
```

Dependencies such as the foundation writer are automatically included. Omitted
fixtures are listed as skipped in the manifest. `--reuse-archive` explicitly
skips extraction and hashes the existing supplied archive. `--skip-build`
requires a receipt matching the **current** source commit and executable hash;
it never relabels an old binary. A historical run can use an exported committed
`tools/porting` directory and `PORTING_FIXTURE_COMMIT=<full fixture commit>` while
the game checkout stays at the historical commit. The runner verifies its own,
helper, input profile and each fixture's bytes against Git blobs from that commit.
Do not silently substitute an older binary or fixture when something fails.

## Guarded timed actor modifiers

The default batch includes `actor-modifiers-1`, `actor-modifiers-2` and
`actor-modifiers-3`, sharing one playable-slice phase. They cover source signed
attack/defense replacement, cancellation, independent expiry, Tiny/Giant, public
event API adapters, controlled enemy damage and real keyboard swaps/rounds.
The existing status phase additionally checks poison-death/Life Shroom cleanup.

`Ttyd64AddAttackBoost(actor, amount, turns)` and `Ttyd64AddDefenseBoost` are explicit
three-argument source APIs; `Ttyd64MakeActorTiny/Giant(actor)` require a matching
signed attack effect. Enemy applications store one extra turn. Same-sign values
replace; opposite signs cancel. Inactive partner timers pause. State is unsaved,
cleared at battle boundaries/death, and guarded by the existing default-off flag. **[Activation policy superseded by ADR 0007; historical behavior.]**
Legacy two-argument permanent BoostAttack/BoostDefense keep their native ABI and
release timed ownership of their axis. Ported scripts should use the explicit
APIs. Native Shrink applications in the guarded context become -1 attack + Tiny,
coexisting with ordinary debuffs; generic native chances/duration inputs remain,
so this does not port every source Shrink move/chance or AI consumer. Full source
buff counters/arrows, HP/FP regeneration and charge conversion remain separate.
No normal activation or campaign parity is implied. **[Activation policy superseded by ADR 0007; historical behavior.]**

## Seed and input provenance

`seed_new_game_gdb.py` runs startup/title, calls native `clear_player_data()`,
adds three FP Drain badges through `add_item`, equips two, sets BP 6, recruits
Bow, sets FP 2/10, then calls native `fio_save_game(3)`. This reconstructs the
explicit original FP Drain test setup **from a new game**, rather than copying
any preexisting save. These are debugger/API grants, not natural progression.
The generated JSON is disposable and never committed. Other fixtures copy it
into their own marked runtimes or generate their own writer saves. The helper
refuses an unmarked runtime or a save directory outside its owned runtime.

`fixtures/keyboard.json` is only the native app's JSON controller/window
configuration (no game save or assets), preserved from the old test profile.
It contains Ship LUS keyboard mappings: WASD directions, X confirm, C cancel,
Space Start, arrows world item/partner menus, Z battle order. The launcher and
runner copy it into a fresh private configuration; they never modify a user's
existing config.

## Fixtures and evidence

The default batch includes combat/death/Life Shroom, HP/save foundation writer
and reader, battle healing, duplicate badge/individual badge writers and readers,
world acquisition, world heal/HUD/swap/battle-return, shared playable-slice phases
for Goombario/Kooper/Bombette (including ground UI), Last Stand unblocked/forced
guard, badge asset decoder checks, and Pity Flower/FP Drain/Flower Saver visual
script diagnostics. `build_badge_assets.py` is a build converter exercised by the
asset checks, not a gameplay fixture. The interactive launcher is documented
separately in [GOOMBARIO_PLAYTEST.md](GOOMBARIO_PLAYTEST.md).

Each `<fixture>.result.json` contains the exact game commit, distinct fixture
commit, executable/script/helper/runner/archive hashes, UTC start/end, pass/fail,
exit code, per-check input/injection methods, raw observations and **full log**.
The runner rejects runtime logs that load an unexpected archive or omit the ROM
archive; it hashes both the built and staged executable. SDL uses X11 explicitly
so an inherited Wayland setting cannot bypass the owned Xvfb.
`run-manifest.json` lists requested/skipped/failed fixtures and build/extraction
skips. `.log`, `.payload.json` and `.methods.json` sidecars aid local debugging;
the result JSON embeds the evidence needed for publication. Preserve failures.
Never carry a previous result forward with a new hash. Publish result JSONs and
the manifest in the coordination repository or link immutable CI artifacts.
Do not publish saves, ROMs, generated archives, extracted assets, binaries,
captures or credentials. Screenshots stay local for independent inspection;
an automated pass does not assert visual inspection or audible verification.

Historical reports made before this runner lacked executable/script/log
provenance and are provisional, even if their assertions were previously run.
Only exact-commit reruns supersede them. New milestones require a PR into
`ttyd64/main` with Linux, Windows, macOS and clang-format green.

## Guarded source status-item group

`status-items-1`, `status-items-2` and `status-items-3` run the shared Mario-owned
item route for Goombario, Kooper and Bombette. Courage Shell (+3 defense), Power
Punch (+2 attack/Giant), Mini Mr. Mini (-2 attack/Tiny, enemies) and Mr. Softener
(-min(normal part-table defense,3), enemies) use three-turn modifiers. Source
PartnersHP's forced SELECT_ONE for friendly buffs is represented in their native
target flags. Native IDs append at 0x171–0x174; existing IDs/save layouts stay fixed.
The two legacy contiguous item lists use a shared explicit ID mapping; all other
consumable-list capacities account for the four appended IDs.

The phase uses real keyboard item/recipient selection, cancellation, consumption,
turns, enemy iteration and flee. Health/inventory/battle setup and a temporary
normal-defense table are debugger controlled; modifier application rejection
checks are API driven. Save/load calls native FIO on the disposable slot. Numerical
scale and frame progression are not independent visual inspection. Published
source PNGs use the same independent decoder check as badge assets. No normal
activation, new shops/campaign acquisition, enemy/partner-owned item choreography,
source status counters, regen/charge or hardware/audio acceptance is implied.

## Guarded regeneration consumer group

`regeneration-1`, `regeneration-2`, and `regeneration-3` share native keyboard
item/recipient/cancel/consumption/turn checks for the three supported ground
partners. Slow Shroom and Couple's Cake set HP +2 for 10 turns; the latter
consumes without effect on its Mario owner. Gradual Syrup sets recipient-owned
FP +2 for 10 turns, recovering shared player-team FP. Meteor Meal heals its
recipient 7 immediately, then HP +2 for 3 turns. IDs 0x175–0x178 append;
all original IDs/save fields remain unchanged. Normal activation stays off. **[Activation policy superseded by ADR 0007; historical behavior.]**
Only guarded battle consumers are implemented; source world use, shops and
recipes are pending. Source message-box/wave choreography and persistent
regeneration counters are not complete.

Recovery runs at native begin-player-turn before all modifier decay. Inactive
partners pause; enemy FP effects do not restore player FP. Setters overwrite
HP/FP axes directly, independently of attack/defense sign cancellation. Native
full clear/death/battle cleanup removes them, and they are never serialized.
The phase discloses debugger inventory/map/HP/transparency setup and controlled
API cases separately from real input. Numeric HP/timer/FX observations do not
establish independent visual, hardware or audible acceptance. The existing
status phase also exercises poison death/Life Shroom with both regen axes set.

## Representative combat playtest group (R2-M5)

`--only goomba-family` uses the shared partner driver in real kmr_06 Spiky0B /
Para09 encounters: controlled recruitment/progression/map/entry/items and HP
refills, then keyboard contact (moving jumps for Para), Do Nothing/flee, native
enemy targeting/damage/turns/world return. Fixed mode expects both team targets;
same-battle controlled Vanilla and zero-partner boundaries check fallback. No
forced AI, guard, RNG or damage; common file-select startup return is forced.
`PORTING_FAMILY_BASELINE=1` reproduces the earlier Mario-only behavior instead.
This is one shared group, not complete enemy/status/timed-guard acceptance.

`check_native_playtest.py` starts both CLI presets without debugger setup or a
private seed; keyboard menus observe the granted copy loadout and its badge
panel. Its reset boundary remains an explicitly controlled API call. Private
badge screenshots aid inspection and must not be committed. The Windows process
preflight additionally exercises the launcher's default status profile; it does
not run the Windows engine/input. See WINDOWS-PLAYTEST.md for the focused brief.
