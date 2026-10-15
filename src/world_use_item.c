#include "common.h"
#include "effects.h"
#include "script_api/battle.h"
#include "sprite/player.h"
#include "ttyd64_partner_hp.h"
#include "world/partners.h"

b32 ttyd64_world_item_can_target_partner(s32 itemID) {
    if (!gTtyd64PartnerHPPrototypeEnabled || gGameStatusPtr->context != CONTEXT_WORLD
        || gGameStatusPtr->demoState != DEMO_STATE_NONE
        || (gPlayerStatus.animFlags & PA_FLAG_USING_PEACH_PHYSICS)
        || !gPlayerData.partners[PARTNER_GOOMBARIO].enabled) {
        return false;
    }
    switch (itemID) {
        case ITEM_MUSHROOM:
        case ITEM_SUPER_SHROOM:
        case ITEM_ULTRA_SHROOM:
        case ITEM_DRIED_SHROOM:
            return true;
    }
    return false;
}

API_CALLABLE(WorldItem_GetHPRecipientPos) {
    Bytecode* args = script->ptrReadPos;
    Vec3f* pos = &gPlayerStatus.pos;

    if (gTtyd64PartnerHPPrototypeEnabled && script->varTable[14] == PARTNER_GOOMBARIO
        && wCurrentPartnerId == PARTNER_GOOMBARIO && wPartnerNpc != nullptr) {
        pos = &wPartnerNpc->pos;
    }
    evt_set_variable(script, *args++, pos->x);
    evt_set_variable(script, *args++, pos->y);
    evt_set_variable(script, *args++, pos->z);
    return ApiStatus_DONE2;
}

API_CALLABLE(WorldItem_ShowUseSparkles) {
    Bytecode* args = script->ptrReadPos;
    s32 x = evt_get_variable(script, *args++);
    s32 y = evt_get_variable(script, *args++);
    s32 z = evt_get_variable(script, *args++);

    fx_sparkles(FX_SPARKLES_0, x, y, z, 60.0f);
    return ApiStatus_DONE2;
}

API_CALLABLE(WorldItem_ShowHPGain) {
    Bytecode* args = script->ptrReadPos;
    s32 x = evt_get_variable(script, *args++);
    s32 y = evt_get_variable(script, *args++);
    s32 z = evt_get_variable(script, *args++);
    s32 amt = evt_get_variable(script, *args++);

    fx_recover(0, x, y, z, amt);
    return ApiStatus_DONE2;
}

API_CALLABLE(WorldItem_ShowFPGain) {
    Bytecode* args = script->ptrReadPos;
    s32 x = evt_get_variable(script, *args++);
    s32 y = evt_get_variable(script, *args++);
    s32 z = evt_get_variable(script, *args++);
    s32 amt = evt_get_variable(script, *args++);

    fx_recover(1, x, y, z, amt);
    return ApiStatus_DONE2;
}

API_CALLABLE(WorldItem_RestoreHP) {
    PlayerData* playerData = &gPlayerData;
    s32 amount = evt_get_variable(script, *script->ptrReadPos);
    s32 newHP;

    if (script->varTable[14] == PARTNER_GOOMBARIO) {
        if (gTtyd64PartnerHPPrototypeEnabled && playerData->partners[PARTNER_GOOMBARIO].enabled) {
            // Active world-item source adds/caps even from zero HP. Battle
            // food's separate no-revival rule must not leak into this path.
            ttyd64_set_partner_hp(PARTNER_GOOMBARIO, ttyd64_get_partner_hp(PARTNER_GOOMBARIO) + amount);
        }
        return ApiStatus_DONE2;
    }
    newHP = playerData->curHP + amount;

    if (newHP > playerData->curMaxHP) {
        newHP = playerData->curMaxHP;
    }

    if (newHP <= 0) {
        newHP = 1;
    }

    playerData->curHP = newHP;
    return ApiStatus_DONE2;
}

API_CALLABLE(WorldItem_RestoreFP) {
    PlayerData* playerData = &gPlayerData;
    s32 newFP = playerData->curFP + evt_get_variable(script, *script->ptrReadPos);

    if (newFP > playerData->curMaxFP) {
        newFP = playerData->curMaxFP;
    }

    if (newFP <= 0) {
        newFP = 1;
    }

    playerData->curFP = newFP;
    return ApiStatus_DONE2;
}

API_CALLABLE(WorldItem_PauseTime) {
    set_time_freeze_mode(TIME_FREEZE_FULL);
#if !VERSION_JP
    gOverrideFlags |= GLOBAL_OVERRIDES_CANT_PICK_UP_ITEMS;
#endif
    return ApiStatus_DONE2;
}

API_CALLABLE(WorldItem_UnpauseTime) {
    set_time_freeze_mode(TIME_FREEZE_NONE);
#if !VERSION_JP
    gOverrideFlags &= ~GLOBAL_OVERRIDES_CANT_PICK_UP_ITEMS;
#endif
    return ApiStatus_DONE2;
}

