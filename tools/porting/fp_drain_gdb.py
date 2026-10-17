"""Native FP Drain resources, copy/BP/save, attack counter and end-turn recovery.

FP_DRAIN_LOAD_ONLY=1 reads the same fixture slot in a new game process.
Uses an exact disposable SHIP_HOME and refuses an existing writer save.
"""

import json
import os
import struct
from pathlib import Path

import gdb


def command(text):
    return gdb.execute(text, to_string=True)


def value(expression):
    return int(gdb.parse_and_eval(expression))


def assign(expression, number):
    command(f"set variable {expression} = {number}")


def stop_at(spec):
    return gdb.Breakpoint(spec, temporary=True, internal=True)


class HappyRolls(gdb.Breakpoint):
    def __init__(self):
        super().__init__("rand_int", internal=True)
        self.roll = 100
        self.calls = 0

    def stop(self):
        if gdb.newest_frame().older().name() != "btl_substate_try_hpfp_recovery":
            return False
        assert value("max") == 100
        self.calls += 1
        command(f"return {self.roll}")
        return False


def call_native(text):
    locking = gdb.parameter("scheduler-locking")
    command("set scheduler-locking off")
    command(text)
    command("set scheduler-locking " + locking)


def load_save():
    # Native save loading can acquire a mutex held by a render/audio thread.
    # Permit those threads to run during this debugger function call.
    locking = gdb.parameter("scheduler-locking")
    command("set scheduler-locking off")
    assert value("fio_load_game(3)") == 1
    command("set scheduler-locking " + locking)


