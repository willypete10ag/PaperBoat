#include "ttyd64_rules.h"
#include "item_enum.h"
// PartnersHP.patch, $PartnersHPTable. IDs 5, 10, 11 are noncombat partners.
static const int16_t PartnerBaseHP[TTYD64_PARTNER_HP_COUNT][3] = { { 0, 0, 0 },    { 10, 20, 30 }, { 10, 15, 25 },
                                                                   { 15, 25, 40 }, { 15, 20, 25 }, { 0, 0, 0 },
                                                                   { 10, 15, 20 }, { 15, 25, 35 }, { 15, 20, 30 },
                                                                   { 10, 20, 30 }, { 0, 0, 0 },    { 0, 0, 0 } };
int ttyd64_partner_base_max_hp(int partner, int rank) {
    if (partner < 0 || partner >= TTYD64_PARTNER_HP_COUNT || !PartnerBaseHP[partner][0])
        return -1;
    if (rank < 0)
        rank = 0;
    if (rank > 2)
        rank = 2;
    return PartnerBaseHP[partner][rank];
}
void ttyd64_health_init(Ttyd64PartnerHP* health, const int* ranks) {
    for (int i = 0; i < TTYD64_PARTNER_HP_COUNT; ++i) {
        int maximum = ttyd64_partner_base_max_hp(i, ranks[i]);
        health[i].curHP = health[i].maxHP = maximum < 0 ? 0 : maximum;
    }
}
// Missing legacy state starts full; explicit zero with a valid maximum stays dead.
void ttyd64_health_normalize(Ttyd64PartnerHP* health, const int* ranks) {
    for (int i = 0; i < TTYD64_PARTNER_HP_COUNT; ++i) {
        int maximum = ttyd64_partner_base_max_hp(i, ranks[i]);
        if (maximum < 0) {
            health[i].curHP = health[i].maxHP = 0;
            continue;
        }
        if (health[i].maxHP <= 0)
            health[i].curHP = maximum;
        health[i].maxHP = maximum;
        if (health[i].curHP < 0)
            health[i].curHP = 0;
        if (health[i].curHP > maximum)
            health[i].curHP = maximum;
    }
}
int ttyd64_badge_can_stack(int badge) {
    switch (badge) {
        case ITEM_LAST_STAND:
        case ITEM_PITY_FLOWER:
        case ITEM_JUMPMAN:
        case ITEM_HAMMERMAN:
        case ITEM_FP_DRAIN:
        case ITEM_FLOWER_SAVER_A:
        case ITEM_FLOWER_SAVER_B:
        case ITEM_DEFEND_PLUS_A:
        case ITEM_DEFEND_PLUS_X:
        case ITEM_DEFEND_PLUS_Y:
            return 1;
        default:
            return 0;
    }
}
int ttyd64_total_bp_cost(const int* costs, int count) {
    int total = 0;
    for (int i = 0; i < count; ++i)
        total += costs[i];
    return total;
}
int ttyd64_move_fp_cost(int base, int savers, int fanatics) {
    if (base == 0)
        return 0;
    int cost = base - savers - 2 * fanatics;
    return cost < 1 ? 1 : cost;
}
int ttyd64_last_stand_damage(int damage, int hp, int copies) {
    return hp <= 5 && copies > 0 ? damage / (copies + 1) : damage;
}
int ttyd64_fp_drain_hit_count(int count) {
    return count < 5 ? count + 1 : count;
}
int ttyd64_fp_drain_recovery(int hits, int copies) {
    return hits > 0 && copies > 0 ? hits + copies - 1 : 0;
}
// Active TTYDBadges.patch Pity Flower hook 802781B4: one rand_int(100) < 33 per copy.
int ttyd64_pity_flower_recovery(int copies, int (*roll)(int)) {
    int recovered = 0;
    for (int i = 0; i < copies; ++i)
        recovered += roll(100) < 33;
    return recovered;
}
int ttyd64_fp_recovery_cap(int amount, int current, int maximum) {
    int missing = maximum - current;
    if (missing < 0)
        missing = 0;
    return amount < missing ? amount : missing;
}
