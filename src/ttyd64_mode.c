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

// Only already-ported differences. The remaining source costs have their own
// review milestone; the static native table stays at the vanilla baseline.
int ttyd64_mode_fp_cost(int mode, int moveID, int vanillaCost) {
    if (mode == TTYD64_MODE_TTYD64) {
        if (moveID == MOVE_DOUBLE_DIP) return TTYD64_FP_DOUBLE_DIP;
        if (moveID == MOVE_TRIPLE_DIP) return TTYD64_FP_TRIPLE_DIP;
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
        }
    }
    return vanillaCost;
}

int ttyd64_consumable_count(void) {
    return ttyd64_mode_enabled() ? ITEM_NUM_CONSUMABLES : ITEM_NUM_VANILLA_CONSUMABLES;
}

int ttyd64_mode_consumable_id_at(int index) {
    return index < ttyd64_consumable_count() ? ttyd64_consumable_id_at(index) : ITEM_NONE;
}
