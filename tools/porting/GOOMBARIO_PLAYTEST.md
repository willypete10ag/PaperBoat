# Isolated Goombario developer playtest

This is a focused native menu/healing/encounter test in the **prepared Linux
cloud environment**, not a packaged TTYD64 release. It needs the existing debug
executable, local game archives, GDB and private fixture seed/controller profile.
The launcher does not download or redistribute game assets. Windows/macOS,
hardware rendering and audible output have not been accepted through this route.

## Start

Use a display you can actually view and control. `:97` is the existing headless
validation display; the launcher does not create a desktop viewer or stream.

```bash
source /workspace/.paperboat-setup/activate.sh
cd /workspace/PaperBoat
# Set DISPLAY to your visible desktop. Use :97 only with a viewer attached,
# or for the automated --verify check.
python3 tools/porting/launch_goombario_playtest.py
```

It allocates a fresh session under
`/workspace/.paperboat-setup/goombario-playtest/sessions/`, copies only the known
private fixture seed/controller profile, starts the native title/file lifecycle,
prepares the scenario, verifies keyboard input, then detaches GDB. The native
game keeps running under your control. The printed directory contains the save,
configuration, launch log and numeric readiness report. Each launch starts fresh;
normal saves/configuration and earlier test sessions are not overwritten.
Close the game window when finished. No debugger commands are needed to play.

To check startup/input and close automatically:

```bash
DISPLAY=:97 SDL_AUDIODRIVER=dummy LIBGL_ALWAYS_SOFTWARE=1 \
    python3 tools/porting/launch_goombario_playtest.py --verify
```

The prototype is explicitly enabled only in this isolated process. Normal game
launches remain default-off; the flag is not saved and new game resets it.
This does not introduce a product setting or enable other partners' HP combat.

## Controls and scenario

| Action | Copied test keyboard profile |
| --- | --- |
| Move / menu directions | W / A / S / D |
| A / confirm / jump | X |
| B / cancel / hammer | C |
| Start / pause | Space |
| World items | Left arrow |
| World partners | Right arrow |
| Native battle turn/position switch | Z |

Start in Goomba Village with Mario at 15/20 HP, Goombario at 3/10 HP, normal-rank
boots/hammer, action commands unlocked, three Mushrooms, one Super Shroom and two
Life Shrooms. Only Goombario is recruited and no badges are equipped. Progression
is controlled setup, not a campaign progression validation.

Try the world item menu, choose Goombario and confirm; check HP in the world bar
and pause Party tab. Cancel a recipient choice to return to inventory without
using the item. Walk through the right exit to Goomba Road for an ordinary
encounter. Use native attacks/menus or Strategies → Run Away (mash X), then
check world control, HP and further item use. User-reported behavior outside the
automated route remains unvalidated until reproduced.

## Known boundaries

- Shared acceptance covers keyboard contact, Mario/partner swap menus, a
  controlled zero-HP swap-back, native keyboard flee, world healing, pause and
  save/load. The shared victory route also selects Headbonk/Jump with keyboard
  input, defeats the native Goombas, awards star points/win count, returns to
  the world and saves through the village Save Block. Full campaign remains
  unfinished.
- Basic Goombas now use source front/back choice under the Goombario guard.
  Z exchanges physical positions; spending a turn preserves them. A living front
  Goombario starts the next round. Actual Goomba hits, death and one Life Shroom
  revival are covered by the shared native route, with controlled initial wounds
  and inventory. Other enemy AI and partner consumers remain unported.
- Without Life Shroom, front Goombario death moves Mario forward and skips the
  unavailable partner turn in later rounds. With Life Shroom, Goombario retains
  the front slot and revives. Full source yaw/effect choreography is unfinished.
  Failed-flee presentation is not yet scenario-accepted.
- Default sessions recruit Goombario. The opt-in ground group below adds Kooper
  and Bombette HP and the same four shroom-family recipient paths.
  Full source choreography/artwork, other foods, other partners, new moves,
  partner badges and campaign conversion remain unfinished.
- World shrooms can heal zero HP, matching source; ordinary battle food cannot.
  Life Shroom remains automatic battle recovery. Save compatibility is retained,
  but these isolated test saves are not a supported TTYD64 campaign format.

