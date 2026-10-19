"""Native world full recovery: direct API, real bed script and Heart Block.

Strict disposable save copy; default-off combat; events advance by continue.
WORLD_HEAL_BASELINE=1 observes the preceding healing executable without saving.
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
    root = fixture_path('partner-world-heal')
    runtime = Path(required_env('SHIP_HOME')).resolve()
    assert runtime == root / 'runtime'
    save = fixture_save()
    original = save.read_bytes()
    assert original == Path(required_env('PORTING_SEED_SAVE')).read_bytes()
    baseline = os.environ.get('WORLD_HEAL_BASELINE', '0') == '1'
    checks, captures = [], []
    jump_attempts = 0
    partners = (1,2,3,4,6,7,8,9)
    def check(name, condition):
        if not condition:
            print('WORLD_HEAL_FAILURE=' + json.dumps({field: str(gdb.parse_and_eval(field)) for field in (
                'gPlayerStatus.actionState','gPlayerStatus.flags','gPlayerStatus.pos',
                'gPlayerData.curHP','gPlayerData.curFP','gPlayerData.starPower','wCurrentPartnerId',
                'gCollisionStatus.curCeiling')}))
            capture('failed-' + name)
        assert condition, name
        checks.append(name); record_check(name)
        print('WORLD_HEAL_CHECK=' + name)
    def hp(i):
        return val(f'ttyd64_get_partner_hp({i})')
    def health(i, amount):
        assert val(f'ttyd64_set_partner_hp({i},{amount})') == amount
    def tick(n=1):
        for _ in range(n):
            until('state_step_world')
    def capture(name):
        window = subprocess.check_output(['xdotool','search','--onlyvisible','--pid',str(gdb.selected_inferior().pid)],text=True).splitlines()[0]
        subprocess.run(['xdotool','windowraise',window],check=True)
        subprocess.run(['xdotool','windowfocus',window],check=True)
        time.sleep(0.5)
        subprocess.run(['import','-window','root',str(root/(name+'.png'))],check=True)
        captures.append(name)
    def key(name, frames=2):
        subprocess.run(['xdotool','keydown',name],check=True)
        try:
            tick(frames)
        finally:
            subprocess.run(['xdotool','keyup',name],check=True)
        tick(5)
    def door(script_name):
        # Activate the actual map-bound trigger; native code supplies MapRoom
        # ownership, moves walls/player/camera and completes its event scripts.
        found = [i for i in range(val('sizeof(wTriggerList) / sizeof(wTriggerList[0])'))
                 if val(f'wTriggerList[{i}]') and val(f'wTriggerList[{i}]->onTriggerEvt == {script_name}')]
        assert len(found) == 1
        target = f'wTriggerList[{found[0]}]->flags'
        put(target,val(target) | val('TRIGGER_FORCE_ACTIVATE'))
        tick(2)
        put(target,val(target) & ~val('TRIGGER_FORCE_ACTIVATE'))
        tick(150)
    def report():
        Path(required_env('WORLD_HEAL_RESULT')).write_text(json.dumps({
            'baseline':baseline,'checks_passed':len(checks),'checks':checks,'captures':captures,
            'health':{str(i):hp(i) for i in partners},'prototype_enabled':val('ttyd64_mode_enabled()'),
            'heart_block_keyboard_jump_attempts':jump_attempts,
            'limits':'Controlled map load/rank/unlock/wound grants and direct full-rest API matrix. Native bed trigger started by fixture, dialog chosen with keyboard; fixture-spawned Heart Block.'},indent=2)+'\n')
        print('WORLD_HEAL_PASSED=' + str(len(checks)))
        cmd('kill')
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
    if not baseline:
        put('gCurrentSaveFile.shipSaveData.ttyd64Mode',1)
        cmd('call ttyd64_mode_select_file(1)')
    # Ordinary Mario house pipe entry, skipping only the already-seen Luigi scene.
    put('gCurrentSaveFile.areaID',0)
    put('gCurrentSaveFile.mapID',11)
    put('gCurrentSaveFile.entryID',4)
    put('gCurrentSaveFile.globalBytes[0]',val('STORY_CH1_DEFEATED_KOOPA_BROS'))
    cmd('call set_global_flag(GF_KMR20_ReunitedWithLuigi)')
    put('gPlayerData.curPartner',1)
    put('gPlayerData.partners[1].enabled',1)
    put('gPlayerData.partners[1].level',0)
    health(1,3)
    put('filemenu_menus[0]->state',val('FM_MAIN_SELECT_FILE'))
    put('filemenu_menus[0]->selected',0)
    put('filemenu_currentMenu',val('FILE_MENU_MAIN'))
    cmd('call set_game_mode(GAME_MODE_END_FILE_SELECT)')
    cmd('return')
    until('state_step_world')
    tick(120)
    check('native-mario-house-world',val('gGameStatusPtr->context') == val('CONTEXT_WORLD') and val('gGameStatusPtr->mapID') == 11)
    if not baseline:
        cmd('call switch_to_partner(PARTNER_GOOMBARIO)')
        tick(60)
        check('native-world-goombario-switch-completes',val('wCurrentPartnerId') == 1 and val('gPlayerData.curPartner') == 1)
    for name, amount in (('curHP',2),('curFP',1),('curMaxHP',30),('curMaxFP',20),('maxStarPower',2),('starPower',0)):
        put('gPlayerData.'+name,amount)
    cmd('call FullyRestoreHPandFP((Evt*)0, 1)')
    check('native-full-rest-keeps-mario-hp-fp',val('gPlayerData.curHP') == 30 and val('gPlayerData.curFP') == 20)
    check('full-rest-sp-remains-separate',val('gPlayerData.starPower') == 0)
    if baseline:
        check('baseline-full-rest-leaves-partner-wounded',hp(1) == 3)
        report()
        return
    check('full-rest-restores-partner-in-ttyd64-file',hp(1) == 10 and val('ttyd64_mode_enabled()') == 1)
    for i in range(12):
        put(f'gPlayerData.partners[{i}].enabled',0)
    health(1,3)
    cmd('call FullyRestoreHPandFP((Evt*)0, 1)')
    check('no-unlocked-partner-leaves-model-alone',hp(1) == 3)
    put('gPlayerData.partners[5].enabled',1)
    cmd('call FullyRestoreHPandFP((Evt*)0, 1)')
    check('noncombat-unlock-does-not-enable-team-heal',hp(1) == 3)
    put('gPlayerData.partners[5].enabled',0)
    put('gPlayerData.partners[9].enabled',1)
    # Source heals all compatible records if any combat partner is unlocked.
    for rank in range(3):
        for i in partners:
            put(f'gPlayerData.partners[{i}].level',rank)
            health(i,0 if i % 2 else 1)
        cmd('call FullyRestoreHPandFP((Evt*)0, 1)')
        for i in partners:
            check(f'full-rest-rank-{rank}-partner-{i}',hp(i) == val(f'ttyd64_partner_base_max_hp({i},{rank})'))
    check('full-rest-preserves-locked-recruitment',val('gPlayerData.partners[1].enabled') == 0 and val('gPlayerData.partners[9].enabled') == 1)
    put('gPlayerData.partners[1].enabled',1)
    put('gPlayerData.partners[1].level',0)
    health(1,0)
    health(9,2)
    for name, amount in (('curPartner',1),('curHP',30),('curFP',20),('starPower',512)):
        put('gPlayerData.'+name,amount)
    cmd('call set_action_state(ACTION_STATE_IDLE)')
    door('EVS_EnterRoomDoor')
    check('native-house-door-entry-completes',val('gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED') == 0)
    for axis, pos in (('x',-80),('y',30),('z',-100)):
        put('gPlayerStatus.pos.'+axis,pos)
    tick(10)
    capture('world-rest-before')
    script = val('start_script(kmr_20_EVS_UseBed, EVT_PRIORITY_1, 0)')
    script_id = val(f'((Evt*){script})->id')
    for _ in range(80):
        key('x')
        tick(8)
        if hp(1) == 10:
            break
    check('native-bed-thread-revives-partner-from-zero',hp(1) == 10 and hp(9) == 30)
    capture('world-rest-healed')
    for _ in range(300):
        if not val(f'does_script_exist({script_id})'):
            break
        tick()
    check('native-bed-script-completes',val(f'does_script_exist({script_id})') == 0)
    check('native-bed-restores-partner-identity',val('gPlayerData.curPartner') == 1)
    check('native-bed-unlocks-input',val('gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED') == 0)
    check('world-heal-retains-file-mode-and-world-hp',val('ttyd64_mode_enabled()') == 1 and val('ttyd64_partner_hp_display()') == 10)
    tick(90)  # the native fade child may outlive the main bed script
    capture('world-rest-complete')
    door('EVS_ExitRoomDoor')
    check('native-house-door-exit-completes',val('gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED') == 0)
    for axis, pos in (('x',200),('y',0),('z',100)):
        put('gPlayerStatus.pos.'+axis,pos)
    for name, amount in (('curHP',3),('curFP',2),('starPower',0)):
        put('gPlayerData.'+name,amount)
    health(1,0)
    health(9,1)
    # MAKE_ENTITY_END is a C preprocessor constant, not a GDB enum symbol.
    block = val('create_entity(&Entity_HeartBlock, 200, 60, 100, 0, 0, (uintptr_t)0x80000000)')
    check('native-heart-block-created',block >= 0)
    tick(10)
    capture('world-heart-block-before')
    print('WORLD_HEAL_BEFORE_JUMP=' + json.dumps({field:str(gdb.parse_and_eval(field)) for field in (
        'gPlayerStatus.pos','gPlayerStatus.actionState','gPlayerStatus.flags','gPlayerStatus.curSpeed',
        'gPlayerStatus.animFlags','playerNpc->jumpScale')}))
    for jump_attempts in range(1,4):
        key('x',5)
        tick(45)  # let a missed jump land before another ordinary A press
        if hp(1) == 10:
            break
    print('WORLD_HEAL_AFTER_JUMP=' + json.dumps({field:str(gdb.parse_and_eval(field)) for field in (
        'gPlayerStatus.pos','gPlayerStatus.actionState','gPlayerStatus.flags','gCollisionStatus.curCeiling')}))
    for _ in range(120):
        if hp(1) == 10:
            break
        tick()
    check('native-heart-block-restores-team',hp(1) == 10 and hp(9) == 30)
    check('native-heart-block-preserves-mario-recovery',val('gPlayerData.curHP') == 30 and val('gPlayerData.curFP') == 20)
    check('native-heart-block-restores-star-power',val('gPlayerData.starPower') == 512)
    capture('world-heart-block-healing')
    tick(120)
    check('native-heart-block-completes-and-unlocks-input',val('gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED') == 0)
    capture('world-heart-block-complete')
    try:
        cmd('call fio_save_game(3)')
        health(1,0)
        health(9,0)
        assert val('fio_load_game(3)') == 1
        check('world-recovered-hp-persists-native-fio',hp(1) == 10 and hp(9) == 30)
    finally:
        save.write_bytes(original)
    check('world-recovery-retains-saved-mode',val('ttyd64_mode_enabled()') == 1)
    report()

try:
    run()
except Exception:
    import traceback
    traceback.print_exc()
    cmd('quit 1')
