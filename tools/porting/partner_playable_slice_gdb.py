"""Shared playable-slice driver: pause and world-recipient phases.

Strict disposable save; wounds/ranks/recruitment are controlled setup.
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
    assert len(stopped) == 1
    stopped[0].switch()
    assert gdb.selected_frame().name() == where


def run():
    root = Path('/workspace/.paperboat-setup/partner-playable-slice')
    runtime = Path(os.environ['SHIP_HOME']).resolve()
    assert runtime == root / 'runtime'
    save = runtime / 'saves/file3.json'
    original = save.read_bytes()
    assert original == Path('/workspace/.paperboat-setup/fp-drain/runtime/saves/file3.json').read_bytes()
    runtime_env = os.environ.copy()
    assert runtime_env.get('DISPLAY'), 'Set DISPLAY to the owned test server'
    phases = os.environ.get('PARTNER_SLICE_PHASES', 'pause,world-items').split(',')
    assert phases and set(phases) <= {'pause', 'world-items'}
    checks, states, captures = [], [], []
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
                 'heart_id':val('Ttyd64PausePartnerHeartHID'),'world_owner':val('WorldPartnerID')}
        states.append(state)
        if not condition:
            (root/'failed-state.json').write_text(json.dumps({'checks_passed':len(checks),'state':state},indent=2)+'\n')
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
        print('PARTNER_PAUSE_TIMEOUT=' + json.dumps({k:val(k) for k in ('gGameStatusPtr->context','StepPauseState','StepPauseDelay','WorldMenuState','gPauseMenuCurrentTab','gPauseTabsCurrentTab','gPausePanelTabs.col','gPlayerStatus.flags')}))
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
        captures.append({'capture':name,'captured_while_running':True,'hp':hp(),'max_hp':val('ttyd64_get_partner_max_hp(1)'),
                         'selected':selected(),'panel':val('gPauseMenuCurrentTab'),'active':val('pause_partners_hp_active()')})
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
    assert save.read_bytes() == original
    Path(os.environ['PARTNER_SLICE_RESULT']).write_text(json.dumps({'phases_run':phases,'checks_passed':len(checks),'checks':checks,'native_states':states,'captures':captures,
        'limits':'Native keyboard pause and/or world item menu/script phases as listed. Recruitment, inventory, ranks and wounds are controlled; no all-partner UI, source artwork/choreography parity or ordinary encounter claim.'},indent=2)+'\n')
    print('PARTNER_SLICE_PHASES_PASSED=' + ','.join(phases) + ':' + str(len(checks)))
    cmd('kill')


try:
    run()
except Exception:
    import traceback
    traceback.print_exc()
    cmd('quit 1')
