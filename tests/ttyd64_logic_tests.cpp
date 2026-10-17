#include "ttyd64_health_json.h"
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
int main() {
    const int table[12][3] = { { 0, 0, 0 },    { 10, 20, 30 }, { 10, 15, 25 }, { 15, 25, 40 },
                               { 15, 20, 25 }, { 0, 0, 0 },    { 10, 15, 20 }, { 15, 25, 35 },
                               { 15, 20, 30 }, { 10, 20, 30 }, { 0, 0, 0 },    { 0, 0, 0 } };
    int ranks[12] = {};
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
    const int allowed[] = { ITEM_LAST_STAND,    ITEM_PITY_FLOWER,    ITEM_JUMPMAN,        ITEM_HAMMERMAN,
                            ITEM_FP_DRAIN,      ITEM_FLOWER_SAVER_A, ITEM_FLOWER_SAVER_B, ITEM_DEFEND_PLUS_A,
                            ITEM_DEFEND_PLUS_X, ITEM_DEFEND_PLUS_Y };
    for (int id = 0; id < 0x180; ++id) {
        bool expected = false;
        for (auto a : allowed)
            expected |= a == id;
        CHECK(bool(ttyd64_badge_can_stack(id)) == expected);
    }
    // Known partial port: costs were translated; Double Dip stacking is not enabled.
    CHECK(!ttyd64_badge_can_stack(ITEM_DOUBLE_DIP));
    CHECK(!ttyd64_badge_can_stack(ITEM_TRIPLE_DIP));
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
    std::cout << checks << " ROM-free gameplay assertions passed\n";
}
