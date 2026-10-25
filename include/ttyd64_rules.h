#ifndef TTYD64_RULES_H
#define TTYD64_RULES_H
#include <stdint.h>
#define TTYD64_PARTNER_HP_COUNT 12
typedef struct Ttyd64PartnerHP {
    int16_t curHP;
    int16_t maxHP;
} Ttyd64PartnerHP;
// Battle_NewStatuses: signed overwrite/cancel effects with independent timers.
typedef struct Ttyd64TimedModifier {
    int8_t amount;
    uint8_t turns;
} Ttyd64TimedModifier;
typedef struct Ttyd64ActorModifiers {
    Ttyd64TimedModifier attack, defense;
    Ttyd64TimedModifier hpRegen, fpRegen;
    int8_t size; // -1 tiny, +1 giant; valid only with matching attack sign
} Ttyd64ActorModifiers;
#define TTYD64_BP_LAST_STAND   1
#define TTYD64_BP_PITY_FLOWER  3
#define TTYD64_BP_DEFEND_PLUS  5
#define TTYD64_BP_FLOWER_SAVER 4
#define TTYD64_BP_JUMPMAN      2
#define TTYD64_BP_HAMMERMAN    2
#define TTYD64_BP_FP_DRAIN     3
#define TTYD64_BP_DOUBLE_DIP   3
#define TTYD64_BP_TRIPLE_DIP   3
#define TTYD64_FP_DOUBLE_DIP   4
#define TTYD64_FP_TRIPLE_DIP   8
#ifdef __cplusplus
extern "C" {
#endif
void ttyd64_regeneration_apply(Ttyd64TimedModifier* effect, int amount, int turns);
int ttyd64_resource_after_regeneration(int current, int maximum, int amount);
void ttyd64_modifier_apply(Ttyd64TimedModifier* effect, int amount, int turns, int enemy);
void ttyd64_modifiers_advance(Ttyd64ActorModifiers* state);
void ttyd64_modifiers_normalize_size(Ttyd64ActorModifiers* state);
int ttyd64_consumable_id_at(int index);
int ttyd64_softener_amount(int defense, int potency);
int ttyd64_partner_base_max_hp(int partner, int rank);
int ttyd64_partner_has_hp_data(int partner);
int ttyd64_partner_world_ready(int partner);
int ttyd64_partner_combat_ready(int partner);
// Source battle home Y; -1 for noncombat IDs. Does not imply readiness.
int ttyd64_partner_battle_home_y(int partner);
void ttyd64_health_init(Ttyd64PartnerHP* health, const int* ranks);
void ttyd64_health_normalize(Ttyd64PartnerHP* health, const int* ranks);
int ttyd64_badge_can_stack(int badge);
int ttyd64_dip_menu_badge(int badge, int hasDoubleDip, int hasTripleDip);
int ttyd64_trim_bp_loadout(int16_t* badges, const int* costs, int count, int budget);
int ttyd64_total_bp_cost(const int* costs, int count);
int ttyd64_move_fp_cost(int base, int savers, int fanatics);
int ttyd64_last_stand_damage(int damage, int hp, int copies);
int ttyd64_fp_drain_hit_count(int count);
int ttyd64_fp_drain_recovery(int hits, int copies);
int ttyd64_pity_flower_recovery(int copies, int (*roll)(int));
int ttyd64_fp_recovery_cap(int amount, int current, int maximum);
#ifdef __cplusplus
}
#endif
#endif
