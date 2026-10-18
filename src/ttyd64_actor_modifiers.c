#include "ttyd64_actor_modifiers.h"
#include "battle/battle.h"
#include "effects.h"

// Source Battle_ExtraActorData_Everyone and Battle_PartnersExtraActorData.
// Partners retain their own records across swaps; inactive timers pause.
static struct {
    Actor* owner;
    Ttyd64ActorModifiers state;
} ModifierActors[1 + MAX_ENEMY_ACTORS];
static Ttyd64ActorModifiers PartnerModifiers[TTYD64_PARTNER_HP_COUNT];
static Actor* ModifierPartnerOwner;
static s32 ModifierPartnerID;

b32 ttyd64_actor_modifiers_active(Actor* actor) {
    if (actor == nullptr || !gTtyd64PartnerHPPrototypeEnabled || gGameStatusPtr->context != CONTEXT_BATTLE
        || (gGameStatusPtr->demoBattleFlags & DEMO_BTL_FLAG_ENABLED)
        || (gPlayerStatusPtr->animFlags & PA_FLAG_USING_PEACH_PHYSICS)
        || (gBattleStatus.flags2 & BS_FLAGS2_PEACH_BATTLE))
        return false;
    if (actor->actorID == ACTOR_PARTNER)
        return ttyd64_partner_combat_active(actor);
    return get_actor(actor->actorID) == actor;
}

