# Reproducible native TTYD64 checks

Partner HP combat remains **off in normal play**. These are developer checks,
not a completed mod or campaign acceptance. All runtime fixtures use debugger
setup; several use injected damage/forced guard/RNG returns. Per-check method
records and complete logs identify those cases. Capturing a frame does not
prove anyone inspected it. Software rendering and dummy audio do not validate
hardware rendering or audible output.

## ROM-free gameplay tests (Linux, no game installation)

On Ubuntu 24.04, from a clean checkout:

```bash
sudo apt-get update
sudo apt-get install -y git cmake ninja-build g++ nlohmann-json3-dev
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
  libopengl-dev libgl1-mesa-dev libogg-dev libvorbis-dev zlib1g-dev libbz2-dev \
  libvulkan-dev libshaderc-dev glslang-dev spirv-tools

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
