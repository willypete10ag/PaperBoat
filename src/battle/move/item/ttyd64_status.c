#include "common.h"
#include "script_api/battle.h"
#include "sprite/player.h"
#include "ttyd64_status_items.h"
#include "ttyd64_mode.h"

#define NAMESPACE battle_item_ttyd64_status
#include "battle/common/move/ItemRefund.inc.c"
#include "battle/common/move/UseItem.inc.c"

API_CALLABLE(N(Prepare)) {
    script->varTable[10] = gBattleStatus.moveArgument;
    script->varTable[9] = gBattleStatus.moveArgument;
    script->varTable[8] = gBattleStatus.moveArgument == ITEM_COURAGE_SHELL
        || gBattleStatus.moveArgument == ITEM_POWER_PUNCH
        || (gBattleStatus.moveArgument >= ITEM_SLOW_SHROOM && gBattleStatus.moveArgument <= ITEM_METEOR_MEAL);
    script->varTable[7] = (gItemTable[gBattleStatus.moveArgument].typeFlags & ITEM_TYPE_FLAG_USE_DRINK_ANIMATION) != 0;
    script->varTable[1] = false;
    return ApiStatus_DONE2;
}
API_CALLABLE(N(Apply)) {
    Actor* owner = get_actor(script->owner1.actorID);
    ttyd64_status_item_apply(script->varTable[9], get_actor(owner->targetActorID), owner->targetPartID);
    return ApiStatus_DONE2;
}
// Active Battle_NewItems_BattleScripts shows one result after the whole item,
// even if Softener finds no positive defense or a boost cancels an old debuff.
API_CALLABLE(N(GetResultMessage)) {
    script->varTable[6] = -1;
    if (ttyd64_mode_enabled()) {
        switch (script->varTable[9]) {
            case ITEM_COURAGE_SHELL:
                script->varTable[6] = BTL_MSG_TTYD64_DEFENSE_BOOST;
                break;
            case ITEM_POWER_PUNCH:
                script->varTable[6] = BTL_MSG_TTYD64_ATTACK_BOOST;
                break;
            case ITEM_MR_SOFTENER:
                script->varTable[6] = BTL_MSG_TTYD64_DEFENSE_DROP;
                break;
            case ITEM_MINI_MR_MINI:
                script->varTable[6] = BTL_MSG_TTYD64_ATTACK_DROP;
                break;
        }
    }
    return ApiStatus_DONE2;
}
EvtScript N(EVS_UseItem) = {
    Call(N(Prepare))
    ExecWait(N(UseItemWithEffect))
    IfEq(LVar7, true)
        ExecWait(N(DrinkItem))
    EndIf
    Call(SetAnimation, ACTOR_PLAYER, 0, ANIM_Mario1_Idle)
    Call(UseBattleCamPreset, BTL_CAM_DEFAULT)
    IfEq(LVar8, true)
        Call(N(Apply))
    Else
        Call(InitTargetIterator)
        Label(0)
        Call(SetGoalToTarget, ACTOR_SELF)
        Set(LVar0, 0)
        Call(ItemCheckHit, LVar0, DAMAGE_TYPE_NO_CONTACT, 0, LVar0, 0)
        IfNe(LVar0, HIT_RESULT_MISS)
            Call(N(Apply))
        EndIf
        Wait(5)
        Call(ChooseNextTarget, ITER_NEXT, LVar0)
        IfNe(LVar0, ITER_NO_MORE)
            Goto(0)
        EndIf
    EndIf
    Wait(20)
    Call(N(GetResultMessage))
    IfNe(LVar6, -1)
        Call(ShowMessageBox, LVar6, 60)
        Call(WaitForMessageBoxDone)
    EndIf
    ExecWait(N(PlayerGoHome))
    Return
    End
};
