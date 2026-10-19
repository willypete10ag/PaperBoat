#include "common.h"
#include "ttyd64_rules.h"

API_CALLABLE(N(BuildItemChoiceList)) {
    Bytecode* args = script->ptrReadPos;
    s32* allowedItemList = (s32*)evt_get_variable(script, *args++);
    s32 i;

    if (allowedItemList != nullptr) {
        for (i = 0; allowedItemList[i] != ITEM_NONE; i++) {
            N(ItemChoiceList)[i] = allowedItemList[i];
        }
        N(ItemChoiceList)[i] = ITEM_NONE;
    } else {
        for (i = 0; i < ttyd64_consumable_count(); i++) {
            N(ItemChoiceList)[i] = ttyd64_mode_consumable_id_at(i);
        }
        N(ItemChoiceList)[i] = ITEM_NONE;
    }
    return ApiStatus_DONE2;
}