def run_checks():
    coexist = os.environ.get("FP_DRAIN_COEXIST", "0") == "1"
    fp_start = int(os.environ.get("FP_DRAIN_FP_START", "2"))
    base_damage = int(os.environ.get("FP_DRAIN_BASE_DAMAGE", "3"))
    assert fp_start in (2, 98) and base_damage in (1, 3)
    assert not (coexist and (fp_start == 98 or base_damage != 3))
    assert not (fp_start == 98 and base_damage != 3)
    runtime = Path(os.environ["SHIP_HOME"]).resolve()
    suffix = "coexist-runtime" if coexist else "cap-runtime" if fp_start == 98 else "zero-runtime" if base_damage == 1 else "runtime"
    assert runtime == Path("/workspace/.paperboat-setup/fp-drain") / suffix
    load_only = os.environ.get("FP_DRAIN_LOAD_ONLY", "0") == "1"
    if not load_only:
        assert not coexist and fp_start == 2 and base_damage == 3
        assert not (runtime / "saves/file3.json").exists(), "Refusing existing fixture save"
    for setting in ("pagination off", "confirm off", "print thread-events off"):
        command("set " + setting)
    stop_at("state_step_startup")
    command("run")
    assign("gPortResetToTitleScreen", 1)
    stop_at("state_step_title_screen")
    command("continue")
    badge = value("ITEM_FP_DRAIN")
    checks, attacks = [], []

    def check(name, condition):
        assert condition, name
        checks.append(name)
        print("FP_DRAIN_CHECK=" + name)

    def count(field):
        size = 128 if field == "badges" else 64
        address = value(f"&gPlayerData.{field}[0]")
        data = gdb.selected_inferior().read_memory(address, size * 2)
        return struct.unpack(f"={size}h", data).count(badge)

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

    check("appended-native-item-and-move", badge == 368
          and value("gItemTable[ITEM_FP_DRAIN].moveID") == 188)
    check("source-cost-three-bp", value("gMoveTable[MOVE_FP_DRAIN].costBP") == 3)
    for suffix in ("", ".pal", ".disabled.pal"):
        check("resource-loaded" + (suffix or "-raster"),
              value(f'GameEngine_GetDataExact("icons/badge/FPDrain{suffix}")') != 0)
    for suffix in ("", ".pal"):
        check("label-resource-loaded" + (suffix or "-raster"),
              value(f'GameEngine_GetDataExact("ui/battle/status/fp_drain{suffix}")') != 0)
    check("native-name-and-description", value("load_message_to_buffer(gItemTable[ITEM_FP_DRAIN].nameMsg)") != 0
          and value("load_message_to_buffer(gItemTable[ITEM_FP_DRAIN].fullDescMsg)") != 0)
    check("entity-and-icon-identity", value("gItemEntityScripts[ITEM_FP_DRAIN] == IES_FPDrain") != 0
          and value("gItemIconRasterOffsets[ITEM_FP_DRAIN]") != 0)
    if not load_only:
        for field, size in (("badges", 128), ("equippedBadges", 64)):
            for i in range(size):
                assign(f"gPlayerData.{field}[{i}]", 0)
        check("unowned-rejected", value(f"pause_badges_try_equip({badge})") == 4)
        for _ in range(3):
            assert value(f"add_item({badge})") >= 0
        assign("gPlayerData.maxBP", 2)
        check("two-bp-insufficient", value(f"pause_badges_try_equip({badge})") == 1)
        assign("gPlayerData.maxBP", 3)
        check("three-bp-equips-one", value(f"pause_badges_try_equip({badge})") == 3)
        assign("gPlayerData.maxBP", 5)
        check("five-bp-rejects-second", value(f"pause_badges_try_equip({badge})") == 1)
        assign("gPlayerData.maxBP", 6)
        check("six-bp-equips-pair", value(f"pause_badges_try_equip({badge})") == 3
              and value("is_ability_active(ABILITY_FP_DRAIN)") == 2)
        check("owned-third-copy-bp-limit", value(f"pause_badges_try_equip({badge})") == 1)
        menu()
        check("independent-menu-rows", rows() == [True, True, False])
        assign("gPauseBadgesSelectedIndex", 1)
        assign("gPausePressedButtons", value("BUTTON_A"))
        command("call pause_badges_handle_input(&gPausePanelBadges)")
        check("menu-removes-only-selected-copy", rows() == [True, False, False]
              and value("pause_get_total_equipped_bp_cost()") == 3)
        assign("gPauseBadgesSelectedIndex", 2)
        command("call pause_badges_handle_input(&gPausePanelBadges)")
        assign("gPausePressedButtons", 0)
        check("menu-equips-third-copy-independently", rows() == [True, False, True]
              and value("pause_get_total_equipped_bp_cost()") == 6)
        assign("gPlayerData.curPartner", value("PARTNER_BOW"))
        assign("gPlayerData.partners[PARTNER_BOW].enabled", 1)
        assign("gPlayerData.hardMaxFP", 10)
        assign("gPlayerData.curMaxFP", 10)
        assign("gPlayerData.curFP", 2)
        command("call fio_save_game(3)")
        saved = json.loads((runtime / "saves/file3.json").read_text())["player"]
        check("native-save-copies", saved["badges"].count(badge) == 3
              and saved["equippedBadges"].count(badge) == 2)
    load_save()
    check("native-load-copies-bp-ability", count("badges") == 3 and count("equippedBadges") == 2
          and value("pause_get_total_equipped_bp_cost()") == 6
          and value("is_ability_active(ABILITY_FP_DRAIN)") == 2)
    menu()
    check("loaded-row-reconstruction", rows() == [True, True, False])

    # Initialization must clear stale state before a first strike can attack.
    assign("gBattleStatus.fpDrainCount", 5)
    command("call load_demo_battle(0)")
    command("return")
    stop_at("initialize_battle")
    command("continue")
    check("counter-stale-before-native-initialize", value("gBattleStatus.fpDrainCount") == 5)
    init_source = Path("/workspace/PaperBoat/src/battle/16C8E0.c")
    reset_end = next(i + 1 for i, line in enumerate(init_source.read_text().splitlines())
                     if "gBattleStatus.flags1 = 0" in line)
    stop_at(f"{init_source}:{reset_end}")
    command("continue")
    check("native-initialize-clears-counter-before-first-strike", value("gBattleStatus.fpDrainCount") == 0)
    load_save()
    stop_at("calc_player_damage_enemy")
    command("continue")
    check("native-demo-enters-hammer-attack", value("gBattleStatus.selectedMoveID") == value("MOVE_HAMMER1"))
    source = Path("/workspace/PaperBoat/src/battle/dmg_player.c")
    lines = source.read_text().splitlines()
    penalty = next(i + 1 for i, line in enumerate(lines) if "if (player_team_is_ability_active(player, ABILITY_FP_DRAIN))" in line)
    penalized = next(i + 1 for i, line in enumerate(lines) if i + 1 > penalty and "if (player_team_is_ability_active(player, ABILITY_HP_DRAIN))" in line)
    hp_subtract = next(i + 1 for i, line in enumerate(lines) if "target->curHP -= currentAttackDamage" in line)
    hp_applied = next(i + 1 for i, line in enumerate(lines) if i + 1 > hp_subtract and "target->lastDamageTaken =" in line)
    damage_done = next(i + 1 for i, line in enumerate(lines) if i + 1 > hp_applied
                       and "if (targetPart->flags & ACTOR_PART_FLAG_DAMAGE_IMMUNE)" in line)
    stop_at(f"{source}:{penalty}")
    command("continue")
    command("set scheduler-locking on")
    penalty_pc = gdb.decode_line(f"{source}:{penalty}")[1][0].pc
    end = gdb.Breakpoint(f"{source}:{penalized}", internal=True)

    def equip(copies, extras=()):
        entries = [badge] * copies + [value(x) for x in extras]
        assert value("sizeof(gPlayerData.equippedBadges[0])") == 2
        assert len(entries) <= 64
        address = value("&gPlayerData.equippedBadges[0]")
        gdb.selected_inferior().write_memory(address, struct.pack("=64h", *(entries + [0] * (64 - len(entries)))))

    for name, copies, base, before, expected, after, first in (
        ("unequipped", 0, 3, 0, 3, 0, False),
        ("one-copy-flat-penalty", 1, 3, 0, 2, 1, False),
        ("two-copies-still-flat-penalty", 2, 3, 0, 2, 1, False),
        ("three-copies-still-flat-penalty", 3, 3, 0, 2, 1, False),
        ("counter-reaches-five", 2, 3, 4, 2, 5, False),
        ("counter-stays-five", 2, 3, 5, 2, 5, False),
        ("all-equipment-slots", 64, 3, 0, 2, 1, False),
        ("zero-base-still-counts", 2, 0, 0, -1, 1, False),
        ("one-base-becomes-zero-still-counts", 2, 1, 0, 0, 1, False),
        ("first-strike-is-not-excluded", 2, 3, 0, 2, 1, True),
    ):
        equip(copies)
        assign("currentAttackDamage", base)
        assign("battleStatus->fpDrainCount", before)
        if first:
            command("set variable gBattleStatus.flags2 |= BS_FLAGS2_IS_FIRST_STRIKE")
        else:
            command("set variable gBattleStatus.flags2 &= ~BS_FLAGS2_IS_FIRST_STRIKE")
        command(f"jump *{penalty_pc}")
        actual, count_after = value("currentAttackDamage"), value("battleStatus->fpDrainCount")
        check(name, actual == expected and count_after == after)
        attacks.append({"case": name, "copies": copies, "base": base, "damage_after_penalty": actual,
                        "counter_before": before, "counter_after": count_after, "first_strike": first})
    equip(2)
    assign("battleStatus->fpDrainCount", 0)
    observed = []
    for _ in range(7):
        assign("currentAttackDamage", 3)
        command(f"jump *{penalty_pc}")
        observed.append(value("battleStatus->fpDrainCount"))
    check("seven-multi-hit-calculations-cap-at-five", observed == [1, 2, 3, 4, 5, 5, 5])
    end.delete()
    command("set scheduler-locking off")

    # The final full native path uses saved equipment. Coexistence adds only
    # the unrelated existing badges via native test grants/equipping after load.
    load_save()
    if coexist:
        assign("gPlayerData.maxBP", 20)
        for extra in ("ITEM_HP_DRAIN", "ITEM_HAPPY_HEART_A", "ITEM_HAPPY_FLOWER_A"):
            assert value(f"add_item({extra})") >= 0
            assert value(f"pause_badges_try_equip({extra})") == 3
        check("coexisting-badges-natively-granted-and-equipped", value("pause_get_total_equipped_bp_cost()") <= 20)
    assign("battleStatus->fpDrainCount", 0)
    assign("battleStatus->hpDrainCount", 0)
    command("set variable gBattleStatus.flags2 &= ~(BS_FLAGS2_IS_FIRST_STRIKE | BS_FLAGS2_HAS_DRAINED_HP)")
    assign("currentAttackDamage", base_damage)
    assign("target->curHP", 10)
    assign("targetDefense", 0)
    assign("player->attackBoost", 0)
    assign("battleStatus->turboChargeTurnsLeft", 0)
    assign("partImmuneToElement", 0)
    command("set variable targetPart->flags &= ~ACTOR_PART_FLAG_DAMAGE_IMMUNE")
    command("set variable targetPart->targetFlags &= ~ACTOR_PART_TARGET_NO_DAMAGE")
    command("set variable gBattleStatus.flags1 &= ~BS_FLAGS1_TUTORIAL_BATTLE")
    assign("gPlayerData.curHP", 5)
    assign("gPlayerData.curMaxHP", 10)
    assign("gPlayerData.curFP", fp_start)
    assign("gPlayerData.hardMaxFP", 99 if fp_start == 98 else 10)
    assign("gPlayerData.curMaxFP", 99 if fp_start == 98 else 10)
    stop_at(f"{source}:{damage_done}")
    command(f"jump *{penalty_pc}")
    damage = 0 if base_damage == 1 else 1 if coexist else 2
    check("saved-copies-native-hit-and-counter", value("target->curHP") == 10 - damage
          and value("battleStatus->lastAttackDamage") == damage
          and value("battleStatus->fpDrainCount") == 1)
    # Demo playback exits immediately after the attack. Clear only its demo
    # control flag so the real native player-turn state machine can continue.
    command("set variable gGameStatusPtr->demoBattleFlags &= ~DEMO_BTL_FLAG_ENABLED")
    command("set scheduler-locking off")
    rolls = HappyRolls()
    rolls.roll = 0 if coexist else 100
    stop_at("btl_substate_try_hpfp_recovery")
    command("continue")
    check("actual-turn-end-sees-attack-counter", value("gBattleStatus.fpDrainCount") == 1)
    return_bp = gdb.FinishBreakpoint(internal=True)
    command("continue")
    if return_bp.is_valid():
        return_bp.delete()
    check("actual-turn-end-clears-counter", value("gBattleStatus.fpDrainCount") == 0)
    expected_vars = [1, 1, 1, 2] if coexist else [0, 0, 0, 2]
    actual_vars = [value(f"gBattleStatus.playerActor->takeTurnScript->varTable[{i}]") for i in range(10, 14)]
    check("actual-turn-end-starts-native-happy-with-fp-drain", actual_vars == expected_vars
          and value("gBattleStatus.battlePhase") == value("PHASE_PLAYER_HAPPY"))

    events = Path("/workspace/PaperBoat/src/battle/player_events.c")
    evt_lines = events.read_text().splitlines()
    spawn_start = next(i for i, line in enumerate(evt_lines) if "API_CALLABLE(SpawnTurnEndFX)" in line)
    spawn_end = next(i + 1 for i, line in enumerate(evt_lines) if i > spawn_start and "return ApiStatus_DONE2" in line)
    stop_at(f"{events}:{spawn_end}")
    command("continue")
    fp_hid = value("HID_FPDrain")
    check("native-fp-drain-label-created", value("get_hud_element(HID_FPDrain)->anim == &HES_FPDrain") != 0)
    positions = {"fp_drain": value("get_hud_element(HID_FPDrain)->renderPosY")}
    if coexist:
        positions["hp_drain"] = value("get_hud_element(HID_HPDrain)->renderPosY")
        positions["happy"] = value("get_hud_element(HID_Happy)->renderPosY")
        check("three-native-labels-spaced-nine-pixels", positions["happy"] - positions["hp_drain"] == 9
              and positions["fp_drain"] - positions["happy"] == 9)
    stop_at("RemoveTurnEndFX")
    command("continue")
    gain = 3 if coexist else 2
    final_fp = min(99 if fp_start == 98 else 10, fp_start + gain)
    check("native-happy-script-recovers-and-caps-fp", value("gPlayerData.curFP") == final_fp)
    check("native-happy-script-preserves-or-recovers-hp", value("gPlayerData.curHP") == (7 if coexist else 5))
    command("finish")
    # HUD_ELEMENT_BATTLE_ID_MASK is the 0x800 macro in hud_element.h; macros
    # are not in this build's debugger symbols.
    check("native-fp-drain-label-freed", value(f"(*gHudElements)[{fp_hid & ~0x800}]") == 0)

    # Branch cases use the real native recovery function while the current Evt
    # is paused. Newly created, unexecuted test scripts are killed explicitly.
    command("set scheduler-locking on")
    recovery_cases = []
    original_state = value("gBattleState")
    for name, copies, hits, dip, stone, out, extras, happy, expected, retained in (
        ("no-badge-no-recovery", 0, 0, 0, False, False, (), False, [0,0,0,0], 0),
        ("no-hit-no-recovery", 2, 0, 0, False, False, (), False, [0,0,0,0], 0),
        ("one-copy-one-hit", 1, 1, 0, False, False, (), False, [0,0,0,1], 0),
        ("two-copies-one-hit", 2, 1, 0, False, False, (), False, [0,0,0,2], 0),
        ("three-copies-five-hits", 3, 5, 0, False, False, (), False, [0,0,0,7], 0),
        ("sixty-four-copies-five-hits", 64, 5, 0, False, False, (), False, [0,0,0,68], 0),
        ("double-dip-defers-recovery", 2, 3, 2, False, False, (), False, [0,0,0,0], 3),
        ("final-dip-allows-recovery", 2, 3, 1, False, False, (), False, [0,0,0,4], 0),
        ("stone-defers-recovery", 2, 3, 0, True, False, (), False, [0,0,0,0], 3),
        ("outta-sight-defers-recovery", 2, 3, 0, False, True, (), False, [0,0,0,0], 3),
        ("happy-flower-alone-var-d-zero", 0, 0, 0, False, False, ("ITEM_HAPPY_FLOWER_A",), True, [0,0,1,0], 0),
        ("hp-and-happy-coexist", 2, 3, 0, False, False,
         ("ITEM_HP_DRAIN", "ITEM_HAPPY_HEART_A", "ITEM_HAPPY_FLOWER_A"), True, [2,1,1,4], 0),
    ):
        equip(copies, extras)
        assign("gBattleStatus.playerActor->takeTurnScript", 0)
        assign("gBattleStatus.playerActor->takeTurnScriptID", 0)
        assign("gBattleStatus.playerActor->stoneStatus", value("STATUS_KEY_STONE") if stone else 0)
        assign("gBattleStatus.outtaSightActive", int(out))
        assign("gBattleStatus.moveCategory", value("BTL_MENU_TYPE_ITEMS") if dip else value("BTL_MENU_TYPE_SMASH"))
        assign("gBattleStatus.itemUsesLeft", dip)
        assign("gBattleStatus.fpDrainCount", hits)
        assign("gBattleStatus.hpDrainCount", 2 if "ITEM_HP_DRAIN" in extras else 0)
        if "ITEM_HP_DRAIN" in extras:
            command("set variable gBattleStatus.flags2 |= BS_FLAGS2_HAS_DRAINED_HP")
        else:
            command("set variable gBattleStatus.flags2 &= ~BS_FLAGS2_HAS_DRAINED_HP")
        rolls.roll = 0 if happy else 100
        call_native("call btl_substate_try_hpfp_recovery()")
        ptr = value("gBattleStatus.playerActor->takeTurnScript")
        actual = [value(f"gBattleStatus.playerActor->takeTurnScript->varTable[{i}]") for i in range(10,14)] if ptr else [0,0,0,0]
        check(name, actual == expected and value("gBattleStatus.fpDrainCount") == retained
              and bool(ptr) == bool(sum(expected)))
        recovery_cases.append({"case": name, "copies": copies, "hits": hits, "vars_a_b_c_d": actual,
                               "counter_after": value("gBattleStatus.fpDrainCount")})
        if ptr:
            call_native("call kill_script_by_ID(gBattleStatus.playerActor->takeTurnScriptID)")
    assert value("gBattleState") == original_state
    report = {"checks_passed": len(checks), "fresh_process": load_only, "coexistence": coexist,
              "checks": checks, "native_item_id": badge, "native_move_id": 188, "bp_per_copy": 3,
              "attack_cases": attacks, "multi_hit_counts": observed, "recovery_cases": recovery_cases,
              "native_turn": {"copies_loaded": 2, "base_damage": base_damage, "damage_applied": damage,
                              "enemy_hp_before": 10, "enemy_hp_after": 10 - damage,
                              "counter_from_attack": 1, "vars_a_b_c_d": actual_vars,
                              "fp_before": fp_start, "fp_after": final_fp, "labels_y": positions}}
    Path(os.environ["FP_DRAIN_RESULT"]).write_text(json.dumps(report, indent=2) + "\n")
    print("FP_DRAIN_RESULT=" + json.dumps(report))
    command("kill")


try:
    run_checks()
except Exception:
    import traceback
    traceback.print_exc()
    command("quit 1")
