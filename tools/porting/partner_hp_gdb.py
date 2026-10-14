"""Partner-health foundation: save compatibility and guarded native spawn/swap.

PARTNER_HP_LOAD_ONLY=1 reuses only this fixture's guarded slot3. No user saves.
Ordinary combat activation remains off; this fixture enables a local prototype.
"""

import json
import os
from pathlib import Path
import re
import gdb


def command(text):
    return gdb.execute(text, to_string=True)


def value(text):
    return int(gdb.parse_and_eval(text))


def assign(text, number):
    command(f"set variable {text} = {number}")


def stop_at(text):
    return gdb.Breakpoint(text, temporary=True, internal=True)


def run_checks():
    runtime = Path(os.environ["SHIP_HOME"]).resolve()
    assert runtime == Path("/workspace/.paperboat-setup/partner-hp/runtime")
    save_path = runtime / "saves/file3.json"
    load_only = os.environ.get("PARTNER_HP_LOAD_ONLY", "0") == "1"
    if not load_only:
        assert not save_path.exists(), "Refusing existing fixture save"
    for setting in ("pagination off", "confirm off", "print thread-events off"):
        command("set " + setting)
    stop_at("state_step_startup")
    command("run")
    assign("gPortResetToTitleScreen", 1)
    stop_at("state_step_title_screen")
    command("continue")
    command("set scheduler-locking off")
    checks, json_cases, swaps = [], [], []
    health = "gCurrentSaveFile.shipSaveData.partnerHP"

    def check(name, condition):
        assert condition, name
        checks.append(name)
        print("PARTNER_HP_CHECK=" + name)

    def current(partner):
        return value(f"ttyd64_get_partner_hp({partner})")

    def maximum(partner):
        return value(f"ttyd64_get_partner_max_hp({partner})")

    # Independent source-table extraction verifies every native rank value.
    source = Path("/workspace/ttyd64/globals/patch/PartnersHP.patch").read_text()
    block = source.split("#new:Data $PartnersHPTable", 1)[1].split("}", 1)[0]
    rows = [list(map(int, re.findall(r"(\d+)`b", line.split("%", 1)[0])))
            for line in block.splitlines()]
    rows = [row for row in rows if row]
    assert len(rows) == 11 and all(len(row) == 3 for row in rows)
    for partner, row in enumerate(rows, 1):
        for rank, expected in enumerate(row):
            check(f"source-rank-{partner}-{rank}", value(f"ttyd64_partner_base_max_hp({partner}, {rank})") == (expected if expected else -1))
    check("invalid-id-low-high-and-none", all(value(f"ttyd64_get_partner_hp({i})") == -1
          and value(f"ttyd64_set_partner_hp({i}, 9)") == -1 for i in (-2147483648, -1, 0, 5, 10, 11, 12, 2147483647)))
    check("rank-input-bounded", value("ttyd64_partner_base_max_hp(1, -2147483648)") == 10
          and value("ttyd64_partner_base_max_hp(3, 2147483647)") == 40)
    check("legacy-layout-unchanged", value("sizeof(PartnerData)") == 8 and value("sizeof(PlayerData)") == 0x428
          and value("sizeof(VanillaSaveData)") == 0x1380
          and value("(char*)&gCurrentSaveFile.shipSaveData - (char*)&gCurrentSaveFile") == 0x1380)
    check("prototype-default-off", value("gTtyd64PartnerHPPrototypeEnabled") == 0)

    if not load_only:
        assign("gTtyd64PartnerHPPrototypeEnabled", 1)
        assign(f"{health}[1].curHP", -20)
        command("call clear_player_data()")
        check("new-game-initializes-health-and-disables-prototype", current(1) == 10 and maximum(1) == 10
              and value("gTtyd64PartnerHPPrototypeEnabled") == 0)
        for partner, rank, hp in ((1, 0, 7), (2, 1, 0), (3, 2, 33), (4, 0, 5),
                                  (6, 1, 8), (7, 2, 16), (8, 1, 3), (9, 2, 4)):
            assign(f"gPlayerData.partners[{partner}].enabled", 1)
            assign(f"gPlayerData.partners[{partner}].level", rank)
            command(f"call ttyd64_reset_partner_hp({partner})")
            check(f"rank-reset-heals-{partner}", current(partner) == rows[partner - 1][rank])
            assert value(f"ttyd64_set_partner_hp({partner}, {hp})") == hp
        check("setter-overflow-caps", value("ttyd64_set_partner_hp(3, 2147483647)") == 40)
        check("setter-negative-floors", value("ttyd64_set_partner_hp(3, -2147483648)") == 0)
        assert value("ttyd64_set_partner_hp(3, 33)") == 33
        for partner in range(12):
            for index in range(3):
                assign(f"gPlayerData.partners[{partner}].unk_02[{index}]", 1000 + 3 * partner + index)
        assign("gPlayerData.curPartner", value("PARTNER_BOW"))
        assign("gPlayerData.maxBP", 8)
        assign("gPlayerData.curFP", 2)
        for _ in range(2):
            assert value("add_item(ITEM_FLOWER_SAVER_A)") >= 0
            assert value("pause_badges_try_equip(ITEM_FLOWER_SAVER_A)") == 3
        assign("gCurrentSaveFile.shipSaveData.hasDiedOnce", 1)
        command("call fio_save_game(3)")
        data = json.loads(save_path.read_text())
        block = data["ship"]["ttyd64PartnerHP"]
        check("native-writer-version-and-count", block["version"] == 1 and len(block["partners"]) == 12)
        check("native-writer-wounded-zero-and-max", block["partners"][9] == {"curHP": 4, "maxHP": 30}
              and block["partners"][2] == {"curHP": 0, "maxHP": 15})
        check("unrelated-ship-key-retained", data["ship"]["hasDiedOnce"] == 1)

    original = save_path.read_bytes()
    assert value("fio_load_game(3)") == 1
    check("native-load-wounded-and-zero", current(9) == 4 and maximum(9) == 30 and current(2) == 0 and maximum(2) == 15)
    check("opaque-partner-fields-retained", all(value(f"gPlayerData.partners[{p}].unk_02[{i}]") == 1000 + 3 * p + i
          for p in range(12) for i in range(3)))
    check("existing-badges-and-ship-flag-retained", value("is_ability_active(ABILITY_FLOWER_SAVER)") == 2
          and value("pause_get_total_equipped_bp_cost()") == 8 and value("gCurrentSaveFile.shipSaveData.hasDiedOnce") == 1)
    check("loading-health-does-not-activate-combat", value("gTtyd64PartnerHPPrototypeEnabled") == 0)

    # Mutate only this disposable fixture save; restore exact bytes even on fail.
    def load_variant(name, block, expected):
        data = json.loads(original)
        if block == "missing":
            del data["ship"]["ttyd64PartnerHP"]
        else:
            data["ship"]["ttyd64PartnerHP"] = block
        save_path.write_text(json.dumps(data))
        assert value("fio_load_game(3)") == 1
        actual = {p: (current(p), maximum(p)) for p in expected}
        if actual != expected:
            print("PARTNER_HP_JSON_MISMATCH=" + json.dumps({"case": name, "actual": actual, "expected": expected}))
        check("json-" + name, actual == expected)
        json_cases.append({"case": name, "observed": actual})
    try:
        full = {1: (10, 10), 2: (15, 15), 3: (40, 40), 9: (30, 30)}
        for name, block in (("legacy-absent", "missing"), ("null", None), ("wrong-shape", []),
                            ("future-version", {"version": 2, "partners": []}),
                            ("string-version", {"version": "1", "partners": []}),
                            ("wrong-partners", {"version": 1, "partners": "bad"})):
            load_variant(name, block, full)
        entries = [{"curHP": 9}, {"curHP": -4}, {"curHP": 99999}, {"curHP": False},
                   {"curHP": "7"}, {}, {"curHP": 0.5}, {"curHP": 0},
                   {"curHP": 18446744073709551615}, {"curHP": -9223372036854775808}]
        load_variant("partial-and-invalid-values", {"version": 1, "partners": entries},
                     {1: (0, 10), 2: (15, 15), 3: (40, 40), 4: (15, 15),
                      6: (15, 15), 7: (0, 35), 8: (20, 20), 9: (0, 30)})
        load_variant("max-is-derived", {"version": 1, "partners": [{}, {"curHP": 5, "maxHP": 9999}]}, {1: (5, 10), 2: (15, 15)})
        load_variant("extra-records-ignored", {"version": 1, "partners": [{"curHP": 1}] * 20}, {1: (1, 10), 9: (1, 30)})
    finally:
        save_path.write_bytes(original)
    assert value("fio_load_game(3)") == 1

    # Exercise the native vanilla converter, not a Python health migration.
    raw = value("(void*)calloc(1, sizeof(SaveData))")
    assert raw
    command(f"set $legacy = (VanillaSaveData*){raw}")
    assign("$legacy->player.partners[3].enabled", 1)
    assign("$legacy->player.partners[3].level", 2)
    assign("$legacy->player.partners[3].unk_02[1]", 12345)
    assign("$legacy->player.coins", 123)
    command(f"call ver_deserialize_vanilla_save((SaveData*){raw})")
    check("native-vanilla-conversion-health", value(f"((SaveData*){raw})->shipSaveData.partnerHP[3].curHP") == 40
          and value(f"((SaveData*){raw})->shipSaveData.partnerHP[3].maxHP") == 40)
    check("native-vanilla-conversion-original-data", value(f"((SaveData*){raw})->player.coins") == 123
          and value(f"((SaveData*){raw})->player.partners[3].level") == 2
          and value(f"((SaveData*){raw})->player.partners[3].unk_02[1]") == 12345)
    command(f"call (void)free((void*){raw})")

    command("call load_demo_battle(0)")
    command("return")
    stop_at("load_partner_actor")
    command("continue")
    assert value("fio_load_game(3)") == 1
    stop_at("calc_player_damage_enemy")
    command("continue")
    command("set scheduler-locking off")
    actor = "gBattleStatus.partnerActor"
    check("default-native-partner-hp-unmodified", value(f"{actor}->curHP") == 99 and current(9) == 4)
    check("inactive-setter-keeps-vanilla-actor", value("ttyd64_set_partner_hp(9, 3)") == 3 and value(f"{actor}->curHP") == 99)
    assert value("ttyd64_set_partner_hp(9, 4)") == 4
    assign("gTtyd64PartnerHPPrototypeEnabled", 1)
    command(f"call ttyd64_partner_hp_bind_actor({actor})")
    check("demo-context-excluded", value(f"{actor}->curHP") == 99)
    command("set variable gGameStatusPtr->demoBattleFlags &= ~DEMO_BTL_FLAG_ENABLED")
    command("set variable gBattleStatus.flags2 |= BS_FLAGS2_PEACH_BATTLE")
    command(f"call ttyd64_partner_hp_bind_actor({actor})")
    check("peach-context-excluded", value(f"{actor}->curHP") == 99)
    command("set variable gBattleStatus.flags2 &= ~BS_FLAGS2_PEACH_BATTLE")
    context = value("gGameStatusPtr->context")
    assign("gGameStatusPtr->context", value("CONTEXT_WORLD"))
    command(f"call ttyd64_partner_hp_bind_actor({actor})")
    check("world-context-excluded", value(f"{actor}->curHP") == 99)
    assign("gGameStatusPtr->context", context)
    command(f"call ttyd64_partner_hp_bind_actor({actor})")
    check("prototype-binds-loaded-health", value(f"{actor}->curHP") == 4 and value(f"{actor}->maxHP") == 30)
    check("bound-setter-syncs-current-actor", value("ttyd64_set_partner_hp(9, 2)") == 2 and value(f"{actor}->curHP") == 2)
    check("other-partner-setter-cannot-touch-current-actor", value("ttyd64_set_partner_hp(1, 6)") == 6 and value(f"{actor}->curHP") == 2)

    for partner, expected in ((2, 0), (1, 6), (9, 2)):
        assign("gBattleStatus.lastSelectedPartner", partner)
        assign("gBattleStatus.controlScriptID", 0)
        assign("gBattleSubState", 3)  # change_partner.c: LOAD_NEW_PARTNER
        command("call btl_state_update_change_partner()")
        hp, cap = value(f"{actor}->curHP"), value(f"{actor}->maxHP")
        check(f"native-swap-loads-partner-{partner}", value("gPlayerData.curPartner") == partner
              and hp == expected and cap == maximum(partner))
        swaps.append({"partner": partner, "cur_hp": hp, "max_hp": cap})
        # Inspect only the native LOAD_NEW_PARTNER boundary. The new init
        # script has not executed; remove that one script before the next
        # controlled swap rather than advancing the paused attack recursively.
        assert value(f"{actor}->takeTurnScript") == 0
        command(f"call kill_script_by_ID({actor}->takeTurnScriptID)")
    check("swaps-preserve-independent-health", current(1) == 6 and current(2) == 0 and current(9) == 2)
    old = value(actor)
    command(f"call btl_delete_actor((Actor*){old})")
    assign("gBattleStatus.partnerActor", 0)
    check("deleted-actor-unbound", value("BoundPartnerActor") == 0
          and value("ttyd64_set_partner_hp(9, 1)") == 1)
    assign("gPlayerData.curPartner", 0)
    command("call load_partner_actor()")
    check("no-partner-spawn-safe", value(actor) == 0)

    # Reload state and save health again, proving the model does not depend on
    # a live actor. Original fixture bytes are restored after this round trip.
    assert value("fio_load_game(3)") == 1
    assert value("ttyd64_set_partner_hp(9, 1)") == 1
    try:
        command("call fio_save_game(3)")
        assert value("fio_load_game(3)") == 1
        check("native-health-save-without-live-actor", current(9) == 1 and current(2) == 0)
    finally:
        save_path.write_bytes(original)
    report = {"checks_passed": len(checks), "fresh_process": load_only, "checks": checks,
              "source_rank_table": rows, "json_cases": json_cases, "native_swaps": swaps,
              "limits": "Default-off foundation; controlled native APIs/spawn/swap, not damage/death/revival/UI or a whole swap animation."}
    Path(os.environ["PARTNER_HP_RESULT"]).write_text(json.dumps(report, indent=2) + "\n")
    print("PARTNER_HP_PASSED=" + str(len(checks)))
    command("kill")


try:
    run_checks()
except Exception:
    import traceback
    traceback.print_exc()
    command("quit 1")
