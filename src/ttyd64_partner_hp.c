#include "ttyd64_actor_modifiers.h"
#include "ttyd64_partner_status.h"
#include "ttyd64_partner_hp.h"
#include "dx/versioning.h"

static Actor* BoundPartnerActor;
static s32 BoundPartnerID = PARTNER_NONE;
static u16 DeathHandledMask;
static s32 DeathScriptID;
static b32 TeamSwapRequested;
static s32 WorldPartnerID = PARTNER_NONE;
static Actor* DisplayPartnerActor;
static b32 DisplayPartnerInWorld;
static s32 DisplayPartnerHP = -1;
static s32 DisplayPartnerHPTimer;

static void partner_ranks(int* ranks, const PlayerData* player) {
    for (int i = 0; i < TTYD64_PARTNER_HP_COUNT; ++i) {
        ranks[i] = player->partners[i].level;
    }
}
void ttyd64_partner_hp_init(Ttyd64PartnerHP* health, const PlayerData* player) {
    int ranks[TTYD64_PARTNER_HP_COUNT];
    partner_ranks(ranks, player);
    ttyd64_health_init(health, ranks);
}
void ttyd64_partner_hp_normalize(Ttyd64PartnerHP* health, const PlayerData* player) {
    int ranks[TTYD64_PARTNER_HP_COUNT];
    partner_ranks(ranks, player);
    ttyd64_health_normalize(health, ranks);
}

// Active 01 Kooper.bpat C/D contracts, represented without legacy actor bytes.
static struct {
    b32 flipped;
    s32 turns;
} KooperFlip;

static void clear_binding(void) {
    BoundPartnerActor = nullptr;
    BoundPartnerID = PARTNER_NONE;
    DeathScriptID = 0;
    TeamSwapRequested = false;
    DisplayPartnerActor = nullptr;
    DisplayPartnerInWorld = false;
    DisplayPartnerHP = -1;
    DisplayPartnerHPTimer = 0;
}

void ttyd64_partner_hp_begin_battle(void) {
    clear_binding();
    DeathHandledMask = 0;
    ttyd64_partner_status_reset();
    ttyd64_actor_modifiers_reset();
    KooperFlip.flipped = false;
    KooperFlip.turns = 0;
}

