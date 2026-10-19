# Strict fixture save; native title/file-select cleanup before keyboard menus.
python
import sys
from pathlib import Path
import os
if not os.environ.get('PORTING_FIXTURE_DIR'):
    raise RuntimeError('Missing PORTING_FIXTURE_DIR; use run_acceptance.sh')
sys.path.insert(0,os.environ['PORTING_FIXTURE_DIR'])
from fixture_support import *
validate_runtime()
import os
from pathlib import Path
runtime = Path(required_env('SHIP_HOME')).resolve()
assert runtime == fixture_path('flower-saver/visual-runtime')
assert (fixture_save()).exists()
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
out = fixture_path('flower-saver')
pid = gdb.selected_inferior().pid
(out / "visual.pid").write_text(str(pid))
assert int(gdb.parse_and_eval("gPlayerData.maxBP")) == 8
assert int(gdb.parse_and_eval("is_ability_active(ABILITY_FLOWER_SAVER)")) == 2
assert int(gdb.parse_and_eval("get_move_bp_cost(MOVE_FLOWER_SAVER)")) == 4
record_check('flower-saver-loaded-copies-and-bp', 'controlled_api_or_state', 'Native fixture save load and debugger map/progression setup; captures require separate visual inspection.')
Path(required_env('FLOWER_SAVER_RESULT')).write_text(json.dumps({"loaded_copies":2, "max_bp":8,
    "bp_per_copy":int(gdb.parse_and_eval("get_move_bp_cost(MOVE_FLOWER_SAVER)"))}, indent=2) + "\n")
end
detach
