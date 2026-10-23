#include "common.h"
#include "fio.h"
#include "game_modes.h"
#include "ttyd64_partner_hp.h"
#include "port/PlaytestSession.h"

// A deliberate disposable developer scenario with an ordinary saved TTYD64 mode.
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
    gPlayerData.curFP = profile == 1 ? 3 : 10;
    gPlayerData.curMaxFP = gPlayerData.hardMaxFP = 10;
    gPlayerData.hammerLevel = 0;
    gPlayerData.hasActionCommands = true;
    // Disposable developer files expose Refresh and Smooch for team recovery.
    gPlayerData.maxStarPower = 5;
    gPlayerData.starPower = 5 * SP_PER_BAR;
    gPlayerData.curPartner = PARTNER_GOOMBARIO;
    for (s32 id = PARTNER_GOOMBARIO; id <= PARTNER_BOMBETTE; ++id) {
        gPlayerData.partners[id].enabled = true;
        ttyd64_reset_partner_hp(id);
        ttyd64_set_partner_hp(id, 3);
    }
    // Only this deliberate new developer file receives a ready badge loadout.
    // Keep FP Drain optional: its attack penalty would erase a basic boot hit.
    ttyd64_mode_select_file(TTYD64_MODE_TTYD64);
    gPlayerData.maxBP = 20;
    static const s16 equipped[] = {
        ITEM_DOUBLE_DIP, ITEM_DOUBLE_DIP, ITEM_FLOWER_SAVER_A,
        ITEM_FLOWER_SAVER_A, ITEM_PITY_FLOWER, ITEM_LAST_STAND,
    };
    static const s16 spare[] = {
        ITEM_LAST_STAND, ITEM_PITY_FLOWER, ITEM_FP_DRAIN, ITEM_FP_DRAIN,
        ITEM_DEFEND_PLUS_A, ITEM_JUMPMAN, ITEM_HAMMERMAN,
        ITEM_FLOWER_SAVER_B, ITEM_FLOWER_SAVER_B,
    };
    for (s32 i = 0; i < ARRAY_COUNT(equipped); ++i) {
        add_item(equipped[i]);
        gPlayerData.equippedBadges[i] = equipped[i];
    }
    for (s32 i = 0; i < ARRAY_COUNT(spare); ++i) {
        add_item(spare[i]);
    }
    if (profile == 1) {
        add_item(ITEM_MUSHROOM);
        add_item(ITEM_MUSHROOM);
        add_item(ITEM_MUSHROOM);
        add_item(ITEM_SUPER_SHROOM);
        add_item(ITEM_LIFE_SHROOM);
        add_item(ITEM_LIFE_SHROOM);
        add_item(ITEM_FRIED_SHROOM);
        add_item(ITEM_HONEY_SYRUP);
        add_item(ITEM_MAPLE_SUPER);
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
    // The same versioned mode contract is used by normal new-file selection.
    fio_save_game(3);
    set_curtain_scale(2.0f);
    set_curtain_fade(0.0f);
    set_game_mode(GAME_MODE_ENTER_WORLD);
    return true;
}
