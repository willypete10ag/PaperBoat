"""Native Flower Saver copies/save and move-menu/payment agreement.

Strict disposable runtime. FLOWER_SAVER_BASELINE=1 is read-only observation of
the preceding FP Drain executable; writer mode refuses an existing slot3.
"""

import json
import os
from pathlib import Path
import struct
import gdb
import sys
if not os.environ.get('PORTING_FIXTURE_DIR'):
    raise RuntimeError('Missing PORTING_FIXTURE_DIR; use run_acceptance.sh')
sys.path.insert(0,os.environ['PORTING_FIXTURE_DIR'])
from fixture_support import *
validate_runtime()


def command(text):
    return gdb.execute(text, to_string=True)


def value(text):
    return int(gdb.parse_and_eval(text))


def assign(text, number):
    command(f"set variable {text} = {number}")


def stop_at(text):
    return gdb.Breakpoint(text, temporary=True, internal=True)


class ChooseItems(gdb.Breakpoint):
    def __init__(self):
        super().__init__("btl_main_menu_update", internal=True)

    def stop(self):
        assert gdb.newest_frame().older().name() == "btl_state_update_player_menu"
        command("return 1")
        return False


def run_checks():
    runtime = Path(required_env('SHIP_HOME')).resolve()
    assert runtime == fixture_path('flower-saver/' + ('vanilla-runtime' if os.environ.get('FLOWER_SAVER_BASELINE') == '1' else 'runtime'))
    baseline = os.environ.get("FLOWER_SAVER_BASELINE", "0") == "1"
    load_only = os.environ.get("FLOWER_SAVER_LOAD_ONLY", "0") == "1"
    assert not (baseline and load_only)
    if not baseline and not load_only:
        assert not (fixture_save()).exists(), "Refusing existing fixture save"
    for setting in ("pagination off", "confirm off", "print thread-events off"):
        command("set " + setting)
    stop_at("state_step_startup")
    command("run")
    assign("gPortResetToTitleScreen", 1)
    stop_at("state_step_title_screen")
    command("continue")
    if not baseline:
        command("call ttyd64_mode_select_file(TTYD64_MODE_TTYD64)")
    command("set scheduler-locking off")
    checks, costs = [], []
    a, b, x = [value("ITEM_FLOWER_SAVER_" + suffix) for suffix in ("A", "B", "X")]
    dip_items = [value("ITEM_DOUBLE_DIP"), value("ITEM_TRIPLE_DIP")]
    attack_items = [value("ITEM_POWER_JUMP"), value("ITEM_POWER_SMASH")]

    def check(name, condition):
        assert condition, name
        checks.append(name); record_check(name)
        print("FLOWER_SAVER_CHECK=" + name)

    def write_slots(field, entries):
        size = 128 if field == "badges" else 64
        assert len(entries) <= size and value(f"sizeof(gPlayerData.{field}[0])") == 2
        address = value(f"&gPlayerData.{field}[0]")
        gdb.selected_inferior().write_memory(address, struct.pack(f"={size}h", *(entries + [0] * (size - len(entries)))))

    def rows():
        return [bool(value(f"pause_badges_is_row_equipped({i})"))
                for i in range(value("gPauseBadgesNumItems"))]

    def menu():
        command("call pause_badges_count_all()")
        command("call pause_badges_init_equipped_copies()")
        assign("gPauseBadgesCurrentTab", 0)
        command("call pause_badges_load_badges(0)")
        assign("gPauseBadgesLevel", 1)
        assign("gPauseBadgesShowNotEnoughBP", 0)
        assign("gPauseMenuCurrentTab", 2)
        return rows()

    def press(index):
        assign("gPauseBadgesSelectedIndex", index)
        assign("gPausePressedButtons", value("BUTTON_A"))
        command("call pause_badges_handle_input(&gPausePanelBadges)")
        assign("gPausePressedButtons", 0)

    expected_bp = 6 if baseline else 4
    check("flower-saver-table-bp", value("get_move_bp_cost(MOVE_FLOWER_SAVER)") == expected_bp)
    check("native-variants-share-ability", all(value(f"gItemTable[{item}].moveID") == value("MOVE_FLOWER_SAVER") for item in (a, b, x)))
    check("double-dip-source-costs", value("get_move_fp_cost(MOVE_DOUBLE_DIP)") == (3 if baseline else 4)
          and value("get_move_bp_cost(MOVE_DOUBLE_DIP)") == (1 if baseline else 3))
    check("triple-dip-source-costs", value("get_move_fp_cost(MOVE_TRIPLE_DIP)") == (6 if baseline else 8)
          and value("get_move_bp_cost(MOVE_TRIPLE_DIP)") == 3)
    if not baseline and not load_only:
        for label, item in (("A", a), ("B", b)):
            write_slots("badges", [])
            write_slots("equippedBadges", [])
            assign("gPlayerData.maxBP", 8)
            assert value(f"add_item({item})") >= 0 and value(f"add_item({item})") >= 0
            check("two-identical-copies-equip-" + label, value(f"pause_badges_try_equip({item})") == 3
                  and value(f"pause_badges_try_equip({item})") == 3
                  and value("is_ability_active(ABILITY_FLOWER_SAVER)") == 2
                  and value("pause_get_total_equipped_bp_cost()") == 8)
            check("no-unowned-third-" + label, value(f"pause_badges_try_equip({item})") == 4)
            check("remove-one-costs-four-" + label, value(f"pause_badges_try_remove({item})") == 1
                  and value("pause_get_total_equipped_bp_cost()") == 4)
        write_slots("badges", [])
        write_slots("equippedBadges", [])
        assign("gPlayerData.maxBP", 20)
        for item in (x, x):
            assert value(f"add_item({item})") >= 0
        check("unused-x-retains-single-equip", value(f"pause_badges_try_equip({x})") == 3
              and value(f"pause_badges_try_equip({x})") == 0)
        write_slots("badges", [])
        write_slots("equippedBadges", [])
        for _ in range(3):
            assert value(f"add_item({a})") >= 0
        assign("gPlayerData.maxBP", 3)
        check("three-bp-insufficient", value(f"pause_badges_try_equip({a})") == 1)
        assign("gPlayerData.maxBP", 4)
        check("four-bp-one-copy", value(f"pause_badges_try_equip({a})") == 3)
        assign("gPlayerData.maxBP", 7)
        check("seven-bp-rejects-second", value(f"pause_badges_try_equip({a})") == 1)
        assign("gPlayerData.maxBP", 8)
        check("eight-bp-two-copies", value(f"pause_badges_try_equip({a})") == 3)
        check("independent-rows", menu() == [True, True, False])
        press(1)
        check("row-removes-one-copy", rows() == [True, False, False]
              and value("pause_get_total_equipped_bp_cost()") == 4)
        press(2)
        check("row-equips-third-copy", rows() == [True, False, True]
              and value("pause_get_total_equipped_bp_cost()") == 8)
        assign("gPlayerData.curPartner", value("PARTNER_BOW"))
        assign("gPlayerData.partners[PARTNER_BOW].enabled", 1)
        assign("gPlayerData.curFP", 2)
        command("call fio_save_game(3)")
        saved = json.loads((fixture_save()).read_text())["player"]
        check("native-save-copies", saved["badges"].count(a) == 3 and saved["equippedBadges"].count(a) == 2)
    if not baseline:
        assert value("fio_load_game(3)") == 1
        check("native-load-count-and-bp", value("is_ability_active(ABILITY_FLOWER_SAVER)") == 2
              and value("pause_get_total_equipped_bp_cost()") == 8 and menu() == [True, True, False])

    command("call load_demo_battle(0)")
    command("return")
    stop_at("calc_player_damage_enemy")
    command("continue")
    if not baseline:
        command("call ttyd64_mode_select_file(TTYD64_MODE_TTYD64)")
    command("set scheduler-locking off")
    check("native-battle-actors-created", value("gBattleStatus.playerActor") != 0
          and value("gBattleStatus.enemyActors[0]") != 0)
    assign("gPlayerData.bootsLevel", 0)
    assign("gPlayerData.hammerLevel", 0)
    assign("gBattleStatus.flags2", 0)
    choose = ChooseItems()

    def item_menu(fp):
        assign("gPlayerData.curFP", fp)
        assign("gBattleSubState", 1)  # menu_player.c: MAIN_CHOOSING
        assign("BattleMenu_ChooseDelay", 0)
        assign("BattleMenu_SwapDelay", 0)
        assign("WheelOptionSubmenu[0]", value("BTL_MENU_TYPE_ITEMS"))
        assign("gGameStatusPtr->pressedButtons[0]", 0)
        command("call btl_state_update_player_menu()")
        return {value(f"gBattleStatus.submenuMoves[{i}]"): {
            "enabled": bool(value(f"gBattleStatus.submenuStatus[{i}]")),
            "base_cost": value(f"MovesOptionDisplayCosts[{i}]"),
            "discount": value(f"MovesOptionDiscounts[{i}]"),
        } for i in range(value("gBattleStatus.submenuMoveCount"))}

    for label, savers, fanatic in (("none", [], False), ("one", [a], False),
                                   ("pair", [a, a], False), ("mixed", [a, b], False),
                                   ("four", [a] * 4, False), ("nine", [a] * 9, False),
                                   ("fanatic-coexist", [a], True)):
        entries = savers + dip_items + attack_items
        if fanatic:
            entries.append(value("ITEM_FLOWER_FANATIC"))
        write_slots("equippedBadges", entries)
        discount = len(savers) + (2 if fanatic else 0)
        for move in ("MOVE_DOUBLE_DIP", "MOVE_TRIPLE_DIP"):
            mid = value(move)
            base = value(f"get_move_fp_cost({mid})")
            expected = max(1, base - discount)
            below = expected - 1
            status = item_menu(below)[mid]
            bug = baseline and base - discount <= 0
            check(label + "-" + move + "-below-cost", status["enabled"] == bug)
            status = item_menu(expected)[mid]
            check(label + "-" + move + "-at-cost", status["enabled"]
                  and status["base_cost"] == base and status["discount"] == discount)
            assign("gBattleStatus.selectedMoveID", mid)
            assign("gPlayerData.curFP", expected)
            command("call deduct_current_move_fp()")
            check(label + "-" + move + "-native-payment", value("gPlayerData.curFP") == 0)
            costs.append({"case": label, "move": move, "copies": len(savers), "base": base,
                          "discount": discount, "fp_cost": expected,
                          "below_cost_enabled": bug, "fp_after_payment": 0})
        for init, move in (("btl_init_menu_boots", "MOVE_POWER_JUMP"),
                           ("btl_init_menu_hammer", "MOVE_POWER_SMASH")):
            expected = max(1, value(f"get_move_fp_cost({move})") - discount)
            for fp in (expected - 1, expected):
                assign("gPlayerData.curFP", fp)
                command(f"call {init}()")
                indices = [i for i in range(value("gBattleStatus.submenuMoveCount"))
                           if value(f"gBattleStatus.submenuMoves[{i}]") == value(move)]
                assert len(indices) == 1
                check(label + "-" + move + f"-fp-{fp}", value(f"gBattleStatus.submenuStatus[{indices[0]}]") == (1 if fp == expected else 0))
            assign("gBattleStatus.selectedMoveID", value(move))
            assign("gPlayerData.curFP", expected)
            command("call deduct_current_move_fp()")
            check(label + "-" + move + "-native-payment", value("gPlayerData.curFP") == 0)
        assign("gBattleStatus.selectedMoveID", value("MOVE_HAMMER1"))
        assign("gPlayerData.curFP", 0)
        command("call deduct_current_move_fp()")
        check(label + "-free-hammer-stays-free", value("gPlayerData.curFP") == 0)

    # Final menu and native payment use the pair loaded from native persistence.
    if not baseline:
        assert value("fio_load_game(3)") == 1
        assign("gPlayerData.maxBP", 14)  # Test budget: saved pair + two item-dip badges.
        for item in dip_items:
            assert value(f"add_item({item})") >= 0
            assert value(f"pause_badges_try_equip({item})") == 3
        status = item_menu(2)[value("MOVE_DOUBLE_DIP")]
        check("saved-pair-double-dip-menu", status["enabled"] and status["base_cost"] == 4 and status["discount"] == 2)
        assign("gBattleStatus.selectedMoveID", value("MOVE_DOUBLE_DIP"))
        command("call deduct_current_move_fp()")
        check("saved-pair-double-dip-pays-two-fp", value("gPlayerData.curFP") == 0)
    choose.delete()
    report = {"checks_passed": len(checks), "baseline": baseline, "fresh_process": load_only,
              "checks": checks, "source_bp": expected_bp, "cost_cases": costs,
              "limits": "Controlled native menu choice/FP calls in live battle; no whole item-dip sequence or partner port."}
    Path(required_env('FLOWER_SAVER_RESULT')).write_text(json.dumps(report, indent=2) + "\n")
    print("FLOWER_SAVER_PASSED=" + str(len(checks)))
    command("kill")


try:
    run_checks()
except Exception:
    import traceback
    traceback.print_exc()
    command("quit 1")
