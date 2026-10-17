"""Guarded world swap HP through native keyboard popup/selection/cleanup.

Only an exact disposable FP Drain save copy is accepted. Recruitment, ranks
and wounds are controlled setup; menu input, rendering and swaps run natively.
Run alone on its display so another runtime cannot steal controller focus.
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
    root = Path('/workspace/.paperboat-setup/partner-world-swap')
    runtime = Path(os.environ['SHIP_HOME']).resolve()
    assert runtime == root / 'runtime'
    save = runtime / 'saves/file3.json'
    original = save.read_bytes()
    assert original == Path('/workspace/.paperboat-setup/fp-drain/runtime/saves/file3.json').read_bytes()
    checks, states, captures, capture_states = [], [], [], []
    def hp():
        return val('ttyd64_get_partner_hp(1)')
    def check(name, condition):
        state = {'check':name,'hp':hp(),'partner':val('gPlayerData.curPartner'),
                 'world_partner':val('wCurrentPartnerId'),'world_menu':val('WorldMenuState'),
                 'popup_state':val('gPopupState'),'selected_row':val('PopupMenu_SelectedIndex'),
                 'content_width':val('gWindows[WIN_POPUP_CONTENT].width'),
                 'content_x':val('gWindows[WIN_POPUP_CONTENT].pos.x')}
        states.append(state)
        assert condition, name + ': ' + json.dumps(state)
        checks.append(name)
        print('WORLD_SWAP_CHECK=' + name)
    def tick(n=1):
        for _ in range(n):
            until('step_game_mode')
    def wait(expression, budget=360):
        for _ in range(budget):
            if val(expression):
                return
            tick()
        print('WORLD_SWAP_TIMEOUT=' + json.dumps({k:val(k) for k in (
            'WorldMenuState','WorldMenuType','gPopupState','gPlayerStatus.flags',
            'gPlayerStatus.animFlags','gPlayerStatus.actionState','gPlayerStatus.curButtons',
            'gPlayerStatus.pressedButtons','gGameStatusPtr->curButtons[0]',
            'gPartnerStatus.partnerActionState','gGameStatusPtr->introPart')}))
        capture('world-swap-timeout')
        raise AssertionError('Native frame budget: ' + expression)
    def focus():
        window = subprocess.check_output(['xdotool','search','--onlyvisible','--pid',str(gdb.selected_inferior().pid)],text=True).splitlines()[0]
        subprocess.run(['xdotool','windowraise',window],check=True)
        subprocess.run(['xdotool','windowfocus',window],check=True)
        assert int(subprocess.check_output(['xdotool','getwindowfocus'],text=True)) == int(window)
    def key(name, frames=3):
        focus()
        subprocess.run(['xdotool','keydown',name],check=True)
        try:
            for _ in range(frames):
                until('state_drawUI_world')
        finally:
            subprocess.run(['xdotool','keyup',name],check=True)
        tick(5)
    def capture(name):
        focus()
        # Take the picture while the game thread is running. Pausing inside
        # graphics construction can leave an incomplete/interpolated frame on
        # screen even though the numeric menu state is correct. The ignored
        # breakpoint lets native drawing run freely, then returns control.
        shot = root / (name + '.png')
        capture_proc = subprocess.Popen(['python3','-c',
            'import json,subprocess,sys,time; time.sleep(0.5); '
            'subprocess.run(["import","-window","root",sys.argv[1]],check=True); '
            'print(json.dumps({"completed_at":time.monotonic()}))',str(shot)],stdout=subprocess.PIPE,text=True)
        point = gdb.Breakpoint('popup_draw_menu_content',temporary=True,internal=True)
        point.silent = True
        point.ignore_count = 180
        cmd('continue')
        stopped_at = time.monotonic()
        stopped = [t for t in gdb.selected_inferior().threads() if t.is_stopped()]
        assert len(stopped) == 1
        stopped[0].switch()
        assert gdb.selected_frame().name() == 'popup_draw_menu_content'
        capture_timing = json.loads(capture_proc.communicate(timeout=5)[0])
        assert capture_proc.returncode == 0 and capture_timing['completed_at'] < stopped_at, 'Capture must complete while game thread runs'
        partner_list = val('WorldPopupMenu.popupType') == val('POPUP_MENU_SWITCH_PARTNER')
        capture_states.append({'capture':name,'ranks':[val(f'WorldPopupMenu.value[{i}]') for i in range(val('WorldPopupMenu.numEntries'))] if partner_list else [],
                               'rank_flags':val('get_hud_element(PopupMenu_PartnerLevelHID)->flags') if partner_list else None,
                               'rank_alpha':val('get_hud_element(PopupMenu_PartnerLevelHID)->opacity') if partner_list else None,
                               'captured_while_running':True,
                               'scroll_offset':val('D_8010D658'),'first_index':val('PopupMenu_FirstDisplayIndex'),
                               'up_flags':val('get_hud_element(PopupMenu_UpArrowHID)->flags'),
                               'down_flags':val('get_hud_element(PopupMenu_DownArrowHID)->flags')})
        captures.append(name)
    def open_menu():
        assert val('WorldMenuState') == 0
        key('Right')  # Native C-right (LUS keyboard scancode 333).
        wait('WorldMenuState == 3 && gPopupState == POPUP_STATE_CHOOSING')
        tick(15)
    def cancel():
        key('c')
        wait('WorldMenuState == 0 && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
        tick(15)
    def select_row(index):
        for _ in range(16):
            selected = val('PopupMenu_SelectedIndex')
            if selected == index:
                return
            key('s' if selected < index else 'w')
        raise AssertionError('Keyboard navigation did not reach row ' + str(index))
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
    open_menu()
    check('off-keyboard-opens-native-world-list',val('WorldPopupMenu.popupType') == val('POPUP_MENU_SWITCH_PARTNER') and val('WorldPopupMenu.numEntries') == 2)
    check('off-native-layout-and-inactive-hp',val('gWindows[WIN_POPUP_CONTENT].width') == 139 and val('popup_world_partner_hp_active()') == 0)
    capture('world-swap-prototype-off')
    cancel()
    check('off-cancel-preserves-partner-hp-and-input',val('wCurrentPartnerId') == 1 and hp() == 3)
    put('gTtyd64PartnerHPPrototypeEnabled',1)
    open_menu()
    check('on-source-world-list-geometry',val('gWindows[WIN_POPUP_CONTENT].width') == 208 and val('gWindows[WIN_POPUP_CONTENT].pos.x') == 91 and val('gWindows[WIN_POPUP_TITLE_B].pos.x') == 45)
    check('on-current-partner-row-remains-disabled',val('WorldPopupMenu.userIndex[0]') == 1 and val('WorldPopupMenu.enabled[0]') == 0 and val('WorldPopupMenu.enabled[1]') != 0)
    check('on-goombario-hp-uses-model-not-rank-value',hp() == 3 and val('WorldPopupMenu.value[0]') == 0 and val('ttyd64_get_partner_max_hp(1)') == 10)
    capture('world-swap-wounded')
    check('on-title-visible',val('gWindows[WIN_POPUP_TITLE_B].flags & WINDOW_FLAG_HIDDEN') == 0)
    check('on-prompt-hidden',val('gWindows[WIN_POPUP_PROMPT].flags & WINDOW_FLAG_HIDDEN') != 0)
    key('x')
    wait('gPopupState == POPUP_STATE_ALREADY_HAVE_PARTNER_AWAIT')
    check('current-row-selection-keeps-native-rejection',val('wCurrentPartnerId') == 1 and hp() == 3)
    key('c')
    wait('gPopupState == POPUP_STATE_CHOOSING')
    tick(5)
    check('rejection-return-keeps-prompt-hidden',val('gWindows[WIN_POPUP_PROMPT].flags & WINDOW_FLAG_HIDDEN') != 0)
    select_row(1)
    check('keyboard-navigates-to-kooper',val('WorldPopupMenu.userIndex[1]') == 2 and val('PopupMenu_SelectedIndex') == 1)
    key('x')
    wait('WorldMenuState == 0 && wCurrentPartnerId == 2 && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
    tick(60)
    check('keyboard-swap-completes-native-npc-and-cleans-popup',val('gPlayerData.curPartner') == 2 and hp() == 3 and val('gPopupState') == val('POPUP_STATE_MINUS_5'))
    assert val('ttyd64_set_partner_hp(1,0)') == 0
    open_menu()
    check('zero-hp-is-still-selectable-in-world',val('WorldPopupMenu.enabled[0]') != 0 and val('WorldPopupMenu.userIndex[0]') == 1)
    capture('world-swap-zero')
    select_row(0)
    key('x')
    wait('WorldMenuState == 0 && wCurrentPartnerId == 1 && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
    tick(60)
    check('keyboard-zero-hp-swap-back-preserves-world-owner',hp() == 0 and val('WorldPartnerID') == 1 and val('ttyd64_partner_hp_display()') == 0)
    put('gPlayerData.partners[1].level',2)
    cmd('call ttyd64_reset_partner_hp(1)')
    open_menu()
    check('ultra-rank-value-preserved-beside-thirty-max-hp',val('WorldPopupMenu.value[0]') == 2 and hp() == 30 and val('ttyd64_get_partner_max_hp(1)') == 30)
    capture('world-swap-ultra')
    cancel()
    # All eight native list identities/ranks exercise scrolling and clipping;
    # only Goombario receives the HP label in this bounded migration.
    for i in (1,2,3,4,6,7,8,9):
        put(f'gPlayerData.partners[{i}].enabled',1)
        put(f'gPlayerData.partners[{i}].level',2)
    open_menu()
    check('eight-partner-list-retains-native-cap-and-scroll',val('WorldPopupMenu.numEntries') == 8 and val('PopupMenu_DisplayedEntryCount') < 8)
    capture('world-swap-eight-top')
    select_row(7)
    tick(20)
    check('keyboard-scroll-reaches-last-native-identity',val('PopupMenu_FirstDisplayIndex') > 0 and val('WorldPopupMenu.userIndex[7]') == 8)
    capture('world-swap-eight-bottom')
    capture('world-swap-eight-bottom-repeat')
    cancel()
    # Switching menu with C-left must not leak widened geometry or HP/rank
    # interpretation into ordinary inventory entries.
    assert val('add_item(ITEM_MUSHROOM)') >= 0
    open_menu()
    key('Left')
    wait('WorldMenuState == 3 && WorldPopupMenu.popupType == POPUP_MENU_USE_ITEM && gPopupState == POPUP_STATE_CHOOSING')
    tick(20)
    check('keyboard-items-switch-restores-native-layout',val('gWindows[WIN_POPUP_CONTENT].width') == 145 and val('popup_world_partner_hp_active()') == 0)
    capture('world-swap-items')
    cancel()
    put('gTtyd64PartnerHPPrototypeEnabled',0)
    open_menu()
    check('off-reopen-restores-native-geometry-with-all-ranks',val('gWindows[WIN_POPUP_CONTENT].width') == 139 and val('popup_world_partner_hp_active()') == 0)
    capture('world-swap-final-off')
    select_row(7)
    tick(20)
    check('off-keyboard-scroll-keeps-native-ranks',val('PopupMenu_FirstDisplayIndex') > 0 and val('WorldPopupMenu.value[7]') == 2)
    capture('world-swap-off-bottom')
    cancel()
    check('final-menu-cleanup-keeps-normal-flag-off',val('gTtyd64PartnerHPPrototypeEnabled') == 0 and val('gPopupState') == val('POPUP_STATE_MINUS_5') and hp() == 30)
    assert save.read_bytes() == original
    Path(os.environ['WORLD_SWAP_RESULT']).write_text(json.dumps({
        'checks_passed':len(checks),'checks':checks,'native_states':states,'captures':captures,'capture_states':capture_states,
        'limits':'Native world C-right/arrow/A/B/C-left input, rendering, popup cleanup and NPC swaps. Recruitment, ranks and wounds are controlled. Goombario HP only; battle/pause lists and other partner combat not claimed.'},indent=2)+'\n')
    print('WORLD_SWAP_PASSED=' + str(len(checks)))
    cmd('kill')


try:
    run()
except Exception:
    import traceback
    traceback.print_exc()
    cmd('quit 1')
