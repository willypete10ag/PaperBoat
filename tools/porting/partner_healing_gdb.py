"""Guarded Goombario shroom healing/HP HUD, including real keyboard item use.

Uses only the exact copied disposable FP Drain save/runtime below. Rendering
threads remain free; native events advance by continue, never recursive updates.
"""
import json
import os
from pathlib import Path
import subprocess
import time
import gdb


def cmd(text):
    return gdb.execute(text, to_string=True)


def val(text):
    return int(gdb.parse_and_eval(text))


def put(text, amount):
    cmd(f'set variable {text} = {amount}')


def until(where):
    point = gdb.Breakpoint(where, temporary=True, internal=True)
    point.silent = True
    cmd('continue')
    stopped = [t for t in gdb.selected_inferior().threads() if t.is_stopped()]
    assert len(stopped) == 1, 'Only the game-tick thread should be stopped'
    stopped[0].switch()
    assert gdb.selected_frame().name() == where, 'Unexpected native stop'


def run():
    root = Path('/workspace/.paperboat-setup/partner-healing')
    runtime = Path(os.environ['SHIP_HOME']).resolve()
    assert runtime == root / 'runtime'
    save = runtime / 'saves/file3.json'
    original = save.read_bytes()
    assert original == Path('/workspace/.paperboat-setup/fp-drain/runtime/saves/file3.json').read_bytes()
    checks, observations, screenshots = [], [], []
    actor = 'gBattleStatus.partnerActor'
    def hp():
        return val('ttyd64_get_partner_hp(PARTNER_GOOMBARIO)')
    def health(amount):
        assert val(f'ttyd64_set_partner_hp(PARTNER_GOOMBARIO, {amount})') == amount
    def check(name, condition):
        assert condition, name
        checks.append(name)
        if val('gGameStatusPtr->context') == val('CONTEXT_BATTLE') and val(actor):
            observations.append({'check':name, 'hp':hp(), 'actor_hp':val(f'{actor}->curHP'),
                                 'display_hp':val('ttyd64_partner_hp_display()'),
                                 'state':val('gBattleState'), 'substate':val('gBattleSubState')})
        print('PARTNER_HEALING_CHECK=' + name)
    def tick(n=1):
        for _ in range(n):
            until('btl_update')
    def wait_for(expression, limit=300):
        for _ in range(limit):
            if val(expression):
                return
            tick()
        print('PARTNER_HEALING_TIMEOUT=' + json.dumps({k:val(k) for k in ('gBattleState','gBattleSubState','BattleMenuState','gBattleStatus.flags1','gBattleStatus.flags2','gBattleStatus.stateFreezeCount','gPlayerData.curPartner','gBattleStatus.moveArgument','gBattleStatus.waitForState','gPopupState','PopupMenu_SelectedIndex','gPopupMenu->result','gPopupMenu->enabled[PopupMenu_SelectedIndex]')}))
        capture('healing-timeout')
        raise AssertionError('Frame budget exceeded: ' + expression)
    def capture(name):
        window = subprocess.check_output(['xdotool','search','--onlyvisible','--pid',str(gdb.selected_inferior().pid)], text=True).splitlines()[0]
        subprocess.run(['xdotool','windowraise',window],check=True)
        subprocess.run(['xdotool','windowfocus',window],check=True)
        time.sleep(0.5)
        subprocess.run(['import','-window','root',str(root/(name+'.png'))],check=True)
        screenshots.append(name)
    # Ship uses LUS scancodes, not SDL codes: A=X, B=C, stick=W/A/S/D.
    def key(name, frames=3):
        subprocess.run(['xdotool','keydown',name],check=True)
        try:
            # SDL polling can be missed by several simulation updates under
            # GDB. Use the same native UI-pass holds as the shared slice driver.
            for _ in range(frames):
                until('render_game_mode_backUI')
        finally:
            subprocess.run(['xdotool','keyup',name],check=True)
        for _ in range(3):
            until('render_game_mode_backUI')
    for setting in ('non-stop on','pagination off','confirm off','print thread-events off'):
        cmd('set ' + setting)
    gdb.Breakpoint('state_step_startup',temporary=True,internal=True)
    cmd('run')
    [t for t in gdb.selected_inferior().threads() if t.is_stopped()][0].switch()
    put('gPortResetToTitleScreen',1)
    until('state_step_title_screen')
    check('prototype-default-off',val('gTtyd64PartnerHPPrototypeEnabled') == 0)
    put('TitleScreenNextState',val('NEXT_STATE_FILE_SELECT'))
    put('gGameStatusPtr->startupState',val('TITLE_STATE_EXIT'))
    put('gGameStatusPtr->titleScreenTimer',0)
    until('filemenu_update')
    assert val('fio_load_game(3)') == 1
    put('filemenu_menus[0]->state',val('FM_MAIN_SELECT_FILE'))
    put('filemenu_menus[0]->selected',0)
    put('filemenu_currentMenu',val('FILE_MENU_MAIN'))
    cmd('call set_game_mode(GAME_MODE_END_FILE_SELECT)')
    cmd('return')
    until('state_step_world')
    cmd('call load_demo_battle(4)')
    cmd('return')
    until('load_partner_actor')
    assert val('fio_load_game(3)') == 1
    cmd('call evt_set_variable((Evt*)0, GF_Tutorial_SwapTurnOrder, 1)')
    put('gPlayerData.curPartner',1)
    put('gPlayerData.partners[1].enabled',1)
    put('gPlayerData.partners[1].level',0)
    cmd('call ttyd64_reset_partner_hp(1)')
    for i in range(64):
        put(f'gPlayerData.equippedBadges[{i}]',0)
    for i in range(10):
        put(f'gPlayerData.invItems[{i}]',0)
    for item in ('ITEM_MUSHROOM','ITEM_MUSHROOM','ITEM_SUPER_SHROOM','ITEM_ULTRA_SHROOM','ITEM_DRIED_SHROOM'):
        assert val(f'add_item({item})') >= 0
    put('gPlayerData.curHP',20)
    put('gPlayerData.curMaxHP',30)
    put('gPlayerData.maxStarPower',0)
    until('calc_enemy_damage_target')
    put('gGameStatusPtr->demoBattleFlags',0)
    put('gBattleStatus.waitForState',val('BATTLE_STATE_NONE'))
    cmd('call set_curtain_scale(2.0f)')
    cmd('call set_curtain_scale_goal(2.0f)')
    cmd('call set_cam_viewport(CAM_BATTLE, 12, 20, 296, 200)')
    put('gTtyd64PartnerHPPrototypeEnabled',1)
    cmd(f'call ttyd64_partner_hp_bind_actor({actor})')
    put('gBattleStatus.curAttackDamage',0)
    cmd('set variable gBattleStatus.curAttackElement = DAMAGE_TYPE_UNBLOCKABLE')
    cmd('set variable gBattleStatus.flags1 &= ~BS_FLAGS1_TUTORIAL_BATTLE')
    cmd('finish')
    tick()
    health(3)
    cmd('call ttyd64_partner_hp_sync_display()')
    check('display-initializes-current-hp',val('ttyd64_partner_hp_display()') == 3)
    # Native menu/renderer prerequisites for the disposable title-origin save.
    print('PARTNER_HEALING_HUD_SETUP=' + json.dumps({k:val(k) for k in ('gGameStatusPtr->introPart','gGameStatusPtr->demoState','gStatusBar.disabled','gStatusBar.hidden','gStatusBar.drawPosY')}))
    assert val('gStatusBar.disabled') == 1
    cmd('call decrement_status_bar_disabled()')
    put('gGameStatusPtr->introPart',-1)
    put('gGameStatusPtr->demoState',val('DEMO_STATE_NONE'))
    wait_for('gBattleState == BATTLE_STATE_PLAYER_MENU && BattleMenuState == BTL_MENU_STATE_CHOOSING')
    tick(20)
    capture('healing-menu-before')
    check('native-mario-menu-and-wounded-hp',hp() == 3 and val('btl_player_can_act()') != 0)
    # Choose Items by ordinary keyboard movement; never write popup selections.
    item_index = next(i for i in range(val('WheelOptionCount')) if val(f'WheelOptionSubmenu[{i}]') == val('BTL_MENU_TYPE_ITEMS'))
    for _ in range(8):
        current = val('BattleMenu_CurPos + BattleMenu_HomePos')
        print('PARTNER_HEALING_WHEEL=' + json.dumps({'current':current,'items':item_index}))
        if current == item_index:
            break
        key('a' if item_index < current else 'd')
        tick(12)
    check('keyboard-wheel-selects-items',val('WheelOptionSubmenu[BattleMenu_CurPos + BattleMenu_HomePos]') == val('BTL_MENU_TYPE_ITEMS'))
    key('x')
    wait_for('gBattleSubState == 41')  # menu_player.c ITEMS_CHOOSING
    wait_for('gPopupState == POPUP_STATE_CHOOSING && PopupDelayTime == 0')
    tick(3)
    mushroom_index = next(i for i in range(val('gPopupMenu->numEntries')) if val(f'gPopupMenu->userIndex[{i}]') == val('ITEM_MUSHROOM'))
    for _ in range(10):
        current = val('PopupMenu_SelectedIndex')
        if current == mushroom_index:
            break
        key('w' if mushroom_index < current else 's')
        tick(5)
    check('keyboard-popup-selects-mushroom',val('gPopupMenu->userIndex[PopupMenu_SelectedIndex]') == val('ITEM_MUSHROOM'))
    capture('healing-item-popup')
    key('x')
    wait_for('gBattleState == BATTLE_STATE_SELECT_TARGET && gBattleSubState == 1')
    tick(10)
    check('native-shroom-targets-mario-and-goombario',val('gBattleStatus.playerActor->targetListLength') == 2)
    # Observe sorted target indices; choose partner through left/right input.
    for _ in range(3):
        if val('gBattleStatus.playerActor->targetData[gBattleStatus.playerActor->targetIndexList[gBattleStatus.playerActor->selectedTargetIndex]].actorID') == val('ACTOR_PARTNER'):
            break
        key('d')
    check('keyboard-targets-goombario',val('gBattleStatus.playerActor->targetData[gBattleStatus.playerActor->targetIndexList[gBattleStatus.playerActor->selectedTargetIndex]].actorID') == val('ACTOR_PARTNER'))
    capture('healing-partner-target')
    key('c')
    wait_for('gBattleState == BATTLE_STATE_PLAYER_MENU && gBattleSubState == 41')
    wait_for('gPopupState == POPUP_STATE_CHOOSING && PopupDelayTime == 0')
    tick(3)
    check('cancel-target-keeps-item-and-health',hp() == 3 and sum(val(f'gPlayerData.invItems[{i}]') == val('ITEM_MUSHROOM') for i in range(10)) == 2)
    key('x')
    wait_for('gBattleState == BATTLE_STATE_SELECT_TARGET && gBattleSubState == 1')
    for _ in range(3):
        if val('gBattleStatus.playerActor->targetData[gBattleStatus.playerActor->targetIndexList[gBattleStatus.playerActor->selectedTargetIndex]].actorID') == val('ACTOR_PARTNER'):
            break
        key('d')
    key('x')
    wait_for('ttyd64_get_partner_hp(1) == 8',400)
    check('native-keyboard-item-heals-3-to-8',hp() == 8 and val(f'{actor}->curHP') == 8 and val('gPlayerData.curHP') == 20)
    count = sum(val(f'gPlayerData.invItems[{i}]') == val('ITEM_MUSHROOM') for i in range(10))
    check('native-item-consumes-exactly-one-of-two',count == 1)
    check('healing-keeps-unused-partner-turn',val('gBattleStatus.flags2 & BS_FLAGS2_PARTNER_TURN_USED') == 0)
    capture('healing-recovery')
    wait_for('gBattleState != BATTLE_STATE_PLAYER_MOVE',400)
    tick(35)
    check('native-healing-turn-completes',val('gBattleState') == val('BATTLE_STATE_PARTNER_MENU') and val('ttyd64_partner_hp_display()') == 8)
    check('healing-spends-mario-turn-only',val('gBattleStatus.flags2 & BS_FLAGS2_PLAYER_TURN_USED') != 0 and val('gBattleStatus.flags2 & BS_FLAGS2_PARTNER_TURN_USED') == 0)
    check('healing-preserves-native-no-ko',val(f'{actor}->koStatus') == 0 and val(f'{actor}->koDuration') == 0)
    capture('healing-hud-after')
    # Persistence round trip, restoring exact bytes, with unrelated Mario state.
    try:
        cmd('call fio_save_game(3)')
        assert val('fio_load_game(3)') == 1
        check('native-save-load-healed-hp-and-inventory',hp() == 8 and sum(val(f'gPlayerData.invItems[{i}]') == val('ITEM_MUSHROOM') for i in range(10)) == 1)
    finally:
        save.write_bytes(original)
    # Compiled model/cap/target boundaries; no script-update calls or turn replay.
    for amount, expected in ((1,4),(5,8),(10,10),(50,10),(2147483647,10),(-1,3),(0,3)):
        health(3)
        recovered = val(f'ttyd64_partner_combat_heal({actor},{amount})')
        check('heal-bound-' + str(amount),hp() == expected and recovered == expected - 3 and val(f'{actor}->curHP') == expected)
    flags2 = val('gBattleStatus.flags2')
    put('gBattleStatus.flags2',flags2 | val('BS_FLAGS2_PARTNER_TURN_USED'))
    health(3)
    check('ordinary-healing-preserves-already-used-turn',val(f'ttyd64_partner_combat_heal({actor},5)') == 5 and val('gBattleStatus.flags2 & BS_FLAGS2_PARTNER_TURN_USED') != 0)
    put('gBattleStatus.flags2',flags2)
    # Exercise native target-list admission independently of popup input.
    target_setup = {name:val('gBattleStatus.' + name) for name in ('flags1','moveCategory','moveArgument','curTargetListFlags')}
    put('gBattleStatus.flags1',val('gBattleStatus.flags1') & ~val('BS_FLAGS1_PARTNER_ACTING'))
    put('gBattleStatus.moveCategory',val('BTL_MENU_TYPE_ITEMS'))
    put('gBattleStatus.moveArgument',val('ITEM_MUSHROOM'))
    put('gBattleStatus.curTargetListFlags',val('TARGET_FLAG_PLAYER'))
    health(0)
    check('ordinary-healing-cannot-revive',val(f'ttyd64_partner_combat_heal({actor},5)') == 0 and hp() == 0)
    check('dead-partner-not-healing-target',val('ttyd64_partner_combat_can_heal_with_item(ITEM_MUSHROOM)') == 0)
    cmd('call create_target_list(gBattleStatus.playerActor, 0)')
    check('native-dead-partner-excluded-from-shroom-list',val('gBattleStatus.playerActor->targetListLength') == 1)
    health(8)
    for item in ('ITEM_MUSHROOM','ITEM_SUPER_SHROOM','ITEM_ULTRA_SHROOM','ITEM_DRIED_SHROOM'):
        check('healing-item-admitted-' + item,val(f'ttyd64_partner_combat_can_heal_with_item({item})') == 1)
        put('gBattleStatus.moveArgument',val(item))
        cmd('call create_target_list(gBattleStatus.playerActor, 0)')
        check('native-target-list-' + item,val('gBattleStatus.playerActor->targetListLength') == 2)
    for item in ('ITEM_LIFE_SHROOM','ITEM_HONEY_SYRUP','ITEM_FIRE_FLOWER'):
        check('unported-item-not-admitted-' + item,val(f'ttyd64_partner_combat_can_heal_with_item({item})') == 0)
    put('gTtyd64PartnerHPPrototypeEnabled',0)
    cmd('call create_target_list(gBattleStatus.playerActor, 0)')
    check('prototype-off-retains-mario-only-shroom-list',val('gBattleStatus.playerActor->targetListLength') == 1)
    put('gTtyd64PartnerHPPrototypeEnabled',1)
    for name, amount in target_setup.items():
        put('gBattleStatus.' + name,amount)
    # Four-update UI cadence and native sync; test independently of wall-clock FPS.
    cmd('call ttyd64_partner_hp_sync_display()')
    health(10)
    for _ in range(3):
        cmd('call ttyd64_partner_hp_update_display()')
    check('hp-display-waits-three-updates',val('ttyd64_partner_hp_display()') == 8)
    cmd('call ttyd64_partner_hp_update_display()')
    check('hp-display-increments-on-fourth',val('ttyd64_partner_hp_display()') == 9 and hp() == 10)
    health(3)
    for _ in range(4):
        cmd('call ttyd64_partner_hp_update_display()')
    check('hp-display-decrements-on-fourth',val('ttyd64_partner_hp_display()') == 8 and hp() == 3)
    health(0)
    cmd('call ttyd64_partner_hp_sync_display()')
    check('hp-display-can-show-zero',val('ttyd64_partner_hp_display()') == 0)
    health(8)
    cmd('call sync_status_bar()')
    check('native-status-sync-includes-partner',val('ttyd64_partner_hp_display()') == 8)
    put('gPlayerData.maxStarPower',1)
    tick(5)
    capture('healing-hud-star-power')
    put('gTtyd64PartnerHPPrototypeEnabled',0)
    check('prototype-off-hides-ui-and-refuses-healing',val('ttyd64_partner_hp_display()') == -1 and val(f'ttyd64_partner_combat_heal({actor},5)') == 0 and hp() == 8)
    tick(5)
    capture('healing-prototype-off')
    report={'checks_passed':len(checks),'checks':checks,'native_states':observations,'captures':screenshots,
            'limits':'Controlled battle/save/prototype setup; first item chosen with real keyboard input. Remaining checks use native APIs. Goombario/four shrooms and battle HUD only.'}
    Path(os.environ['PARTNER_HEALING_RESULT']).write_text(json.dumps(report,indent=2)+'\n')
    print('PARTNER_HEALING_PASSED='+str(len(checks)))
    cmd('kill')

try:
    run()
except Exception:
    import traceback
    traceback.print_exc()
    cmd('quit 1')