static Ttyd64ActorModifiers* record(Actor* actor, b32 guarded) {
    if (actor == nullptr || (guarded && !ttyd64_actor_modifiers_active(actor)))
        return nullptr;
    if (actor == ModifierPartnerOwner && ModifierPartnerID > 0 && ModifierPartnerID < ARRAY_COUNT(PartnerModifiers))
        return &PartnerModifiers[ModifierPartnerID];
    s32 index = actor->actorID == ACTOR_PLAYER ? 0 : actor->actorID - ACTOR_ENEMY0 + 1;
    if (index < 0 || index >= ARRAY_COUNT(ModifierActors))
        return nullptr;
    if (ModifierActors[index].owner != actor) {
        if (!guarded)
            return nullptr;
        ModifierActors[index].owner = actor;
        ModifierActors[index].state = (Ttyd64ActorModifiers) { 0 };
    }
    return &ModifierActors[index].state;
}
void ttyd64_actor_modifiers_reset(void) {
    for (s32 i = 0; i < ARRAY_COUNT(ModifierActors); i++) {
        ModifierActors[i].owner = nullptr;
        ModifierActors[i].state = (Ttyd64ActorModifiers) { 0 };
    }
    for (s32 i = 0; i < ARRAY_COUNT(PartnerModifiers); i++)
        PartnerModifiers[i] = (Ttyd64ActorModifiers) { 0 };
    ModifierPartnerOwner = nullptr;
    ModifierPartnerID = PARTNER_NONE;
}
void ttyd64_actor_modifiers_bind_partner(Actor* actor) {
    if (ttyd64_partner_combat_active(actor)) {
        ModifierPartnerOwner = actor;
        ModifierPartnerID = gPlayerData.curPartner;
    }
}
void ttyd64_actor_modifiers_unbind_partner(Actor* actor) {
    if (actor == ModifierPartnerOwner) {
        ModifierPartnerOwner = nullptr;
        ModifierPartnerID = PARTNER_NONE;
    }
}
void ttyd64_actor_modifiers_forget(Actor* actor) {
    if (actor == ModifierPartnerOwner) {
        ttyd64_actor_modifiers_unbind_partner(actor);
        return;
    }
    for (s32 i = 0; i < ARRAY_COUNT(ModifierActors); i++)
        if (ModifierActors[i].owner == actor) {
            ModifierActors[i].owner = nullptr;
            ModifierActors[i].state = (Ttyd64ActorModifiers) { 0 };
        }
}
void ttyd64_actor_modifiers_clear(Actor* actor) {
    Ttyd64ActorModifiers* state = record(actor, false);
    if (state != nullptr)
        *state = (Ttyd64ActorModifiers) { 0 };
}
void ttyd64_actor_modifiers_clear_axis(Actor* actor, b32 defense) {
    Ttyd64ActorModifiers* state = record(actor, false);
    if (state != nullptr) {
        *(defense ? &state->defense : &state->attack) = (Ttyd64TimedModifier) { 0 };
        ttyd64_modifiers_normalize_size(state);
    }
}
// Mario's Actor.curHP is scratch storage, not initialized by load_player_actor.
// Enemy/partner actors own their live HP; Mario's authority is PlayerData.
static b32 alive(Actor* actor) {
    return actor->actorID == ACTOR_PLAYER ? gPlayerData.curHP > 0 : actor->curHP > 0;
}
b32 ttyd64_actor_set_regeneration(Actor* actor, b32 fp, s32 amount, s32 turns) {
    Ttyd64ActorModifiers* state = record(actor, true);
    if (state == nullptr || !alive(actor))
        return false;
    ttyd64_regeneration_apply(fp ? &state->fpRegen : &state->hpRegen, amount, turns);
    return true;
}
void ttyd64_actor_clear_regeneration(Actor* actor, b32 fp) {
    Ttyd64ActorModifiers* state = record(actor, true);
    if (state != nullptr)
        *(fp ? &state->fpRegen : &state->hpRegen) = (Ttyd64TimedModifier) { 0 };
}
static void update_rush(void) {
    gBattleStatus.rushFlags = RUSH_FLAG_NONE;
    gBattleStatus.flags2 &= ~BS_FLAGS2_HAS_RUSH;
    if (gPlayerData.curHP <= PERIL_THRESHOLD && is_ability_active(ABILITY_MEGA_RUSH))
        gBattleStatus.rushFlags = RUSH_FLAG_MEGA;
    else if (gPlayerData.curHP <= DANGER_THRESHOLD && is_ability_active(ABILITY_POWER_RUSH))
        gBattleStatus.rushFlags = RUSH_FLAG_POWER;
    if (gBattleStatus.rushFlags != RUSH_FLAG_NONE)
        gBattleStatus.flags2 |= BS_FLAGS2_HAS_RUSH;
}
s32 ttyd64_actor_regeneration_heal(Actor* actor, s32 amount) {
    if (!ttyd64_actor_modifiers_active(actor) || !alive(actor))
        return 0;
    s32 current = actor->actorID == ACTOR_PLAYER ? gPlayerData.curHP : actor->curHP;
    s32 maximum = actor->actorID == ACTOR_PLAYER ? gPlayerData.curMaxHP : actor->maxHP;
    s32 next = ttyd64_resource_after_regeneration(current, maximum, amount);
    if (actor->actorID == ACTOR_PLAYER) {
        gPlayerData.curHP = next;
        update_rush();
    } else if (actor->actorID == ACTOR_PARTNER) {
        ttyd64_set_partner_hp(gPlayerData.curPartner, next);
    } else {
        actor->curHP = next;
    }
    return next - current;
}
// Battle_StatusEffects begin-player-turn hook: all present actors recover
// before any timers decay. Inactive partner sidecars are deliberately untouched.
// Partner death clears buffs before Life Shroom; regeneration cannot revive.
void ttyd64_actor_regeneration_recover(void) {
    Actor* actors[2 + MAX_ENEMY_ACTORS];
    actors[0] = gBattleStatus.playerActor;
    actors[1] = gBattleStatus.partnerActor;
    for (s32 i = 0; i < MAX_ENEMY_ACTORS; i++)
        actors[i + 2] = gBattleStatus.enemyActors[i];
    b32 shown = false;
    for (s32 i = 0; i < ARRAY_COUNT(actors); i++) {
        Actor* actor = actors[i];
        Ttyd64ActorModifiers* state = record(actor, true);
        if (state == nullptr)
            continue;
        if (!alive(actor)) {
            *state = (Ttyd64ActorModifiers) { 0 };
            continue;
        }
        s32 hp = state->hpRegen.turns ? state->hpRegen.amount : 0;
        s32 fp = state->fpRegen.turns ? state->fpRegen.amount : 0;
        if (hp) {
            ttyd64_actor_regeneration_heal(actor, hp);
            fx_recover(0, actor->curPos.x, actor->curPos.y + 20, actor->curPos.z, hp);
            shown = true;
        }
        if (fp) {
            // Source displays enemy FP effects but only the player team owns FP.
            if (actor->actorID < ACTOR_ENEMY0)
                gPlayerData.curFP = ttyd64_resource_after_regeneration(gPlayerData.curFP, gPlayerData.curMaxFP, fp);
            fx_recover(1, actor->curPos.x, actor->curPos.y + (hp ? 43 : 20), actor->curPos.z, fp);
            shown = true;
        }
    }
    if (shown)
        sfx_play_sound(SOUND_HEART_PICKUP);
}
b32 ttyd64_actor_add_modifier(Actor* actor, b32 defense, s32 amount, s32 turns) {
    Ttyd64ActorModifiers* state = record(actor, true);
    if (state == nullptr || !alive(actor))
        return false;
    Ttyd64TimedModifier* effect = defense ? &state->defense : &state->attack;
    // Source API takes ownership of this axis, including cancellation against
    // an existing legacy boost. Legacy APIs explicitly release timed ownership.
    if (effect->turns == 0)
        effect->amount = defense ? actor->defenseBoost : actor->attackBoost;
    ttyd64_modifier_apply(effect, amount, turns, actor->actorID >= ACTOR_ENEMY0);
    if (defense)
        actor->defenseBoost = 0;
    else
        actor->attackBoost = 0;
    ttyd64_modifiers_normalize_size(state);
    return true;
}
b32 ttyd64_actor_set_size(Actor* actor, s32 size) {
    Ttyd64ActorModifiers* state = record(actor, true);
    if (state == nullptr || !alive(actor))
        return false;
    state->size = size < 0 ? -1 : (size > 0 ? 1 : 0);
    ttyd64_modifiers_normalize_size(state);
    return true;
}
s32 ttyd64_actor_attack_boost(Actor* actor) {
    Ttyd64ActorModifiers* state = record(actor, true);
    return state != nullptr && state->attack.turns ? state->attack.amount : actor->attackBoost;
}
s32 ttyd64_actor_defense_boost(Actor* actor) {
    Ttyd64ActorModifiers* state = record(actor, true);
    return state != nullptr && state->defense.turns ? state->defense.amount : actor->defenseBoost;
}
b32 ttyd64_actor_is_tiny(Actor* actor) {
    Ttyd64ActorModifiers* state = record(actor, true);
    return state != nullptr && state->size < 0 && state->attack.amount < 0 && state->attack.turns > 0;
}
f32 ttyd64_actor_size_target(Actor* actor) {
    Ttyd64ActorModifiers* state = record(actor, true);
    if (state != nullptr && state->attack.turns) {
        if (state->size < 0 && state->attack.amount < 0)
            return 0.4f;
        if (state->size > 0 && state->attack.amount > 0)
            return 2.0f;
    }
    return actor->debuff == STATUS_KEY_SHRINK ? 0.4f : 1.0f;
}
void ttyd64_actor_modifiers_advance(void) {
    Actor* actors[2 + MAX_ENEMY_ACTORS];
    actors[0] = gBattleStatus.playerActor;
    actors[1] = gBattleStatus.partnerActor;
    for (s32 i = 0; i < MAX_ENEMY_ACTORS; i++)
        actors[i + 2] = gBattleStatus.enemyActors[i];
    for (s32 i = 0; i < ARRAY_COUNT(actors); i++) {
        Ttyd64ActorModifiers* state = record(actors[i], true);
        if (state != nullptr) {
            if (!alive(actors[i]))
                *state = (Ttyd64ActorModifiers) { 0 };
            else
                ttyd64_modifiers_advance(state);
        }
    }
}
static Actor* api_actor(Evt* script, Bytecode** args) {
    s32 id = evt_get_variable(script, *(*args)++);
    return get_actor(id == ACTOR_SELF ? script->owner1.actorID : id);
}
static ApiStatus add_api(Evt* script, b32 defense) {
    Bytecode* args = script->ptrReadPos;
    Actor* actor = api_actor(script, &args);
    s32 amount = evt_get_variable(script, *args++);
    s32 turns = evt_get_variable(script, *args++);
    ttyd64_actor_add_modifier(actor, defense, amount, turns);
    return ApiStatus_DONE2;
}
static ApiStatus regeneration_api(Evt* script, b32 fp) {
    Bytecode* args = script->ptrReadPos;
    Actor* actor = api_actor(script, &args);
    s32 amount = evt_get_variable(script, *args++);
    s32 turns = evt_get_variable(script, *args++);
    ttyd64_actor_set_regeneration(actor, fp, amount, turns);
    return ApiStatus_DONE2;
}
API_CALLABLE(Ttyd64SetHPRegeneration) {
    return regeneration_api(script, false);
}
API_CALLABLE(Ttyd64SetFPRegeneration) {
    return regeneration_api(script, true);
}
API_CALLABLE(Ttyd64AddAttackBoost) {
    return add_api(script, false);
}
API_CALLABLE(Ttyd64AddDefenseBoost) {
    return add_api(script, true);
}
API_CALLABLE(Ttyd64MakeActorTiny) {
    Bytecode* args = script->ptrReadPos;
    ttyd64_actor_set_size(api_actor(script, &args), -1);
    return ApiStatus_DONE2;
}
API_CALLABLE(Ttyd64MakeActorGiant) {
    Bytecode* args = script->ptrReadPos;
    ttyd64_actor_set_size(api_actor(script, &args), 1);
    return ApiStatus_DONE2;
}
