#include "ttyd64_partner_hp.h"
#include "dx/versioning.h"

// Translated from PartnersHP.patch: $PartnersHPTable/$updatePartnerMaxHP.
// Goombario combat below is a validated, default-off bounded prototype.
// HP Plus P, healing items and displayed HP remain later consumers.
static const s16 PartnerBaseHP[TTYD64_PARTNER_HP_COUNT][3] = {
    [PARTNER_GOOMBARIO]  = { 10, 20, 30 },
    [PARTNER_KOOPER]     = { 10, 15, 25 },
    [PARTNER_BOMBETTE]   = { 15, 25, 40 },
    [PARTNER_PARAKARRY]  = { 15, 20, 25 },
    [PARTNER_WATT]       = { 10, 15, 20 },
    [PARTNER_SUSHIE]     = { 15, 25, 35 },
    [PARTNER_LAKILESTER] = { 15, 20, 30 },
    [PARTNER_BOW]        = { 10, 20, 30 },
};

b32 gTtyd64PartnerHPPrototypeEnabled = false;
static Actor* BoundPartnerActor;
static s32 BoundPartnerID = PARTNER_NONE;
static u16 DeathHandledMask;
static s32 DeathScriptID;

s32 ttyd64_partner_base_max_hp(s32 partnerID, s32 rank) {
    if (partnerID < 0 || partnerID >= ARRAY_COUNT(PartnerBaseHP) || PartnerBaseHP[partnerID][0] == 0) {
        return -1;
    }
    if (rank < PARTNER_RANK_NORMAL) {
        rank = PARTNER_RANK_NORMAL;
    }
    if (rank > PARTNER_RANK_ULTRA) {
        rank = PARTNER_RANK_ULTRA;
    }
    return PartnerBaseHP[partnerID][rank];
}

void ttyd64_partner_hp_init(Ttyd64PartnerHP* health, const PlayerData* player) {
    s32 i;
    for (i = 0; i < TTYD64_PARTNER_HP_COUNT; i++) {
        s32 maximum = ttyd64_partner_base_max_hp(i, player->partners[i].level);
        health[i].maxHP = health[i].curHP = maximum < 0 ? 0 : maximum;
    }
}

void ttyd64_partner_hp_normalize(Ttyd64PartnerHP* health, const PlayerData* player) {
    s32 i;
    for (i = 0; i < TTYD64_PARTNER_HP_COUNT; i++) {
        s32 maximum = ttyd64_partner_base_max_hp(i, player->partners[i].level);
        if (maximum < 0) {
            health[i].maxHP = health[i].curHP = 0;
            continue;
        }
        // Missing legacy state starts full. Explicit zero HP with a valid
        // record remains zero. Maxima derive from rank until HP Plus P ports.
        if (health[i].maxHP <= 0) {
            health[i].curHP = maximum;
        }
        health[i].maxHP = maximum;
        if (health[i].curHP < 0) {
            health[i].curHP = 0;
        }
        if (health[i].curHP > maximum) {
            health[i].curHP = maximum;
        }
    }
}

static void clear_binding(void) {
    BoundPartnerActor = nullptr;
    BoundPartnerID = PARTNER_NONE;
    DeathScriptID = 0;
}

void ttyd64_partner_hp_begin_battle(void) {
    clear_binding();
    DeathHandledMask = 0;
}

void ttyd64_partner_hp_new_game(void) {
    ttyd64_partner_hp_init(gCurrentSaveFile.shipSaveData.partnerHP, &gPlayerData);
    gTtyd64PartnerHPPrototypeEnabled = false;
    ttyd64_partner_hp_begin_battle();
}

static Ttyd64PartnerHP* get_health(s32 partnerID) {
    if (ttyd64_partner_base_max_hp(partnerID, PARTNER_RANK_NORMAL) < 0) {
        return nullptr;
    }
    ttyd64_partner_hp_normalize(gCurrentSaveFile.shipSaveData.partnerHP, &gPlayerData);
    return &gCurrentSaveFile.shipSaveData.partnerHP[partnerID];
}

s32 ttyd64_get_partner_hp(s32 partnerID) {
    Ttyd64PartnerHP* health = get_health(partnerID);
    return health == nullptr ? -1 : health->curHP;
}

s32 ttyd64_get_partner_max_hp(s32 partnerID) {
    Ttyd64PartnerHP* health = get_health(partnerID);
    return health == nullptr ? -1 : health->maxHP;
}

static b32 can_bind_actor(void) {
    return gTtyd64PartnerHPPrototypeEnabled && gGameStatusPtr->context == CONTEXT_BATTLE
        && !(gGameStatusPtr->demoBattleFlags & DEMO_BTL_FLAG_ENABLED)
        && !(gPlayerStatusPtr->animFlags & PA_FLAG_USING_PEACH_PHYSICS)
        && !(gBattleStatus.flags2 & BS_FLAGS2_PEACH_BATTLE);
}

static void sync_bound_actor(s32 partnerID, Ttyd64PartnerHP* health) {
    if (can_bind_actor() && partnerID == BoundPartnerID && partnerID == gPlayerData.curPartner
        && BoundPartnerActor != nullptr && BoundPartnerActor == gBattleStatus.partnerActor) {
        BoundPartnerActor->curHP = health->curHP;
        BoundPartnerActor->maxHP = health->maxHP;
    }
}