void ttyd64_partner_hp_new_game(void) {
    ttyd64_partner_hp_init(gCurrentSaveFile.shipSaveData.partnerHP, &gPlayerData);
    ttyd64_mode_select_file(TTYD64_MODE_VANILLA);
    WorldPartnerID = PARTNER_NONE;
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

b32 ttyd64_partner_hp_supported(s32 partnerID) {
    return partnerID == PARTNER_GOOMBARIO || partnerID == PARTNER_KOOPER || partnerID == PARTNER_BOMBETTE;
}

b32 ttyd64_has_hp_partner(void) {
    for (s32 i = 1; i < TTYD64_PARTNER_HP_COUNT; i++) {
        if (ttyd64_partner_hp_supported(i) && gPlayerData.partners[i].enabled) {
            return true;
        }
    }
    return false;
}

static b32 can_bind_actor(void) {
    return ttyd64_mode_enabled() && gGameStatusPtr->context == CONTEXT_BATTLE
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

s32 ttyd64_heal_current_partner(s32 amount) {
    s32 partnerID = gPlayerData.curPartner;
    s32 context = gGameStatusPtr->context;
    s32 current;
    s32 maximum;

    // PartnersHP.patch hooks 18CF98/801352E0 use Get/SetPartnerHP for the
    // current identity, unlike the separate full-rest all-partner hook.
    if (!ttyd64_mode_enabled() || (context != CONTEXT_WORLD && context != CONTEXT_BATTLE)
        || (gPlayerStatusPtr->animFlags & PA_FLAG_USING_PEACH_PHYSICS)
        || (context == CONTEXT_WORLD && gGameStatusPtr->demoState != DEMO_STATE_NONE)
        || (context == CONTEXT_BATTLE && ((gGameStatusPtr->demoBattleFlags & DEMO_BTL_FLAG_ENABLED)
            || (gBattleStatus.flags2 & BS_FLAGS2_PEACH_BATTLE)))) {
        return -1;
    }
    maximum = ttyd64_get_partner_max_hp(partnerID);
    if (maximum < 0) {
        return -1;
    }
    current = ttyd64_get_partner_hp(partnerID);
    if (amount <= 0) {
        return current;
    }
    // Bound before addition, including externally supplied large amounts.
    if (amount > maximum - current) {
        amount = maximum - current;
    }
    return ttyd64_set_partner_hp(partnerID, current + amount);
}

void ttyd64_fully_restore_partner_hp(void) {
    if (!ttyd64_mode_enabled()) return;
    s32 i;
    b32 anyUnlocked = false;

    // PartnersHP.patch $Function_GetPartnersUnlocked/$Function_HealPartners:
    // if any combat partner is recruited, restore every compatible HP record.
    // Do not recruit locked partners or touch legacy partner data.
    for (i = 0; i < TTYD64_PARTNER_HP_COUNT; i++) {
        if (ttyd64_partner_base_max_hp(i, PARTNER_RANK_NORMAL) >= 0 && gPlayerData.partners[i].enabled) {
            anyUnlocked = true;
            break;
        }
    }
    if (!anyUnlocked) {
        return;
    }
    for (i = 0; i < TTYD64_PARTNER_HP_COUNT; i++) {
        if (ttyd64_partner_base_max_hp(i, PARTNER_RANK_NORMAL) >= 0) {
            ttyd64_reset_partner_hp(i);
        }
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
        ttyd64_actor_modifiers_bind_partner(actor);
        ttyd64_partner_status_bind(actor);
    }
}

void ttyd64_partner_hp_unbind_actor(Actor* actor) {
    if (actor == BoundPartnerActor) {
        ttyd64_partner_status_unbind(actor);
        ttyd64_actor_modifiers_unbind_partner(actor);
        clear_binding();
    }
}

b32 ttyd64_partner_combat_active(Actor* actor) {
    return can_bind_actor() && actor != nullptr && actor == BoundPartnerActor
        && actor == gBattleStatus.partnerActor && ttyd64_partner_hp_supported(BoundPartnerID)
        && gPlayerData.curPartner == BoundPartnerID;
}

b32 ttyd64_kooper_flipped(Actor* actor) {
    return ttyd64_partner_combat_active(actor) && BoundPartnerID == PARTNER_KOOPER && KooperFlip.flipped;
}

s32 ttyd64_kooper_flip_turns(void) {
    return KooperFlip.turns;
}

void ttyd64_kooper_set_flipped(Actor* actor, b32 flipped) {
    if (ttyd64_partner_combat_active(actor) && BoundPartnerID == PARTNER_KOOPER) {
        KooperFlip.flipped = flipped;
        KooperFlip.turns = flipped ? 2 : 0;
    }
}

s32 ttyd64_kooper_enemy_end(Actor* actor) {
    if (!ttyd64_kooper_flipped(actor) || actor->curHP <= 0 || KooperFlip.turns <= 0) {
        return -1;
    }
    return --KooperFlip.turns;
}

b32 ttyd64_partner_combat_turn_blocked(Actor* actor) {
    return ttyd64_partner_combat_active(actor)
        && (ttyd64_get_partner_hp(BoundPartnerID) <= 0 || ttyd64_kooper_flipped(actor) || ttyd64_partner_status_blocks_turn(actor));
}

void ttyd64_partner_combat_begin_round(void) {
    Actor* actor = gBattleStatus.partnerActor;
    if (ttyd64_partner_combat_active(actor)
        && (ttyd64_get_partner_hp(BoundPartnerID) <= 0 || ttyd64_kooper_flipped(actor))) {
        gBattleStatus.flags2 |= BS_FLAGS2_PARTNER_TURN_USED;
        // PartnersHP.patch 80241B74: the recovery round is still unavailable.
        // GetsUp restores the pose/defense at enemy end, before this latch clears.
        if (ttyd64_kooper_flipped(actor) && KooperFlip.turns == 0) {
            KooperFlip.flipped = false;
        }
    }
}

void ttyd64_partner_combat_begin_player_turn(void) {
    Actor* actor = gBattleStatus.partnerActor;
    ttyd64_actor_regeneration_recover();
    ttyd64_actor_modifiers_advance();
    ttyd64_partner_status_update(actor);
    // Battle_PartnersExtraActorData.patch AdvancePartnersExtraData: inactive
    // Kooper also recovers over rounds. Saturate rather than wrap the source byte.
    if (ttyd64_partner_combat_active(actor) && BoundPartnerID != PARTNER_KOOPER
        && KooperFlip.flipped && KooperFlip.turns > 0) {
        KooperFlip.turns--;
    }
}

s32 ttyd64_partner_combat_damage_event(Actor* actor, s32 event, s32 elements) {
    if (ttyd64_partner_combat_active(actor) && BoundPartnerID == PARTNER_KOOPER
        && actor->curHP > 0 && (elements & (DAMAGE_TYPE_JUMP | DAMAGE_TYPE_POW | DAMAGE_TYPE_QUAKE))
        && (event == EVENT_HIT || event == EVENT_HIT_COMBO || event == EVENT_IMMUNE || event == EVENT_ZERO_DAMAGE)) {
        return EVENT_FLIP_TRIGGER;
    }
    return event;
}

// Battle_PlayerTeam_DontSwapPositions: native position flags remain physical
// because guarded automatic menu/turn swaps are suppressed. No source RAM byte
// or saved field is needed; only an explicit keyboard-swap request is transient.
b32 ttyd64_partner_team_active(void) {
    return gBattleStatus.playerActor != nullptr
        && ttyd64_partner_combat_active(gBattleStatus.partnerActor);
}

void ttyd64_partner_team_request_swap(void) {
    if (ttyd64_partner_team_active()) {
        TeamSwapRequested = true;
    }
}

b32 ttyd64_partner_team_should_swap(b32 nativeSwap) {
    b32 requested = TeamSwapRequested;
    TeamSwapRequested = false;
    return ttyd64_partner_team_active() ? requested : nativeSwap;
}

void ttyd64_partner_team_swap_completed(b32 nativePlayerInBack) {
    if (ttyd64_partner_team_active()) {
        gBattleStatus.flags1 ^= BS_FLAGS1_PLAYER_IN_BACK;
    } else if (nativePlayerInBack) {
        gBattleStatus.flags1 |= BS_FLAGS1_PLAYER_IN_BACK;
    } else {
        gBattleStatus.flags1 &= ~BS_FLAGS1_PLAYER_IN_BACK;
    }
}

s32 ttyd64_partner_team_resolve_target(s32 targetActorID) {
    // PartnersHP SetTargetActor: a dead-partner target must attack Mario.
    if (targetActorID == ACTOR_PARTNER && ttyd64_partner_team_active()
        && ttyd64_get_partner_hp(BoundPartnerID) <= 0) {
        return ACTOR_PLAYER;
    }
    return targetActorID;
}

s32 ttyd64_partner_team_target(b32 back) {
    if (!ttyd64_partner_team_active()) {
        return ACTOR_PLAYER;
    }
    b32 marioInFront = !(gBattleStatus.flags1 & BS_FLAGS1_PLAYER_IN_BACK);
    return ttyd64_partner_team_resolve_target(back == marioInFront ? ACTOR_PARTNER : ACTOR_PLAYER);
}

void ttyd64_partner_combat_load_hp(Actor* actor) {
    if (ttyd64_partner_combat_active(actor)) {
        actor->curHP = ttyd64_get_partner_hp(BoundPartnerID);
        actor->maxHP = ttyd64_get_partner_max_hp(BoundPartnerID);
    }
}

void ttyd64_partner_combat_store_hp(Actor* actor) {
    if (ttyd64_partner_combat_active(actor)) {
        ttyd64_set_partner_hp(BoundPartnerID, actor->curHP);
    }
}

b32 ttyd64_partner_combat_death_handled(Actor* actor) {
    return ttyd64_partner_combat_active(actor) && (DeathHandledMask & (1 << BoundPartnerID));
}

void ttyd64_partner_combat_mark_dead(Actor* actor) {
    if (ttyd64_partner_combat_active(actor) && actor->curHP == 0) {
        DeathHandledMask |= 1 << BoundPartnerID;
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
    if (ttyd64_get_partner_hp(BoundPartnerID) == 0) {
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
    if (ttyd64_get_partner_hp(BoundPartnerID) > 0 || ttyd64_partner_combat_death_handled(partner)) {
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
    if (!ttyd64_partner_combat_active(actor) || ttyd64_get_partner_hp(BoundPartnerID) != 0
        || gPlayerData.curHP <= 0 || find_item(ITEM_LIFE_SHROOM) < 0) {
        return 0;
    }
    remove_item(ITEM_LIFE_SHROOM);
    // PartnersHP.patch $UseLifeShroom_Actor restores ten and returns the turn.
    s32 hp = ttyd64_set_partner_hp(BoundPartnerID, 10);
    gBattleStatus.flags2 &= ~BS_FLAGS2_PARTNER_TURN_USED;
    return hp;
}

b32 ttyd64_partner_combat_can_heal_with_item(s32 itemID) {
    Actor* partner = gBattleStatus.partnerActor;
    if (!ttyd64_partner_combat_active(partner) || ttyd64_get_partner_hp(BoundPartnerID) <= 0
        || (DeathScriptID != 0 && does_script_exist(DeathScriptID))) {
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

s32 ttyd64_partner_combat_heal(Actor* actor, s32 amount) {
    if (!ttyd64_partner_combat_active(actor) || amount <= 0
        || (DeathScriptID != 0 && does_script_exist(DeathScriptID))) {
        return 0;
    }
    s32 hp = ttyd64_get_partner_hp(BoundPartnerID);
    if (hp <= 0) {
        return 0;
    }
    // PartnersItems.patch $Heal_PlayerTeam/$heal_actor: cap to max HP. Bound
    // before addition so even an oversized script argument cannot overflow.
    s32 missing = ttyd64_get_partner_max_hp(BoundPartnerID) - hp;
    s32 recovered = amount > missing ? missing : amount;
    ttyd64_set_partner_hp(BoundPartnerID, hp + recovered);
    return recovered;
}

static b32 can_display_world_hp(void) {
    return ttyd64_mode_enabled() && gGameStatusPtr->context == CONTEXT_WORLD
        && gGameStatusPtr->demoState == DEMO_STATE_NONE
        && !(gPlayerStatusPtr->animFlags & PA_FLAG_USING_PEACH_PHYSICS)
        && ttyd64_partner_hp_supported(WorldPartnerID) && gPlayerData.curPartner == WorldPartnerID
        && gPlayerData.partners[WorldPartnerID].enabled;
}

void ttyd64_partner_hp_world_bind(s32 partnerID) {
    WorldPartnerID = partnerID;
    // PartnersHP.patch hook 83DF0 snaps the displayed value when a world
    // partner is created. The selected identity alone does not prove ownership.
    ttyd64_partner_hp_sync_display();
}

void ttyd64_partner_hp_world_unbind(void) {
    WorldPartnerID = PARTNER_NONE;
    ttyd64_partner_hp_sync_display();
}

void ttyd64_partner_hp_sync_display(void) {
    Actor* partner = gBattleStatus.partnerActor;
    DisplayPartnerInWorld = can_display_world_hp();
    DisplayPartnerActor = !DisplayPartnerInWorld && ttyd64_partner_combat_active(partner) ? partner : nullptr;
    DisplayPartnerHP = DisplayPartnerInWorld || DisplayPartnerActor ? ttyd64_get_partner_hp(DisplayPartnerInWorld ? WorldPartnerID : BoundPartnerID) : -1;
    DisplayPartnerHPTimer = 0;
}

void ttyd64_partner_hp_update_display(void) {
    Actor* partner = gBattleStatus.partnerActor;
    b32 inWorld = can_display_world_hp();
    if ((!inWorld && !ttyd64_partner_combat_active(partner)) || DisplayPartnerInWorld != inWorld
        || (!inWorld && DisplayPartnerActor != partner)) {
        ttyd64_partner_hp_sync_display();
        return;
    }
    // NewStatsMenu.patch $PartnerHP_AnimationTimer: one HP every four frames,
    // both damage and healing. Presentation state is separate from saved HP.
    s32 hp = ttyd64_get_partner_hp(inWorld ? WorldPartnerID : BoundPartnerID);
    if (DisplayPartnerHP == hp) {
        DisplayPartnerHPTimer = 0;
    } else if (++DisplayPartnerHPTimer >= 4) {
        DisplayPartnerHP += DisplayPartnerHP < hp ? 1 : -1;
        DisplayPartnerHPTimer = 0;
    }
}

s32 ttyd64_partner_hp_display(void) {
    b32 inWorld = can_display_world_hp();
    if (DisplayPartnerInWorld != inWorld
        || (!inWorld && (!ttyd64_partner_combat_active(gBattleStatus.partnerActor)
            || DisplayPartnerActor != gBattleStatus.partnerActor))) {
        return -1;
    }
    return DisplayPartnerHP;
}

s32 ttyd64_partner_hp_display_partner(void) {
    if (ttyd64_partner_hp_display() < 0) {
        return PARTNER_NONE;
    }
    return DisplayPartnerInWorld ? WorldPartnerID : BoundPartnerID;
}
