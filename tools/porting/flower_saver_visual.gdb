# Strict fixture save; native title/file-select cleanup before keyboard menus.
python
import os
from pathlib import Path
runtime = Path(os.environ["SHIP_HOME"]).resolve()
assert runtime == Path("/workspace/.paperboat-setup/flower-saver/visual-runtime")
assert (runtime / "saves/file3.json").exists()
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
set variable gCurrentSaveFile.globalBytes[0] = -126
set variable gCurrentSaveFile.areaID = 0
set variable gCurrentSaveFile.mapID = 1
set variable gCurrentSaveFile.entryID = 5
set variable gCurrentSaveFile.savePos.x = 250
set variable gCurrentSaveFile.savePos.y = 0
set variable gCurrentSaveFile.savePos.z = 85
set variable filemenu_menus[0]->state = FM_MAIN_SELECT_FILE
set variable filemenu_menus[0]->selected = 0
set variable filemenu_currentMenu = FILE_MENU_MAIN
call set_game_mode(GAME_MODE_END_FILE_SELECT)
return
tbreak state_step_world
continue
python
import json
out = Path("/workspace/.paperboat-setup/flower-saver")
pid = gdb.selected_inferior().pid
(out / "visual.pid").write_text(str(pid))
assert int(gdb.parse_and_eval("gPlayerData.maxBP")) == 8
assert int(gdb.parse_and_eval("is_ability_active(ABILITY_FLOWER_SAVER)")) == 2
(out / "visual-state.json").write_text(json.dumps({"loaded_copies":2, "max_bp":8,
    "bp_per_copy":int(gdb.parse_and_eval("gMoveTable[MOVE_FLOWER_SAVER].costBP"))}, indent=2) + "\n")
end
detach
