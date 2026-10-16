#include "ttyd64_partner_status.h"
#include "battle/battle.h"
#include "effects.h"

// Source extra partner data, translated to named fields rather than ROM bytes.
// Ordinary inactive status timers pause; Kooper's inactive flip is independent.
typedef struct PartnerBattleStatus {
    s8 debuff;
    s8 debuffDuration;
    s8 staticDuration;
    s8 transparentDuration;
    s8 stoneDuration;
} PartnerBattleStatus;
static PartnerBattleStatus PartnerStatuses[TTYD64_PARTNER_HP_COUNT];
static Actor* StatusActor;

void ttyd64_partner_status_reset(void) {
    StatusActor = nullptr;
    for (s32 i = 0; i < ARRAY_COUNT(PartnerStatuses); i++) {
        PartnerStatuses[i] = (PartnerBattleStatus) {0};
    }
}

static void store(Actor* actor) {
    PartnerStatuses[gPlayerData.curPartner] = (PartnerBattleStatus) {
        actor->debuff, actor->debuffDuration, actor->staticDuration,
        actor->transparentDuration, actor->stoneDuration,
    };
}

b32 ttyd64_partner_status_blocks_turn(Actor* actor) {
    return ttyd64_partner_combat_active(actor)
        && ((actor->debuff != 0 && actor->debuff != STATUS_KEY_POISON
            && actor->debuff != STATUS_KEY_SHRINK) || actor->stoneStatus != 0);
}

void ttyd64_partner_status_sync_ko(Actor* actor) {
    if (!ttyd64_partner_combat_active(actor)) {
        return;
    }
    // Source counter mirrors the debuff timer except Shrink. It is display
    // state, not native damage KO; turn/guard admission uses the actual debuff.
    actor->koDuration = actor->debuff == STATUS_KEY_SHRINK ? 0 : actor->debuffDuration;
    actor->koStatus = actor->koDuration > 0 ? STATUS_KEY_KO : 0;
    actor->disableEffect->data.disableX->koDuration = actor->koDuration;
}

static void dismiss_ice(Actor* actor) {
    if (actor->icePillarEffect != nullptr) {
        actor->icePillarEffect->flags |= FX_INSTANCE_FLAG_DISMISS;
        actor->icePillarEffect = nullptr;
    }
}

// Tasty Tonic / Super Soda / Refresh clear debuffs, not beneficial statuses.
b32 ttyd64_partner_status_can_target_item(s32 itemID) {
    return (itemID == ITEM_TASTY_TONIC || itemID == ITEM_SUPER_SODA)
        && ttyd64_partner_combat_can_heal_with_item(ITEM_MUSHROOM);
}

void ttyd64_partner_status_cure_debuff(Actor* actor) {
    if (!ttyd64_partner_combat_active(actor)) {
        return;
    }
    dismiss_ice(actor);
    actor->debuff = actor->debuffDuration = 0;
    remove_status_debuff(actor->hudElementDataIndex);
    ttyd64_partner_status_sync_ko(actor);
    set_actor_pal_adjustment(actor, ACTOR_PAL_ADJUST_NONE);
    store(actor);
}

void ttyd64_partner_status_clear(Actor* actor) {
    if (!ttyd64_partner_combat_active(actor)) {
        return;
    }
    ttyd64_partner_status_cure_debuff(actor);
    PartnerStatuses[gPlayerData.curPartner] = (PartnerBattleStatus) {0};
    actor->staticStatus = actor->staticDuration = 0;
    actor->transparentStatus = actor->transparentDuration = 0;
    actor->stoneStatus = actor->stoneDuration = 0;
    remove_status_static(actor->hudElementDataIndex);
    remove_status_transparent(actor->hudElementDataIndex);
    ttyd64_partner_status_sync_ko(actor);
    set_actor_pal_adjustment(actor, ACTOR_PAL_ADJUST_NONE);
}

void ttyd64_partner_status_unbind(Actor* actor) {
    if (actor != nullptr && actor == StatusActor) {
        if (ttyd64_partner_combat_active(actor)) {
            store(actor);
            if (ttyd64_partner_status_blocks_turn(actor)) {
                gBattleStatus.flags2 |= BS_FLAGS2_PARTNER_TURN_USED;
            }
        }
        // Ownership survives a debugger flag toggle until native deletion.
        // Native delete owns icons/disable-X; ice is separately dismissed here.
        dismiss_ice(actor);
        StatusActor = nullptr;
    }
}

void ttyd64_partner_status_bind(Actor* actor) {
    if (!ttyd64_partner_combat_active(actor) || actor->curHP <= 0) {
        return;
    }
    StatusActor = actor;
    PartnerBattleStatus status = PartnerStatuses[gPlayerData.curPartner];
    if (status.debuff != 0 && status.debuffDuration > 0) {
        inflict_status(actor, status.debuff, status.debuffDuration);
    }
    if (status.staticDuration > 0) {
        inflict_status(actor, STATUS_KEY_STATIC, status.staticDuration);
    }
    if (status.transparentDuration > 0) {
        inflict_status(actor, STATUS_KEY_TRANSPARENT, status.transparentDuration);
    }
    if (status.stoneDuration > 0) {
        inflict_status(actor, STATUS_KEY_STONE, status.stoneDuration);
    }
    ttyd64_partner_status_sync_ko(actor);
    if (ttyd64_partner_status_blocks_turn(actor)) {
        gBattleStatus.flags2 |= BS_FLAGS2_PARTNER_TURN_USED;
    }
}

void ttyd64_partner_status_poison(void) {
    Actor* actor = gBattleStatus.partnerActor;
    // Source Battle_StatusEffects.patch 170E04, before duration advancement.
    if (ttyd64_partner_combat_active(actor) && actor->curHP > 0
        && actor->debuff == STATUS_KEY_POISON && actor->debuffDuration > 0) {
        dispatch_damage_event_partner(1, EVENT_HIT, false);
    }
}

void ttyd64_partner_status_update(Actor* actor) {
    if (!ttyd64_partner_combat_active(actor) || actor->curHP <= 0) {
        return;
    }
    // Source 170F00: advance once at player-turn maintenance, even if the
    // partner cannot act. Do not advance again at partner-turn admission.
    if (actor->debuff != 0) {
        if (actor->debuffDuration > 0) {
            actor->debuffDuration--;
        }
        if (actor->debuffDuration == 0) {
            actor->debuff = 0;
            remove_status_debuff(actor->hudElementDataIndex);
            dismiss_ice(actor);
            // Hit/poison reactions own their event until done. Recovery is
            // cosmetic and must never replace a pending lethal/death event.
            if (actor->handleEventScript == nullptr || !does_script_exist(actor->handleEventScriptID)) {
                dispatch_event_partner(EVENT_RECOVER_FROM_KO);
            }
        }
    }
    if (actor->staticDuration > 0 && --actor->staticDuration == 0) {
        actor->staticStatus = 0;
        remove_status_static(actor->hudElementDataIndex);
    }
    if (actor->transparentDuration > 0 && --actor->transparentDuration == 0) {
        actor->transparentStatus = 0;
        remove_status_transparent(actor->hudElementDataIndex);
    }
    if (actor->stoneDuration > 0 && --actor->stoneDuration == 0) {
        actor->stoneStatus = 0;
    }
    ttyd64_partner_status_sync_ko(actor);
    store(actor);
}

void ttyd64_partner_status_end_battle(void) {
    ttyd64_partner_status_clear(gBattleStatus.partnerActor);
    if (StatusActor != nullptr) {
        dismiss_ice(StatusActor);
    }
    ttyd64_partner_status_reset();
}
