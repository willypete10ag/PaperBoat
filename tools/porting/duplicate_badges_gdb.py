"""Native inventory/menu/save regression checks in an isolated game process.

Run with GDB from the asset directory. SHIP_HOME must be a disposable directory;
DUPLICATE_BADGES_RESULT names the numeric report. Uses save slot 3 there only.
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


def run_checks():
    runtime = Path(required_env('SHIP_HOME')).resolve()
    assert runtime == fixture_path('duplicate-badges/runtime')
    load_only = os.environ.get("DUPLICATE_BADGES_LOAD_ONLY", "0") == "1"
    if not load_only:
        assert not (fixture_save()).exists(), "Use a fresh disposable save directory"
    command("set pagination off")
    command("set confirm off")
    command("set print thread-events off")
    gdb.Breakpoint("state_step_startup", temporary=True, internal=True)
    command("run")
    assign("gPortResetToTitleScreen", 1)
    gdb.Breakpoint("state_step_title_screen", temporary=True, internal=True)
    command("continue")
    command("call ttyd64_mode_select_file(TTYD64_MODE_TTYD64)")
    badge = value("ITEM_LAST_STAND")
    other = value("ITEM_SPEEDY_SPIN")
    cost = value("get_move_bp_cost(MOVE_LAST_STAND)")
    assert cost == 1
    results = []

    def check(name, condition):
        assert condition, name
        results.append(name); record_check(name)

    def clear():
        for field, size in [("badges", 128), ("equippedBadges", 64)]:
            for index in range(size):
                assign(f"gPlayerData.{field}[{index}]", 0)
        assign("gPlayerData.maxBP", 127)

    def count(field, item=badge):
        size = 128 if field == "badges" else 64
        return sum(value(f"gPlayerData.{field}[{index}]") == item for index in range(size))

    def grant(item=badge):
        return value(f"add_item({item})")

    def equip(item=badge):
        return value(f"pause_badges_try_equip({item})")

    def setup_menu():
        command("call pause_badges_count_all()")
        command("call pause_badges_init_equipped_copies()")
        assign("gPauseBadgesCurrentTab", 0)
        command("call pause_badges_load_badges(0)")
        assign("gPauseBadgesLevel", 1)
        assign("gPauseBadgesShowNotEnoughBP", 0)
        assign("gPauseMenuCurrentTab", 2)

    def press(row):
        assign("gPauseBadgesSelectedIndex", row)
        assign("gPauseBadgesCurrentPage", row // 8)
        assign("gPausePressedButtons", value("BUTTON_A"))
        command("call pause_badges_handle_input(&gPausePanelBadges)")
        assign("gPausePressedButtons", 0)

    def rows():
        return [bool(value(f"pause_badges_is_row_equipped({i})"))
                for i in range(value("gPauseBadgesNumItems"))]

    if load_only:
        check("fresh-process-load", value("fio_load_game(3)") == 1)
        check("fresh-process-owned-count", count("badges") == 3)
        check("fresh-process-equipped-count", count("equippedBadges") == 2)
        check("fresh-process-bp", value("pause_get_total_equipped_bp_cost()") == 2 * cost)
        check("fresh-process-ability-count", value("is_ability_active(ABILITY_LAST_STAND)") == 2)
        setup_menu()
        check("fresh-process-row-reconstruction", rows() == [True, True, False])
        press(2)
        check("fresh-process-equip-remaining-copy", rows() == [True, True, True]
              and count("equippedBadges") == 3)

        # Enter a real attack, then load the saved copies through the native
        # reader. Do not inject equipped entries into this battle fixture.
        command("call load_demo_battle(4)")
        command("return")
        gdb.Breakpoint("calc_enemy_damage_target", temporary=True, internal=True)
        command("continue")
        assert value("fio_load_game(3)") == 1
        assign("gPlayerData.curHP", 5)
        assign("gBattleStatus.curAttackDamage", 6)
        command("set variable gBattleStatus.curAttackElement |= DAMAGE_TYPE_UNBLOCKABLE")
        command("set variable gBattleStatus.flags1 &= ~BS_FLAGS1_TUTORIAL_BATTLE")
        command("set variable gBattleStatus.playerActor->flags &= ~ACTOR_FLAG_NO_DMG_APPLY")
        source = source_path('src/battle/1A5830.c').read_text().splitlines()
        hp_line = next(i + 1 for i, line in enumerate(source) if "gPlayerData.curHP = target->curHP" in line)
        after_hp = next(i + 1 for i, line in enumerate(source) if i + 1 > hp_line and "if (gBattleStatus.flags1" in line)
        gdb.Breakpoint(f"{source_path('src/battle/1A5830.c')}:{after_hp}", temporary=True, internal=True)
        command("continue")
        check("fresh-load-to-native-battle-hit", count("equippedBadges") == 2
              and value("gBattleStatus.lastAttackDamage") == 2 and value("gPlayerData.curHP") == 3)
        Path(required_env('DUPLICATE_BADGES_RESULT')).write_text(
            json.dumps({"checks_passed": len(results), "checks": results, "fresh_process": True,
                        "battle_hit": {"loaded_copies": 2, "attack_damage": 6,
                                       "damage_applied": 2, "hp_before": 5, "hp_after": 3}}, indent=2) + "\n")
        print("DUPLICATE_BADGES_FRESH_LOAD=" + json.dumps(results))
        command("kill")
        return

    clear()
    check("unowned-equip-rejected", equip() == 4 and count("equippedBadges") == 0)
    check("duplicate-acquisition", grant() >= 0 and grant() >= 0 and count("badges") == 2)
    check("two-copies-equip", equip() == 3 and equip() == 3 and count("equippedBadges") == 2)
    check("per-copy-bp", value("pause_get_total_equipped_bp_cost()") == 2 * cost)
    check("cannot-equip-unowned-third-copy", equip() == 4 and count("equippedBadges") == 2)
    grant()
    assign("gPlayerData.maxBP", 2 * cost)
    check("bp-limit-rejects-owned-third-copy", equip() == 1 and count("equippedBadges") == 2)
    check("remove-single-equipped-copy", value(f"pause_badges_try_remove({badge})") > 0 and count("equippedBadges") == 1)
    check("bp-released-per-copy", value("pause_get_total_equipped_bp_cost()") == cost)
    check("re-equip-after-removal", equip() == 3 and count("equippedBadges") == 2)
    check("inventory-removal-unequips-one", value(f"remove_item({badge})") >= 0
          and count("badges") == 2 and count("equippedBadges") == 1)
    assign("gPlayerData.unused_288", 77)
    check("missing-equipped-removal-safe", value(f"pause_badges_try_remove({other})") == 0
          and count("equippedBadges") == 1 and value("gPlayerData.unused_288") == 77)
    check("missing-inventory-removal-safe", value(f"remove_item({other})") == -1
          and count("equippedBadges") == 1)
    check("invalid-remove-safe", value("pause_badges_try_remove(32766)") == 0
          and value("pause_badges_try_remove(0)") == 0 and count("equippedBadges") == 1)

    clear()
    grant(other)
    grant(other)
    check("unmigrated-badge-keeps-single-equip", equip(other) == 3 and equip(other) == 0
          and count("equippedBadges", other) == 1)
    setup_menu()
    press(1)
    check("unmigrated-copy-does-not-toggle-other-row", count("equippedBadges", other) == 1 and rows() == [True, False])

    clear()
    power_a = value("ITEM_POWER_PLUS_A")
    power_b = value("ITEM_POWER_PLUS_B")
    grant(power_a)
    grant(power_b)
    check("legacy-distinct-id-stack-equip", equip(power_a) == 3 and equip(power_b) == 3)
    check("legacy-distinct-id-stack-bp", value("pause_get_total_equipped_bp_cost()")
          == 2 * value("get_move_bp_cost(MOVE_POWER_PLUS)"))

    clear()
    for _ in range(3):
        grant()
    setup_menu()
    press(2)
    check("equip-selected-third-row", rows() == [False, False, True] and count("equippedBadges") == 1)
    press(0)
    check("equip-independent-first-row", rows() == [True, False, True] and count("equippedBadges") == 2)
    press(2)
    check("unequip-only-selected-third-row", rows() == [True, False, False] and count("equippedBadges") == 1)
    press(2)
    assign("gPlayerData.maxBP", 2 * cost)
    press(1)
    check("menu-bp-error-preserves-other-copies", value("gPauseBadgesShowNotEnoughBP") == 1
          and rows() == [True, False, True] and count("equippedBadges") == 2)
    assign("gPlayerData.maxBP", 127)
    assign("gPauseBadgesShowNotEnoughBP", 0)
    assign("gPauseBadgesCurrentTab", 1)
    command("call pause_badges_load_badges(1)")
    check("active-tab-has-two-copy-rows", value("gPauseBadgesNumItems") == 2 and rows() == [True, True])
    press(1)
    check("active-row-removal-independent", rows() == [True, False] and count("equippedBadges") == 1)
    press(1)
    check("active-row-re-equip-independent", rows() == [True, True] and count("equippedBadges") == 2)
    assign("gPauseBadgesCurrentTab", 0)
    command("call pause_badges_load_badges(0)")
    check("all-tab-preserves-copy-selection", rows() == [True, False, True])

    command("call fio_save_game(3)")
    saved = json.loads((fixture_save()).read_text())
    check("json-preserves-owned-and-equipped-multiplicity",
          saved["player"]["badges"].count(badge) == 3
          and saved["player"]["equippedBadges"].count(badge) == 2)
    clear()
    check("native-save-load-round-trip", value("fio_load_game(3)") == 1
          and count("badges") == 3 and count("equippedBadges") == 2
          and value("pause_get_total_equipped_bp_cost()") == 2 * cost)
    setup_menu()
    check("reopened-menu-reconstructs-two-copies", rows() == [True, True, False])

    # Preserve the existing negative-cost removal protection using a temporary
    # cost fixture, with another badge offsetting the bonus BP.
    clear()
    grant()
    grant(other)
    assign("get_move_bp_cost(MOVE_LAST_STAND)", -1)
    assign("gPlayerData.maxBP", 0)
    check("negative-bp-equip-fixture", equip() == 3 and equip(other) == 3)
    check("negative-bp-removal-protection", value(f"pause_badges_try_remove({badge})") == -1
          and count("equippedBadges") == 1)
    assign("get_move_bp_cost(MOVE_LAST_STAND)", cost)

    clear()
    assign("gPlayerData.badges[11]", badge)
    assign("gPlayerData.badges[127]", badge)
    assign("gPlayerData.equippedBadges[63]", badge)
    setup_menu()
    press(1)
    check("sparse-arrays-sort-and-match-copies", rows() == [True, True] and count("equippedBadges") == 2)
    clear()
    for _ in range(9):
        grant()
    setup_menu()
    press(8)
    check("second-page-copy-toggles-independently", rows() == [False] * 8 + [True]
          and count("equippedBadges") == 1)

    clear()
    for _ in range(128):
        assert grant() >= 0
    check("full-inventory-rejects-extra-copy", grant() == -1 and count("badges") == 128)
    assign("get_move_bp_cost(MOVE_LAST_STAND)", 0)
    for _ in range(64):
        assert equip() == 3
    check("full-equipped-array-rejects-extra-copy", equip() == 2 and count("equippedBadges") == 64)
    assign("get_move_bp_cost(MOVE_LAST_STAND)", cost)
    clear()
    setup_menu()
    check("empty-menu-standin-not-equipped", value("gPauseBadgesItemIds[0]") == 32766 and rows() == [False])
    report = {"checks_passed": len(results), "checks": results,
              "saved_owned_copies": 3, "saved_equipped_copies": 2,
              "stackable_badge": "Last Stand", "schema_changed": False}
    Path(required_env('DUPLICATE_BADGES_RESULT')).write_text(json.dumps(report, indent=2) + "\n")
    print("DUPLICATE_BADGES_RESULT=" + json.dumps(report))
    command("kill")


try:
    run_checks()
except Exception:
    import traceback
    traceback.print_exc()
    gdb.execute("quit 1")
