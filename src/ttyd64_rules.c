#include "ttyd64_rules.h"
#include "item_enum.h"
// Appended consumables are separated from the original contiguous range by
// badges/keys/menu IDs. Preserve those IDs and keep every legacy list valid.
int ttyd64_consumable_id_at(int index) {
    if (index < 0 || index >= ITEM_NUM_CONSUMABLES)
        return ITEM_NONE;
    if (index < ITEM_NUM_VANILLA_CONSUMABLES)
        return ITEM_FIRST_CONSUMABLE + index;
    return ITEM_COURAGE_SHELL + index - ITEM_NUM_VANILLA_CONSUMABLES;
}
int ttyd64_softener_amount(int defense, int potency) {
    if (defense <= 0 || potency <= 0)
        return 0;
    return -(defense < potency ? defense : potency);
}
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
// Native IDs, not source compact extra-data order (Bow occupies native ID 9).
// World presentation/recipient support and combat lifecycle readiness are
// deliberately separate contracts, even where today's admitted sets coincide.
static const struct { uint8_t world, combat; int8_t homeY; } PartnerAdapters[TTYD64_PARTNER_HP_COUNT] = {
    [1] = { 1, 1 }, // Goombario
    [2] = { 1, 1 }, // Kooper
    [3] = { 1, 1 }, // Bombette
    [4] = { 1, 1, 4 }, // Parakarry
    [6] = { 0, 0, 11 }, // Watt: source height only; adapter not admitted
    [7] = { 0, 0, 0 }, // Sushie
    [8] = { 0, 0, 4 }, // Lakilester
    [9] = { 0, 0, 9 }, // Bow
};
int ttyd64_partner_has_hp_data(int partner) {
    return ttyd64_partner_base_max_hp(partner, 0) >= 0;
}
int ttyd64_partner_world_ready(int partner) {
    return ttyd64_partner_has_hp_data(partner) && PartnerAdapters[partner].world;
}
int ttyd64_partner_combat_ready(int partner) {
    return ttyd64_partner_has_hp_data(partner) && PartnerAdapters[partner].combat;
}
int ttyd64_partner_battle_home_y(int partner) {
    return ttyd64_partner_has_hp_data(partner) ? PartnerAdapters[partner].homeY : -1;
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
        case ITEM_DOUBLE_DIP:
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
// Active TTYD_BadgeSystem.patch hooks802A63D0/802A6414: the first
// Double Dip adds Double Dip, the second adds Triple Dip, further copies add
// nothing. A standalone Triple Dip shares that row, irrespective of order.
int ttyd64_dip_menu_badge(int badge, int hasDoubleDip, int hasTripleDip) {
    if (badge == ITEM_DOUBLE_DIP && hasDoubleDip)
        badge = ITEM_TRIPLE_DIP;
    return badge == ITEM_TRIPLE_DIP && hasTripleDip ? ITEM_NONE : badge;
}
// Experimental TTYD64 files can predate a BP-cost correction. Drop equipped
// slots from the end until affordable; owned inventory and its order are intact.
int ttyd64_trim_bp_loadout(int16_t* badges, const int* costs, int count, int budget) {
    int total = ttyd64_total_bp_cost(costs, count);
    int removed = 0;
    if (budget < 0)
        budget = 0;
    for (int i = count - 1; i >= 0 && total > budget; --i) {
        if (badges[i]) {
            badges[i] = 0;
            total -= costs[i];
            ++removed;
        }
    }
    return removed;
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

// Active AddAttackBoost/AddDefenseBoost: opposite signs cancel completely;
// same sign replaces strength and timer. Enemy applications store one extra turn.
void ttyd64_modifier_apply(Ttyd64TimedModifier* effect, int amount, int turns, int enemy) {
    int opposite = (effect->amount < 0 && amount > 0) || (effect->amount > 0 && amount < 0);
    if (opposite || amount == 0 || turns <= 0) {
        *effect = (Ttyd64TimedModifier) { 0 };
        return;
    }
    effect->amount = amount < -128 ? -128 : (amount > 127 ? 127 : amount);
    effect->turns = turns >= 255 ? 255 : turns + !!enemy;
}
void ttyd64_modifiers_normalize_size(Ttyd64ActorModifiers* state) {
    if (state->attack.turns == 0 || (state->size < 0 && state->attack.amount >= 0)
        || (state->size > 0 && state->attack.amount <= 0))
        state->size = 0;
}
// HP/FP source setters overwrite directly, without sign cancellation or an
// enemy extra turn. Expiry is after recovery; keep arithmetic bounded in C.
void ttyd64_regeneration_apply(Ttyd64TimedModifier* effect, int amount, int turns) {
    if (!amount || turns <= 0) {
        *effect = (Ttyd64TimedModifier) { 0 };
        return;
    }
    effect->amount = amount < -128 ? -128 : (amount > 127 ? 127 : amount);
    effect->turns = turns > 255 ? 255 : turns;
}
int ttyd64_resource_after_regeneration(int current, int maximum, int amount) {
    int64_t next = (int64_t) current + amount;
    if (maximum < 0 || next < 0)
        return 0;
    return next > maximum ? maximum : (int) next;
}
void ttyd64_modifiers_advance(Ttyd64ActorModifiers* state) {
    if (state->hpRegen.turns && --state->hpRegen.turns == 0)
        state->hpRegen.amount = 0;
    if (state->fpRegen.turns && --state->fpRegen.turns == 0)
        state->fpRegen.amount = 0;
    if (state->attack.turns && --state->attack.turns == 0)
        state->attack.amount = 0;
    if (state->defense.turns && --state->defense.turns == 0)
        state->defense.amount = 0;
    ttyd64_modifiers_normalize_size(state);
}
