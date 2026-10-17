"""Generate the seed using clear_player_data and fio_save_game, never private saves."""

import os, sys
from pathlib import Path

if not os.environ.get("PORTING_FIXTURE_DIR"):
    raise RuntimeError("Missing PORTING_FIXTURE_DIR; use run_acceptance.sh")
sys.path.insert(0, os.environ["PORTING_FIXTURE_DIR"])
from fixture_support import *
import gdb

validate_runtime()
for setting in ("pagination off", "confirm off", "print thread-events off"):
    gdb.execute("set " + setting)
gdb.Breakpoint("state_step_startup", temporary=True, internal=True)
gdb.execute("run")
gdb.execute("set variable gPortResetToTitleScreen=1")
gdb.Breakpoint("state_step_title_screen", temporary=True, internal=True)
gdb.execute("continue")
gdb.execute("call clear_player_data()")
# A deterministic test seed, not a normal playthrough. Match the documented
# original FP Drain fixture setup using native inventory APIs after a new game.
for _ in range(3):
    assert int(gdb.parse_and_eval("add_item(ITEM_FP_DRAIN)")) >= 0
for expression, value in [
    ("gPlayerData.maxBP", 6),
    ("gPlayerData.equippedBadges[0]", int(gdb.parse_and_eval("ITEM_FP_DRAIN"))),
    ("gPlayerData.equippedBadges[1]", int(gdb.parse_and_eval("ITEM_FP_DRAIN"))),
    ("gPlayerData.curPartner", int(gdb.parse_and_eval("PARTNER_BOW"))),
    ("gPlayerData.partners[PARTNER_BOW].enabled", 1),
    ("gPlayerData.hardMaxFP", 10),
    ("gPlayerData.curMaxFP", 10),
    ("gPlayerData.curFP", 2),
]:
    gdb.execute(f"set variable {expression}={value}")
gdb.execute("call fio_save_game(3)")
record_check("new-game-native-save-with-controlled-fp-drain-setup")
assert fixture_save().is_file(), "Native new-game writer did not create file3.json"
print("PORTING_SEED_CREATED_FROM_NEW_GAME")
gdb.execute("kill")
