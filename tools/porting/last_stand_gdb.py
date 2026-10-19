"""GDB integration check against a real Tubba Blubba demo-battle attack.

Run via `gdb -batch -x tools/porting/last_stand_gdb.py <debug executable>`
from the executable's asset directory. See the coordination handoff for environment
variables. LAST_STAND_VARIANT is `stacking` (default) or `baseline`;
LAST_STAND_SOURCE must name the source matching the executable's debug lines.
LAST_STAND_BLOCKED=1 additionally forces the native block check to succeed.

The fixture changes only a throwaway process: no save or gameplay test mode is added.
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


def breakpoint_at(specification):
    return gdb.Breakpoint(specification, temporary=True, internal=True)


def run_checks():
    variant = os.environ.get("LAST_STAND_VARIANT", "stacking")
    assert variant in ("baseline", "stacking"), variant
    blocked = os.environ.get("LAST_STAND_BLOCKED", "0") == "1"
    source = Path(required_env('LAST_STAND_SOURCE')).read_text().splitlines()
    native_source = str(source_path("src/battle/1A5830.c"))
    start_line = next(i + 1 for i, line in enumerate(source) if "isPlayer = actorClass" in line)
    end_line = next(i + 1 for i, line in enumerate(source) if i + 1 > start_line and "switch (actorClass)" in line)
    hp_line = next(i + 1 for i, line in enumerate(source) if "gPlayerData.curHP = target->curHP" in line)
    applied_line = next(i + 1 for i, line in enumerate(source) if i + 1 > hp_line and "if (gBattleStatus.flags1" in line)

    command("set pagination off")
    command("set confirm off")
    command("set print thread-events off")
    command("set breakpoint pending off")
    breakpoint_at("state_step_startup")
    command("run")
    assign("gPortResetToTitleScreen", 1)
    breakpoint_at("state_step_title_screen")
    command("continue")
    command("call load_demo_battle(4)")
    command("return")  # Do not let the old title handler overwrite the new mode.
    breakpoint_at("calc_enemy_damage_target")
    command("continue")
    assert value("gGameStatusPtr->context") == value("CONTEXT_BATTLE")
    assert value("attacker->actorID") >= 0x200
    breakpoint_at(f"{native_source}:{start_line}")
    command("continue")
    assert value("actorClass") == 0  # This attack really targets Mario.
    command("call ttyd64_mode_select_file(" + ("1" if variant == "stacking" else "0") + ")")
    command("set scheduler-locking on")
    start_pc = gdb.decode_line(f"{native_source}:{start_line}")[1][0].pc
    end_breakpoint = gdb.Breakpoint(f"{native_source}:{end_line}", internal=True)
    last_stand = value("ITEM_LAST_STAND")
    size = value("sizeof(gPlayerData.equippedBadges) / sizeof(gPlayerData.equippedBadges[0])")

    def fixture(hp, count, damage, actor_class=0):
        for index in range(size):
            assign(f"gPlayerData.equippedBadges[{index}]", last_stand if index < count else 0)
        assign("gPlayerData.curHP", hp)
        assign("target->curHP", hp)
        assign("actorClass", actor_class)
        assign("damage", damage)
        # Replay only the compiled defensive-badge block in the live battle frame.
        command(f"jump *{start_pc}")
        return value("damage")

    cases = [
        ("above-danger", 6, 2, 6, 0, 6, 6),
        ("unequipped", 5, 0, 6, 0, 6, 6),
        ("one-copy", 5, 1, 6, 0, 3, 3),
        ("two-copies", 5, 2, 6, 0, 3, 2),
        ("three-copies", 5, 3, 6, 0, 3, 1),
        ("odd-damage", 5, 2, 5, 0, 2, 1),
        ("peril", 1, 2, 6, 0, 3, 2),
        ("rounds-to-zero", 5, 2, 1, 0, 0, 0),
        ("zero-damage", 5, 2, 0, 0, 0, 0),
        ("non-player-branch", 5, 2, 6, 0x200, 6, 6),
        ("full-equipped-array", 5, size, 65, 0, 32, 1),
    ]
    results = []
    for name, hp, count, damage, actor_class, old, new in cases:
        actual = fixture(hp, count, damage, actor_class)
        expected = old if variant == "baseline" else new
        assert actual == expected, (name, actual, expected)
        record_check(name)
        results.append({"case": name, "hp": hp, "copies": count, "input": damage, "observed": actual})

    # Let one injected 6-damage attack actually apply HP after two-copy mitigation.
    fixture(5, 2, 6)
    end_breakpoint.delete()
    assign("target->debuff", 0)
    assign("target->stoneStatus", 0)
    command("set variable target->flags &= ~ACTOR_FLAG_NO_DMG_APPLY")
    command("set variable targetPart->flags &= ~ACTOR_PART_FLAG_DAMAGE_IMMUNE")
    command("set variable gBattleStatus.flags1 &= ~BS_FLAGS1_TUTORIAL_BATTLE")
    if blocked:
        command("set variable battleStatus->curAttackElement &= ~DAMAGE_TYPE_UNBLOCKABLE")
        breakpoint_at("check_block_input")
        command("continue")
        command("return 1")
    else:
        command("set variable battleStatus->curAttackElement |= DAMAGE_TYPE_UNBLOCKABLE")
    breakpoint_at(f"{native_source}:{applied_line}")
    command("continue")
    expected_damage = (3 if variant == "baseline" else 2) - int(blocked)
    actual_hp = value("gPlayerData.curHP")
    actual_damage = value("battleStatus->lastAttackDamage")
    assert actual_damage == expected_damage, (actual_damage, expected_damage)
    assert actual_hp == 5 - expected_damage, (actual_hp, expected_damage)
    assert value("target->curHP") == actual_hp
    record_check("applied-hit-forced-guard" if blocked else "applied-hit-unblocked")
    report = {"variant": variant, "branch_checks": results, "battle_hit": {
        "blocked": blocked, "hp_before": 5, "input": 6, "copies": 2,
        "damage_applied": actual_damage, "hp_after": actual_hp,
    }}
    print("LAST_STAND_RESULT=" + json.dumps(report, sort_keys=True))
    output = required_env("LAST_STAND_RESULT")
    if output:
        Path(output).write_text(json.dumps(report, indent=2) + "\n")
    command("kill")


try:
    run_checks()
except Exception:
    # gdb -batch otherwise can return success after a Python assertion failed.
    import traceback
    traceback.print_exc()
    gdb.execute("quit 1")
