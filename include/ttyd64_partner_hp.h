#ifndef TTYD64_PARTNER_HP_H
#define TTYD64_PARTNER_HP_H

#include "common.h"

// Native save extension; the legacy PartnerData/PlayerData layouts stay intact.
#define TTYD64_PARTNER_HP_COUNT 12
typedef struct Ttyd64PartnerHP {
    s16 curHP;
    s16 maxHP;
} Ttyd64PartnerHP;

#ifdef __cplusplus
extern "C" {
#endif

// Development-only actor binding, off at startup/new game and never saved.
// Damage/death/item/UI consumers must be translated before normal activation.
extern b32 gTtyd64PartnerHPPrototypeEnabled;

// Returns -1 for no partner/noncombat IDs; clamps rank to the supported range.
s32 ttyd64_partner_base_max_hp(s32 partnerID, s32 rank);
void ttyd64_partner_hp_init(Ttyd64PartnerHP* health, const PlayerData* player);
void ttyd64_partner_hp_normalize(Ttyd64PartnerHP* health, const PlayerData* player);
void ttyd64_partner_hp_new_game(void);
s32 ttyd64_get_partner_hp(s32 partnerID);
s32 ttyd64_get_partner_max_hp(s32 partnerID);
s32 ttyd64_set_partner_hp(s32 partnerID, s32 amount);
void ttyd64_reset_partner_hp(s32 partnerID);

// Only bind eligible normal battles while the prototype is explicitly enabled.
void ttyd64_partner_hp_begin_battle(void);
void ttyd64_partner_hp_bind_actor(Actor* actor);
void ttyd64_partner_hp_unbind_actor(Actor* actor);

// First combat consumer: only the currently bound Goombario prototype.
b32 ttyd64_partner_combat_active(Actor* actor);
void ttyd64_partner_combat_load_hp(Actor* actor);
void ttyd64_partner_combat_store_hp(Actor* actor);
b32 ttyd64_partner_combat_check_defeat(void);
b32 ttyd64_partner_combat_allow_event(Actor* actor, s32 event);
void ttyd64_partner_combat_event_started(Actor* actor, s32 event, s32 scriptID);
b32 ttyd64_partner_combat_death_handled(Actor* actor);
void ttyd64_partner_combat_mark_dead(Actor* actor);
s32 ttyd64_partner_combat_use_life_shroom(Actor* actor);

// First ordinary healing-item consumer. Dead partners require revival, not food.
b32 ttyd64_partner_combat_can_heal_with_item(s32 itemID);
s32 ttyd64_partner_combat_heal(Actor* actor, s32 amount);

// Unsaved presentation state; do not reuse legacy partner/status-bar fields.
void ttyd64_partner_hp_sync_display(void);
void ttyd64_partner_hp_update_display(void);
s32 ttyd64_partner_hp_display(void);

#ifdef __cplusplus
}
#endif
#endif
