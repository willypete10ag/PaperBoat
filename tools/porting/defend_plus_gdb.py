"""Defend Plus copy/BP/save checks and native battle-defense integration.

DEFEND_PLUS_LOAD_ONLY=1 reads the fixture save in a fresh process.
DEFEND_PLUS_BLOCKED=1 forces native blocking for the final saved-copy hit.
All state/saves belong to the exact disposable runtime below.
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
    assert runtime == fixture_path('defend-plus/runtime')
    load_only = os.environ.get("DEFEND_PLUS_LOAD_ONLY", "0") == "1"
    blocked = os.environ.get("DEFEND_PLUS_BLOCKED", "0") == "1"
    final_input = int(os.environ.get("DEFEND_PLUS_INPUT", "6"))
    assert final_input in (1, 6) and not (blocked and final_input == 1)
    if not load_only:
        assert not (fixture_save()).exists(), "Refusing existing fixture save"
    for setting in ("pagination off", "confirm off", "print thread-events off"):
        command("set " + setting)
    stop_at("state_step_startup")
    command("run")
    assign("gPortResetToTitleScreen", 1)
    stop_at("state_step_title_screen")
    command("continue")
    command("call ttyd64_mode_select_file(TTYD64_MODE_TTYD64)")
    variants = [value(f"ITEM_DEFEND_PLUS_{suffix}") for suffix in ("A", "X", "Y")]
    badge = variants[0]
    checks, branches = [], []

    def check(name, condition):
        assert condition, name
        checks.append(name); record_check(name)

    def clear():
        for field, size in (("badges", 128), ("equippedBadges", 64)):
            for i in range(size):
                assign(f"gPlayerData.{field}[{i}]", 0)
        assign("gPlayerData.maxBP", 20)

    def copies(field, item=badge):
        size = 128 if field == "badges" else 64
        return sum(value(f"gPlayerData.{field}[{i}]") == item for i in range(size))

    def menu():
        command("call pause_badges_count_all()")
        command("call pause_badges_init_equipped_copies()")
        assign("gPauseBadgesCurrentTab", 0)
        command("call pause_badges_load_badges(0)")
        assign("gPauseBadgesLevel", 1)
        assign("gPauseBadgesShowNotEnoughBP", 0)
        assign("gPauseMenuCurrentTab", 2)

    def rows():
        return [bool(value(f"pause_badges_is_row_equipped({i})"))
                for i in range(value("gPauseBadgesNumItems"))]

    def press(index):
        assign("gPauseBadgesSelectedIndex", index)
        assign("gPausePressedButtons", value("BUTTON_A"))
        command("call pause_badges_handle_input(&gPausePanelBadges)")
        assign("gPausePressedButtons", 0)

    check("source-cost-five-bp", value("get_move_bp_cost(MOVE_DEFEND_PLUS)") == 5)
    check("all-native-variants-share-validated-effect", all(
        value(f"gItemTable[{item}].moveID") == value("MOVE_DEFEND_PLUS") for item in variants))
    if not load_only:
        for suffix, item in zip(("A", "X", "Y"), variants):
            clear()
            assert value(f"add_item({item})") >= 0 and value(f"add_item({item})") >= 0
            check("same-id-two-copies-equip-" + suffix, value(f"pause_badges_try_equip({item})") == 3
                  and value(f"pause_badges_try_equip({item})") == 3)
            check("copies-count-and-cost-" + suffix, copies("equippedBadges", item) == 2
                  and value("is_ability_active(ABILITY_DEFEND_PLUS)") == 2
                  and value("pause_get_total_equipped_bp_cost()") == 10)
            check("unowned-extra-copy-rejected-" + suffix, value(f"pause_badges_try_equip({item})") == 4)
            check("remove-one-copy-releases-five-bp-" + suffix,
                  value(f"pause_badges_try_remove({item})") == 1
                  and value("pause_get_total_equipped_bp_cost()") == 5)
        clear()
        for item in variants:
            assert value(f"add_item({item})") >= 0
            assert value(f"pause_badges_try_equip({item})") == 3
        check("distinct-variant-stack-preserved", value("is_ability_active(ABILITY_DEFEND_PLUS)") == 3
              and value("pause_get_total_equipped_bp_cost()") == 15)
        clear()
        other = value("ITEM_SPEEDY_SPIN")
        assert value(f"add_item({other})") >= 0 and value(f"add_item({other})") >= 0
        check("unmigrated-effect-still-single-equip", value(f"pause_badges_try_equip({other})") == 3
              and value(f"pause_badges_try_equip({other})") == 0)
        clear()
        for _ in range(3):
            assert value(f"add_item({badge})") >= 0
        assign("gPlayerData.maxBP", 4)
        check("four-bp-insufficient", value(f"pause_badges_try_equip({badge})") == 1)
        assign("gPlayerData.maxBP", 5)
        check("five-bp-equips-one", value(f"pause_badges_try_equip({badge})") == 3)
        assign("gPlayerData.maxBP", 9)
        check("nine-bp-rejects-second", value(f"pause_badges_try_equip({badge})") == 1)
        assign("gPlayerData.maxBP", 10)
        check("ten-bp-equips-pair", value(f"pause_badges_try_equip({badge})") == 3)
        check("owned-third-copy-bp-limit", value(f"pause_badges_try_equip({badge})") == 1)
        menu()
        check("independent-owned-copy-rows", rows() == [True, True, False])
        press(0)
        check("menu-removes-only-selected-copy", rows() == [False, True, False]
              and value("pause_get_total_equipped_bp_cost()") == 5)
        press(2)
        check("menu-equips-third-copy", rows() == [False, True, True]
              and value("pause_get_total_equipped_bp_cost()") == 10)
        command("call fio_save_game(3)")
        saved = json.loads((fixture_save()).read_text())["player"]
        check("native-save-copies-and-cost", saved["badges"].count(badge) == 3
              and saved["equippedBadges"].count(badge) == 2)
        clear()
    assert value("fio_load_game(3)") == 1
    check("native-load-copies-and-bp", copies("badges") == 3 and copies("equippedBadges") == 2
          and value("pause_get_total_equipped_bp_cost()") == 10)
    menu()
    check("loaded-menu-reconstructs-copy-rows", rows() == [True, True, False])
    command("call load_demo_battle(4)")
    command("return")
    stop_at("calc_enemy_damage_target")
    command("continue")
    command("call ttyd64_mode_select_file(TTYD64_MODE_TTYD64)")
    source = source_path('src/battle/1A5830.c')
    lines = source.read_text().splitlines()
    start = next(i + 1 for i, line in enumerate(lines) if "isPlayer = actorClass" in line)
    end = next(i + 1 for i, line in enumerate(lines) if i + 1 > start and "switch (actorClass)" in line)
    hp = next(i + 1 for i, line in enumerate(lines) if "gPlayerData.curHP = target->curHP" in line)
    applied = next(i + 1 for i, line in enumerate(lines) if i + 1 > hp and "if (gBattleStatus.flags1" in line)
    stop_at(f"{source}:{start}")
    command("continue")
    command("set scheduler-locking on")
    start_pc = gdb.decode_line(f"{source}:{start}")[1][0].pc
    stop = gdb.Breakpoint(f"{source}:{end}", internal=True)

    def defend(items, damage=6, actor_class=0, hp=10):
        for i in range(64):
            assign(f"gPlayerData.equippedBadges[{i}]", items[i] if i < len(items) else 0)
        assign("damage", damage)
        assign("actorClass", actor_class)
        assign("target->curHP", hp)
        command(f"jump *{start_pc}")
        return value("damage")

    cases = [
        ("unequipped", [], 6, 0, 10, 6),
        ("one-copy", [badge], 6, 0, 10, 5),
        ("two-identical-copies", [badge] * 2, 6, 0, 10, 4),
        ("three-identical-copies", [badge] * 3, 6, 0, 10, 3),
        ("mixed-variant-copies", variants, 6, 0, 10, 3),
        ("six-copies-reach-zero", [badge] * 6, 6, 0, 10, 0),
        ("low-input-before-final-clamp", [badge] * 2, 1, 0, 10, -1),
        ("non-player-defense-branch", [badge] * 2, 6, 0x200, 10, 6),
        ("defend-before-last-stand", [badge] * 2 + [value("ITEM_LAST_STAND")] * 2, 6, 0, 5, 1),
    ]
    for name, items, incoming, actor_class, cur_hp, expected in cases:
        actual = defend(items, incoming, actor_class, cur_hp)
        check(name, actual == expected)
        branches.append({"case": name, "items": items, "input": incoming, "observed": actual})
    # Load the real menu-equipped pair; do not inject equipped entries for the
    # final native HP application. Damage is controlled after defense at 6.
    assert value("fio_load_game(3)") == 1
    assign("damage", final_input)
    assign("actorClass", 0)
    assign("target->curHP", 10)
    assign("gPlayerData.curHP", 10)
    command(f"jump *{start_pc}")
    check("saved-copies-mitigate-native-damage", value("damage") == (4 if final_input == 6 else -1))
    stop.delete()
    assign("target->debuff", 0)
    assign("target->stoneStatus", 0)
    command("set variable target->flags &= ~ACTOR_FLAG_NO_DMG_APPLY")
    command("set variable targetPart->flags &= ~ACTOR_PART_FLAG_DAMAGE_IMMUNE")
    command("set variable gBattleStatus.flags1 &= ~BS_FLAGS1_TUTORIAL_BATTLE")
    if blocked:
        command("set variable battleStatus->curAttackElement &= ~DAMAGE_TYPE_UNBLOCKABLE")
        stop_at("check_block_input")
        command("continue")
        command("return 1")
    else:
        command("set variable battleStatus->curAttackElement |= DAMAGE_TYPE_UNBLOCKABLE")
    stop_at(f"{source}:{applied}")
    command("continue")
    expected_hp = 10 if final_input == 1 else (7 if blocked else 6)
    check("saved-copies-native-hp-application", value("gPlayerData.curHP") == expected_hp
          and value("target->curHP") == expected_hp)
    report = {"checks_passed": len(checks), "fresh_process": load_only, "checks": checks,
              "bp_per_copy": 5, "native_variants": variants, "defense_branches": branches,
              "battle_hit": {"copies_loaded": 2, "input_after_defense": final_input,
                             "blocked": blocked, "damage_applied": 10 - expected_hp,
                             "hp_before": 10, "hp_after": expected_hp}}
    Path(required_env('DEFEND_PLUS_RESULT')).write_text(json.dumps(report, indent=2) + "\n")
    print("DEFEND_PLUS_RESULT=" + json.dumps(report))
    command("kill")


try:
    run_checks()
except Exception:
    import traceback
    traceback.print_exc()
    command("quit 1")
