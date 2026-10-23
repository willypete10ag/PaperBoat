#include "ttyd64_partner_status.h"

// Active Item_VoltShroom / Item_ElectroPop scripts use the selected actor.
// Keep the original Mario script outside the living, saved-mode partner path.
API_CALLABLE(N(GetElectricTarget)) {
    Actor* owner = get_actor(script->owner1.actorID);
    script->varTable[9] = ACTOR_PLAYER;
    if (owner == gBattleStatus.playerActor && owner->targetActorID == ACTOR_PARTNER
        && !(gBattleStatus.flags1 & BS_FLAGS1_PARTNER_ACTING)
        && ttyd64_partner_status_can_target_item(gBattleStatus.moveArgument)) {
        script->varTable[9] = ACTOR_PARTNER;
    }
    return ApiStatus_DONE2;
}

API_CALLABLE(N(InflictElectric)) {
    Actor* target = get_actor(script->varTable[9]);
    inflict_status(target, STATUS_KEY_STATIC, script->varTable[0]);
    target->statusAfflicted = 0;
    return ApiStatus_DONE2;
}
