#include "ttyd64_status_items.h"
#include "ttyd64_actor_modifiers.h"
#include "battle/battle.h"
#include "effects.h"

b32 ttyd64_status_item_supported(s32 itemID) {
    return itemID >= ITEM_COURAGE_SHELL && itemID <= ITEM_MR_SOFTENER;
}
b32 ttyd64_status_item_can_target_partner(s32 itemID) {
    return (itemID == ITEM_COURAGE_SHELL || itemID == ITEM_POWER_PUNCH)
        && ttyd64_partner_combat_can_heal_with_item(ITEM_MUSHROOM);
}

// Battle_NewItems_BattleScripts: shared status-item branches. Source item IDs
// are translated to appended native IDs; no legacy actor/save fields are reused.
b32 ttyd64_status_item_apply(s32 itemID, Actor* target, s32 partID) {
    if (!ttyd64_status_item_supported(itemID) || !ttyd64_actor_modifiers_active(target))
        return false;
    s32 amount = gItemTable[itemID].potencyA;
    b32 defense = itemID == ITEM_COURAGE_SHELL || itemID == ITEM_MR_SOFTENER;
    s32 arrow = defense ? 6 : 0;
    if (itemID == ITEM_MINI_MR_MINI) {
        amount = -amount;
        arrow = 3;
    } else if (itemID == ITEM_MR_SOFTENER) {
        ActorPart* part = get_actor_part(target, partID);
        if (part == nullptr)
            return false;
        // Source Function_GetActorDefense looks up this part's normal defense
        // table, excluding existing boosts/debuffs. Nonpositive values do not
        // receive an effect. Existing signed power cancels via the shared API.
        amount = ttyd64_softener_amount(lookup_defense((s32*) part->defenseTable, ELEMENT_NORMAL), amount);
        if (amount == 0)
            return false;
    }
    if (!ttyd64_actor_add_modifier(target, defense, amount, 3))
        return false;
    if (itemID == ITEM_POWER_PUNCH || itemID == ITEM_MINI_MR_MINI)
        ttyd64_actor_set_size(target, amount > 0 ? 1 : -1);
    EffectInstance* effect =
        fx_stat_change(arrow, target->curPos.x + 15, target->curPos.y + 35, target->curPos.z + 6, 1.5f, 60);
    effect->data.statChange->arrowValue = amount;
    if (itemID == ITEM_MR_SOFTENER)
        effect->data.statChange->arrowType = 3; // source blue downward arrow
    sfx_play_sound_at_position(
        amount < 0 ? SOUND_INFLICT_CHILL_OUT : (itemID == ITEM_POWER_PUNCH ? SOUND_GROW : SOUND_CHARGE_UP),
        SOUND_SPACE_DEFAULT, target->curPos.x, target->curPos.y, target->curPos.z
    );
    return true;
}
