#ifndef TTYD64_ACTOR_MODIFIERS_H
#define TTYD64_ACTOR_MODIFIERS_H
#include "ttyd64_partner_hp.h"
#ifdef __cplusplus
extern "C" {
#endif
// Unsaved sidecars: no Actor/PartnerData/save ABI changes. Explicit source APIs
// coexist with the vanilla two-argument permanent BoostAttack/BoostDefense APIs.
b32 ttyd64_actor_modifiers_active(Actor* actor);
void ttyd64_actor_modifiers_reset(void);
void ttyd64_actor_modifiers_bind_partner(Actor* actor);
void ttyd64_actor_modifiers_unbind_partner(Actor* actor);
void ttyd64_actor_modifiers_forget(Actor* actor);
void ttyd64_actor_modifiers_clear(Actor* actor);
void ttyd64_actor_modifiers_clear_axis(Actor* actor, b32 defense);
void ttyd64_actor_modifiers_advance(void);
b32 ttyd64_actor_add_modifier(Actor* actor, b32 defense, s32 amount, s32 turns);
b32 ttyd64_actor_set_size(Actor* actor, s32 size);
s32 ttyd64_actor_attack_boost(Actor* actor);
s32 ttyd64_actor_defense_boost(Actor* actor);
f32 ttyd64_actor_size_target(Actor* actor);
b32 ttyd64_actor_is_tiny(Actor* actor);
API_CALLABLE(Ttyd64AddAttackBoost);
API_CALLABLE(Ttyd64AddDefenseBoost);
API_CALLABLE(Ttyd64MakeActorTiny);
API_CALLABLE(Ttyd64MakeActorGiant);
#ifdef __cplusplus
}
#endif
#endif
