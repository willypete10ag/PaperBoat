#ifndef TTYD64_STATUS_ITEMS_H
#define TTYD64_STATUS_ITEMS_H
#include "common.h"
#ifdef __cplusplus
extern "C" {
#endif
b32 ttyd64_status_item_supported(s32 itemID);
b32 ttyd64_status_item_can_target_partner(s32 itemID);
b32 ttyd64_status_item_apply(s32 itemID, Actor* target, s32 partID);
#ifdef __cplusplus
}
#endif
#endif
