#include "ttyd64_mode.h"
#include "ttyd64_rules.h"
#include "item_enum.h"
#include "move_enum.h"

static Ttyd64Mode ActiveFileMode = TTYD64_MODE_VANILLA;

int ttyd64_mode_enabled(void) {
    return ActiveFileMode == TTYD64_MODE_TTYD64;
}

void ttyd64_mode_select_file(int mode) {
    ActiveFileMode = mode == TTYD64_MODE_TTYD64 ? TTYD64_MODE_TTYD64 : TTYD64_MODE_VANILLA;
}

// Source b8d2058ea globals/Moves.xml, matching semantic move identities only.
// Source-rule CTest compares these lookups with the pinned original XML; the
// static native table retains Vanilla costs, including reused/relocated IDs.
int ttyd64_mode_fp_cost(int mode, int moveID, int vanillaCost) {
    if (mode == TTYD64_MODE_TTYD64) {
        if (moveID == MOVE_DOUBLE_DIP) return TTYD64_FP_DOUBLE_DIP;
        if (moveID == MOVE_TRIPLE_DIP) return TTYD64_FP_TRIPLE_DIP;
        if (moveID == MOVE_CHARGE) return 3;
        if (moveID == MOVE_MULTIBONK) return 4;
        if (moveID == MOVE_OUTTA_SIGHT) return 1;
    }
    return vanillaCost;
}

int ttyd64_mode_bp_cost(int mode, int moveID, int vanillaCost) {
    if (mode == TTYD64_MODE_TTYD64) {
        switch (moveID) {
            case MOVE_DOUBLE_DIP: return TTYD64_BP_DOUBLE_DIP;
            case MOVE_TRIPLE_DIP: return TTYD64_BP_TRIPLE_DIP;
            case MOVE_DEFEND_PLUS: return TTYD64_BP_DEFEND_PLUS;
            case MOVE_FLOWER_SAVER: return TTYD64_BP_FLOWER_SAVER;
            case MOVE_D_DOWN_POUND: return 1;
            case MOVE_HAMMER_THROW: return 1;
            case MOVE_POWER_BOUNCE: return 3;
            case MOVE_D_DOWN_JUMP: return 1;
            case MOVE_DAMAGE_DODGE: return 2;
            case MOVE_QUICK_CHANGE: return 7;
            case MOVE_PRETTY_LUCKY: return 2;
            case MOVE_FEELING_FINE: return 4;
            case MOVE_ZAP_TAP: return 3;
            case MOVE_MONEY_MONEY: return 5;
            case MOVE_CHILL_OUT_BADGE: return 1;
            case MOVE_HAPPY_HEART: return 2;
            case MOVE_I_SPY: return 0;
            case MOVE_SPEEDY_SPIN: return 0;
            case MOVE_HAPPY_FLOWER: return 2;
            case MOVE_GROUP_FOCUS: return 1;
            case MOVE_PEEKABOO: return 0;
        }
    }
    return vanillaCost;
}

int ttyd64_mode_dip_menu_cost(int mode, int base, int savers, int fanatics) {
    // Preserve Vanilla's original eligibility calculation, even its mismatch
    // with minimum-1 payment. Only the TTYD64 fix changes that menu behavior.
    return mode == TTYD64_MODE_TTYD64 ? ttyd64_move_fp_cost(base, savers, fanatics)
        : base - savers - 2 * fanatics;
}

int ttyd64_consumable_count(void) {
    return ttyd64_mode_enabled() ? ITEM_NUM_CONSUMABLES : ITEM_NUM_VANILLA_CONSUMABLES;
}

int ttyd64_mode_consumable_id_at(int index) {
    return index < ttyd64_consumable_count() ? ttyd64_consumable_id_at(index) : ITEM_NONE;
}
