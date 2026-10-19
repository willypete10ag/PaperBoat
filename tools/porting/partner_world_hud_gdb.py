"""Guarded Goombario world HP ownership and native NPC/map lifecycle.

Only the runner-generated disposable new-game seed copy is writable. Native switch/map
APIs control selections; event scripts advance by continue, not recursive calls.
"""
import json
import os
from pathlib import Path
import subprocess
import time
import gdb
import sys
if not os.environ.get('PORTING_FIXTURE_DIR'):
    raise RuntimeError('Missing PORTING_FIXTURE_DIR; use run_acceptance.sh')
sys.path.insert(0,os.environ['PORTING_FIXTURE_DIR'])
from fixture_support import *
validate_runtime()


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
    root = fixture_path('partner-world-hud')
    runtime = Path(required_env('SHIP_HOME')).resolve()
    assert runtime == root / 'runtime'
    save = fixture_save()
    original = save.read_bytes()
    assert original == Path(required_env('PORTING_SEED_SAVE')).read_bytes()
    checks, snapshots, captures = [], [], []
    def hp(i=1):
        return val(f'ttyd64_get_partner_hp({i})')
    def display():
        return val('ttyd64_partner_hp_display()')
    def health(n):
        assert val(f'ttyd64_set_partner_hp(1,{n})') == n
    def check(name, condition):
        snapshots.append({'check':name,'hp':hp(),'display_hp':display(),
                          'selected_partner':val('gPlayerData.curPartner'),
                          'world_partner':val('wCurrentPartnerId'),
                          'context':val('gGameStatusPtr->context'),
                          'world_owner':val('WorldPartnerID'),
                          'demo_state':val('gGameStatusPtr->demoState'),
                          'hud_disabled':val('gStatusBar.disabled'),
                          'intro_part':val('gGameStatusPtr->introPart')})
        assert condition, name + ': ' + json.dumps(snapshots[-1])
        checks.append(name); record_check(name)
        print('WORLD_HUD_CHECK=' + name)
    def tick(n=1):
        for _ in range(n):
            # The native HUD advances in the UI pass. Simulation steps may
            # outnumber drawn frames under debugger-induced frame skipping.
            until('state_drawUI_world')
    def capture(name):
        cmd('call open_status_bar_quickly()')
        tick(15)
        window = subprocess.check_output(['xdotool','search','--onlyvisible','--pid',str(gdb.selected_inferior().pid)],text=True).splitlines()[0]
        subprocess.run(['xdotool','windowraise',window],check=True)
        subprocess.run(['xdotool','windowfocus',window],check=True)
        time.sleep(0.5)
        subprocess.run(['import','-window','root',str(root/(name+'.png'))],check=True)
        captures.append(name)
    def switch(i):
        cmd(f'call switch_to_partner({i})')
        tick(100)
        assert val('wCurrentPartnerId') == i and val('gPlayerData.curPartner') == i
        assert val('gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED') == 0
    for setting in ('non-stop on','pagination off','confirm off','print thread-events off'):
        cmd('set ' + setting)
    gdb.Breakpoint('state_step_startup',temporary=True,internal=True)
    cmd('run')
    [t for t in gdb.selected_inferior().threads() if t.is_stopped()][0].switch()
    put('gPortResetToTitleScreen',1)
    until('state_step_title_screen')
    check('prototype-default-off',val('ttyd64_mode_enabled()') == 0)
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
    for i in (1,2):
        put(f'gPlayerData.partners[{i}].enabled',1)
        put(f'gPlayerData.partners[{i}].level',0)
    health(3)
    assert val('ttyd64_set_partner_hp(2,4)') == 4
    put('filemenu_menus[0]->state',val('FM_MAIN_SELECT_FILE'))
    put('filemenu_menus[0]->selected',0)
    put('filemenu_currentMenu',val('FILE_MENU_MAIN'))
    cmd('call set_game_mode(GAME_MODE_END_FILE_SELECT)')
    cmd('return')
    until('state_step_world')
    tick(90)
    # End-file-select restores PlayerData from the loaded record. Apply test
    # recruitment after that copy; the original fixture unlocks Bow alone.
    for i in (1,2):
        put(f'gPlayerData.partners[{i}].enabled',1)
    switch(1)
    check('native-world-switch-keeps-prototype-off',display() == -1 and hp() == 3)
    cmd('call ttyd64_mode_select_file(1)')
    cmd('call sync_status_bar()')
    tick()
    check('guarded-world-display-initializes-current-hp',display() == 3)
    capture('world-hud-wounded')
    health(7)
    cmd('call ttyd64_partner_hp_sync_display()')
    health(3)
    for _ in range(3):
        cmd('call ttyd64_partner_hp_update_display()')
    check('world-display-waits-three-updates',display() == 7)
    cmd('call ttyd64_partner_hp_update_display()')
    check('world-display-decrements-on-fourth',display() == 6)
    tick(20)
    check('native-world-updates-reach-wounded-hp',display() == 3)
    health(1)
    cmd('call sync_status_bar()')
    check('native-world-status-sync-snaps-hp',display() == 1)
    cmd('call FullyRestoreHPandFP((Evt*)0,1)')
    check('world-full-heal-preserves-display-animation',hp() == 10 and display() == 1)
    for _ in range(4):
        cmd('call ttyd64_partner_hp_update_display()')
    check('world-full-heal-display-increments-on-fourth',display() == 2)
    tick(40)
    check('native-world-full-heal-animation-finishes',display() == 10)
    capture('world-hud-restored')
    health(6)
    switch(2)
    # Ground-partner support was already extended to Kooper/Bombette. The
    # former Goombario-only hidden-row expectation is obsolete at this head.
    check('native-supported-kooper-owns-world-row',display() == 10 and hp() == 6 and hp(2) == 10
          and val('ttyd64_partner_hp_display_partner()') == 2 and val('WorldPartnerID') == 2)
    capture('world-hud-supported-kooper')
    put('gPlayerData.partners[4].enabled',1)
    switch(4)
    check('native-unsupported-parakarry-hides-world-row',display() == -1 and hp() == 6 and hp(2) == 10
          and val('ttyd64_partner_hp_display_partner()') == 0)
    capture('world-hud-unsupported-parakarry')
    switch(1)
    check('native-swap-back-snaps-saved-health',display() == 6 and hp() == 6)
    capture('world-hud-swap-back')
    switch(0)
    check('native-put-away-hides-row',display() == -1 and hp() == 6)
    put('gPlayerData.curPartner',1)
    check('selected-id-without-world-owner-stays-hidden',display() == -1)
    put('gPlayerData.curPartner',0)
    health(0)
    switch(1)
    check('native-bring-out-shows-zero-hp',display() == 0 and hp() == 0)
    capture('world-hud-zero')
    old_flags = val('gPlayerStatus.animFlags')
    put('gPlayerStatus.animFlags',old_flags | val('PA_FLAG_USING_PEACH_PHYSICS'))
    check('peach-context-hides-world-hp',display() == -1)
    cmd('call ttyd64_partner_hp_update_display()')
    put('gPlayerStatus.animFlags',old_flags)
    cmd('call ttyd64_partner_hp_update_display()')
    check('world-display-returns-after-peach-guard',display() == 0)
    put('gGameStatusPtr->demoState',val('DEMO_STATE_ACTIVE'))
    check('world-demo-hides-hp',display() == -1)
    put('gGameStatusPtr->demoState',val('DEMO_STATE_NONE'))
    put('gPlayerData.partners[1].enabled',0)
    check('locked-goombario-hides-hp',display() == -1)
    put('gPlayerData.partners[1].enabled',1)
    put('gGameStatusPtr->context',val('CONTEXT_BATTLE'))
    check('world-owner-cannot-leak-into-unbound-battle',display() == -1)
    put('gGameStatusPtr->context',val('CONTEXT_WORLD'))
    put('gPlayerData.partners[1].level',1)
    cmd('call ttyd64_reset_partner_hp(1)')
    cmd('call sync_status_bar()')
    put('gPlayerData.maxStarPower',1)
    check('world-rank-max-and-status-sync',hp() == 20 and display() == 20 and val('ttyd64_get_partner_max_hp(1)') == 20)
    capture('world-hud-rank-and-star-power')
    # Native map teardown/reset/recreation must invalidate old world ownership.
    cmd('call set_global_flag(GF_KMR20_ReunitedWithLuigi)')
    for name, n in (('areaID',0),('mapID',11),('entryID',4)):
        put('gGameStatusPtr->'+name,n)
    cmd('call set_game_mode(GAME_MODE_CHANGE_MAP)')
    until('create_partner_npc')
    check('native-map-teardown-invalidates-old-row',display() == -1 and hp() == 20)
    until('state_step_world')
    tick(150)
    check('native-map-recreation-restores-current-row',display() == 20 and hp() == 20 and val('wCurrentPartnerId') == 1)
    capture('world-hud-after-map-change')
    try:
        cmd('call fio_save_game(3)')
        health(0)
        assert val('fio_load_game(3)') == 1
        cmd('call sync_status_bar()')
        check('native-fio-preserves-world-hp-and-rank',hp() == 20 and display() == 20)
    finally:
        save.write_bytes(original)
    cmd('call ttyd64_mode_select_file(0)')
    check('prototype-off-immediately-hides-world-row',display() == -1 and hp() == 20)
    capture('world-hud-prototype-off')
    Path(required_env('WORLD_HUD_RESULT')).write_text(json.dumps({
        'checks_passed':len(checks),'checks':checks,'native_states':snapshots,'captures':captures,
        'limits':'Guarded Goombario world HUD. Controlled native world switch/map selections, API wounds/rank/full-rest/FIO, synthetic Peach/demo/context guard branches. No partner-menu controller, upgrade animation or natural battle-exit claim.'},indent=2)+'\n')
    print('WORLD_HUD_PASSED=' + str(len(checks)))
    cmd('kill')

try:
    run()
except Exception:
    import traceback
    traceback.print_exc()
    cmd('quit 1')