s32 ttyd64_set_partner_hp(s32 partnerID, s32 amount) {
    Ttyd64PartnerHP* health = get_health(partnerID);
    if (health == nullptr) {
        return -1;
    }
    if (amount < 0) {
        amount = 0;
    }
    if (amount > health->maxHP) {
        amount = health->maxHP;
    }
    if (health->curHP == 0 && amount > 0) {
        DeathHandledMask &= ~(1 << partnerID);
    }
    health->curHP = amount;
    sync_bound_actor(partnerID, health);
    return amount;
}

void ttyd64_reset_partner_hp(s32 partnerID) {
    Ttyd64PartnerHP* health = get_health(partnerID);
    if (health != nullptr) {
        DeathHandledMask &= ~(1 << partnerID);
        health->curHP = health->maxHP;
        sync_bound_actor(partnerID, health);
    }
}

void ttyd64_partner_hp_bind_actor(Actor* actor) {
    clear_binding();
    if (actor == nullptr || actor != gBattleStatus.partnerActor || !can_bind_actor()) {
        return;
    }
    Ttyd64PartnerHP* health = get_health(gPlayerData.curPartner);
    if (health != nullptr) {
        BoundPartnerID = gPlayerData.curPartner;
        BoundPartnerActor = actor;
        sync_bound_actor(BoundPartnerID, health);
    }
}

void ttyd64_partner_hp_unbind_actor(Actor* actor) {
    if (actor == BoundPartnerActor) {
        clear_binding();
    }
}

b32 ttyd64_partner_combat_active(Actor* actor) {
    return can_bind_actor() && actor != nullptr && actor == BoundPartnerActor
        && actor == gBattleStatus.partnerActor && BoundPartnerID == PARTNER_GOOMBARIO
        && gPlayerData.curPartner == PARTNER_GOOMBARIO;
}

void ttyd64_partner_combat_load_hp(Actor* actor) {
    if (ttyd64_partner_combat_active(actor)) {
        actor->curHP = ttyd64_get_partner_hp(PARTNER_GOOMBARIO);
        actor->maxHP = ttyd64_get_partner_max_hp(PARTNER_GOOMBARIO);
    }
}

void ttyd64_partner_combat_store_hp(Actor* actor) {
    if (ttyd64_partner_combat_active(actor)) {
        ttyd64_set_partner_hp(PARTNER_GOOMBARIO, actor->curHP);
    }
}

b32 ttyd64_partner_combat_death_handled(Actor* actor) {
    return ttyd64_partner_combat_active(actor) && (DeathHandledMask & (1 << PARTNER_GOOMBARIO));
}

void ttyd64_partner_combat_mark_dead(Actor* actor) {
    if (ttyd64_partner_combat_active(actor) && actor->curHP == 0) {
        DeathHandledMask |= 1 << PARTNER_GOOMBARIO;
        gBattleStatus.flags2 |= BS_FLAGS2_PARTNER_TURN_USED;
        actor->flags &= ~ACTOR_FLAG_USING_IDLE_ANIM;
    }
}

b32 ttyd64_partner_combat_allow_event(Actor* actor, s32 event) {
    if (!ttyd64_partner_combat_active(actor)) {
        return true;
    }
    if (DeathScriptID != 0 && does_script_exist(DeathScriptID)) {
        return false;
    }
    if (ttyd64_get_partner_hp(PARTNER_GOOMBARIO) == 0) {
        return event == EVENT_DEATH && !ttyd64_partner_combat_death_handled(actor);
    }
    return true;
}

void ttyd64_partner_combat_event_started(Actor* actor, s32 event, s32 scriptID) {
    if (ttyd64_partner_combat_active(actor) && event == EVENT_DEATH) {
        DeathScriptID = scriptID;
    }
}

b32 ttyd64_partner_combat_check_defeat(void) {
    Actor* partner = gBattleStatus.partnerActor;
    if (!ttyd64_partner_combat_active(partner)) {
        return false;
    }
    if (DeathScriptID != 0 && does_script_exist(DeathScriptID)) {
        return true;
    }
    DeathScriptID = 0;
    if (ttyd64_get_partner_hp(PARTNER_GOOMBARIO) > 0 || ttyd64_partner_combat_death_handled(partner)) {
        return false;
    }
    // Let the previous hit animation finish before the source-style death event.
    if (partner->handleEventScript != nullptr && does_script_exist(partner->handleEventScriptID)) {
        return true;
    }
    if (partner->handleEventSource == nullptr) {
        return true;
    }
    dispatch_event_partner(EVENT_DEATH);
    return true;
}

s32 ttyd64_partner_combat_use_life_shroom(Actor* actor) {
    if (!ttyd64_partner_combat_active(actor) || ttyd64_get_partner_hp(PARTNER_GOOMBARIO) != 0
        || gPlayerData.curHP <= 0 || find_item(ITEM_LIFE_SHROOM) < 0) {
        return 0;
    }
    remove_item(ITEM_LIFE_SHROOM);
    // PartnersHP.patch $UseLifeShroom_Actor restores ten and returns the turn.
    s32 hp = ttyd64_set_partner_hp(PARTNER_GOOMBARIO, 10);
    gBattleStatus.flags2 &= ~BS_FLAGS2_PARTNER_TURN_USED;
    return hp;
}
