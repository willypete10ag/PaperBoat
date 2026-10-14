#include "ttyd64_partner_hp.h"
#include "dx/versioning.h"

// Translated from PartnersHP.patch: $PartnersHPTable/$updatePartnerMaxHP.
// HP Plus P, damage/death, healing items and displayed HP are later consumers.
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

void ttyd64_partner_hp_begin_battle(void) {
    BoundPartnerActor = nullptr;
    BoundPartnerID = PARTNER_NONE;
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
    health->curHP = amount;
    sync_bound_actor(partnerID, health);
    return amount;
}

void ttyd64_reset_partner_hp(s32 partnerID) {
    Ttyd64PartnerHP* health = get_health(partnerID);
    if (health != nullptr) {
        health->curHP = health->maxHP;
        sync_bound_actor(partnerID, health);
    }
}

void ttyd64_partner_hp_bind_actor(Actor* actor) {
    ttyd64_partner_hp_begin_battle();
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
        ttyd64_partner_hp_begin_battle();
    }
}