## Shared developer acceptance

`partner_playable_slice_gdb.py` reuses one native lifecycle/input driver. Select
`PARTNER_SLICE_PHASES=victory` for the living-front route or `victory-dead` for
natural no-item partner death followed by Mario finishing the battle. They may
be combined in one process. Existing pause/world-items/battle/team phases remain.

The acceptance runtime is strictly
`/workspace/.paperboat-setup/partner-playable-slice/runtime`, with disposable
slot 3 matching the private FP Drain seed before launch. Use the prepared shell,
run GDB from `build/ninja-debug`, supply DISPLAY, SHIP_HOME, software GL/dummy
audio and PARTNER_SLICE_RESULT, then source this Python driver with `gdb -batch
-x`. Run one fixture at a time on the display. This is developer acceptance,
not an additional way to launch a player session.

Setup controls map/position, recruitment/progression, initial wounds/items and
a non-level-up reward boundary. Targets, attack damage, enemy defeat, victory,
rewards and Save Block interaction are native. Reload explicitly calls native
FIO; this does not claim a fresh-process/title restart or level-up validation.
Exact disposable save bytes are restored in a finally block. Screenshots and
logs stay private; only numeric results belong in the coordination repository.

## Ground-partner HP prototype

Add `--ground-partners` to recruit Goombario, Kooper and Bombette in the new
isolated session, each initially wounded at 3 HP. Native normal-rank maxima are
10, 10 and 15. Use the world Partners menu or battle Change Partner to select
one. `--verify --ground-partners` checks setup/input and closes automatically.
Default invocation still recruits only Goombario; normal launches remain off.

The supported HP group shares damage/death/Life Shroom, turn skipping, team
positions, shrooms and HP presentation. Kooper additionally has source DEF1
(flipped DEF0), jump/POW/quake flipping, two-round recovery and unavailable
recovery turns. His countdown also advances while another supported partner is
active. Basic one-damage Goomba hits should deal zero to an upright Kooper.
Bombette retains native burn/contact/shock explosions and skips the legacy drop
in HP mode. Lethal contact selects death/revival directly.

Complete move sets, source status animation assets and remaining combat/cure
interactions, broader enemy AI and flying exceptions remain unfinished. The
guarded group now enables native status infliction/lifecycle as described below.
Normal play stays off, and original save layouts are preserved.

For developer acceptance, PARTNER_SLICE_PARTNER=2 or 3 selects Kooper/Bombette
in the shared ground-contracts, ground-combat, team, victory and victory-dead
phases. Kooper team/dead-victory fixtures give enemies a controlled +1 attack
boost to exercise death through DEF1; this is distinct from an unmodified
Goomba encounter. Ground-contracts combines controlled enemy/item/contact APIs
with keyboard rounds, swaps, flee and normal death/Life Shroom ownership.
Ground-ui checks world swaps, pause rows and world recipients together. Strict
disposable-slot guards and byte-for-byte restoration still apply.

The [shared ground combat handoff](https://github.com/willypete10ag/ttyd64-port/blob/main/docs/handoffs/2026-10-16-ground-combat-contracts.md)
records exact implementation/evidence pins, limits and the next subsystem batch.

The guarded ground group also supports native status application, typed swap
storage, turn gates, active-partner timer advancement and poison HP/death/revival.
Ordinary inactive status timers pause; Kooper's inactive flip timer is separate.
Ordinary debuffs allow action in the round they expire, while Kooper flip spends
its recovery round. Native icon/palette/ice ownership follows the live actor and
clears on death, victory or battle exit. Source-specific status animation assets
and remaining combat/cure interactions are still incomplete.

Developer acceptance uses PARTNER_SLICE_PHASES=statuses for partner1/2/3, sharing
native keyboard rounds, frozen swaps and flee, with controlled API infliction
and setup. This does not claim natural status-bearing enemy AI, all item effects,
all partner moves or a campaign port. The prototype remains off in normal play.
See the [shared status handoff](https://github.com/willypete10ag/ttyd64-port/blob/main/docs/handoffs/2026-10-16-partner-status-lifecycle.md)
for source timing, validation scope and the remaining combat/cure interactions.
