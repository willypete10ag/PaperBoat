#ifndef TTYD64_PARTNER_STATUS_H
#define TTYD64_PARTNER_STATUS_H
#include "ttyd64_partner_hp.h"

#ifdef __cplusplus
extern "C" {
#endif

// Unsaved source Battle_StatusEffects/Battle_PartnersExtraActorData contracts.
void ttyd64_partner_status_reset(void);
void ttyd64_partner_status_bind(Actor* actor);
void ttyd64_partner_status_unbind(Actor* actor);
void ttyd64_partner_status_clear(Actor* actor);
void ttyd64_partner_status_cure_debuff(Actor* actor);
b32 ttyd64_partner_status_can_target_item(s32 itemID);
void ttyd64_partner_status_end_battle(void);
void ttyd64_partner_status_update(Actor* actor);
void ttyd64_partner_status_poison(void);
b32 ttyd64_partner_status_blocks_turn(Actor* actor);
void ttyd64_partner_status_sync_ko(Actor* actor);
#ifdef __cplusplus
}
#endif
#endif
