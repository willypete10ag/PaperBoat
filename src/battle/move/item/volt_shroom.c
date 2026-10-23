#include "common.h"
#include "script_api/battle.h"
#include "effects.h"
#include "sprite/player.h"

#define NAMESPACE battle_item_volt_shroom

#include "battle/common/move/ItemRefund.inc.c"

#include "battle/common/move/ElectricItem.inc.c"

#include "battle/common/move/UseItem.inc.c"

EvtScript N(EVS_UseItem) = {
    SetConst(LVarA, ITEM_VOLT_SHROOM)
    ExecWait(N(UseItemWithEffect))
    ExecWait(N(EatItem))
    Call(N(GetElectricTarget))
    Call(SetAnimation, ACTOR_PLAYER, 0, ANIM_Mario1_Idle)
    Call(GetActorPos, LVar9, LVar0, LVar1, LVar2)
    Set(LVar3, 20)
    Call(MultiplyByActorScale, LVar3)
    Add(LVar1, LVar3)
    SetF(LVar3, Float(1.0))
    Call(MultiplyByActorScale, LVar3)
    PlayEffect(EFFECT_SNAKING_STATIC, 0, LVar0, LVar1, LVar2, LVar3, 30, 0)
    Call(PlaySound, SOUND_VOLT_SHROOM_APPLY)
    Call(GetItemPower, ITEM_VOLT_SHROOM, LVar0, LVar1)
    Call(N(InflictElectric))
    Wait(20)
    Call(ShowMessageBox, BTL_MSG_PLAYER_CHARGED, 60)
    Call(WaitForMessageBoxDone)
    ExecWait(N(PlayerGoHome))
    Return
    End
};
