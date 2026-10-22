# Windows TTYD64 partner playtest

> **Policy supersession:** prior off/unsaved/reset activation policy below is superseded by [ADR 0007](https://github.com/willypete10ag/ttyd64-port/blob/main/docs/decisions/0007-per-save-ttyd64-mode.md). Historical code/results keep their original scope. This branch implements per-save mode; use the milestone PR for current acceptance/CI status.

This is an early Goomba Village/Road slice, not the full TTYD64 campaign. Normal
Paperboat.exe offers Vanilla (default) or experimental TTYD64 when creating a
file. Existing saves stay Vanilla. Use the launcher below
to opt into a fresh isolated developer session with Goombario, Kooper and Bombette.
No GDB, Python, source checkout or private seed save is needed to play.

1. Download the **Paperboat-windows** artifact from the milestone PR's green
   Build workflow. Extract the entire ZIP to a regular writable folder outside
   OneDrive and temporary folders. Keep the EXE, DLL, assets/, config.yml,
   paperboat.o2r, launcher scripts and playtest-keyboard.json together.
2. Double-click **Play-TTYD64.cmd**. Select your own supported **Paper Mario
   (USA)** ROM when prompted. The native extractor validates the ROM and builds
   a local archive; extraction may take a while. Never upload the ROM or archive.
3. The game starts in Goomba Village with Mario 15/20 HP and 10/10 FP. All three
   supported partners start wounded at 3 HP. Use the right exit toward Goomba
   Road for battles. Close the game window when finished.

Keyboard: WASD move/menu; X confirm/jump; C cancel/hammer; Space pause; Left arrow
world items; Right arrow world partners; Z battle team position/order. Connected
controllers retain the engine's default mappings; check/remap in its input menu
if needed. Controller hardware and actual Windows rendering/input need a human
playtest; a green CI compile or ROM-free preflight does not validate those.

Default **status** inventory: Courage Shell, Power Punch, Mini Mr. Mini,
Mr. Softener, Slow Shroom, Gradual Syrup, Couples Cake, Meteor Meal and two
Life Shrooms. Both profiles now start with 20 BP and six equipped badges:
two Double Dips, two Flower Saver A copies, Pity Flower and Last Stand (18 BP).
Double/Triple Dip should cost 2/6 FP with those two Flower Savers, paid once.
Spare copies and FP Drain, Defend Plus, Jumpman and Hammerman are owned too;
inspect/change them in Pause → Badges. FP Drain reduces damage, so it starts
unequipped; equipping both Jumpman and Hammerman locks both attack commands.
These are deliberate developer grants, not source world distribution.
Both profiles also start with five Star Spirit powers and five bars, including
Refresh and Smooch, for the team recovery test. In battle, both show “Mario &
Partner” and two pointers when a supported partner is alive. Smooch heals 20 HP
up to each maximum; Refresh heals 5 HP/shared FP and cures debuffs.

Goombas, Paragoombas and Spiky Goombas use TTYD64 front/back target choice with
supported partners. Z changes the front actor; a dead partner is not an enemy
target. Other enemy families and unsupported partners remain incomplete.

For a focused test, try Double/Triple Dip, status/regeneration items on Mario
and partners, Z position changes and ordinary Road damage/death/Life Shroom.
Observe badge copy rows, costs and effects; report which partner, item/badges
and action were involved. Pity Flower is random, and Last Stand needs low HP.
Try world healing and a Save Block with the alternate **healing** inventory
(three Mushrooms, a Super Shroom and two Life Shrooms):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Play-TTYD64.ps1 -Profile healing
```

The process-scoped execution policy option runs the supplied local script; it
does not change your machine's policy. If organizational policy forbids scripts,
retain the error for troubleshooting rather than changing system policy.

For explicit paths, including paths with spaces:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Play-TTYD64.ps1 -Rom 'D:\My ROMs\Paper Mario.z64' -Profile healing
```

The launcher caches the generated archive under
`%LOCALAPPDATA%\PaperBoat-TTYD64-playtest\archives`, keyed by ROM/executable hashes,
and verifies it before reuse. An existing locally generated archive can be used
with `-Archive 'D:\Private data\pm64.o2r'`. Native extraction assets are included
in the ZIP. A missing/incomplete cache reports its exact folder; move that
generated folder aside and retry. No archive or extracted ROM data is distributed.

Each launch creates a **new** session under
`%LOCALAPPDATA%\PaperBoat-TTYD64-playtest\sessions`. Its marked folder contains
the session's saves, config, copied archives, engine logs and setup manifest.
Launcher/extraction output goes to a matching `logs-...` folder. `-SessionRoot`
can select another writable local parent. Existing session folders are refused.
The native entry point checks the engine's actual config/save roots before
initialization; it does not rely on SHIP_HOME for Windows. Portable Windows
builds are required. Normal game configuration and saves are not imported.

Session state comes from native new-game initialization with deliberate developer
recruitment, wounds, inventory and progression. The file explicitly saves TTYD64
rules; native file selection/continuation restores its mode. The one-shot setup
request is consumed once; a new file still defaults to Vanilla.
Save Blocks write within the session. This launcher currently starts fresh each
time; resuming a session across launches is not provided. Keep experimental saves
separate from normal campaign saves. Source story progression, flying partners,
most source content and complete source item presentation remain incomplete.

When reporting problems, describe the profile, partner, action and expected/actual
behavior. Share the launcher `launch.json`, stdout/stderr logs and relevant engine
log, after checking local paths for personal information. Do not upload the
session directory, ROM, archive, extracted assets or save files.

For maintainers, `--ttyd64-playtest-preflight NEW_SESSION PACKAGE ROM_ARCHIVE
healing|status` performs staging/path checks without graphics or loading archives.
`check_playtest_preflight.py` supplies a clearly synthetic text archive and runs
positive/negative process checks on Linux and the packaged Windows executable in
CI. These are ROM-free path/process checks, not gameplay acceptance.
