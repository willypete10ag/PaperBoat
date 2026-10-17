"""Native Jumpman resources, copy/BP/save, command lock and attack integration.

JUMPMAN_LOAD_ONLY=1 reads the same fixture slot in a new game process.
Uses an exact disposable SHIP_HOME and refuses an existing writer save.
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
    runtime = Path(required_env('SHIP_HOME')).resolve()
    assert runtime == fixture_path('jumpman/runtime')
    load_only = os.environ.get("JUMPMAN_LOAD_ONLY", "0") == "1"
    if not load_only:
        assert not (fixture_save()).exists(), "Refusing existing fixture save"
    for setting in ("pagination off", "confirm off", "print thread-events off"):
        command("set " + setting)
    stop_at("state_step_startup")
    command("run")
    assign("gPortResetToTitleScreen", 1)
    stop_at("state_step_title_screen")
    command("continue")
    badge = value("ITEM_JUMPMAN")
    checks, attacks = [], []

    def check(name, condition):
        assert condition, name
        checks.append(name); record_check(name)

    def count(field):
        size = 128 if field == "badges" else 64
        return sum(value(f"gPlayerData.{field}[{i}]") == badge for i in range(size))

    def menu():
        command("call pause_badges_count_all()")
        command("call pause_badges_init_equipped_copies()")
        assign("gPauseBadgesCurrentTab", 0)
        command("call pause_badges_load_badges(0)")
        assign("gPauseBadgesLevel", 1)
        assign("gPauseBadgesShowNotEnoughBP", 0)
        assign("gPauseMenuCurrentTab", 2)

    def rows():
        return [bool(value(f"pause_badges_is_row_equipped({i})")) for i in range(3)]

    check("appended-native-item-and-move", badge == 366
          and value("gItemTable[ITEM_JUMPMAN].moveID") == 186)
    check("source-cost-two-bp", value("gMoveTable[MOVE_JUMPMAN].costBP") == 2)
    for suffix in ("", ".pal", ".disabled.pal"):
        check("resource-loaded" + (suffix or "-raster"),
              value(f'GameEngine_GetDataExact("icons/badge/Jumpman{suffix}")') != 0)
    check("native-name-and-description", value("load_message_to_buffer(gItemTable[ITEM_JUMPMAN].nameMsg)") != 0
          and value("load_message_to_buffer(gItemTable[ITEM_JUMPMAN].fullDescMsg)") != 0)
    check("entity-and-icon-identity", value("gItemEntityScripts[ITEM_JUMPMAN] == IES_Jumpman") != 0
          and value("gItemIconRasterOffsets[ITEM_JUMPMAN]") != 0)
    if not load_only:
        for field, size in (("badges", 128), ("equippedBadges", 64)):
            for i in range(size):
                assign(f"gPlayerData.{field}[{i}]", 0)
        check("unowned-rejected", value(f"pause_badges_try_equip({badge})") == 4)
        for _ in range(3):
            assert value(f"add_item({badge})") >= 0
        assign("gPlayerData.maxBP", 1)
        check("one-bp-insufficient", value(f"pause_badges_try_equip({badge})") == 1)
        assign("gPlayerData.maxBP", 2)
        check("two-bp-equips-one", value(f"pause_badges_try_equip({badge})") == 3)
        assign("gPlayerData.maxBP", 3)
        check("three-bp-rejects-second", value(f"pause_badges_try_equip({badge})") == 1)
        assign("gPlayerData.maxBP", 4)
        check("four-bp-equips-pair", value(f"pause_badges_try_equip({badge})") == 3
              and value("is_ability_active(ABILITY_JUMPMAN)") == 2)
        check("owned-third-copy-bp-limit", value(f"pause_badges_try_equip({badge})") == 1)
        menu()
        check("independent-menu-rows", rows() == [True, True, False])
        assign("gPauseBadgesSelectedIndex", 1)
        assign("gPausePressedButtons", value("BUTTON_A"))
        command("call pause_badges_handle_input(&gPausePanelBadges)")
        check("menu-removes-only-selected-copy", rows() == [True, False, False]
              and value("pause_get_total_equipped_bp_cost()") == 2)
        assign("gPauseBadgesSelectedIndex", 2)
        command("call pause_badges_handle_input(&gPausePanelBadges)")
        assign("gPausePressedButtons", 0)
        check("menu-equips-third-copy-independently", rows() == [True, False, True]
              and value("pause_get_total_equipped_bp_cost()") == 4)
        assign("gPlayerData.curPartner", value("PARTNER_BOW"))
        assign("gPlayerData.partners[PARTNER_BOW].enabled", 1)
        command("call fio_save_game(3)")
        saved = json.loads((fixture_save()).read_text())["player"]
        check("native-save-copies", saved["badges"].count(badge) == 3
              and saved["equippedBadges"].count(badge) == 2)
    assert value("fio_load_game(3)") == 1
    check("native-load-copies-bp-ability", count("badges") == 3 and count("equippedBadges") == 2
          and value("pause_get_total_equipped_bp_cost()") == 4
          and value("is_ability_active(ABILITY_JUMPMAN)") == 2)
    menu()
    check("loaded-row-reconstruction", rows() == [True, True, False])

    start_source = source_path('src/battle/states/start_battle.c')
    start_lines = start_source.read_text().splitlines()
    init = next(i + 1 for i, line in enumerate(start_lines) if "battleStatus->enabledMenusFlags = -1" in line)
    initialized = next(i + 1 for i, line in enumerate(start_lines) if i + 1 > init and "battleStatus->itemUsesLeft = 0" in line)
    command("call load_demo_battle(1)")
    command("return")
    stop_at(f"{start_source}:{init}")
    command("continue")
    assert value("fio_load_game(3)") == 1
    stop_at(f"{start_source}:{initialized}")
    command("continue")
    check("saved-copies-disable-only-hammer-command", (value("battleStatus->enabledMenusFlags") & 0xFFFF) == 0xFFFD)
    command("set scheduler-locking on")
    init_pc = gdb.decode_line(f"{start_source}:{init}")[1][0].pc
    mask_end = gdb.Breakpoint(f"{start_source}:{initialized}", internal=True)
    for n, mask in ((0, 0xFFFF), (1, 0xFFFD), (3, 0xFFFD)):
        for i in range(64):
            assign(f"gPlayerData.equippedBadges[{i}]", badge if i < n else 0)
        command(f"jump *{init_pc}")
        check(f"command-mask-{n}-copies", (value("battleStatus->enabledMenusFlags") & 0xFFFF) == mask)
    assert value("fio_load_game(3)") == 1
    command(f"jump *{init_pc}")
    mask_end.delete()
    command("set scheduler-locking off")
    stop_at("calc_player_damage_enemy")
    command("continue")
    source = source_path('src/battle/dmg_player.c')
    lines = source.read_text().splitlines()
    boost = next(i + 1 for i, line in enumerate(lines) if "selectedMoveID != MOVE_FIRST_STRIKE_HAMMER" in line)
    boosted = next(i + 1 for i, line in enumerate(lines) if i + 1 > boost and "if (player_team_is_ability_active(player, ABILITY_BERSERKER))" in line)
    hp = next(i + 1 for i, line in enumerate(lines) if "target->curHP -= currentAttackDamage" in line)
    applied = next(i + 1 for i, line in enumerate(lines) if i + 1 > hp and "target->lastDamageTaken =" in line)
    stop_at(f"{source}:{boost}")
    command("continue")
    command("set scheduler-locking on")
    boost_pc = gdb.decode_line(f"{source}:{boost}")[1][0].pc
    end = gdb.Breakpoint(f"{source}:{boosted}", internal=True)
    cases = [
        ("unequipped", 0, "MOVE_JUMP1", 3),
        ("one-copy", 1, "MOVE_JUMP1", 4),
        ("two-copies", 2, "MOVE_JUMP1", 5),
        ("three-copies", 3, "MOVE_JUMP1", 6),
        ("jump-first-strike-gets-bonus", 2, "MOVE_FIRST_STRIKE_JUMP", 5),
        ("hammer-first-strike-excluded", 2, "MOVE_FIRST_STRIKE_HAMMER", 3),
        ("forced-normal-hammer-matches-upstream-hook", 2, "MOVE_HAMMER1", 5),
    ]
    for name, n, move, expected in cases:
        for i in range(64):
            assign(f"gPlayerData.equippedBadges[{i}]", badge if i < n else 0)
        assign("currentAttackDamage", 3)
        assign("battleStatus->selectedMoveID", value(move))
        command(f"jump *{boost_pc}")
        actual = value("currentAttackDamage")
        check(name, actual == expected)
        attacks.append({"case": name, "copies": n, "selected_move": move, "input": 3, "observed": actual})
    assert value("fio_load_game(3)") == 1
    assign("currentAttackDamage", 3)
    assign("battleStatus->selectedMoveID", value("MOVE_JUMP1"))
    command(f"jump *{boost_pc}")
    check("saved-copies-boost-compiled-attack", value("currentAttackDamage") == 5)
    end.delete()
    assign("target->curHP", 10)
    assign("targetDefense", 0)
    assign("player->attackBoost", 0)
    assign("battleStatus->turboChargeTurnsLeft", 0)
    assign("partImmuneToElement", 0)
    command("set variable targetPart->flags &= ~ACTOR_PART_FLAG_DAMAGE_IMMUNE")
    command("set variable targetPart->targetFlags &= ~ACTOR_PART_TARGET_NO_DAMAGE")
    command("set variable gBattleStatus.flags1 &= ~BS_FLAGS1_TUTORIAL_BATTLE")
    stop_at(f"{source}:{applied}")
    command("continue")
    check("saved-copies-native-enemy-hp-application", value("target->curHP") == 5
          and value("battleStatus->lastAttackDamage") == 5)
    # Exercise the real command-wheel consumer after the attack fixture. Give
    # this disposable save a basic hammer so the entry exists for the check.
    assign("gPlayerData.hammerLevel", 0)
    assign("gBattleSubState", 302)  # menu_player.c: BTL_SUBSTATE_CREATE_MAIN_MENU.
    command("call btl_state_update_player_menu()")
    options = {value(f"WheelOptionSubmenu[{i}]"): {
        "enabled": bool(value(f"WheelOptionEnabled[{i}]")),
        "error": value(f"WheelOptionError[{i}]")
    } for i in range(value("WheelOptionCount"))}
    hammer = options[value("BTL_MENU_TYPE_SMASH")]
    check("native-command-wheel-disables-hammer", not hammer["enabled"]
          and hammer["error"] == value("BTL_MSG_CANT_SELECT_NOW"))
    check("native-command-wheel-retains-jump", options[value("BTL_MENU_TYPE_JUMP")]["enabled"])
    report = {"checks_passed": len(checks), "fresh_process": load_only, "checks": checks,
              "native_item_id": badge, "native_move_id": 186, "bp_per_copy": 2,
              "command_mask": "0xFFFD", "command_wheel": options, "attack_branches": attacks,
              "native_hit": {"copies_loaded": 2, "controlled_base_damage": 3,
                             "damage_applied": 5, "enemy_hp_before": 10, "enemy_hp_after": 5}}
    Path(required_env('JUMPMAN_RESULT')).write_text(json.dumps(report, indent=2) + "\n")
    print("JUMPMAN_RESULT=" + json.dumps(report))
    command("kill")


try:
    run_checks()
except Exception:
    import traceback
    traceback.print_exc()
    command("quit 1")
