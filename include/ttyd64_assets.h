#ifndef TTYD64_ASSETS_H
#define TTYD64_ASSETS_H

// Native IDs are appended; Star Rod's item/move/message indices are not reused.
#define MSG_TTYD64_PityFlowerName MESSAGE_ID(0x2F, 0)
#define MSG_TTYD64_PityFlowerDesc MESSAGE_ID(0x2F, 1)
#define MSG_TTYD64_JumpmanName MESSAGE_ID(0x2F, 2)
#define MSG_TTYD64_JumpmanDesc MESSAGE_ID(0x2F, 3)

static const ALIGN_ASSET(2) char ICON_badge_PityFlower_raster[] = "__OTR__icons/badge/PityFlower";
static const ALIGN_ASSET(2) char ICON_badge_PityFlower_palette[] = "__OTR__icons/badge/PityFlower.pal";
#define ICON_badge_PityFlower_disabled_raster ICON_badge_PityFlower_raster
static const ALIGN_ASSET(2) char ICON_badge_PityFlower_disabled_palette[] = "__OTR__icons/badge/PityFlower.disabled.pal";

static const ALIGN_ASSET(2) char ICON_badge_Jumpman_raster[] = "__OTR__icons/badge/Jumpman";
static const ALIGN_ASSET(2) char ICON_badge_Jumpman_palette[] = "__OTR__icons/badge/Jumpman.pal";
#define ICON_badge_Jumpman_disabled_raster ICON_badge_Jumpman_raster
static const ALIGN_ASSET(2) char ICON_badge_Jumpman_disabled_palette[] = "__OTR__icons/badge/Jumpman.disabled.pal";

#endif
