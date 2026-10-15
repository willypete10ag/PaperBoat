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
  save/load. It does not establish a controller-driven victory or full campaign.
- Regular Goombas still choose Mario through vanilla AI. TTYD64's front/back
  target selection and source position rules are the next combat batch. Existing
  partner damage/death/Life Shroom checks use controlled enemy targets; do not
  equate those with ordinary enemy-AI coverage in this launcher.
- Only Goombario HP and four shroom-family recipient paths are supported here.
  Full source choreography/artwork, other foods, other partners, new moves,
  partner badges and campaign conversion remain unfinished.
- World shrooms can heal zero HP, matching source; ordinary battle food cannot.
  Life Shroom remains automatic battle recovery. Save compatibility is retained,
  but these isolated test saves are not a supported TTYD64 campaign format.
