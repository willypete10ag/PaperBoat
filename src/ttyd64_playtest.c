#include "common.h"
#include "fio.h"
#include "game_modes.h"
#include "ttyd64_partner_hp.h"
#include "port/PlaytestSession.h"

// A deliberate process-only developer scenario, never a normal new-game preset.
int ttyd64_playtest_startup(void) {
    const int profile = ttyd64_playtest_take_request();
    if (profile == 0) {
        return false;
    }
    clear_player_data();
    clear_saved_variables();
    get_map_IDs_by_name_checked("kmr_02", &gGameStatusPtr->areaID, &gGameStatusPtr->mapID);
    gGameStatusPtr->entryID = 5;
    gGameStatusPtr->savedPos.x = 250;
    gGameStatusPtr->savedPos.y = 0;
    gGameStatusPtr->savedPos.z = 85;
    evt_set_variable(nullptr, GB_StoryProgress, STORY_CH1_DEFEATED_KOOPA_BROS);
    evt_set_variable(nullptr, GF_Tutorial_SwapTurnOrder, true);
    gPlayerData.curHP = 15;
    gPlayerData.curMaxHP = gPlayerData.hardMaxHP = 20;
    gPlayerData.curFP = gPlayerData.curMaxFP = gPlayerData.hardMaxFP = 10;
    gPlayerData.hammerLevel = 0;
    gPlayerData.hasActionCommands = true;
    gPlayerData.curPartner = PARTNER_GOOMBARIO;
    for (s32 id = PARTNER_GOOMBARIO; id <= PARTNER_BOMBETTE; ++id) {
        gPlayerData.partners[id].enabled = true;
        ttyd64_reset_partner_hp(id);
        ttyd64_set_partner_hp(id, 3);
    }
    if (profile == 1) {
        add_item(ITEM_MUSHROOM);
        add_item(ITEM_MUSHROOM);
        add_item(ITEM_MUSHROOM);
        add_item(ITEM_SUPER_SHROOM);
        add_item(ITEM_LIFE_SHROOM);
        add_item(ITEM_LIFE_SHROOM);
    } else {
        add_item(ITEM_COURAGE_SHELL);
        add_item(ITEM_POWER_PUNCH);
        add_item(ITEM_MINI_MR_MINI);
        add_item(ITEM_MR_SOFTENER);
        add_item(ITEM_SLOW_SHROOM);
        add_item(ITEM_GRADUAL_SYRUP);
        add_item(ITEM_COUPLES_CAKE);
        add_item(ITEM_METEOR_MEAL);
        add_item(ITEM_LIFE_SHROOM);
        add_item(ITEM_LIFE_SHROOM);
    }
    // Same native serialization/new-game path as file creation; no distributed seed.
    // The optional HP save field contains health only, never the activation flag.
    gTtyd64PartnerHPPrototypeEnabled = true;
    fio_save_game(3);
    set_curtain_scale(2.0f);
    set_curtain_fade(0.0f);
    set_game_mode(GAME_MODE_ENTER_WORLD);
    return true;
}
