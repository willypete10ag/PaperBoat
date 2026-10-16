"""Shared native route: menus, recipients, contact, team combat, victory and saving.

Strict disposable save; wounds/ranks/recruitment are controlled setup.
"""
import json
import os
import re
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
    assert len(stopped) == 1
    stopped[0].switch()
    assert gdb.selected_frame().name() == where


def run():
    playtest = os.environ.get('PARTNER_SLICE_PLAYTEST') == '1'
    runtime = Path(os.environ['SHIP_HOME']).resolve()
    root = runtime.parent if playtest else Path('/workspace/.paperboat-setup/partner-playable-slice')
    assert runtime == root / 'runtime'
    if playtest:
        assert root.parent == Path('/workspace/.paperboat-setup/goombario-playtest/sessions')
        assert re.fullmatch(r'[0-9]{8}T[0-9]{6}-[a-f0-9]{8}', root.name)
        assert (root / '.owned-playtest').read_text() == 'PaperBoat Goombario isolated playtest v1\n'
    save = runtime / 'saves/file3.json'
    original = save.read_bytes()
    assert original == Path('/workspace/.paperboat-setup/fp-drain/runtime/saves/file3.json').read_bytes()
    runtime_env = os.environ.copy()
    assert runtime_env.get('DISPLAY'), 'Set DISPLAY to the owned test server'
    cmd('set environment DISPLAY ' + runtime_env['DISPLAY'])
    print('PARTNER_SLICE_DISPLAY=' + runtime_env['DISPLAY'])
    phases = ['playtest'] if playtest else os.environ.get('PARTNER_SLICE_PHASES', 'pause,world-items,battle').split(',')
    assert phases == ['playtest'] if playtest else phases and set(phases) <= {'pause', 'world-items', 'battle', 'team', 'victory', 'victory-dead'}
    checks, states, captures = [], [], []
    team_trace = []
    def hp():
        return val('ttyd64_get_partner_hp(1)')
    def selected():
        if not val('gPausePartnersNumPartners'):
            return 0
        return val('gPausePartnersPartnerIDs[gPausePartnersPartnerIdx[gPausePartnersCurrentPartnerIdx]]')
    def check(name, condition):
        state = {'check':name,'hp':hp(),'max_hp':val('ttyd64_get_partner_max_hp(1)'),
                 'context':val('gGameStatusPtr->context'),'world_partner':val('wCurrentPartnerId'),
                 'selected':selected(),'panel':val('gPauseMenuCurrentTab'),
                 'tabs_col':val('gPausePanelTabs.col'),'ability_level':val('gPausePartnersLevel'),
                 'heart_id':val('Ttyd64PausePartnerHeartHID'),'world_owner':val('WorldPartnerID'),
                 'battle_state':val('gBattleState'),'battle_substate':val('gBattleSubState'),
                 'encounter_state':val('gEncounterState'),'player_in_back':bool(val('gBattleStatus.flags1 & BS_FLAGS1_PLAYER_IN_BACK'))}
        states.append(state)
        if not condition:
            (root/'failed-state.json').write_text(json.dumps({'checks_passed':len(checks),'state':state,'team_trace':team_trace},indent=2)+'\n')
        assert condition, name + ': ' + json.dumps(state)
        checks.append(name)
        print('PARTNER_SLICE_CHECK=' + name)
    def tick(n=1):
        for _ in range(n):
            until('step_game_mode')
    def wait(expression, budget=480):
        for _ in range(budget):
            if val(expression):
                return
            tick()
        print('PARTNER_PAUSE_TIMEOUT=' + json.dumps({k:val(k) for k in ('gGameStatusPtr->context','StepPauseState','StepPauseDelay','WorldMenuState','gPauseMenuCurrentTab','gPauseTabsCurrentTab','gPausePanelTabs.col','gPlayerStatus.flags','gBattleState','gBattleSubState','BattleMenuState','gPopupState','StratsCursorPos')}))
        raise AssertionError('Native frame budget: ' + expression)
    def focus():
        window = subprocess.check_output(['xdotool','search','--onlyvisible','--pid',str(gdb.selected_inferior().pid)],text=True,env=runtime_env).splitlines()[0]
        subprocess.run(['xdotool','windowraise',window],check=True,env=runtime_env)
        subprocess.run(['xdotool','windowfocus',window],check=True,env=runtime_env)
        assert int(subprocess.check_output(['xdotool','getwindowfocus'],text=True,env=runtime_env)) == int(window)
    def key(name, frames=3):
        focus()
        subprocess.run(['xdotool','keydown',name],check=True,env=runtime_env)
        try:
            for _ in range(frames):
                until('render_game_mode_backUI')
        finally:
            subprocess.run(['xdotool','keyup',name],check=True,env=runtime_env)
        for _ in range(3):
            until('render_game_mode_backUI')
    def capture(name):
        if val('gGameStatusPtr->context') == val('CONTEXT_BATTLE') and val('ttyd64_partner_combat_active(gBattleStatus.partnerActor)'):
            for _ in range(180):
                if val('ttyd64_partner_hp_display()') == hp():
                    break
                until('render_game_mode_backUI')
            else:
                raise AssertionError('Animated partner HP did not settle before capture')
        capture_start = {k:val(k) for k in ('gGameStatusPtr->context','gBattleState','gBattleSubState','gEncounterState')}
        focus()
        proc = subprocess.Popen(['python3','-c',
            'import json,subprocess,sys,time; time.sleep(0.5); '
            'subprocess.run(["import","-window","root",sys.argv[1]],check=True); '
            'print(json.dumps({"completed_at":time.monotonic()}))',str(root/(name+'.png'))],stdout=subprocess.PIPE,text=True,env=runtime_env)
        point = gdb.Breakpoint('render_game_mode_backUI',temporary=True,internal=True)
        point.silent = True
        point.ignore_count = 180
        cmd('continue')
        stopped_at = time.monotonic()
        stopped = [t for t in gdb.selected_inferior().threads() if t.is_stopped()]
        assert len(stopped) == 1
        stopped[0].switch()
        timing = json.loads(proc.communicate(timeout=5)[0])
        assert proc.returncode == 0 and timing['completed_at'] < stopped_at
        captures.append({'capture':name,'captured_while_running':True,'start_state':capture_start,'hp':hp(),'max_hp':val('ttyd64_get_partner_max_hp(1)'),
                         'selected':selected(),'panel':val('gPauseMenuCurrentTab'),'active':val('pause_partners_hp_active()'),
                         'context':val('gGameStatusPtr->context'),'encounter_state':val('gEncounterState'),'display_hp':val('ttyd64_partner_hp_display()')})
    def open_party():
        key('space')
        wait('gGameStatusPtr->context == CONTEXT_PAUSE && StepPauseDelay < -10')
        for _ in range(8):
            if val('gPauseTabsCurrentTab') == 3:
                break
            key('d')
        else:
            raise AssertionError('Keyboard did not reach Party tab')
        tick(50)
        key('x')
        wait('gPauseMenuCurrentTab == 4')
        tick(20)
    cycle = 0
    def close_pause():
        nonlocal cycle
        cycle += 1
        owned = val('Ttyd64PausePartnerHeartHID')
        focus()
        subprocess.run(['xdotool','keydown','space'],check=True,env=runtime_env)
        try:
            until('pause_partners_cleanup')
        finally:
            subprocess.run(['xdotool','keyup','space'],check=True,env=runtime_env)
        cmd('finish')
        check('native-pause-heart-cleanup-cycle-' + str(cycle),val('Ttyd64PausePartnerHeartHID') == -1 and (owned < 0 or val(f'get_hud_element({owned})') == 0))
        wait('gGameStatusPtr->context == CONTEXT_WORLD && WorldMenuState == 0 && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
        tick(20)
    def inventory(item='ITEM_MUSHROOM'):
        for i in range(10):
            put(f'gPlayerData.invItems[{i}]',val(item) if i < 2 else 0)
    def item_count():
        return sum(val(f'gPlayerData.invItems[{i}]') != 0 for i in range(10))
    def menu_ready(kind):
        wait(f'WorldMenuState == 3 && WorldMenuType == {kind} && gPopupState == POPUP_STATE_CHOOSING')
        tick(15)
    def open_items():
        key('Left')
        menu_ready(1)
    def open_recipient():
        open_items()
        key('x')
        menu_ready(3)
    def consume(row):
        if row:
            key('s')
        assert val('PopupMenu_SelectedIndex') == row
        key('x')
        wait('WorldMenuState == 0 && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
        tick(30)
    def enter_road_battle():
        put('gTtyd64PartnerHPPrototypeEnabled',1)
        put('gPlayerData.partners[1].level',0)
        cmd('call ttyd64_reset_partner_hp(1)')
        assert val('ttyd64_set_partner_hp(1,3)') == 3
        for field in ('curHP','curMaxHP','hardMaxHP'):
            put('gPlayerData.' + field,20)
        put('gPlayerData.hasActionCommands',1)
        for i in range(64):
            put(f'gPlayerData.equippedBadges[{i}]',0)
        inventory()
        cmd('call evt_set_variable((Evt*)0, GB_StoryProgress, STORY_CH1_DEFEATED_KOOPA_BROS)')
        cmd('call evt_set_variable((Evt*)0, GF_Tutorial_SwapTurnOrder, 1)')
        cmd('call switch_to_partner(1)')
        tick(80)
        # Map travel is controlled setup; collision, battle menus and outcome
        # below use ordinary keyboard input, without StartBattle/end-state calls.
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_CANT_TOUCH'))
        for field, amount in [('areaID',0),('mapID',7),('entryID',0)]:
            put('gGameStatusPtr->' + field,amount)
        cmd('call set_game_mode(GAME_MODE_CHANGE_MAP)')
        until('state_step_world')
        tick(100)
        wait('gGameStatusPtr->context == CONTEXT_WORLD && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
        check('battle-route-native-road-ready',val('gGameStatusPtr->mapID') == 7 and val('WorldPartnerID') == 1 and hp() == 3)
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_NONE'))
        walk_inputs = 0
        for _ in range(40):
            if val('gEncounterState') != val('ENCOUNTER_STATE_NEUTRAL'):
                break
            key('d',16)
            walk_inputs += 1
        wait('gGameStatusPtr->context == CONTEXT_BATTLE && gBattleState == BATTLE_STATE_PLAYER_MENU && BattleMenuState == BTL_MENU_STATE_CHOOSING',900)
        check('keyboard-contact-enters-guarded-native-battle',walk_inputs > 0 and val('gGameStatusPtr->debugEnemyContact') == 0 and val('gBattleStatus.partnerActor->curHP') == 3 and val('ttyd64_partner_combat_active(gBattleStatus.partnerActor)') == 1)
    def wheel(kind):
        index = next(i for i in range(val('WheelOptionCount')) if val(f'WheelOptionSubmenu[{i}]') == val(kind))
        for _ in range(10):
            current = val('BattleMenu_CurPos + BattleMenu_HomePos')
            if current == index:
                break
            key('a' if index < current else 'd')
            tick(12)
        assert val('BattleMenu_CurPos + BattleMenu_HomePos') == index
        key('x')
    def strategies():
        wheel('BTL_MENU_TYPE_STRATEGIES')
        wait('gBattleSubState == 201 && StratsMenuState == BTL_SUBMENU_STATE_CHOOSING')
        tick(10)
    def strategy(kind):
        index = next(i for i in range(val('StratsOptionCount')) if val(f'StratsOptionMenuTypes[{i}]') == val(kind))
        for _ in range(10):
            current = val('StratsCursorPos')
            if current == index:
                break
            key('w' if index < current else 's')
        assert val('StratsCursorPos') == index
        key('x')
    def battle_partners():
        strategies()
        strategy('BTL_MENU_TYPE_CHANGE_PARTNER')
        wait('gBattleSubState == 31 && gPopupState == POPUP_STATE_CHOOSING')
        tick(15)
    def cancel_battle_partners():
        key('c')
        wait('gBattleSubState == 201')
        key('c')
        wait('gBattleSubState < 4 && BattleMenuState == BTL_MENU_STATE_CHOOSING')
        tick(15)
    def spend_turn():
        state = val('gBattleState')
        strategies()
        strategy('BTL_MENU_TYPE_DO_NOTHING')
        wait(f'gBattleState != {state}',600)
        wait('(gBattleState == BATTLE_STATE_PLAYER_MENU || gBattleState == BATTLE_STATE_PARTNER_MENU) && gBattleSubState < 4 && BattleMenuState == BTL_MENU_STATE_CHOOSING',1800)
    def flee_battle():
        strategies()
        strategy('BTL_MENU_TYPE_RUN_AWAY')
        wait('gBattleState == BATTLE_STATE_RUN_AWAY',480)
        wait('gActionCommandStatus.state == 11',480)
        for _ in range(30):
            if val('gActionCommandStatus.state') != 11:
                break
            key('x',1)
        wait('gGameStatusPtr->context == CONTEXT_WORLD && gEncounterState == ENCOUNTER_STATE_NEUTRAL',1200)
    for setting in ('non-stop on','pagination off','confirm off','print thread-events off'):
        cmd('set ' + setting)
    gdb.Breakpoint('state_step_startup',temporary=True,internal=True)
    cmd('run')
    [t for t in gdb.selected_inferior().threads() if t.is_stopped()][0].switch()
    put('gPortResetToTitleScreen',1)
    until('state_step_title_screen')
    check('startup-prototype-off',val('gTtyd64PartnerHPPrototypeEnabled') == 0)
    put('TitleScreenNextState',val('NEXT_STATE_FILE_SELECT'))
    put('gGameStatusPtr->startupState',val('TITLE_STATE_EXIT'))
    put('gGameStatusPtr->titleScreenTimer',0)
    until('filemenu_update')
    assert val('fio_load_game(3)') == 1
    for name, amount in (('areaID',0),('mapID',1),('entryID',5)):
        put('gCurrentSaveFile.'+name,amount)
    put('gCurrentSaveFile.globalBytes[0]',val('STORY_CH0_MET_INNKEEPER'))
    for axis, n in (('x',250),('y',0),('z',85)):
        put('gCurrentSaveFile.savePos.'+axis,n)
    put('filemenu_menus[0]->state',val('FM_MAIN_SELECT_FILE'))
    put('filemenu_menus[0]->selected',0)
    put('filemenu_currentMenu',val('FILE_MENU_MAIN'))
    cmd('call set_game_mode(GAME_MODE_END_FILE_SELECT)')
    cmd('return')
    until('state_step_world')
    tick(100)
    # End-file-select has now restored PlayerData from the disposable record.
    for i in range(1,12):
        put(f'gPlayerData.partners[{i}].enabled',int(i in (1,2)))
        put(f'gPlayerData.partners[{i}].level',0)
    cmd('call ttyd64_reset_partner_hp(1)')
    assert val('ttyd64_set_partner_hp(1,3)') == 3
    cmd('call switch_to_partner(1)')
    tick(100)
    wait('wCurrentPartnerId == 1 && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
    if playtest:
        # Seed only this newly-created isolated session, after native load.
        # A new session is allocated by the launcher; real saves are not used.
        for i in range(1,12):
            put(f'gPlayerData.partners[{i}].enabled',int(i == 1))
        for field, amount in [('curHP',15),('curMaxHP',20),('hardMaxHP',20),
                              ('curFP',10),('curMaxFP',10),('hardMaxFP',10),
                              ('bootsLevel',0),('hammerLevel',0),('hasActionCommands',1)]:
            put('gPlayerData.' + field,amount)
        for i in range(64):
            put(f'gPlayerData.equippedBadges[{i}]',0)
        for i in range(10):
            put(f'gPlayerData.invItems[{i}]',val(['ITEM_MUSHROOM','ITEM_MUSHROOM','ITEM_MUSHROOM','ITEM_SUPER_SHROOM','ITEM_LIFE_SHROOM','ITEM_LIFE_SHROOM'][i]) if i < 6 else 0)
        cmd('call evt_set_variable((Evt*)0, GB_StoryProgress, STORY_CH1_DEFEATED_KOOPA_BROS)')
        cmd('call evt_set_variable((Evt*)0, GF_Tutorial_SwapTurnOrder, 1)')
        put('gTtyd64PartnerHPPrototypeEnabled',1)
        cmd('call ttyd64_partner_hp_world_bind(wCurrentPartnerId)')
        check('isolated-playtest-world-ready',hp() == 3 and val('ttyd64_partner_hp_display()') == 3 and val('wCurrentPartnerId') == 1 and val('gPlayerStatus.inputDisabledCount') == 0)
        # Prove native input is live before handing control to the tester.
        open_items()
        check('isolated-playtest-keyboard-items-open',val('WorldPopupMenu.numEntries') == 6)
        key('c')
        wait('WorldMenuState == 0 && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
        cmd('call open_status_bar_quickly()')
        tick(30)
        capture('playtest-ready')
        report = {'phases_run':phases,'checks_passed':len(checks),'checks':checks,
                  'native_states':states,'captures':captures,
                  'session':str(root),'pid':gdb.selected_inferior().pid,
                  'limits':'Prepared cloud/Linux developer launcher, existing private fixture seed and archives required. Fresh isolated session; prototype on only in this process. Goombario only, shroom family and existing native maps; incomplete TTYD64 port.'}
        Path(os.environ['PARTNER_SLICE_RESULT']).write_text(json.dumps(report,indent=2)+'\n')
        assert save.read_bytes() == original
        if os.environ.get('PARTNER_SLICE_VERIFY_ONLY') == '1':
            cmd('kill')
            print('GOOMBARIO_PLAYTEST_VERIFIED=1')
        else:
            cmd('detach')
            print('GOOMBARIO_PLAYTEST_READY=' + str(report['pid']))
        return
    if 'pause' in phases:
        open_party()
        check('off-keyboard-pause-party-keeps-native-no-heart',val('Ttyd64PausePartnerHeartHID') == -1 and val('pause_partners_hp_active()') == 0 and selected() == 1)
        capture('pause-party-off')
        close_pause()
        check('off-native-world-return-preserves-health',hp() == 3 and val('gPlayerData.curPartner') == 1)
        put('gTtyd64PartnerHPPrototypeEnabled',1)
        # Native creation is deliberately used before opening the guarded cycle.
        cmd('call switch_to_partner(2)')
        tick(100)
        cmd('call switch_to_partner(1)')
        tick(100)
        check('guarded-world-owner-before-pause',val('WorldPartnerID') == 1 and val('ttyd64_partner_hp_display()') == 3)
        open_party()
        check('guarded-pause-owns-manual-heart',val('Ttyd64PausePartnerHeartHID') >= 0 and val('get_hud_element(Ttyd64PausePartnerHeartHID)->flags & HUD_ELEMENT_FLAG_MANUAL_RENDER') != 0)
        check('guarded-selected-goombario-shows-wounded-health',val('pause_partners_hp_active()') != 0 and hp() == 3 and selected() == 1)
        capture('pause-party-wounded')
        key('d')
        wait('gPausePartnersCurrentPartnerIdx == 1')
        tick(30)
        check('carousel-other-selection-hides-goombario-hp',selected() == 2 and val('pause_partners_hp_active()') == 0 and val('gPlayerData.curPartner') == 1 and hp() == 3)
        capture('pause-party-kooper')
        key('a')
        wait('gPausePartnersCurrentPartnerIdx == 0')
        tick(30)
        check('carousel-back-restores-goombario-health',selected() == 1 and val('pause_partners_hp_active()') != 0 and hp() == 3)
        key('x')
        wait('gPausePartnersLevel == 1')
        check('keyboard-abilities-open-keeps-hp',val('pause_partners_hp_active()') != 0 and val('gWindows[WIN_PAUSE_PARTNERS_MOVELIST].height') == 56)
        capture('pause-party-abilities')
        key('s')
        check('keyboard-abilities-navigate-native-moves',val('gPausePartnersSelectedMove') == 1)
        key('c')
        wait('gPausePartnersLevel == 0')
        check('keyboard-abilities-back-keeps-carousel-hp',val('gPauseMenuCurrentTab') == 4 and val('pause_partners_hp_active()') != 0)
        assert val('ttyd64_set_partner_hp(1,0)') == 0
        check('pause-zero-hp-visible-without-changing-world-partner',val('pause_partners_hp_active()') != 0 and hp() == 0 and val('gPlayerData.curPartner') == 1)
        capture('pause-party-zero')
        put('gPlayerData.partners[1].level',2)
        cmd('call ttyd64_reset_partner_hp(1)')
        assert val('ttyd64_set_partner_hp(1,27)') == 27
        check('pause-ultra-rank-has-independent-current-and-max',hp() == 27 and val('ttyd64_get_partner_max_hp(1)') == 30 and val('gPlayerData.partners[1].level') == 2)
        capture('pause-party-ultra')
        key('c')
        wait('gPauseMenuCurrentTab == 0')
        key('a')
        tick(50)
        check('keyboard-page-away-leaves-partner-data-alone',val('gPauseTabsCurrentTab') != 3 and hp() == 27)
        capture('pause-party-page-away')
        key('d')
        tick(50)
        check('keyboard-page-return-preserves-health',val('gPauseTabsCurrentTab') == 3 and hp() == 27)
        capture('pause-party-page-return')
        close_pause()
        check('guarded-unpause-restores-world-hp-owner',val('WorldPartnerID') == 1 and val('ttyd64_partner_hp_display()') == 27 and hp() == 27)
        capture('pause-party-world-return')
        put('gTtyd64PartnerHPPrototypeEnabled',0)
        open_party()
        check('off-reopen-allocates-no-experimental-heart',val('Ttyd64PausePartnerHeartHID') == -1 and val('pause_partners_hp_active()') == 0 and hp() == 27)
        capture('pause-party-final-off')
        close_pause()
        check('off-final-world-control-and-passive-hp',val('gTtyd64PartnerHPPrototypeEnabled') == 0 and hp() == 27 and val('gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED') == 0)
    if 'world-items' in phases:
        put('gTtyd64PartnerHPPrototypeEnabled',1)
        put('gPlayerData.partners[1].level',0)
        cmd('call ttyd64_reset_partner_hp(1)')
        put('gPlayerData.curHP',2)
        inventory()
        assert val('ttyd64_set_partner_hp(1,3)') == 3
        open_recipient()
        check('world-recipient-native-menu-identities',val('WorldPopupMenu.numEntries') == 2 and val('WorldPopupMenu.userIndex[0]') == 0 and val('WorldPopupMenu.userIndex[1]') == 1 and item_count() == 2)
        capture('world-item-recipient')
        key('c')
        menu_ready(1)
        check('world-recipient-cancel-returns-inventory-without-consumption',item_count() == 2 and hp() == 3 and val('gPlayerData.curHP') == 2)
        key('c')
        wait('WorldMenuState == 0 && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
        check('world-recipient-cancel-restores-input-count',val('gPlayerStatus.inputDisabledCount') == 0 and val('gPartnerStatus.inputDisabledCount') == 0)
        open_recipient()
        consume(1)
        check('world-mushroom-heals-goombario-once-only',hp() == 8 and val('gPlayerData.curHP') == 2 and item_count() == 1 and val('gPlayerStatus.inputDisabledCount') == 0)
        capture('world-item-healed')
        # Group the remaining item potencies through the same real menu/script.
        for item, initial, expected in [('ITEM_MUSHROOM',0,5),('ITEM_SUPER_SHROOM',1,10),('ITEM_ULTRA_SHROOM',1,10),('ITEM_DRIED_SHROOM',3,4)]:
            inventory(item)
            assert val(f'ttyd64_set_partner_hp(1,{initial})') == initial
            open_recipient()
            consume(1)
            check('world-' + item.lower() + '-potency-zero-or-cap',hp() == expected and val('gPlayerData.curHP') == 2 and item_count() == 1)
        inventory()
        assert val('ttyd64_set_partner_hp(1,3)') == 3
        open_recipient()
        consume(0)
        check('world-mario-recipient-retains-native-heal',hp() == 3 and val('gPlayerData.curHP') == 7 and item_count() == 1)
        cmd('call switch_to_partner(2)')
        tick(100)
        inventory()
        open_recipient()
        consume(1)
        check('world-inactive-goombario-heals-without-changing-partner',hp() == 8 and val('wCurrentPartnerId') == 2 and val('gPlayerData.curHP') == 7 and item_count() == 1)
        put('gTtyd64PartnerHPPrototypeEnabled',0)
        put('gPlayerData.curHP',2)
        inventory()
        open_items()
        key('x')
        wait('WorldMenuState == 0 && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
        tick(30)
        check('world-off-item-remains-direct-native-mario-consumption',hp() == 8 and val('gPlayerData.curHP') == 7 and item_count() == 1 and val('WorldMenuType') == 1)
        capture('world-item-final-off')
    if 'battle' in phases:
        enter_road_battle()
        battle_partners()
        check('mario-battle-list-native-identities-and-geometry',val('gPopupMenu->numEntries') == 2 and val('gPopupMenu->userIndex[0]') == 1 and val('gPopupMenu->userIndex[1]') == 2 and val('gPopupMenu->enabled[0]') == 0 and val('gWindows[WIN_POPUP_CONTENT].width') == 181 and val('gWindows[WIN_POPUP_TITLE_B].pos.x') == 37)
        capture('battle-swap-wounded')
        key('x')
        wait('gBattleSubState == 31 && gPopupState == POPUP_STATE_CHOOSING')
        check('battle-current-row-rejection-preserves-hp-and-turns',hp() == 3 and val('gPlayerData.curPartner') == 1 and val('gBattleStatus.flags2 & BS_FLAGS2_PLAYER_TURN_USED') == 0)
        cancel_battle_partners()
        put('gTtyd64PartnerHPPrototypeEnabled',0)
        battle_partners()
        check('battle-off-list-keeps-native-width',val('gWindows[WIN_POPUP_CONTENT].width') == 139 and val('popup_partner_hp_active()') == 0 and hp() == 3)
        capture('battle-swap-off')
        cancel_battle_partners()
        put('gTtyd64PartnerHPPrototypeEnabled',1)
        battle_partners()
        key('s')
        assert val('gPopupMenu->userIndex[PopupMenu_SelectedIndex]') == 2
        key('x')
        wait('gBattleState == BATTLE_STATE_PARTNER_MENU && gPlayerData.curPartner == 2 && BattleMenuState == BTL_MENU_STATE_CHOOSING',900)
        check('mario-keyboard-swap-spends-mario-turn-preserves-goombario',hp() == 3 and val('gBattleStatus.flags2 & BS_FLAGS2_PLAYER_TURN_USED') != 0 and val('gBattleStatus.flags2 & BS_FLAGS2_PARTNER_TURN_USED') == 0 and val('ttyd64_partner_combat_active(gBattleStatus.partnerActor)') == 0)
        assert val('ttyd64_set_partner_hp(1,0)') == 0
        battle_partners()
        check('partner-menu-shows-selectable-zero-goombario',val('gPopupMenu->enabled[0]') != 0 and val('gPopupMenu->enabled[1]') == 0 and hp() == 0)
        capture('battle-swap-zero')
        key('w')
        assert val('gPopupMenu->userIndex[PopupMenu_SelectedIndex]') == 1
        key('x')
        wait('gBattleState == BATTLE_STATE_PLAYER_MENU && gPlayerData.curPartner == 1 && BattleMenuState == BTL_MENU_STATE_CHOOSING',1200)
        check('partner-keyboard-zero-swap-back-completes-next-turn',hp() == 0 and val('gBattleStatus.partnerActor->curHP') == 0 and val('btl_partner_can_act()') == 0)
        flee_battle()
        check('keyboard-flee-returns-world-with-zero-hp-owner',val('gCurrentEncounter.battleOutcome') == val('OUTCOME_PLAYER_FLED') and hp() == 0 and val('WorldPartnerID') == 1 and val('ttyd64_partner_hp_display()') == 0 and val('gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED') == 0)
        # The completed flee above is unforced. Prevent a new road encounter
        # during the subsequent world/pause/save observation and free capture.
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_CANT_TOUCH'))
        inventory()
        open_recipient()
        consume(1)
        check('post-battle-keyboard-world-shroom-restores-zero-partner',hp() == 5 and item_count() == 1 and val('WorldPartnerID') == 1)
        open_party()
        check('post-battle-pause-shows-healed-partner',selected() == 1 and hp() == 5 and val('pause_partners_hp_active()') != 0)
        close_pause()
        try:
            cmd('call fio_save_game(3)')
            assert val('ttyd64_set_partner_hp(1,0)') == 0
            assert val('fio_load_game(3)') == 1
            check('playable-route-health-and-item-persist-native-fio',hp() == 5 and item_count() == 1)
        finally:
            save.write_bytes(original)
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_CANT_TOUCH'))
        cmd('call open_status_bar_quickly()')
        tick(30)
        capture('battle-route-world-return')
        check('route-final-capture-remains-in-world',val('gGameStatusPtr->context') == val('CONTEXT_WORLD') and val('gEncounterState') == val('ENCOUNTER_STATE_NEUTRAL'))
        put('gTtyd64PartnerHPPrototypeEnabled',0)
    if 'team' in phases:
        enter_road_battle()
        check('team-native-front-back-helper-mario-front',val('ttyd64_partner_team_target(0)') == val('ACTOR_PLAYER') and val('ttyd64_partner_team_target(1)') == val('ACTOR_PARTNER'))
        key('z')
        wait('gBattleState == BATTLE_STATE_PARTNER_MENU && gBattleSubState == 3 && BattleMenuState == BTL_MENU_STATE_CHOOSING')
        check('team-keyboard-z-exchanges-positions-and-acting-partner',val('gBattleStatus.flags1 & BS_FLAGS1_PLAYER_IN_BACK') != 0 and val('gBattleStatus.partnerActor->homePos.x > gBattleStatus.playerActor->homePos.x') != 0 and val('ttyd64_partner_team_target(0)') == val('ACTOR_PARTNER') and val('ttyd64_partner_team_target(1)') == val('ACTOR_PLAYER'))
        capture('team-partner-front')
        key('z')
        wait('gBattleState == BATTLE_STATE_PLAYER_MENU && gBattleSubState == 1 && BattleMenuState == BTL_MENU_STATE_CHOOSING')
        check('team-keyboard-z-restores-mario-front',val('gBattleStatus.flags1 & BS_FLAGS1_PLAYER_IN_BACK') == 0 and val('gBattleStatus.playerActor->homePos.x > gBattleStatus.partnerActor->homePos.x') != 0)
        key('z')
        wait('gBattleState == BATTLE_STATE_PARTNER_MENU && gBattleSubState == 3 && BattleMenuState == BTL_MENU_STATE_CHOOSING')
        # Only initial wound/inventory are controlled. Actual Goomba rolls,
        # targets, damage, death/revival and subsequent turn progression run.
        assert val('ttyd64_set_partner_hp(1,1)') == 1
        for i in range(10):
            put(f'gPlayerData.invItems[{i}]',val('ITEM_LIFE_SHROOM') if i < 2 else 0)
        def model_hp():
            return val('gCurrentSaveFile.shipSaveData.partnerHP[1].curHP')
        def life_count():
            return sum(val(f'gPlayerData.invItems[{i}]') == val('ITEM_LIFE_SHROOM') for i in range(10))
        class TraceFinish(gdb.FinishBreakpoint):
            def __init__(self, kind, actor_id=0):
                super().__init__(gdb.newest_frame(), internal=True)
                self.kind, self.actor_id = kind, actor_id
                self.silent = True
            def stop(self):
                row = {'event':self.kind,'hp':model_hp(),'life_items':life_count(),
                       'mario_hp':val('gPlayerData.curHP'),'player_in_back':bool(val('gBattleStatus.flags1 & BS_FLAGS1_PLAYER_IN_BACK'))}
                if self.kind == 'target':
                    row['enemy_id'] = self.actor_id
                    row['target'] = val(f'gBattleStatus.enemyActors[{self.actor_id & 255}]->targetActorID')
                team_trace.append(row)
                return False
        class Trace(gdb.Breakpoint):
            def __init__(self, where, kind):
                super().__init__(where, internal=True)
                self.kind = kind
                self.silent = True
            def stop(self):
                if self.kind == 'target':
                    TraceFinish('target',val('script->owner1.actorID'))
                elif self.kind == 'life':
                    TraceFinish('life')
                elif self.kind == 'death':
                    team_trace.append({'event':'death','hp':model_hp(),'life_items':life_count()})
                elif val('actor') == val('gBattleStatus.partnerActor'):
                    team_trace.append({'event':'damage-store','before':model_hp(),'actor_hp':val('actor->curHP')})
                return False
        trace_points = [Trace('Ttyd64GoombaChooseTarget','target'),Trace('ttyd64_partner_combat_use_life_shroom','life'),Trace('ttyd64_partner_combat_mark_dead','death'),Trace('ttyd64_partner_combat_store_hp','damage')]
        spend_turn()
        check('team-automatic-next-actor-keeps-partner-in-front',val('gBattleState') == val('BATTLE_STATE_PLAYER_MENU') and val('gBattleStatus.flags1 & BS_FLAGS1_PLAYER_IN_BACK') != 0 and val('gBattleStatus.partnerActor->homePos.x > gBattleStatus.playerActor->homePos.x') != 0)
        for _ in range(12):
            if any(row['event'] == 'life' for row in team_trace):
                break
            spend_turn()
        check('team-ordinary-goomba-hit-revives-once',any(row['event'] == 'target' and row['target'] == val('ACTOR_PARTNER') for row in team_trace) and any(row['event'] == 'damage-store' and row['actor_hp'] < row['before'] for row in team_trace) and len([r for r in team_trace if r['event'] == 'life']) == 1 and life_count() == 1 and hp() > 0)
        check('team-life-shroom-keeps-front-and-restores-pose',val('gBattleStatus.flags1 & BS_FLAGS1_PLAYER_IN_BACK') != 0 and val('gBattleStatus.partnerActor->rot.x') == 0)
        check('team-front-partner-opens-next-round',val('gBattleState') == val('BATTLE_STATE_PARTNER_MENU') and val('btl_partner_can_act()') != 0)
        capture('team-natural-revival')
        for i in range(10):
            put(f'gPlayerData.invItems[{i}]',0)
        assert val('ttyd64_set_partner_hp(1,1)') == 1
        for _ in range(12):
            if hp() == 0:
                break
            spend_turn()
        check('team-natural-no-item-death-restores-mario-front',hp() == 0 and val('gBattleState') == val('BATTLE_STATE_PLAYER_MENU') and val('gBattleStatus.flags1 & BS_FLAGS1_PLAYER_IN_BACK') == 0 and val('gBattleStatus.playerActor->homePos.x > gBattleStatus.partnerActor->homePos.x') != 0 and val('gBattleStatus.partnerActor->rot.x') == 86)
        check('team-dead-partner-target-falls-back-to-mario',val('ttyd64_partner_team_target(0)') == val('ACTOR_PLAYER') and val('ttyd64_partner_team_target(1)') == val('ACTOR_PLAYER') and val('ttyd64_partner_team_resolve_target(ACTOR_PARTNER)') == val('ACTOR_PLAYER') and val('btl_partner_can_act()') == 0)
        capture('team-natural-death')
        after_death = len(team_trace)
        spend_turn()
        targets = [r for r in team_trace[after_death:] if r['event'] == 'target']
        check('team-next-round-ai-attacks-mario-not-dead-partner',len(targets) >= 2 and all(r['target'] == val('ACTOR_PLAYER') for r in targets) and hp() == 0 and len([r for r in team_trace if r['event'] == 'death']) == 2)
        put('gTtyd64PartnerHPPrototypeEnabled',0)
        check('team-off-target-and-swap-helpers-preserve-native',val('ttyd64_partner_team_active()') == 0 and val('ttyd64_partner_team_resolve_target(ACTOR_PARTNER)') == val('ACTOR_PARTNER') and val('ttyd64_partner_team_should_swap(1)') != 0 and val('ttyd64_partner_team_should_swap(0)') == 0 and hp() == 0)
        put('gTtyd64PartnerHPPrototypeEnabled',1)
        flee_battle()
        check('team-natural-combat-flee-keeps-zero-health-world-owner',hp() == 0 and val('WorldPartnerID') == 1 and val('gCurrentEncounter.battleOutcome') == val('OUTCOME_PLAYER_FLED'))
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_CANT_TOUCH'))
        for point in trace_points:
            point.delete()
    for victory_phase in [phase for phase in phases if phase in ('victory', 'victory-dead')]:
        enter_road_battle()
        # Seed a non-level-up reward boundary; attack/HP/outcome/rewards are
        # observed, never forced. Basic attacks intentionally omit timed A.
        put('gPlayerData.starPoints',0)
        before_wins = val('gPlayerData.battlesWon')
        before_items = item_count()
        key('z')
        wait('gBattleState == BATTLE_STATE_PARTNER_MENU && gBattleSubState == 3 && BattleMenuState == BTL_MENU_STATE_CHOOSING')
        dead_victory = victory_phase == 'victory-dead'
        if dead_victory:
            assert val('ttyd64_set_partner_hp(1,1)') == 1
            for i in range(10):
                put(f'gPlayerData.invItems[{i}]',0)
            before_items = 0
            for _ in range(16):
                if hp() == 0:
                    break
                spend_turn()
            check('victory-natural-death-before-mario-finishes',hp() == 0 and val('gBattleStatus.partnerActor->rot.x') == 86 and val('gBattleState') == val('BATTLE_STATE_PLAYER_MENU'))
        victory_trace = []
        class VictoryTrace(gdb.Breakpoint):
            def __init__(self):
                super().__init__('btl_state_update_celebration', internal=True)
                self.silent = True
            def stop(self):
                if not victory_trace:
                    victory_trace.append({'hp':hp(),'rotation':val('gBattleStatus.partnerActor->rot.x'),
                        'player_in_back':bool(val('gBattleStatus.flags1 & BS_FLAGS1_PLAYER_IN_BACK')),
                        'partner_ahead':bool(val('gBattleStatus.partnerActor->homePos.x > gBattleStatus.playerActor->homePos.x')),
                        'reward':val('gBattleStatus.totalStarPoints')})
                return False
        victory_point = VictoryTrace()
        attacks = []
        for _ in range(16):
            if val('gGameStatusPtr->context') != val('CONTEXT_BATTLE') or val('gBattleState') == val('BATTLE_STATE_CELEBRATION'):
                break
            partner_turn = val('gBattleState') == val('BATTLE_STATE_PARTNER_MENU')
            wheel('BTL_MENU_TYPE_ABILITY' if partner_turn else 'BTL_MENU_TYPE_JUMP')
            if partner_turn:
                wait('gBattleSubState == 11 && MovesMenuState == BTL_SUBMENU_STATE_CHOOSING')
                key('x')
            wait('gBattleState == BATTLE_STATE_SELECT_TARGET && gBattleSubState == 1')
            attacks.append({'actor':256 if partner_turn else 0,'move':val('gBattleStatus.selectedMoveID')})
            key('x')
            wait('gBattleState != BATTLE_STATE_SELECT_TARGET')
            wait('(gBattleState == BATTLE_STATE_PLAYER_MENU || gBattleState == BATTLE_STATE_PARTNER_MENU) && gBattleSubState < 4 && BattleMenuState == BTL_MENU_STATE_CHOOSING || gBattleState == BATTLE_STATE_CELEBRATION',2400)
        # State transition precedes the first celebration update callback.
        if not victory_trace:
            tick()
        check('victory-ordinary-attacks-defeat-native-goombas',bool(victory_trace) and (dead_victory or any(a['actor'] == 256 for a in attacks)) and any(a['actor'] == 0 for a in attacks))
        check('victory-dead-partner-upright-without-revival' if dead_victory else 'victory-living-front-partner-keeps-position-and-upright-pose',victory_trace[0]['rotation'] == 0 and (victory_trace[0]['hp'] == 0 and not victory_trace[0]['player_in_back'] if dead_victory else victory_trace[0]['hp'] > 0 and victory_trace[0]['player_in_back'] and victory_trace[0]['partner_ahead']))
        capture(victory_phase + '-celebration')
        wait('gGameStatusPtr->context == CONTEXT_WORLD && gEncounterState == ENCOUNTER_STATE_NEUTRAL && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)',2400)
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_CANT_TOUCH'))
        reward = victory_trace[0]['reward']
        check('victory-native-star-points-and-win-count-awarded-once',reward > 0 and val('gPlayerData.starPoints') == reward and val('gPlayerData.battlesWon') == before_wins + 1 and val('gCurrentEncounter.battleOutcome') == val('OUTCOME_PLAYER_WON'))
        remaining_hp = hp()
        check('victory-world-owns-wounded-health-and-unused-items',(remaining_hp == 0 if dead_victory else remaining_hp > 0) and val('WorldPartnerID') == 1 and val('ttyd64_partner_hp_display()') == remaining_hp and item_count() == before_items)
        # Controlled map/position setup; the block hit, prompt and save itself
        # are driven by ordinary input. Keep the strict disposable slot guard.
        for field, amount in [('areaID',0),('mapID',1),('entryID',0)]:
            put('gGameStatusPtr->' + field,amount)
        cmd('call set_game_mode(GAME_MODE_CHANGE_MAP)')
        until('state_step_world')
        tick(100)
        wait('gGameStatusPtr->context == CONTEXT_WORLD && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
        for axis, amount in [('x',250),('y',0),('z',75)]:
            put('gPlayerStatus.pos.' + axis,amount)
        tick(20)
        wait('gPlayerStatus.actionState == ACTION_STATE_IDLE')
        capture(victory_phase + '-save-ready')
        saves = []
        class SaveTrace(gdb.Breakpoint):
            def __init__(self):
                super().__init__('entity_SaveBlock_save_data',internal=True)
                self.silent = True
            def stop(self):
                saves.append({'hp':hp(),'star_points':val('gPlayerData.starPoints'),'slot':val('gGameStatusPtr->saveSlot')})
                return False
        save_point = SaveTrace()
        try:
            assert val('gGameStatusPtr->saveSlot') == 3
            # A world jump needs a sustained hold; the short menu-confirm tap
            # can release below the block. Do not alter jump physics/position.
            key('x',18)
            for _ in range(30):
                if saves:
                    break
                key('x')
                tick(25)
            print('PARTNER_SAVE_OBSERVATION=' + json.dumps({'saves':saves,'position':{axis:val('gPlayerStatus.pos.'+axis) for axis in ('x','y','z')},'action':val('gPlayerStatus.actionState'),'input_disabled':val('gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED'),'tutorial_closed':val('SaveBlockTutorialPrinterClosed'),'result_closed':val('SaveBlockResultPrinterClosed')}))
            if not saves:
                capture(victory_phase + '-save-failure')
            check('victory-keyboard-save-block-writes-disposable-slot',len(saves) == 1 and saves[0]['slot'] == 3 and saves[0]['hp'] == remaining_hp and save.read_bytes() != original)
            for _ in range(12):
                if not val('gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED'):
                    break
                key('x')
                tick(20)
            check('victory-save-block-releases-world-input',val('gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED') == 0 and hp() == remaining_hp)
            disturbed_hp = 4 if remaining_hp == 0 else 0
            assert val(f'ttyd64_set_partner_hp(1,{disturbed_hp})') == disturbed_hp
            put('gPlayerData.starPoints',0)
            assert val('fio_load_game(3)') == 1
            check('victory-native-save-load-preserves-reward-and-health',hp() == remaining_hp and val('gPlayerData.starPoints') == reward and val('gPlayerData.battlesWon') == before_wins + 1)
        finally:
            save_point.delete()
            save.write_bytes(original)
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_CANT_TOUCH'))
        cmd('call open_status_bar_quickly()')
        tick(30)
        capture(victory_phase + '-world-return')
        victory_point.delete()
        team_trace.extend([{'event':victory_phase,'attacks':attacks,'saves':saves,**victory_trace[0]}])
        put('gTtyd64PartnerHPPrototypeEnabled',0)
    assert save.read_bytes() == original
    Path(os.environ['PARTNER_SLICE_RESULT']).write_text(json.dumps({'phases_run':phases,'checks_passed':len(checks),'checks':checks,'native_states':states,'captures':captures,'team_trace':team_trace,
        'limits':'Only listed phases run. Victory phases use keyboard attacks, native enemy defeat/rewards/world return and keyboard Save Block hit/prompt; map/position, initial HP/items/progression and non-level-up boundary are controlled. Reload calls native FIO, not a title restart. Native keyboard pause and/or world item menu/script phases as listed. Recruitment, inventory, ranks and wounds are controlled; no all-partner UI, source artwork/choreography parity or campaign claim. Battle phase controls map/progression, inventory, health and action-command unlock; contact, swap menus, flee outcome, recovery menus and native lifecycle use real keyboard input.'},indent=2)+'\n')
    print('PARTNER_SLICE_PHASES_PASSED=' + ','.join(phases) + ':' + str(len(checks)))
    cmd('kill')


try:
    run()
except Exception:
    import traceback
    traceback.print_exc()
    cmd('quit 1')