API_CALLABLE(WorldItem_GetItemProperties) {
    s32 itemIdx = evt_get_variable(script, *script->ptrReadPos);
    s32 var15;

    script->varTable[11] = (&gItemTable[itemIdx])->potencyA;
    script->varTable[12] = (&gItemTable[itemIdx])->potencyB;
    script->varTable[13] = false;

    if ((&gItemTable[itemIdx])->typeFlags & ITEM_TYPE_FLAG_USE_DRINK_ANIMATION) {
        script->varTable[13] = true;
    }

    var15 = 0;
    if (script->varTable[11] < 0 || (script->varTable[11] <= 0 && script->varTable[12] < 0)) {
        var15 = 1;
    }
    script->varTable[15] = var15;

    return ApiStatus_DONE2;
}

API_CALLABLE(WorldItem_ConsumeItem) {
    remove_consumable();
    return ApiStatus_DONE2;
}

EvtScript EVS_WorldItem_ShowUsedItem = {
    SetGroup(EVT_GROUP_NEVER_PAUSE)
    Call(SetPlayerAnimation, ANIM_Mario1_UsePower)
    Call(WorldItem_GetHPRecipientPos, LVar0, LVar1, LVar2)
    Add(LVar1, 45)
    Call(MakeItemEntity, LVarA, LVar0, LVar1, LVar2, 1, 0)
    Set(LVarA, LVar0)
    Wait(15)
    Call(WorldItem_GetHPRecipientPos, LVar0, LVar1, LVar2)
    Add(LVar1, 20)
    Call(WorldItem_ShowUseSparkles, LVar0, LVar1, LVar2)
    Call(RemoveItemEntity, LVarA)
    Return
    End
};

EvtScript EVS_WorldItem_PlayEatingSounds = {
    Thread
        Loop(4)
            Call(PlaySound, SOUND_EAT_OR_DRINK)
            Wait(10)
        EndLoop
    EndThread
    Call(SetPlayerAnimation, ANIM_Mario1_Eat)
    Wait(45)
    Return
    End
};

EvtScript EVS_WorldItem_PlayDrinkingSounds = {
    Thread
        Loop(4)
            Call(PlaySound, SOUND_EAT_OR_DRINK)
            Wait(10)
        EndLoop
    EndThread
    Call(SetPlayerAnimation, ANIM_Mario1_Drink)
    Wait(45)
    Return
    End
};

EvtScript EVS_World_UseItem = {
    SetGroup(EVT_GROUP_NEVER_PAUSE)
    Call(DisablePlayerInput, true)
    Call(GetPartnerInUse, LVar0)
    IfNe(LVar0, 0)
        Call(InterruptUsePartner)
        Wait(20)
    EndIf
    Call(WorldItem_PauseTime)
    Call(WorldItem_GetItemProperties, LVarA)
    ExecWait(EVS_WorldItem_ShowUsedItem)
    IfEq(LVarE, PARTNER_GOOMBARIO)
        // Mario presents the food; retain the native partner's own idle AI.
        Call(SetPlayerAnimation, ANIM_Mario1_UsePower)
        Call(PlaySound, SOUND_EAT_OR_DRINK)
        Wait(45)
    Else
        IfEq(LVarD, 0)
            ExecWait(EVS_WorldItem_PlayEatingSounds)
        Else
            ExecWait(EVS_WorldItem_PlayDrinkingSounds)
        EndIf
    EndIf
    IfEq(LVarF, 1)
        Call(SetPlayerAnimation, ANIM_Mario1_StickOutTongue)
    EndIf
    IfGt(LVarB, 0)
        Call(WorldItem_GetHPRecipientPos, LVar0, LVar1, LVar2)
        Add(LVar0, 0)
        Add(LVar1, 35)
        Call(WorldItem_ShowHPGain, LVar0, LVar1, LVar2, LVarB)
    EndIf
    IfGt(LVarC, 0)
        Call(GetPlayerPos, LVar0, LVar1, LVar2)
        Add(LVar0, 20)
        Add(LVar1, 25)
        Call(WorldItem_ShowFPGain, LVar0, LVar1, LVar2, LVarC)
    EndIf
    Call(WorldItem_GetHPRecipientPos, LVar0, LVar1, LVar2)
    Add(LVar1, 25)
    Call(ShowStartRecoveryShimmer, LVar0, LVar1, LVar2, LVarB)
    IfNe(LVarB, 0)
        Call(WorldItem_RestoreHP, LVarB)
    EndIf
    IfNe(LVarC, 0)
        Call(WorldItem_RestoreFP, LVarC)
    EndIf
    IfEq(LVarF, 0)
        Wait(10)
        Call(SetPlayerAnimation, ANIM_Mario1_ThumbsUp)
        Wait(30)
    Else
        Wait(30)
    EndIf
    Call(WorldItem_GetHPRecipientPos, LVar0, LVar1, LVar2)
    Call(ShowRecoveryShimmer, LVar0, LVar1, LVar2, LVarB)
    Call(SetPlayerAnimation, ANIM_Mario1_Idle)
    Wait(20)
    Call(WorldItem_ConsumeItem)
    Call(DisablePlayerInput, false)
    Call(WorldItem_UnpauseTime)
    Return
    End
};
