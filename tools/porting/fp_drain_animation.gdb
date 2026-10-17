# Requires this feature's disposable writer save copied into animation-runtime.
python
import os
from pathlib import Path
assert Path(os.environ["SHIP_HOME"]).resolve() == Path("/workspace/.paperboat-setup/fp-drain/animation-runtime")
assert (Path(os.environ["SHIP_HOME"]) / "saves/file3.json").exists()
end
set non-stop on
set pagination off
set confirm off
set print thread-events off
tbreak state_step_startup
run
python
stopped = [thread for thread in gdb.selected_inferior().threads() if thread.is_stopped()]
assert len(stopped) == 1, "Expected only the game-tick thread paused"
stopped[0].switch()
end
set variable gPortResetToTitleScreen = 1
tbreak state_step_title_screen
continue
python
stopped = [thread for thread in gdb.selected_inferior().threads() if thread.is_stopped()]
assert len(stopped) == 1, "Expected only the game-tick thread paused"
stopped[0].switch()
end
set variable TitleScreenNextState = NEXT_STATE_FILE_SELECT
set variable gGameStatusPtr->startupState = TITLE_STATE_EXIT
set variable gGameStatusPtr->titleScreenTimer = 0
tbreak filemenu_update
continue
python
stopped = [thread for thread in gdb.selected_inferior().threads() if thread.is_stopped()]
assert len(stopped) == 1, "Expected only the game-tick thread paused"
stopped[0].switch()
end
call fio_load_game(3)
set variable filemenu_menus[0]->state = FM_MAIN_SELECT_FILE
set variable filemenu_menus[0]->selected = 0
set variable filemenu_currentMenu = FILE_MENU_MAIN
call set_game_mode(GAME_MODE_END_FILE_SELECT)
return
tbreak state_step_world
continue
python
stopped = [thread for thread in gdb.selected_inferior().threads() if thread.is_stopped()]
assert len(stopped) == 1, "Expected only the game-tick thread paused"
stopped[0].switch()
end
call load_demo_battle(0)
return
tbreak initialize_battle
continue
python
stopped = [thread for thread in gdb.selected_inferior().threads() if thread.is_stopped()]
assert len(stopped) == 1, "Expected only the game-tick thread paused"
stopped[0].switch()
end
call fio_load_game(3)
tbreak calc_player_damage_enemy
continue
python
stopped = [thread for thread in gdb.selected_inferior().threads() if thread.is_stopped()]
assert len(stopped) == 1, "Expected only the game-tick thread paused"
stopped[0].switch()
end
python
source = Path("/workspace/PaperBoat/src/battle/dmg_player.c")
line = next(i + 1 for i, text in enumerate(source.read_text().splitlines()) if "if (player_team_is_ability_active(player, ABILITY_FP_DRAIN))" in text)
gdb.Breakpoint(f"{source}:{line}", temporary=True, internal=True)
end
continue
python
stopped = [thread for thread in gdb.selected_inferior().threads() if thread.is_stopped()]
assert len(stopped) == 1, "Expected only the game-tick thread paused"
stopped[0].switch()
end
set variable currentAttackDamage = 3
set variable targetDefense = 0
set variable target->curHP = 10
set variable partImmuneToElement = 0
set variable targetPart->flags &= ~ACTOR_PART_FLAG_DAMAGE_IMMUNE
set variable targetPart->targetFlags &= ~ACTOR_PART_TARGET_NO_DAMAGE
set variable gBattleStatus.flags1 &= ~BS_FLAGS1_TUTORIAL_BATTLE
set variable gBattleStatus.fpDrainCount = 0
set variable gPlayerData.curHP = 5
set variable gPlayerData.curFP = 2
set variable gPlayerData.curMaxFP = 10
# Permit the native state machine to reach turn end instead of ending demo playback.
set variable gGameStatusPtr->demoBattleFlags &= ~DEMO_BTL_FLAG_ENABLED
tbreak btl_substate_try_hpfp_recovery
continue
python
stopped = [thread for thread in gdb.selected_inferior().threads() if thread.is_stopped()]
assert len(stopped) == 1, "Expected only the game-tick thread paused"
stopped[0].switch()
end
python
assert int(gdb.parse_and_eval("gBattleStatus.fpDrainCount")) == 1
end
tbreak recover_update if effect->data.recover->type == 1 && effect->data.recover->lifetime >= 18
continue
python
stopped = [thread for thread in gdb.selected_inferior().threads() if thread.is_stopped()]
assert len(stopped) == 1, "Expected only the game-tick thread paused"
stopped[0].switch()
end
python
import json
report = {"effect_type":int(gdb.parse_and_eval("effect->data.recover->type")),
          "lifetime":int(gdb.parse_and_eval("effect->data.recover->lifetime")),
          "popup_amount":int(gdb.parse_and_eval("effect->data.recover->unk_40")),
          "fp_before":2,"fp_after":int(gdb.parse_and_eval("gPlayerData.curFP")),
          "counter_after":int(gdb.parse_and_eval("gBattleStatus.fpDrainCount")),
          "label_y":int(gdb.parse_and_eval("get_hud_element(HID_FPDrain)->renderPosY"))}
assert report["effect_type"] == 1 and report["popup_amount"] == 2
assert report["fp_after"] == 4 and report["counter_after"] == 0
assert int(gdb.parse_and_eval("get_hud_element(HID_FPDrain)->anim == &HES_FPDrain")) != 0
root=Path("/workspace/.paperboat-setup/fp-drain")
(root/"animation.pid").write_text(str(gdb.selected_inferior().pid))
(root/"animation.json").write_text(json.dumps(report,indent=2)+"\n")
# Keep the game-tick thread stopped while rendering threads finish presenting
# the preceding recovery frame. Capture before the native labels expire.
import subprocess, time
window = subprocess.check_output(["xdotool", "search", "--onlyvisible", "--pid", str(gdb.selected_inferior().pid)],text=True).splitlines()[0]
subprocess.run(["xdotool", "windowraise", window],check=True)
time.sleep(2)
subprocess.run(["import", "-window", "root", str(root/"animation.png")],check=True)
end
detach
