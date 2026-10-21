#ifndef TTYD64_STATUS_ITEMS_H
#define TTYD64_STATUS_ITEMS_H
#include "common.h"
#ifdef __cplusplus
extern "C" {
#endif
// Appended native popup IDs; the source ROM indices are not reused.
enum Ttyd64ItemResultMessages {
    BTL_MSG_TTYD64_DEFENSE_BOOST = 0x55,
    BTL_MSG_TTYD64_ATTACK_BOOST = 0x56,
    BTL_MSG_TTYD64_DEFENSE_DROP = 0x57,
    BTL_MSG_TTYD64_ATTACK_DROP = 0x58,
};

b32 ttyd64_status_item_supported(s32 itemID);
b32 ttyd64_status_item_can_target_partner(s32 itemID);
b32 ttyd64_status_item_apply(s32 itemID, Actor* target, s32 partID);
#ifdef __cplusplus
}
#endif
#endif
