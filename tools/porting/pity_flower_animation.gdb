# Requires the disposable native world-acquisition save copied into this runtime.
python
import os
from pathlib import Path
assert Path(os.environ["SHIP_HOME"]).resolve() == Path("/workspace/.paperboat-setup/pity-flower/animation-runtime")
assert (Path(os.environ["SHIP_HOME"]) / "saves/file3.json").exists()
end
set pagination off
set confirm off
set print thread-events off
tbreak state_step_startup
run
set variable gPortResetToTitleScreen = 1
tbreak state_step_title_screen
continue
set variable TitleScreenNextState = NEXT_STATE_FILE_SELECT
set variable gGameStatusPtr->startupState = TITLE_STATE_EXIT
set variable gGameStatusPtr->titleScreenTimer = 0
tbreak filemenu_update
continue
call fio_load_game(3)
set variable filemenu_menus[0]->state = FM_MAIN_SELECT_FILE
set variable filemenu_menus[0]->selected = 0
set variable filemenu_currentMenu = FILE_MENU_MAIN
call set_game_mode(GAME_MODE_END_FILE_SELECT)
return
tbreak state_step_world
continue
call load_demo_battle(4)
return
tbreak calc_enemy_damage_target
continue
call fio_load_game(3)
set variable gBattleStatus.playerActor->curHP = 10
set variable gPlayerData.curHP = 10
set variable gPlayerData.curFP = 0
set variable gBattleStatus.curAttackDamage = 6
set variable gBattleStatus.playerActor->flags &= ~(ACTOR_FLAG_NO_DMG_APPLY | ACTOR_FLAG_NO_DMG_POPUP)
set variable gBattleStatus.playerActor->partsTable->flags &= ~ACTOR_PART_FLAG_DAMAGE_IMMUNE
set variable gBattleStatus.flags1 &= ~BS_FLAGS1_TUTORIAL_BATTLE
set variable gBattleStatus.curAttackElement |= DAMAGE_TYPE_UNBLOCKABLE
tbreak try_pity_flower
continue
set variable gRandSeed = 3
tbreak recover_update if effect->data.recover->type == 1 && effect->data.recover->lifetime >= 12
continue
p gPlayerData.curFP
p gPlayerData.curHP
p effect->data.recover[0]
p effect->data.recover[1]
set variable gGameStepDelayAmount = 127
set variable gGameStepDelayCount = 127
python
import json
from pathlib import Path
assert int(gdb.parse_and_eval("gPlayerData.curFP")) == 1
assert int(gdb.parse_and_eval("gPlayerData.curHP")) == 4
assert int(gdb.parse_and_eval("effect->data.recover->type")) == 1
assert int(gdb.parse_and_eval("effect->data.recover->unk_40")) == 1
Path("/workspace/.paperboat-setup/pity-flower/animation.pid").write_text(str(gdb.selected_inferior().pid))
Path("/workspace/.paperboat-setup/pity-flower/animation.json").write_text(json.dumps({"fp_after":int(gdb.parse_and_eval("gPlayerData.curFP")),"hp_after":int(gdb.parse_and_eval("gPlayerData.curHP")),"effect_type":int(gdb.parse_and_eval("effect->data.recover->type")),"lifetime":int(gdb.parse_and_eval("effect->data.recover->lifetime")),"popup_amount":int(gdb.parse_and_eval("effect->data.recover->unk_40"))},indent=2)+"\n")
end
detach
