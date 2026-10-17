"""Native Pity Flower inventory, resource, save and battle integration fixture.

Use an isolated SHIP_HOME and Debug executable with assets, under GDB/Python.
PITY_FLOWER_LOAD_ONLY=1 reads a previous fixture save in a fresh process.
Random boundary checks force rand_int's return, not the badge logic; the final
loaded battle also runs the real native RNG with a controlled seed.
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


class Rolls(gdb.Breakpoint):
    def __init__(self):
        super().__init__("rand_int", internal=True)
        self.values = []
        self.calls = 0
        self.forced = True

    def stop(self):
        if gdb.newest_frame().older().name() not in ("try_pity_flower", "ttyd64_pity_flower_recovery"):
            return False
        assert value("max") == 100
        self.calls += 1
        if self.forced:
            assert self.values, "Unexpected extra random roll"
            command(f"return {self.values.pop(0)}")
        return False


class Recovery(gdb.Breakpoint):
    def __init__(self):
        super().__init__("recover_main", internal=True)
        self.amounts = []

    def stop(self):
        if gdb.newest_frame().older().name() != "try_pity_flower":
            return False
        assert value("type") == 1
        self.amounts.append(value("duration"))
        return False


def run_checks():
    runtime = Path(required_env('SHIP_HOME')).resolve()
    assert runtime == fixture_path('pity-flower/runtime')
    load_only = os.environ.get("PITY_FLOWER_LOAD_ONLY", "0") == "1"
    blocked = os.environ.get("PITY_FLOWER_BLOCKED", "0") == "1"
    applied_damage = 5 if blocked else 6
    if not load_only:
        assert not (fixture_save()).exists(), "Refusing existing fixture save"
    for setting in ("pagination off", "confirm off", "print thread-events off"):
        command("set " + setting)
    stop_at("state_step_startup")
    command("run")
    assign("gPortResetToTitleScreen", 1)
    stop_at("state_step_title_screen")
    command("continue")
    badge = value("ITEM_PITY_FLOWER")
    results, battles = [], []

    def check(name, condition):
        assert condition, name
        results.append(name); record_check(name)

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
        return [bool(value(f"pause_badges_is_row_equipped({i})")) for i in range(3)]

    def press(row):
        assign("gPauseBadgesSelectedIndex", row)
        assign("gPausePressedButtons", value("BUTTON_A"))
        command("call pause_badges_handle_input(&gPausePanelBadges)")
        assign("gPausePressedButtons", 0)
        return [bool(value(f"pause_badges_is_row_equipped({i})")) for i in range(3)]

    check("appended-native-item-and-move", badge == 365 and value("gItemTable[ITEM_PITY_FLOWER].moveID") == 185)
    check("badge-classification-and-bp", value("gItemTable[ITEM_PITY_FLOWER].typeFlags & ITEM_TYPE_FLAG_BADGE") != 0
          and value("gMoveTable[MOVE_PITY_FLOWER].costBP") == 3)
    name = gdb.parse_and_eval("load_message_to_buffer(gItemTable[ITEM_PITY_FLOWER].nameMsg)")
    raw = bytes(gdb.selected_inferior().read_memory(int(name), 12))
    check("dedicated-name-message-loaded", raw == b"\x30\x49\x54\x59\xF7\x26\x4C\x4F\x57\x45\x52\xFD")
    check("description-loaded", value("load_message_to_buffer(gItemTable[ITEM_PITY_FLOWER].shortDescMsg)") != 0)
    for suffix in ("", ".pal", ".disabled.pal"):
        check("resource-loaded" + (suffix or "-raster"),
              value(f'GameEngine_GetDataExact("icons/badge/PityFlower{suffix}")') != 0)
    check("entity-script-and-icon-tables", value("gItemEntityScripts[ITEM_PITY_FLOWER] == IES_PityFlower") != 0
          and value("gItemIconRasterOffsets[ITEM_PITY_FLOWER]") != 0)
    if not load_only:
        for field, size in (("badges", 128), ("equippedBadges", 64)):
            for i in range(size):
                assign(f"gPlayerData.{field}[{i}]", 0)
        assign("gPlayerData.maxBP", 6)
        check("unowned-rejected", value(f"pause_badges_try_equip({badge})") == 4)
        for _ in range(3):
            assert value(f"add_item({badge})") >= 0
        check("three-copies-acquired", count("badges") == 3)
        check("two-copies-equip", value(f"pause_badges_try_equip({badge})") == 3
              and value(f"pause_badges_try_equip({badge})") == 3)
        check("per-copy-bp-and-limit", value("pause_get_total_equipped_bp_cost()") == 6
              and value(f"pause_badges_try_equip({badge})") == 1)
        check("independent-menu-rows", menu() == [True, True, False])
        check("menu-removes-selected-copy", press(1) == [True, False, False]
              and value("pause_get_total_equipped_bp_cost()") == 3)
        check("menu-equips-third-copy-independently", press(2) == [True, False, True]
              and value("pause_get_total_equipped_bp_cost()") == 6)
        check("menu-bp-rejection-preserves-copy-rows", press(1) == [True, False, True])
        check("remove-one-releases-three-bp", value(f"pause_badges_try_remove({badge})") == 1
              and value("pause_get_total_equipped_bp_cost()") == 3)
        assert value(f"pause_badges_try_equip({badge})") == 3
        command("call fio_save_game(3)")
        saved = json.loads((fixture_save()).read_text())["player"]
        check("native-json-preserves-new-id", saved["badges"].count(badge) == 3
              and saved["equippedBadges"].count(badge) == 2)
    command("call fio_load_game(3)")
    check("native-load-copies-bp-ability", count("badges") == 3 and count("equippedBadges") == 2
          and value("pause_get_total_equipped_bp_cost()") == 6
          and value("is_ability_active(ABILITY_PITY_FLOWER)") == 2)
    check("loaded-menu-rows", menu() == [True, True, False])

    command("call load_demo_battle(4)")
    command("return")
    stop_at("calc_enemy_damage_target")
    command("continue")
    command("call fio_load_game(3)")
    assign("gBattleStatus.playerActor->curHP", 10)
    assign("gPlayerData.curHP", 10)
    assign("gPlayerData.curMaxFP", 10)
    assign("gPlayerData.curFP", 0)
    assign("gBattleStatus.curAttackDamage", 6)
    command("set variable gBattleStatus.playerActor->flags &= ~(ACTOR_FLAG_NO_DMG_APPLY | ACTOR_FLAG_NO_DMG_POPUP)")
    command("set variable gBattleStatus.playerActor->partsTable->flags &= ~ACTOR_PART_FLAG_DAMAGE_IMMUNE")
    command("set variable gBattleStatus.flags1 &= ~BS_FLAGS1_TUTORIAL_BATTLE")
    if blocked:
        command("set variable gBattleStatus.curAttackElement &= ~DAMAGE_TYPE_UNBLOCKABLE")
    else:
        command("set variable gBattleStatus.curAttackElement |= DAMAGE_TYPE_UNBLOCKABLE")
    source = source_path('src/battle/1A5830.c')
    lines = source.read_text().splitlines()
    start = next(i + 1 for i, line in enumerate(lines) if "if (!(target->flags & ACTOR_FLAG_NO_DMG_POPUP))" in line)
    end = next(i + 1 for i, line in enumerate(lines) if i + 1 > start and "if (battleStatus->lastAttackDamage > 0)" in line)
    stop_at(f"{source}:{start}")
    if blocked:
        stop_at("check_block_input")
        command("continue")
        command("return 1")  # Test the native blocked path, not input timing.
    command("continue")
    check("real-attack-applied-hp-before-proc", value("gPlayerData.curHP") == 10 - applied_damage
          and value("actorClass") == 0 and value("battleStatus->lastAttackDamage") == applied_damage)
    if blocked:
        check("real-native-block-flag", value("gBattleStatus.flags1 & BS_FLAGS1_ATK_BLOCKED") != 0)
    command("set scheduler-locking on")
    start_pc = gdb.decode_line(f"{source}:{start}")[1][0].pc
    stop = gdb.Breakpoint(f"{source}:{end}", internal=True)
    rolls, recovery = Rolls(), Recovery()
    base_flags = value("target->flags")
    base_element = value("battleStatus->curAttackElement")
    assign("gRandSeed", 3)
    rolls.forced = False
    command("continue")
    check("loaded-native-hit-real-rng-recovery", rolls.calls == 2
          and value("gPlayerData.curFP") == 1 and recovery.amounts == [1]
          and value("gPlayerData.curHP") == 10 - applied_damage)
    rolls.forced = True

    def hit(name, copies, rolls_values, expected, fp=0, damage=6, actor_class=0, no_popup=False, element=0, max_fp=10):
        for i in range(64):
            assign(f"gPlayerData.equippedBadges[{i}]", badge if i < copies else 0)
        assign("gPlayerData.curFP", fp)
        assign("gPlayerData.curMaxFP", max_fp)
        assign("actorClass", actor_class)
        assign("battleStatus->lastAttackDamage", damage)
        assign("target->flags", base_flags | (value("ACTOR_FLAG_NO_DMG_POPUP") if no_popup else 0))
        assign("battleStatus->curAttackElement", base_element | element)
        rolls.values, rolls.calls, recovery.amounts = list(rolls_values), 0, []
        command(f"jump *{start_pc}")
        actual = value("gPlayerData.curFP")
        check(name, actual == expected and not rolls.values and rolls.calls == len(rolls_values))
        battles.append({"case": name, "copies": copies, "rolls": rolls_values, "fp_before": fp,
                        "fp_after": actual, "recovery_popups": list(recovery.amounts)})
        return recovery.amounts

    assert hit("unequipped-no-rng", 0, [], 0) == []
    assert hit("roll-zero-success", 1, [0], 1) == [1]
    assert hit("roll-32-success", 1, [32], 1) == [1]
    assert hit("roll-33-failure", 1, [33], 0) == []
    assert hit("roll-100-failure", 1, [100], 0) == []
    assert hit("copies-roll-independently", 3, [0, 100, 32], 2) == [2]
    assert hit("fp-capped-at-max", 3, [0, 0, 0], 10, fp=9) == [3]
    assert hit("full-fp-still-rolls-and-shows-effect", 1, [0], 10, fp=10) == [1]
    assert hit("high-fp-many-copies-no-signed-wrap", 42, [0] * 42, 99, fp=98, max_fp=99) == [42]
    hit("zero-damage-no-proc", 2, [], 0, damage=0)
    hit("suppressed-popup-no-proc", 2, [], 0, no_popup=True)
    hit("multiple-popups-no-proc", 2, [], 0, element=value("DAMAGE_TYPE_MULTIPLE_POPUPS"))
    hit("smash-popup-no-proc", 2, [], 0, element=value("DAMAGE_TYPE_SMASH"))
    hit("partner-no-proc", 2, [], 0, actor_class=value("ACTOR_CLASS_PARTNER"))
    assign("target->curHP", 0)
    assert hit("lethal-hp-preserves-upstream-trigger", 1, [0], 1) == [1]
    assign("target->curHP", 4)
    # Restore equipped copies from disk, then replay this real hit's popup path
    # using the native RNG. Seed 3's first two rolls (9, 91) are checked independently.
    command("call fio_load_game(3)")
    assign("gPlayerData.curMaxFP", 10)
    assign("gPlayerData.curFP", 0)
    assign("actorClass", 0)
    assign("target->flags", base_flags)
    assign("battleStatus->lastAttackDamage", 6)
    assign("battleStatus->curAttackElement", base_element)
    assign("gRandSeed", 3)
    rolls.calls, rolls.forced, recovery.amounts = 0, False, []
    command(f"jump *{start_pc}")
    check("saved-copies-real-rng-battle", rolls.calls == 2 and count("equippedBadges") == 2
          and value("gPlayerData.curFP") == 1 and recovery.amounts == [1])
    rolls.delete()
    recovery.delete()
    stop.delete()
    report = {"checks_passed": len(results), "load_only": load_only, "checks": results,
              "native_item_id": badge, "native_move_id": 185, "bp_per_copy": 3,
              "native_hit": {"copies_loaded": 2, "attack_damage": 6, "damage_applied": applied_damage,
                             "hp_before": 10, "hp_after": 10 - applied_damage,
                             "fp_before": 0, "fp_after": 1, "rng_seed": 3, "blocked": blocked},
              "battle_cases": battles, "saved_copies_real_rng_fp": value("gPlayerData.curFP")}
    Path(required_env('PITY_FLOWER_RESULT')).write_text(json.dumps(report, indent=2) + "\n")
    print("PITY_FLOWER_RESULT=" + json.dumps(report))
    command("kill")


try:
    run_checks()
except Exception:
    import traceback
    traceback.print_exc()
    command("quit 1")
