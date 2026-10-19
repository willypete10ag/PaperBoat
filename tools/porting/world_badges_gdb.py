"""Native world pickup/persistence fixture, using the real file-select lifecycle.

WORLD_BADGES_LOAD_ONLY=1 reads the fixture slot in a fresh process.
WORLD_BADGES_VISUAL=1 prepares an independent world and detaches for keyboard
checks. SHIP_HOME is restricted to the two disposable directories below.
"""

import json
import os
from pathlib import Path

import gdb
import sys
if not os.environ.get('PORTING_FIXTURE_DIR'):
    raise RuntimeError('Missing PORTING_FIXTURE_DIR; use run_acceptance.sh')
sys.path.insert(0,os.environ['PORTING_FIXTURE_DIR'])
from fixture_support import *
validate_runtime()


def command(text):
    return gdb.execute(text, to_string=True)


def value(expression):
    return int(gdb.parse_and_eval(expression))


def assign(expression, number):
    command(f"set variable {expression} = {number}")


def stop_at(spec):
    return gdb.Breakpoint(spec, temporary=True, internal=True)


def run_checks():
    visual = os.environ.get("WORLD_BADGES_VISUAL", "0") == "1"
    load_only = os.environ.get("WORLD_BADGES_LOAD_ONLY", "0") == "1"
    runtime = Path(required_env('SHIP_HOME')).resolve()
    expected = str(fixture_path("pity-flower")) + "/" + (
        "world-visual-runtime" if visual else "acquisition-runtime")
    assert runtime == Path(expected)
    if not load_only:
        assert not (fixture_save()).exists(), "Refusing existing fixture save"
    for setting in ("pagination off", "confirm off", "print thread-events off"):
        command("set " + setting)
    stop_at("state_step_startup")
    command("run")
    assign("gPortResetToTitleScreen", 1)
    stop_at("state_step_title_screen")
    command("continue")
    # Use native title exit cleanup and let file-select allocate its HUD before
    # selecting the load path. Jumping from title straight into the world leaves
    # render overrides and curtain/window state behind.
    assign("TitleScreenNextState", value("NEXT_STATE_FILE_SELECT"))
    assign("gGameStatusPtr->startupState", value("TITLE_STATE_EXIT"))
    assign("gGameStatusPtr->titleScreenTimer", 0)
    stop_at("filemenu_update")
    command("continue")
    if not load_only:
        command("call clear_player_data()")
        command("call ttyd64_mode_select_file(TTYD64_MODE_TTYD64)")
        assign("gPlayerData.maxBP", 6)
        assign("gGameStatusPtr->areaID", 0)
        assign("gGameStatusPtr->mapID", 1)
        assign("gGameStatusPtr->entryID", 5)
        for axis, pos in (("x", 250), ("y", 0), ("z", 85)):
            assign(f"gGameStatusPtr->savedPos.{axis}", pos)
        assign("gCurrentSaveFile.globalBytes[0]", value("STORY_CH0_MET_INNKEEPER"))
        command("call set_global_flag(GF_Tutorial_SaveBlock)")
        command("call set_global_flag(GF_MAP_GoombaVillage)")
        command("call clear_global_flag(2046)")
        command("call clear_global_flag(2047)")
        command("call fio_save_game(3)")
    assert value("fio_load_game(3)") == 1
    assign("filemenu_menus[0]->state", value("FM_MAIN_SELECT_FILE"))
    assign("filemenu_menus[0]->selected", 0)
    assign("filemenu_currentMenu", value("FILE_MENU_MAIN"))
    command("call set_game_mode(GAME_MODE_END_FILE_SELECT)")
    command("return")
    stop_at("state_step_world")
    command("continue")
    assert value("gGameStatusPtr->areaID") == 0 and value("gGameStatusPtr->mapID") == 1
    assert value("gOverrideFlags & GLOBAL_OVERRIDES_DISABLE_RENDER_WORLD") == 0
    badge = value("ITEM_PITY_FLOWER")
    results = []

    def check(name, condition):
        assert condition, name
        results.append(name); record_check(name)

    def owned():
        return sum(value(f"gPlayerData.badges[{i}]") == badge for i in range(128))

    def equipped():
        return sum(value(f"gPlayerData.equippedBadges[{i}]") == badge for i in range(64))

    def entities():
        found = []
        for i in range(256):
            item = value(f"WorldItemEntities[{i}]")
            if item and value(f"((ItemEntity*){item})->itemID") == badge:
                found.append(item)
        return found

    def flags():
        return [value(f"get_global_flag({i})") for i in (2046, 2047)]

    check("normal-map-has-no-proof-pity-flowers", entities() == [])
    if not load_only:
        # Explicit debugger-only entities preserve native pickup/capacity
        # acceptance after removing proof content from BOTH ordinary modes.
        for x, flag in ((210, 2046), (170, 2047)):
            assert value(f"make_item_entity_nodelay(ITEM_PITY_FLOWER, {x}.0, 15.0, 150.0, ITEM_SPAWN_MODE_FIXED_NEVER_VANISH, {flag})") >= 0

    if visual:
        check("native-world-two-unclaimed-pickups", len(entities()) == 2 and owned() == 0 and flags() == [0, 0])
        Path(required_env('WORLD_BADGES_PID')).write_text(str(gdb.selected_inferior().pid))
        command("detach")
        return

    if load_only:
        check("fresh-world-load-ownership", owned() == 2)
        check("fresh-world-load-equipping-bp", equipped() == 2 and value("pause_get_total_equipped_bp_cost()") == 6)
        check("fresh-world-load-independent-flags", flags() == [1, 1])
        check("fresh-world-map-does-not-respawn-pickups", entities() == [])
    else:
        items = sorted(entities(), key=lambda p: value(f"((ItemEntity*){p})->boundVar"))
        check("debugger-spawns-two-test-only-badge-entities", len(items) == 2 and owned() == 0)
        check("independent-pickup-save-bits", [value(f"((ItemEntity*){p})->boundVar") for p in items] == [2046, 2047])
        check("initial-pickup-flags-clear", flags() == [0, 0])

        def tick():
            # Let the actual world update handle collision, pickup animation,
            # receipt, flagging and cleanup. A confirms the ordinary pickup UI.
            assign("gGameStatusPtr->pressedButtons[0]", value("BUTTON_A"))
            stop_at("state_step_world")
            command("continue")

        def receive(item, expected_count):
            command(f"set variable ((ItemEntity*){item})->flags |= ITEM_ENTITY_FLAG_AUTO_COLLECT")
            for _ in range(200):
                tick()
                if owned() == expected_count and value("isPickingUpItem") == 0:
                    break
            else:
                raise AssertionError("Native pickup did not finish")

        last_stand = value("ITEM_LAST_STAND")
        for i in range(128):
            assign(f"gPlayerData.badges[{i}]", last_stand)
        for item_name, expected, case in (
            ("ITEM_POWER_JUMP", 0, "full-inventory-protects-vanilla-field-badges"),
            ("ITEM_MUSHROOM", 1, "full-badge-inventory-does-not-block-consumables"),
        ):
            item_id = value(f"make_item_entity_nodelay({item_name}, 5000.0, 15.0, 150.0, ITEM_SPAWN_MODE_FIXED_SPAWN_ALWAYS, 0)")
            pointer = value(f"get_item_entity({item_id})")
            command(f"set variable ((ItemEntity*){pointer})->flags |= ITEM_ENTITY_FLAG_AUTO_COLLECT")
            check(case, value(f"test_item_player_collision((ItemEntity*){pointer})") == expected)
            command(f"call remove_item_entity_by_reference((ItemEntity*){pointer})")
        command(f"set variable ((ItemEntity*){items[0]})->flags |= ITEM_ENTITY_FLAG_AUTO_COLLECT")
        for _ in range(5):
            tick()
        check("full-badge-inventory-retains-field-pickups", owned() == 0 and len(entities()) == 2)
        check("full-inventory-does-not-consume-save-bit", flags() == [0, 0] and value("isPickingUpItem") == 0)
        assert value(f"remove_item({last_stand})") >= 0
        receive(items[0], 1)
        check("native-first-copy-received", owned() == 1 and len(entities()) == 1)
        check("first-copy-flag-only", flags() == [1, 0])
        assert value(f"remove_item({last_stand})") >= 0
        receive(items[1], 2)
        check("native-second-identical-copy-received", owned() == 2 and entities() == [])
        check("both-copy-flags-persist", flags() == [1, 1])
        for _ in range(126):
            assert value(f"remove_item({last_stand})") >= 0
        check("world-acquired-copies-equip-independently", value(f"pause_badges_try_equip({badge})") == 3
              and value(f"pause_badges_try_equip({badge})") == 3 and equipped() == 2)
        check("world-acquired-copies-cost-six-bp", value("pause_get_total_equipped_bp_cost()") == 6)
        command("call fio_save_game(3)")
        for _ in range(2):
            assert value(f"remove_item({badge})") >= 0
        command("call clear_global_flag(2046)")
        command("call clear_global_flag(2047)")
        assert value("fio_load_game(3)") == 1
        check("native-reload-ownership-and-equipment", owned() == 2 and equipped() == 2)
        check("native-reload-pickup-flags", flags() == [1, 1])
        command("call set_game_mode(GAME_MODE_ENTER_WORLD)")
        command("return")
        stop_at("state_step_world")
        command("continue")
        check("real-map-reload-no-respawn", entities() == [] and owned() == 2 and flags() == [1, 1])

    report = {"checks_passed": len(results), "checks": results, "fresh_process": load_only,
              "owned_debugger_spawned_pickup_copies": 2, "equipped_copies": 2,
              "bp_cost": 6, "pickup_flags": [2046, 2047], "setup": "Native map has no proof pickups; debugger injects two disposable test entities, then native pickup/FIO", "schema_changed": True}
    Path(required_env('WORLD_BADGES_RESULT')).write_text(json.dumps(report, indent=2) + "\n")
    print("WORLD_BADGES_RESULT=" + json.dumps(report))
    command("kill")


try:
    run_checks()
except Exception:
    import traceback
    traceback.print_exc()
    command("quit 1")
