#include "ttyd64_health_json.h"
#include "ttyd64_mode_json.h"
#include "move_enum.h"
#include "item_enum.h"
#include <climits>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>
using nlohmann::ordered_json;
static int checks;
#define CHECK(x) \
    do { \
        ++checks; \
        if (!(x)) { \
            std::cerr << __LINE__ << ": " #x "\n"; \
            std::exit(1); \
        } \
    } while (0)
static uint32_t rng;
static int calls;
static int roll(int max) {
    ++calls;
    rng = 1664525U * rng + 1013904223U;
    return (rng >> 16) % (max + 1);
}
static int boundary;
static int fixed(int max) {
    CHECK(max == 100);
    return boundary;
}
int main(int argc, char** argv) {
    // External source oracle supplies actual native base costs; this path calls
    // the same pure lookups used by inventory/menu gameplay, without an engine.
    if (argc == 2 && std::string(argv[1]) == "--source-rules") {
        const auto input = ordered_json::parse(std::cin);
        auto costs = ordered_json::array();
        for (const auto& row : input.at("costs")) {
            int id = row.at("index"), fp = row.at("fp"), bp = row.at("bp");
            costs.push_back({ { "index", id },
                              { "vanilla", { ttyd64_mode_fp_cost(0, id, fp), ttyd64_mode_bp_cost(0, id, bp) } },
                              { "ttyd64", { ttyd64_mode_fp_cost(1, id, fp), ttyd64_mode_bp_cost(1, id, bp) } } });
        }
        auto health = ordered_json::array();
        for (int partner = 1; partner < TTYD64_PARTNER_HP_COUNT; ++partner) {
            health.push_back({ ttyd64_partner_base_max_hp(partner, 0),
                               ttyd64_partner_base_max_hp(partner, 1),
                               ttyd64_partner_base_max_hp(partner, 2) });
        }
        std::cout << ordered_json { { "costs", costs }, { "health", health } }.dump() << "\n";
        return 0;
    }
    // Independent persistence contract: never infer from health/proof content.
    CHECK(!ttyd64_mode_enabled());
    auto modeShip = ordered_json { { "hasDiedOnce", 1 }, { "otherExtension", { { "keep", 17 } } } };
    CHECK(ttyd64_read_mode(modeShip) == TTYD64_MODE_VANILLA);
    ttyd64_write_mode(modeShip, TTYD64_MODE_TTYD64);
    CHECK(ttyd64_read_mode(ordered_json::parse(modeShip.dump())) == TTYD64_MODE_TTYD64);
    CHECK(modeShip["hasDiedOnce"] == 1 && modeShip["otherExtension"]["keep"] == 17);
    CHECK(!ttyd64_mode_enabled()); // JSON preview never activates anything.
    ttyd64_mode_select_file(TTYD64_MODE_TTYD64);
    ttyd64_write_mode(modeShip, TTYD64_MODE_VANILLA);
    CHECK(ttyd64_read_mode(modeShip) == TTYD64_MODE_VANILLA && ttyd64_mode_enabled());
    for (const auto& invalid : {
            ordered_json(nullptr), ordered_json::array(), ordered_json(17),
            ordered_json { { "ttyd64PartnerHP", { { "version", 1 } } } },
            ordered_json { { "ttyd64Mode", true } },
            ordered_json { { "ttyd64Mode", { { "version", 1 } } } },
            ordered_json { { "ttyd64Mode", { { "version", 2 }, { "rules", "ttyd64" } } } },
            ordered_json { { "ttyd64Mode", { { "version", 1.0 }, { "rules", "ttyd64" } } } },
            ordered_json { { "ttyd64Mode", { { "version", "1" }, { "rules", "ttyd64" } } } },
            ordered_json { { "ttyd64Mode", { { "version", UINT64_MAX }, { "rules", "ttyd64" } } } },
            ordered_json { { "ttyd64Mode", { { "version", 1 }, { "rules", true } } } },
            ordered_json { { "ttyd64Mode", { { "version", 1 }, { "rules", "unknown" } } } } }) {
        CHECK(ttyd64_read_mode(invalid) == TTYD64_MODE_VANILLA);
        CHECK(ttyd64_mode_enabled());
    }
    for (int mode : { TTYD64_MODE_VANILLA, TTYD64_MODE_TTYD64 }) {
        ttyd64_mode_select_file(mode);
        CHECK(ttyd64_consumable_count() == (mode ? 104 : 96));
        CHECK(ttyd64_mode_consumable_id_at(95) == ITEM_FIRST_CONSUMABLE + 95);
        CHECK(ttyd64_mode_consumable_id_at(96) == (mode ? ITEM_COURAGE_SHELL : ITEM_NONE));
        CHECK(ttyd64_mode_consumable_id_at(ttyd64_consumable_count()) == ITEM_NONE);
        CHECK(ttyd64_mode_dip_menu_cost(mode, 3, 3, 0) == (mode ? 1 : 0));
        CHECK(ttyd64_mode_dip_menu_cost(mode, 3, 1, 2) == (mode ? 1 : -2));
        CHECK(ttyd64_mode_fp_cost(mode, MOVE_DOUBLE_DIP, 3) == (mode ? 4 : 3));
        CHECK(ttyd64_mode_fp_cost(mode, MOVE_TRIPLE_DIP, 6) == (mode ? 8 : 6));
        CHECK(ttyd64_mode_bp_cost(mode, MOVE_DOUBLE_DIP, 1) == (mode ? 3 : 1));
        CHECK(ttyd64_mode_bp_cost(mode, MOVE_DEFEND_PLUS, 6) == (mode ? 5 : 6));
        CHECK(ttyd64_mode_bp_cost(mode, MOVE_FLOWER_SAVER, 6) == (mode ? 4 : 6));
        CHECK(ttyd64_mode_bp_cost(mode, MOVE_POWER_JUMP, 1) == 1);
    }
    ttyd64_mode_select_file(INT_MAX);
    CHECK(!ttyd64_mode_enabled());
    CHECK(ttyd64_consumable_id_at(-1) == ITEM_NONE);
    CHECK(ttyd64_consumable_id_at(0) == ITEM_FIRST_CONSUMABLE);
    CHECK(ttyd64_consumable_id_at(95) == ITEM_FIRST_CONSUMABLE + 95);
    const int addedItems[] = { ITEM_COURAGE_SHELL, ITEM_POWER_PUNCH,   ITEM_MINI_MR_MINI, ITEM_MR_SOFTENER,
                               ITEM_SLOW_SHROOM,   ITEM_GRADUAL_SYRUP, ITEM_COUPLES_CAKE, ITEM_METEOR_MEAL };
    for (int i = 0; i < 8; ++i)
        CHECK(ttyd64_consumable_id_at(96 + i) == addedItems[i]);
    CHECK(ttyd64_consumable_id_at(ITEM_NUM_CONSUMABLES) == ITEM_NONE);
    CHECK(ttyd64_softener_amount(-1, 3) == 0);
    CHECK(ttyd64_softener_amount(0, 3) == 0);
    CHECK(ttyd64_softener_amount(1, 3) == -1);
    CHECK(ttyd64_softener_amount(2, 3) == -2);
    CHECK(ttyd64_softener_amount(3, 3) == -3);
    CHECK(ttyd64_softener_amount(INT_MAX, 3) == -3);
    CHECK(ttyd64_softener_amount(3, 0) == 0);
    const int table[12][3] = { { 0, 0, 0 },    { 10, 20, 30 }, { 10, 15, 25 }, { 15, 25, 40 },
                               { 15, 20, 25 }, { 0, 0, 0 },    { 10, 15, 20 }, { 15, 25, 35 },
                               { 15, 20, 30 }, { 10, 20, 30 }, { 0, 0, 0 },    { 0, 0, 0 } };
    int ranks[12] = {};
    const int homeY[12] = { -1, 0, 0, 0, 4, -1, 11, 0, 4, 9, -1, -1 };
    // Native-ID roster contract: eight HP records, four admitted adapters.
    // Temporary actors and incomplete Bow/Watt/Sushie/Lakilester adapters must
    // not become combat/world-ready merely because their HP JSON is valid.
    for (int partner : { INT_MIN, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, INT_MAX }) {
        bool health = partner == 1 || partner == 2 || partner == 3 || partner == 4
            || partner == 6 || partner == 7 || partner == 8 || partner == 9;
        bool ready = partner >= 1 && partner <= 4;
        CHECK(!!ttyd64_partner_has_hp_data(partner) == health);
        CHECK(!!ttyd64_partner_world_ready(partner) == ready);
        CHECK(!!ttyd64_partner_combat_ready(partner) == ready);
        CHECK(ttyd64_partner_battle_home_y(partner)
            == (partner >= 0 && partner < 12 ? homeY[partner] : -1));
    }
    Ttyd64PartnerHP h[12], loaded[12];
    for (int id = 0; id < 12; ++id)
        for (int rank = 0; rank < 3; ++rank)
            CHECK(ttyd64_partner_base_max_hp(id, rank) == (table[id][rank] ? table[id][rank] : -1));
    CHECK(ttyd64_partner_base_max_hp(INT_MIN, 0) == -1);
    CHECK(ttyd64_partner_base_max_hp(INT_MAX, 0) == -1);
    CHECK(ttyd64_partner_base_max_hp(1, INT_MIN) == 10);
    CHECK(ttyd64_partner_base_max_hp(3, INT_MAX) == 40);
    ranks[2] = 1;
    ranks[3] = 2;
    ttyd64_health_init(h, ranks);
    CHECK(h[2].curHP == 15 && h[3].curHP == 40 && h[5].curHP == 0);
    h[1] = { -3, 10 };
    h[2] = { 0, 15 };
    h[3] = { 32767, 1 };
    h[4] = { 0, 0 };
    h[5] = { 55, 55 };
    ttyd64_health_normalize(h, ranks);
    CHECK(h[1].curHP == 0);
    CHECK(h[2].curHP == 0);
    CHECK(h[3].curHP == 40 && h[3].maxHP == 40);
    CHECK(h[4].curHP == 15);
    CHECK(h[5].curHP == 0);
    auto ship = ordered_json { { "hasDiedOnce", 1 }, { "ttyd64PartnerHP", ttyd64_write_health(h, ranks) } };
    auto serialized = ship.dump();
    ttyd64_read_health(loaded, ranks, ordered_json::parse(serialized));
    for (int i = 0; i < 12; ++i)
        CHECK(loaded[i].curHP == h[i].curHP && loaded[i].maxHP == h[i].maxHP);
    CHECK(ship["hasDiedOnce"] == 1);
    for (auto invalid :
         { ordered_json::object(), ordered_json { { "ttyd64PartnerHP", nullptr } },
           ordered_json { { "ttyd64PartnerHP", { { "version", 2 }, { "partners", ordered_json::array() } } } },
           ordered_json { { "ttyd64PartnerHP", { { "version", 1 }, { "partners", 3 } } } } })
    {
        ttyd64_read_health(loaded, ranks, invalid);
        CHECK(loaded[1].curHP == 10 && loaded[2].curHP == 15);
    }
    auto entries = ordered_json::array(
        { nullptr,
          { { "curHP", -9223372036854775807LL } },
          { { "curHP", std::numeric_limits<uint64_t>::max() }, { "maxHP", 1 } },
          { { "curHP", 1.5 } },
          { { "curHP", 0 } },
          { { "curHP", 999 } },
          { { "curHP", "oops" } } }
    );
    ship["ttyd64PartnerHP"] = { { "version", 1 }, { "partners", entries } };
    ttyd64_read_health(loaded, ranks, ship);
    CHECK(loaded[1].curHP == 0);
    CHECK(loaded[2].curHP == 15);
    CHECK(loaded[3].curHP == 40);
    CHECK(loaded[4].curHP == 0);
    CHECK(loaded[5].curHP == 0);
    CHECK(loaded[6].curHP == 10);
    CHECK(loaded[9].curHP == 10);
    for (int i = 0; i < 30; ++i)
        entries.push_back({ { "curHP", 0 } });
    ship["ttyd64PartnerHP"]["partners"] = entries;
    ttyd64_read_health(loaded, ranks, ship);
    CHECK(loaded[11].curHP == 0);
    const int allowed[] = { ITEM_DOUBLE_DIP,    ITEM_LAST_STAND,     ITEM_PITY_FLOWER,    ITEM_JUMPMAN,
                            ITEM_HAMMERMAN,     ITEM_FP_DRAIN,       ITEM_FLOWER_SAVER_A, ITEM_FLOWER_SAVER_B,
                            ITEM_DEFEND_PLUS_A, ITEM_DEFEND_PLUS_X,  ITEM_DEFEND_PLUS_Y };
    for (int id = 0; id < 0x180; ++id) {
        bool expected = false;
        for (auto a : allowed)
            expected |= a == id;
        CHECK(bool(ttyd64_badge_can_stack(id)) == expected);
    }
    CHECK(ttyd64_badge_can_stack(ITEM_DOUBLE_DIP));
    CHECK(!ttyd64_badge_can_stack(ITEM_TRIPLE_DIP));
    CHECK(ttyd64_dip_menu_badge(ITEM_DOUBLE_DIP, 0, 0) == ITEM_DOUBLE_DIP);
    CHECK(ttyd64_dip_menu_badge(ITEM_DOUBLE_DIP, 1, 0) == ITEM_TRIPLE_DIP);
    CHECK(ttyd64_dip_menu_badge(ITEM_DOUBLE_DIP, 1, 1) == ITEM_NONE);
    CHECK(ttyd64_dip_menu_badge(ITEM_DOUBLE_DIP, 0, 1) == ITEM_DOUBLE_DIP);
    CHECK(ttyd64_dip_menu_badge(ITEM_TRIPLE_DIP, 0, 0) == ITEM_TRIPLE_DIP);
    CHECK(ttyd64_dip_menu_badge(ITEM_TRIPLE_DIP, 1, 1) == ITEM_NONE);
    CHECK(ttyd64_dip_menu_badge(ITEM_NONE, 1, 1) == ITEM_NONE);
    int16_t loadout[] = { ITEM_DOUBLE_DIP, 0, ITEM_DOUBLE_DIP, ITEM_LAST_STAND };
    int loadoutCosts[] = { 3, 0, 3, 1 };
    CHECK(ttyd64_trim_bp_loadout(loadout, loadoutCosts, 4, 7) == 0);
    CHECK(ttyd64_trim_bp_loadout(loadout, loadoutCosts, 4, 3) == 2);
    CHECK(loadout[0] == ITEM_DOUBLE_DIP && loadout[1] == 0 && loadout[2] == 0 && loadout[3] == 0);
    CHECK(ttyd64_trim_bp_loadout(loadout, loadoutCosts, 0, 0) == 0);
    int16_t signedLoadout[] = { ITEM_DOUBLE_DIP, ITEM_TRIPLE_DIP, ITEM_LAST_STAND };
    int signedCosts[] = { 3, 3, -2 };
    CHECK(ttyd64_trim_bp_loadout(signedLoadout, signedCosts, 3, 3) == 2);
    CHECK(signedLoadout[0] == ITEM_DOUBLE_DIP && !signedLoadout[1] && !signedLoadout[2]);
    int16_t noBudget[] = { ITEM_DOUBLE_DIP };
    int noBudgetCosts[] = { 3 };
    CHECK(ttyd64_trim_bp_loadout(noBudget, noBudgetCosts, 1, -1) == 1 && !noBudget[0]);

    CHECK(TTYD64_BP_DOUBLE_DIP == 3 && TTYD64_FP_DOUBLE_DIP == 4);
    CHECK(TTYD64_BP_TRIPLE_DIP == 3 && TTYD64_FP_TRIPLE_DIP == 8);
    CHECK(TTYD64_BP_LAST_STAND == 1 && TTYD64_BP_DEFEND_PLUS == 5 && TTYD64_BP_FLOWER_SAVER == 4);
    int bp[64] = { TTYD64_BP_FP_DRAIN, TTYD64_BP_FP_DRAIN, 0, TTYD64_BP_JUMPMAN, TTYD64_BP_DOUBLE_DIP };
    CHECK(ttyd64_total_bp_cost(bp, 64) == 11);
    bp[1] = 0;
    CHECK(ttyd64_total_bp_cost(bp, 64) == 8);
    bp[3] = 0;
    bp[4] = 0;
    CHECK(ttyd64_total_bp_cost(bp, 64) == 3);
    CHECK(ttyd64_total_bp_cost(bp, 0) == 0);
    for (int& cost : bp)
        cost = TTYD64_BP_PITY_FLOWER;
    CHECK(ttyd64_total_bp_cost(bp, 64) == 192);
    CHECK(ttyd64_move_fp_cost(0, 5, 2) == 0);
    CHECK(ttyd64_move_fp_cost(TTYD64_FP_DOUBLE_DIP, 2, 0) == 2);
    CHECK(ttyd64_move_fp_cost(4, 99, 2) == 1);
    CHECK(ttyd64_move_fp_cost(8, 1, 2) == 3);
    CHECK(ttyd64_last_stand_damage(6, 6, 3) == 6);
    CHECK(ttyd64_last_stand_damage(6, 5, 0) == 6);
    CHECK(ttyd64_last_stand_damage(6, 5, 1) == 3);
    CHECK(ttyd64_last_stand_damage(6, 5, 2) == 2);
    CHECK(ttyd64_last_stand_damage(1, 1, 64) == 0);
    int count = 0;
    for (int i = 0; i < 20; ++i)
        count = ttyd64_fp_drain_hit_count(count);
    CHECK(count == 5);
    CHECK(ttyd64_fp_drain_recovery(0, 3) == 0);
    CHECK(ttyd64_fp_drain_recovery(5, 0) == 0);
    CHECK(ttyd64_fp_drain_recovery(5, 3) == 7);
    for (int n : { 0, 32, 33, 100 }) {
        boundary = n;
        CHECK(ttyd64_pity_flower_recovery(3, fixed) == (n < 33 ? 3 : 0));
    }
    rng = 1234;
    calls = 0;
    int first = ttyd64_pity_flower_recovery(64, roll);
    CHECK(calls == 64);
    rng = 1234;
    calls = 0;
    CHECK(ttyd64_pity_flower_recovery(64, roll) == first);
    CHECK(calls == 64);
    // Freeze an independent expected value for this fixed RNG stream.
    CHECK(first == 21);
    CHECK(ttyd64_fp_recovery_cap(64, 98, 99) == 1);
    CHECK(ttyd64_fp_recovery_cap(3, 10, 10) == 0);
    CHECK(ttyd64_fp_recovery_cap(2, 1, 10) == 2);
    // Shared source overwrite/cancel/expiry rules, both axes and byte bounds.
    for (int enemy : { 0, 1 }) {
        Ttyd64ActorModifiers m {};
        ttyd64_modifier_apply(&m.attack, 2, 3, enemy);
        CHECK(m.attack.amount == 2 && m.attack.turns == 3 + enemy);
        ttyd64_modifier_apply(&m.attack, 1, 2, enemy);
        CHECK(m.attack.amount == 1 && m.attack.turns == 2 + enemy);
        m.size = 1;
        ttyd64_modifier_apply(&m.defense, -2, 1, enemy);
        ttyd64_modifiers_advance(&m);
        CHECK(m.attack.turns == 1 + enemy && m.size == 1);
        CHECK(m.defense.amount == (enemy ? -2 : 0));
        ttyd64_modifier_apply(&m.attack, -3, 4, enemy);
        ttyd64_modifiers_normalize_size(&m);
        CHECK(m.attack.amount == 0 && m.attack.turns == 0 && m.size == 0);
        ttyd64_modifier_apply(&m.attack, -1, 1, enemy);
        m.size = -1;
        for (int i = 0; i < 1 + enemy; ++i)
            ttyd64_modifiers_advance(&m);
        CHECK(m.attack.amount == 0 && m.size == 0);
        ttyd64_modifier_apply(&m.defense, -4, 3, enemy);
        ttyd64_modifier_apply(&m.defense, 1, 3, enemy);
        CHECK(m.defense.amount == 0 && m.defense.turns == 0);
        ttyd64_modifier_apply(&m.attack, INT_MIN, INT_MAX, enemy);
        CHECK(m.attack.amount == -128 && m.attack.turns == 255);
        ttyd64_modifier_apply(&m.attack, -2, 0, enemy);
        CHECK(m.attack.amount == 0 && m.attack.turns == 0);
        ttyd64_modifier_apply(&m.attack, INT_MAX, INT_MAX, enemy);
        CHECK(m.attack.amount == 127 && m.attack.turns == 255);
        ttyd64_modifier_apply(&m.attack, 0, 3, enemy);
        CHECK(m.attack.amount == 0 && m.attack.turns == 0);
    }
    // Direct regen overwrite differs from attack/defense cancellation. Both
    // axes get their final recovery before independent decay clears them.
    Ttyd64ActorModifiers regen {};
    ttyd64_regeneration_apply(&regen.hpRegen, 2, 10);
    ttyd64_regeneration_apply(&regen.fpRegen, 3, 2);
    int hp = 1, fp = 0;
    for (int turn = 0; turn < 10; ++turn) {
        hp = ttyd64_resource_after_regeneration(hp, 50, regen.hpRegen.amount);
        fp = ttyd64_resource_after_regeneration(fp, 5, regen.fpRegen.amount);
        ttyd64_modifiers_advance(&regen);
        CHECK(regen.hpRegen.turns == 9 - turn);
    }
    CHECK(hp == 21 && fp == 5);
    CHECK(!regen.hpRegen.amount && !regen.fpRegen.amount);
    ttyd64_regeneration_apply(&regen.hpRegen, -3, 4);
    ttyd64_regeneration_apply(&regen.hpRegen, 1, 2);
    CHECK(regen.hpRegen.amount == 1 && regen.hpRegen.turns == 2);
    ttyd64_regeneration_apply(&regen.hpRegen, INT_MIN, INT_MAX);
    CHECK(regen.hpRegen.amount == -128 && regen.hpRegen.turns == 255);
    ttyd64_regeneration_apply(&regen.fpRegen, INT_MAX, 1);
    CHECK(regen.fpRegen.amount == 127 && regen.fpRegen.turns == 1);
    ttyd64_regeneration_apply(&regen.hpRegen, 2, 0);
    CHECK(!regen.hpRegen.amount && !regen.hpRegen.turns);
    CHECK(ttyd64_resource_after_regeneration(1, 10, -3) == 0);
    CHECK(ttyd64_resource_after_regeneration(9, 10, 3) == 10);
    CHECK(ttyd64_resource_after_regeneration(INT_MAX, INT_MAX, INT_MAX) == INT_MAX);
    CHECK(ttyd64_resource_after_regeneration(1, -1, 3) == 0);
    std::cout << checks << " ROM-free gameplay assertions passed\n";
}
