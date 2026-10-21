#ifndef TTYD64_PARTNER_HP_H
#define TTYD64_PARTNER_HP_H

#include "common.h"

// Native save extension; the legacy PartnerData/PlayerData layouts stay intact.
#include "ttyd64_rules.h"

#ifdef __cplusplus
extern "C" {
#endif

// Returns -1 for no partner/noncombat IDs; clamps rank to the supported range.
s32 ttyd64_partner_base_max_hp(s32 partnerID, s32 rank);
void ttyd64_partner_hp_init(Ttyd64PartnerHP* health, const PlayerData* player);
void ttyd64_partner_hp_normalize(Ttyd64PartnerHP* health, const PlayerData* player);
void ttyd64_partner_hp_new_game(void);
s32 ttyd64_get_partner_hp(s32 partnerID);
s32 ttyd64_get_partner_max_hp(s32 partnerID);
s32 ttyd64_set_partner_hp(s32 partnerID, s32 amount);
void ttyd64_reset_partner_hp(s32 partnerID);
// Source level-up/world-heart consumers: current compatible partner only,
// including zero-HP recovery. Returns new HP, or -1 outside a normal TTYD64 file.
s32 ttyd64_heal_current_partner(s32 amount);
// World full-rest/Heart Block consumer; does not enable actor HP combat.
void ttyd64_fully_restore_partner_hp(void);

// Guarded world shroom recipients; selection lives in the native item script.
b32 ttyd64_world_item_can_target_partner(s32 itemID);
b32 ttyd64_world_item_target_menu_active(void);
s32 ttyd64_use_consumable_on_partner(s32 invSlot, s32 partnerID);

// Only bind eligible normal battles while the prototype is explicitly enabled.
void ttyd64_partner_hp_begin_battle(void);
void ttyd64_partner_hp_bind_actor(Actor* actor);
void ttyd64_partner_hp_unbind_actor(Actor* actor);

// Explicit supported ground group; other partners keep native combat.
b32 ttyd64_partner_hp_supported(s32 partnerID);
b32 ttyd64_has_hp_partner(void);
// Only the currently bound, supported partner can own combat HP.
b32 ttyd64_partner_combat_active(Actor* actor);
void ttyd64_partner_combat_load_hp(Actor* actor);
void ttyd64_partner_combat_store_hp(Actor* actor);
b32 ttyd64_partner_combat_begin_defeat(void);
b32 ttyd64_partner_combat_update_defeat(void);
b32 ttyd64_partner_combat_allow_event(Actor* actor, s32 event);
void ttyd64_partner_combat_event_started(Actor* actor, s32 event, s32 scriptID);
b32 ttyd64_partner_combat_death_handled(Actor* actor);
void ttyd64_partner_combat_mark_dead(Actor* actor);
s32 ttyd64_partner_combat_use_life_shroom(Actor* actor);

// Battle-local Kooper state survives actor replacement, never save serialization.
b32 ttyd64_kooper_flipped(Actor* actor);
s32 ttyd64_kooper_flip_turns(void);
void ttyd64_kooper_set_flipped(Actor* actor, b32 flipped);
s32 ttyd64_kooper_enemy_end(Actor* actor);
void ttyd64_partner_combat_begin_round(void);
void ttyd64_partner_combat_begin_player_turn(void);
b32 ttyd64_partner_combat_turn_blocked(Actor* actor);
s32 ttyd64_partner_combat_damage_event(Actor* actor, s32 event, s32 elements);

// Source team positions/targeting, scoped to the bound supported ground partner.
// Keep physical position (native PLAYER_IN_BACK) separate from acting turn.
b32 ttyd64_partner_team_active(void);
void ttyd64_partner_team_request_swap(void);
b32 ttyd64_partner_team_should_swap(b32 nativeSwap);
void ttyd64_partner_team_swap_completed(b32 nativePlayerInBack);
s32 ttyd64_partner_team_resolve_target(s32 targetActorID);
s32 ttyd64_partner_team_target(b32 back);

// First ordinary healing-item consumer. Dead partners require revival, not food.
b32 ttyd64_partner_combat_can_heal_with_item(s32 itemID);
s32 ttyd64_partner_combat_heal(Actor* actor, s32 amount);

// Unsaved presentation state; do not reuse legacy partner/status-bar fields.
void ttyd64_partner_hp_world_bind(s32 partnerID);
void ttyd64_partner_hp_world_unbind(void);
void ttyd64_partner_hp_sync_display(void);
void ttyd64_partner_hp_update_display(void);
s32 ttyd64_partner_hp_display(void);
s32 ttyd64_partner_hp_display_partner(void);

API_CALLABLE(Ttyd64PartnerHPState);
API_CALLABLE(Ttyd64PartnerRestoreDeadPose);
extern EvtScript EVS_Ttyd64PartnerDeath;

#ifdef __cplusplus
}
#endif
#endif
