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
    playtest = os.environ.get('PARTNER_SLICE_PLAYTEST') == '1'
    runtime = Path(required_env('SHIP_HOME')).resolve()
    root = runtime.parent if playtest else fixture_path('partner-playable-slice')
    assert runtime == root / 'runtime'
    if playtest:
        assert root.parent == fixture_path('goombario-playtest/sessions')
        assert re.fullmatch(r'[0-9]{8}T[0-9]{6}-[a-f0-9]{8}', root.name)
        assert (root / '.owned-playtest').read_text() == 'PaperBoat Goombario isolated playtest v1\n'
    save = fixture_save()
    original = save.read_bytes()
    assert original == Path(required_env('PORTING_SEED_SAVE')).read_bytes()
    runtime_env = os.environ.copy()
    assert runtime_env.get('DISPLAY'), 'Set DISPLAY to the owned test server'
    cmd('set environment DISPLAY ' + runtime_env['DISPLAY'])
    print('PARTNER_SLICE_DISPLAY=' + runtime_env['DISPLAY'])
    partner_id = int(os.environ.get('PARTNER_SLICE_PARTNER','1'))
    assert partner_id in (1,2,3)
    cmd(f'set $slicePartner = {partner_id}')
    phases = ['playtest'] if playtest else os.environ.get('PARTNER_SLICE_PHASES', 'pause,world-items,battle').split(',')
    assert phases == ['playtest'] if playtest else phases and set(phases) <= {'pause', 'world-items', 'battle', 'team', 'victory', 'victory-dead', 'ground-ui', 'ground-combat', 'ground-contracts', 'statuses', 'recovery', 'modifiers', 'status-items', 'regeneration', 'recovery-hooks', 'level-up', 'bp', 'dip', 'family', 'native-guard', 'native-status', 'defeat-review', 'orphan-badges', 'hammer-shrink'}
    assert partner_id == 1 or set(phases) <= {'ground-combat','ground-contracts','statuses','recovery','modifiers','status-items','regeneration','recovery-hooks','level-up','team','victory','victory-dead','native-guard','native-status','defeat-review', 'orphan-badges', 'hammer-shrink'}
    checks, states, captures = [], [], []
    team_trace = []
    def hp():
        return val('ttyd64_get_partner_hp($slicePartner)')
    def selected():
        if not val('gPausePartnersNumPartners'):
            return 0
        return val('gPausePartnersPartnerIDs[gPausePartnersPartnerIdx[gPausePartnersCurrentPartnerIdx]]')
    def check(name, condition):
        state = {'check':name,'hp':hp(),'max_hp':val('ttyd64_get_partner_max_hp($slicePartner)'),
                 'context':val('gGameStatusPtr->context'),'world_partner':val('wCurrentPartnerId'),
                 'selected':selected(),'panel':val('gPauseMenuCurrentTab'),
                 'tabs_col':val('gPausePanelTabs.col'),'ability_level':val('gPausePartnersLevel'),
                 'heart_id':val('Ttyd64PausePartnerHeartHID'),'world_owner':val('WorldPartnerID'),
                 'battle_state':val('gBattleState'),'battle_substate':val('gBattleSubState'),
                 'encounter_state':val('gEncounterState'),'combat_partner':val('gPlayerData.curPartner'),'player_in_back':bool(val('gBattleStatus.flags1 & BS_FLAGS1_PLAYER_IN_BACK'))}
        if ({'statuses','recovery'} & set(phases)) and val('gGameStatusPtr->context') == val('CONTEXT_BATTLE') and val('gBattleStatus.partnerActor'):
            state['partner_status'] = {name:val('gBattleStatus.partnerActor->'+name) for name in ('debuff','debuffDuration','staticStatus','staticDuration','transparentStatus','transparentDuration','stoneStatus','stoneDuration','koStatus','koDuration')}
            state['partner_status']['pillar_owned'] = bool(val('gBattleStatus.partnerActor->icePillarEffect'))
            state['partner_status']['turn_used'] = bool(val('gBattleStatus.flags2 & BS_FLAGS2_PARTNER_TURN_USED'))
        if 'regeneration' in phases and val('gGameStatusPtr->context') == val('CONTEXT_BATTLE'):
            state['regeneration'] = {axis:{field:val(f'PartnerModifiers[$slicePartner].{axis}.{field}') for field in ('amount','turns')} for axis in ('hpRegen','fpRegen')}
            state['regeneration']['player_hp'] = val('gPlayerData.curHP')
            state['regeneration']['team_fp'] = val('gPlayerData.curFP')
        states.append(state)
        if not condition:
            (root/'failed-state.json').write_text(json.dumps({'checks_passed':len(checks),'state':state,'team_trace':team_trace},indent=2)+'\n')
        assert condition, name + ': ' + json.dumps(state)
        checks.append(name); record_check(name)
        print('PARTNER_SLICE_CHECK=' + name)
    def tick(n=1):
        for _ in range(n):
            until('step_game_mode')
    def wait(expression, budget=480):
        for _ in range(budget):
            if val(expression):
                return
            tick()
        print('PARTNER_PAUSE_TIMEOUT=' + json.dumps({k:val(k) for k in ('gGameStatusPtr->context','StepPauseState','StepPauseDelay','WorldMenuState','gPauseMenuCurrentTab','gPauseTabsCurrentTab','gPausePanelTabs.col','gPlayerStatus.flags','gPlayerStatus.actionState','gBattleState','gBattleSubState','BattleMenuState','gPopupState','StratsCursorPos','gBattleStatus.inputBitmask','BattleMenu_ChooseDelay','gBattleStatus.curButtonsPressed')}))
        (root/'failed-wait.json').write_text(json.dumps({'waiting_for':expression,
            'player_hp':val('gPlayerData.curHP'),'player_max_hp':val('gPlayerData.curMaxHP'),
            'context':val('gGameStatusPtr->context'),'area':val('gGameStatusPtr->areaID'),
            'map':val('gGameStatusPtr->mapID'),'battle_state':val('gBattleState'),
            'battle_substate':val('gBattleSubState'),'team_trace':team_trace},indent=2)+'\n')
        raise AssertionError('Native frame budget: ' + expression)
    def focus():
        window = subprocess.check_output(['xdotool','search','--onlyvisible','--pid',str(gdb.selected_inferior().pid)],text=True,env=runtime_env).splitlines()[0]
        subprocess.run(['xdotool','windowraise',window],check=True,env=runtime_env)
        subprocess.run(['xdotool','windowfocus',window],check=True,env=runtime_env)
        assert int(subprocess.check_output(['xdotool','getwindowfocus'],text=True,env=runtime_env)) == int(window)
    def key(name, frames=8):
        # A visible popup can still be in its native input debounce interval.
        # Wait for actual readiness; keep all selection/cancel actions keyboard driven.
        if val('gPopupState') == val('POPUP_STATE_CHOOSING') and val('PopupDelayTime') > 0:
            print('PARTNER_INPUT_WAITS_POPUP_READY=' + name)
            wait('gPopupState != POPUP_STATE_CHOOSING || PopupDelayTime == 0')
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
        if partner_id != 1:
            name = str(partner_id) + "-" + name
        if val('gGameStatusPtr->context') == val('CONTEXT_BATTLE') and val('ttyd64_partner_combat_active(gBattleStatus.partnerActor)'):
            for _ in range(180):
                if val('ttyd64_partner_hp_display()') == val('ttyd64_get_partner_hp(gPlayerData.curPartner)'):
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
        captures.append({'capture':name,'captured_while_running':True,'start_state':capture_start,'hp':hp(),'max_hp':val('ttyd64_get_partner_max_hp($slicePartner)'),
                         'selected':selected(),'panel':val('gPauseMenuCurrentTab'),'active':val('pause_partners_hp_active()'),
                         'context':val('gGameStatusPtr->context'),'encounter_state':val('gEncounterState'),'display_hp':val('ttyd64_partner_hp_display()'),'display_partner':val('ttyd64_partner_hp_display_partner()')})
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
        # A world-menu open is edge-triggered. Retry real input only if the
        # prior short/queued tap left ordinary world control unchanged.
        wait('WorldMenuState == 0 && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED) && gPlayerStatus.actionState == ACTION_STATE_IDLE')
        for _ in range(3):
            key('Left')
            if val('WorldMenuState') != 0: break
        menu_ready(1)
    def open_recipient():
        open_items()
        key('x')
        menu_ready(3)
    def consume(row):
        for _ in range(row):
            key('s')
        assert val('PopupMenu_SelectedIndex') == row
        key('x')
        wait('WorldMenuState == 0 && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
        tick(30)
    def enter_road_battle(family=None, formation=None):
        cmd('call ttyd64_mode_select_file(1)')
        put('gPlayerData.partners[$slicePartner].level',0)
        cmd('call ttyd64_reset_partner_hp($slicePartner)')
        assert val('ttyd64_set_partner_hp($slicePartner,3)') == 3
        for field in ('curHP','curMaxHP','hardMaxHP'):
            put('gPlayerData.' + field,99 if formation is not None else 20)
        put('gPlayerData.hasActionCommands',1)
        for i in range(64):
            put(f'gPlayerData.equippedBadges[{i}]',0)
        inventory()
        cmd('call evt_set_variable((Evt*)0, GB_StoryProgress, STORY_CH1_DEFEATED_KOOPA_BROS)')
        cmd('call evt_set_variable((Evt*)0, GF_Tutorial_SwapTurnOrder, 1)')
        cmd('call switch_to_partner($slicePartner)')
        tick(80)
        # Map travel is controlled setup; collision, battle menus and outcome
        # below use ordinary keyboard input, without StartBattle/end-state calls.
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_CANT_TOUCH'))
        if family:
            cmd('call get_map_IDs_by_name_checked("kmr_06", &gGameStatusPtr->areaID, &gGameStatusPtr->mapID)')
            put('gGameStatusPtr->entryID', 1 if family == 'para' else 0)
        else:
            for field, amount in [('areaID',0),('mapID',7),('entryID',0)]:
                put('gGameStatusPtr->' + field,amount)
        cmd('call set_game_mode(GAME_MODE_CHANGE_MAP)')
        until('state_step_world')
        tick(100)
        wait('gGameStatusPtr->context == CONTEXT_WORLD && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
        check('battle-route-native-road-ready',(family is not None or val('gGameStatusPtr->mapID') == 7) and val('WorldPartnerID') == partner_id and hp() == 3)
        if formation is not None:
            # Controlled real formation selection; native world collision still
            # initiates the battle. No actor-type replacement or script forcing.
            for i in range(val('gCurrentEncounter.numEncounters')):
                if val(f'gCurrentEncounter.encounterList[{i}]'):
                    put(f'gCurrentEncounter.encounterList[{i}]->battle', formation)
                    put(f'gCurrentEncounter.encounterList[{i}]->stage', -1)
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_NONE'))
        walk_inputs = 0
        for _ in range(40):
            if val('gEncounterState') != val('ENCOUNTER_STATE_NEUTRAL'):
                break
            # Para is airborne: real moving jumps make contact; walking under
            # it would reach the unrelated ground Spiky encounter instead.
            key('a+x' if family == 'para' else 'd',16)
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
        key('x',6)
        # A short render-pass tap can land between native input polls. Retry
        # only while the same wheel still owns input; never force menu state.
        if val('BattleMenuState') == val('BTL_MENU_STATE_CHOOSING') and val('gBattleSubState') < 4:
            print('PARTNER_WHEEL_CONFIRM_RETRY=' + kind)
            key('x',8)
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
    def flee_battle(retries=1):
        for attempt in range(retries):
            if retries > 1: put('gPlayerData.curHP',99)
            strategies()
            strategy('BTL_MENU_TYPE_RUN_AWAY')
            wait('gBattleState == BATTLE_STATE_RUN_AWAY',480)
            wait('gActionCommandStatus.state == 11',480)
            for _ in range(30):
                if val('gActionCommandStatus.state') != 11:
                    break
                key('x',1)
            wait('(gGameStatusPtr->context == CONTEXT_WORLD && gEncounterState == ENCOUNTER_STATE_NEUTRAL) || '
                 '(gBattleState == BATTLE_STATE_PLAYER_MENU && gBattleSubState < 4 && BattleMenuState == BTL_MENU_STATE_CHOOSING)',1800)
            if val('gGameStatusPtr->context') == val('CONTEXT_WORLD'): return
            team_trace.append({'event':'native-flee-failed','attempt':attempt+1,'player_hp':val('gPlayerData.curHP')})
            print('NATIVE_FLEE_FAILED_RETRY='+str(attempt+1),flush=True)
        raise AssertionError('Native escape did not succeed within input attempts')
    for setting in ('non-stop on','pagination off','confirm off','print thread-events off'):
        cmd('set ' + setting)
    gdb.Breakpoint('state_step_startup',temporary=True,internal=True)
    cmd('run')
    [t for t in gdb.selected_inferior().threads() if t.is_stopped()][0].switch()
    put('gPortResetToTitleScreen',1)
    until('state_step_title_screen')
    check('startup-prototype-off',val('ttyd64_mode_enabled()') == 0)
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
        put(f'gPlayerData.partners[{i}].enabled',int(i in (1,2,partner_id)))
        put(f'gPlayerData.partners[{i}].level',0)
    cmd('call ttyd64_reset_partner_hp($slicePartner)')
    assert val('ttyd64_set_partner_hp($slicePartner,3)') == 3
    cmd('call switch_to_partner($slicePartner)')
    tick(100)
    wait('wCurrentPartnerId == $slicePartner && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
    if 'orphan-badges' in phases:
        baseline = os.environ.get('MENU_SHRINK_BASELINE') == '1'
        def equipped(item):
            return sum(val(f'gPlayerData.equippedBadges[{i}]')==val(item) for i in range(64))
        for mode in (1,0):
            cmd(f'call ttyd64_mode_select_file({mode})')
            for i in range(128): put(f'gPlayerData.badges[{i}]',val('ITEM_LAST_STAND') if i==0 else val('ITEM_POWER_JUMP') if i==1 else 0)
            for i in range(64): put(f'gPlayerData.equippedBadges[{i}]',val('ITEM_LAST_STAND') if i<2 else val('ITEM_JUMPMAN') if i==2 else 0)
            put('gPlayerData.maxBP',30)
            before_cost=val('pause_get_total_equipped_bp_cost()')
            check('orphan-setup-costs-bp-mode-'+str(mode),before_cost>0 and equipped('ITEM_JUMPMAN')==1)
            key('space'); wait('gGameStatusPtr->context==CONTEXT_PAUSE && StepPauseDelay < -10')
            for _ in range(8):
                if val('gPauseTabsCurrentTab')==1: break
                key('d')
            tick(50); key('x'); wait('gPauseMenuCurrentTab==2');tick(20)
            check('orphan-owned-inventory-preserved-mode-'+str(mode),sum(val(f'gPlayerData.badges[{i}]')!=0 for i in range(128))==2)
            key('s'); wait('gPauseBadgesCurrentTab==1')
            rows=[val(f'gPauseBadgesItemIds[{i}]') for i in range(val('gPauseBadgesNumItems'))]
            team_trace.append({'event':'orphan-menu','mode':mode,'baseline':baseline,'rows':rows,'equipped_last_stand':equipped('ITEM_LAST_STAND'),'equipped_jumpman':equipped('ITEM_JUMPMAN'),'bp':val('pause_get_total_equipped_bp_cost()')})
            if mode==0:
                check('vanilla-orphan-equipped-copies-retained',equipped('ITEM_LAST_STAND')==2 and equipped('ITEM_JUMPMAN')==1 and val('pause_get_total_equipped_bp_cost()')==before_cost)
                check('vanilla-active-menu-shows-equipped-array',rows.count(val('ITEM_LAST_STAND'))==2 and rows.count(val('ITEM_JUMPMAN'))==1)
            else:
                check('ttyd64-orphan-active-menu-one-owned-copy',rows==[val('ITEM_LAST_STAND')])
                check('ttyd64-orphan-copy-policy',equipped('ITEM_LAST_STAND')==(2 if baseline else 1) and equipped('ITEM_JUMPMAN')==(1 if baseline else 0))
                key('x');wait('gPauseBadgesLevel==1');key('x');key('c');tick(20)
                check('ttyd64-keyboard-unequip-owned-row',equipped('ITEM_LAST_STAND')==(1 if baseline else 0))
                check('ttyd64-orphan-hidden-cost-reproduced' if baseline else 'ttyd64-orphan-cost-and-effects-cleared',val('pause_get_total_equipped_bp_cost()')>0 if baseline else val('pause_get_total_equipped_bp_cost()')==0 and equipped('ITEM_JUMPMAN')==0)
                check('ttyd64-active-empty-after-row-removed',val('gPauseBadgesItemIds[0]')==0x7FFE)
                capture('orphan-baseline' if baseline else 'orphan-fixed')
            key('space');wait('gGameStatusPtr->context==CONTEXT_WORLD && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)');tick(20)
        team_trace.append({'event':'orphan-method','method':'Malformed owned/equipped arrays and BP are injected into strict disposable runtime, not an actual Save Editor or disk-edit workflow. Keyboard pause/badges/Active/unequip/close, native menu projection/counter/effects observed. Mode comparison injected; common file-select return forced. Capture requires separate inspection.'})
    if 'hammer-shrink' in phases:
        baseline = os.environ.get('MENU_SHRINK_BASELINE') == '1'
        rows=[]
        class ShrinkFinish(gdb.FinishBreakpoint):
            def __init__(self,target,duration):
                super().__init__(internal=True);self.silent=True;self.target=target;self.duration=duration
            def stop(self):
                row={'event':'hammer-shrink-apply','frame':val('gGameStatusPtr->frameCounter'),'mode':val('ttyd64_mode_enabled()'),'target':val(f'((Actor*){self.target})->actorID'),'requested_duration':self.duration,'returned':int(self.return_value),'attack_amount':val('ModifierActors[0].state.attack.amount'),'attack_turns':val('ModifierActors[0].state.attack.turns'),'size':val('ModifierActors[0].state.size'),'vanilla_debuff':val(f'((Actor*){self.target})->debuff'),'vanilla_duration':val(f'((Actor*){self.target})->debuffDuration')}
                rows.append(row);team_trace.append(row);return False
        class ShrinkStart(gdb.Breakpoint):
            def stop(self):
                if val('statusTypeKey')==val('STATUS_KEY_SHRINK'): ShrinkFinish(val('(uintptr_t)target'),val('duration'))
                return False
        trace=ShrinkStart('inflict_status',internal=True);trace.silent=True
        for mode in (1,0):
            enter_road_battle(formation=0x220f)
            check('hammer-real-native-formation-mode-'+str(mode),sum(bool(val(f'gBattleStatus.enemyActors[{i}]')) for i in range(24))==2 and all(val(f'gBattleStatus.enemyActors[{i}]->actorType')==val('ACTOR_TYPE_HAMMER_BROS') for i in range(24) if val(f'gBattleStatus.enemyActors[{i}]')))
            cmd(f'call ttyd64_mode_select_file({mode})')
            start=len(rows)
            for _ in range(24):
                put('gPlayerData.curHP',99);spend_turn()
                if any(x['returned'] and x['target']==val('ACTOR_PLAYER') for x in rows[start:]): break
            hits=[x for x in rows[start:] if x['returned'] and x['target']==val('ACTOR_PLAYER')]
            check('hammer-native-script-inflicts-shrink-mode-'+str(mode),bool(hits))
            expected=3 if baseline or mode==0 else 4
            check('hammer-native-requested-duration-mode-'+str(mode),all(x['requested_duration']==expected for x in hits))
            if mode:
                check('hammer-source-attack-minus-one',all(x['attack_amount']==-1 for x in hits))
                check('hammer-source-duration-and-tiny',all(x['attack_turns']==expected and x['size']==-1 for x in hits))
                capture('hammer-baseline' if baseline else 'hammer-fixed')
            else:
                check('hammer-vanilla-exclusive-shrink-preserved',all(x['vanilla_debuff']==val('STATUS_KEY_SHRINK') and x['vanilla_duration']==3 for x in hits))
            wait('(gBattleState==BATTLE_STATE_PLAYER_MENU || gBattleState==BATTLE_STATE_PARTNER_MENU) && gBattleSubState<4 && BattleMenuState==BTL_MENU_STATE_CHOOSING',1800)
            if val('gBattleState')==val('BATTLE_STATE_PARTNER_MENU'):spend_turn()
            flee_battle(retries=6)
            check('hammer-keyboard-flee-world-mode-'+str(mode),val('gGameStatusPtr->context')==val('CONTEXT_WORLD'))
        trace.delete()
        team_trace.append({'event':'hammer-method','method':'Controlled shared startup/progression/recruitment/rank/stats/inventory and real native220f Hammer Bros formation assigned to disposable Road encounters; keyboard collision/Do Nothing/flee, real native attacks/RNG/status application. Mario99HP/refills and same-battle mode are injected. No actor substitution, forced guard/RNG/status/damage/result. Not natural Bowser Castle route, partner targeting or exhaustive Hammer variants/attacks/lifecycle acceptance.'})
    if 'defeat-review' in phases:
        baseline = os.environ.get('PARTNER_DEFEAT_BASELINE') == '1'
        # Native frames and scripts after explicit fault/post-move setup. These
        # injected zero-HP/null-handler states are not naturally reachable input.
        for label, state_name, substate, missing, revive in (
            ('player-death','BATTLE_STATE_PLAYER_MOVE',4,False,False),
            ('partner-death','BATTLE_STATE_PARTNER_MOVE',3,False,False),
            ('player-null','BATTLE_STATE_PLAYER_MOVE',4,True,False),
            ('partner-null','BATTLE_STATE_PARTNER_MOVE',3,True,False),
            ('partner-life','BATTLE_STATE_PARTNER_MOVE',3,False,True),
            ('partner-null-life','BATTLE_STATE_PARTNER_MOVE',3,True,True),
        ):
            enter_road_battle()
            for field in ('curHP','curMaxHP','hardMaxHP'): put('gPlayerData.'+field,99)
            inventory('ITEM_LIFE_SHROOM' if revive else 'ITEM_MUSHROOM')
            if revive: put('gPlayerData.invItems[1]',0)
            before_items = val('find_item(ITEM_LIFE_SHROOM)')
            source = val('(uintptr_t)gBattleStatus.partnerActor->handleEventSource')
            assert source and not val('gBattleStatus.partnerActor->takeTurnScript')
            assert not val('gBattleStatus.partnerActor->handleEventScript')
            assert val('ttyd64_set_partner_hp($slicePartner,0)') == 0
            put('gStatusBar.disabled',3)
            put('gBattleState',val(state_name)); put('gBattleSubState',substate)
            if missing: put('gBattleStatus.partnerActor->handleEventSource',0)
            trace = []
            class Decrement(gdb.Breakpoint):
                def stop(self):
                    trace.append({'event':'decrement','frame':val('gGameStatusPtr->frameCounter'),
                        'state':val('gBattleState'),'substate':val('gBattleSubState'),
                        'disabled_before':val('gStatusBar.disabled')})
                    return False
            dec = Decrement('decrement_status_bar_disabled',internal=True); dec.silent=True
            samples=[]
            for frame in range(180 if not revive else 600):
                samples.append({'frame':val('gGameStatusPtr->frameCounter'),'state':val('gBattleState'),
                    'substate':val('gBattleSubState'),'disabled':val('gStatusBar.disabled'),
                    'death_script':val('DeathScriptID'),'handled':val('DeathHandledMask'),'hp':hp()})
                tick()
            dec.delete()
            team_trace.append({'event':'defeat-review','case':label,'baseline':baseline,
                'injected_state':state_name,'missing_handler':missing,'life_shroom':revive,
                'decrements':trace,'samples':samples})
            if missing and baseline:
                check(label+'-reproduces-bounded-stall',val('gBattleState')==val(state_name) and val('gBattleSubState')==substate and hp()==0 and val('DeathScriptID')==0)
                check(label+'-reproduces-counter-drain',len(trace)>=120 and val('gStatusBar.disabled')==0)
                # Restore only the injected fault so native death/turn flow can
                # continue; retain all pre-restoration samples above.
                put('gBattleStatus.partnerActor->handleEventSource',source)
                tick(240)
            else:
                check(label+'-bounded-native-continuation',val('gBattleState')!=val(state_name) and bool(val('DeathHandledMask') & (1<<partner_id)) != revive)
                check(label+'-counter-release-count',len(trace)==(2 if baseline else 1))
                check(label+'-independent-status-bar-holds',val('gStatusBar.disabled')==(1 if baseline else 2))
                if revive:
                    check(label+'-native-life-shroom-consumed',before_items>=0 and val('find_item(ITEM_LIFE_SHROOM)')<0 and hp()==10)
                else:
                    check(label+'-native-dead-partner',hp()==0 and val('(int)gBattleStatus.partnerActor->rot.x')==86)
            if missing: put('gBattleStatus.partnerActor->handleEventSource',source)
            wait('(gBattleState==BATTLE_STATE_PLAYER_MENU || gBattleState==BATTLE_STATE_PARTNER_MENU) && gBattleSubState<4 && BattleMenuState==BTL_MENU_STATE_CHOOSING',1800)
            if val('gBattleState')==val('BATTLE_STATE_PARTNER_MENU'): spend_turn()
            # These are the two independent injected holds, removed by setup
            # cleanup, not by the post-move lifecycle under observation.
            put('gStatusBar.disabled',0)
            flee_battle(retries=6)
            check(label+'-keyboard-flee-world',val('gGameStatusPtr->context')==val('CONTEXT_WORLD'))
        if not baseline:
            enter_road_battle()
            saved_state, saved_substate = val('gBattleState'), val('gBattleSubState')
            assert val('ttyd64_set_partner_hp($slicePartner,0)') == 0
            check('mario-alive-predicate-does-not-dispatch-partner-death',val('btl_check_player_defeated()')==0 and val('gBattleState')==saved_state and val('gBattleSubState')==saved_substate and val('DeathScriptID')==0)
            cmd('call ttyd64_mode_select_file(0)')
            check('vanilla-does-not-enter-partner-defeat',val('ttyd64_partner_combat_begin_defeat()')==0 and val('gBattleState')==saved_state)
            put('gStatusBar.disabled',3)
            put('gBattleState',val('BATTLE_STATE_PLAYER_MOVE')); put('gBattleSubState',4)
            tick(180)
            check('vanilla-post-move-releases-one-hold',val('gStatusBar.disabled')==2 and val('DeathScriptID')==0 and val('DeathHandledMask')==0)
            # API transition check only; restore injected death before any frame
            # runs. This does not claim Mario game-over or Life Shroom playback.
            before_state, before_substate = val('gBattleState'), val('gBattleSubState')
            put('gPlayerData.curHP',0)
            check('mario-zero-hp-keeps-native-defeat-transition',val('btl_check_player_defeated()')==1 and val('gBattleState')==val('BATTLE_STATE_DEFEAT') and val('gDefeatedBattleState')==before_state and val('gDefeatedBattleSubstate')==before_substate)
            check('mario-zero-hp-prevents-partner-defeat',val('ttyd64_partner_combat_begin_defeat()')==0)
            put('gPlayerData.curHP',99); put('gBattleState',before_state); put('gBattleSubState',before_substate)
            put('gStatusBar.disabled',0)
            wait('(gBattleState==BATTLE_STATE_PLAYER_MENU || gBattleState==BATTLE_STATE_PARTNER_MENU) && gBattleSubState<4 && BattleMenuState==BTL_MENU_STATE_CHOOSING')
            if val('gBattleState')==val('BATTLE_STATE_PARTNER_MENU'): spend_turn()
            flee_battle(retries=6)
            check('vanilla-keyboard-flee-world',val('gGameStatusPtr->context')==val('CONTEXT_WORLD'))
        team_trace.append({'event':'defeat-review-method','method':'Controlled shared startup/progression/recruitment/rank/HP/inventory/map; real keyboard collision. Injected zero HP, exact post-move state/substate, independent status-bar holds, optional null handler and Life Shroom. Native frame updates/death/revival scripts and passive decrement trace; no forced returns/guard/RNG. Baseline fault restored after bounded180-frame observation. Real keyboard continuation/flee with HP refills. Not natural null-handler reach or campaign acceptance.'})
    if 'native-status' in phases:
        baseline = os.environ.get('PARTNER_STATUS_BASELINE') == '1'
        class StatusFinish(gdb.FinishBreakpoint):
            def __init__(self, attacker):
                super().__init__(internal=True); self.silent=True
                self.target=val(f'((Actor*){attacker})->targetActorID')
                self.row={'event':'native-status-hit','type':val(f'((Actor*){attacker})->actorType'),
                          'target':self.target,'mode':val('ttyd64_mode_enabled()'),
                          'player_in_back':bool(val('gBattleStatus.flags1 & BS_FLAGS1_PLAYER_IN_BACK')),
                          'attack_status':val('gBattleStatus.curAttackStatus'),
                          'partner_before':hp(),'player_before':val('gPlayerData.curHP')}
            def stop(self):
                self.row.update(partner_after=hp(),player_after=val('gPlayerData.curHP'),
                                target_debuff=val(f'get_actor({self.target})->debuff'),
                                target_duration=val(f'get_actor({self.target})->debuffDuration'),
                                partner_debuff=val('gBattleStatus.partnerActor->debuff'),
                                blocked=bool(val('gBattleStatus.flags1 & BS_FLAGS1_ATK_BLOCKED')),
                                damage=val('gBattleStatus.lastAttackDamage'))
                team_trace.append(self.row)
                return False
        class StatusHit(gdb.Breakpoint):
            def stop(self):
                StatusFinish(val('attacker')); return False
        trace=StatusHit('calc_enemy_damage_target',internal=True); trace.silent=True
        class StatusTimerFinish(gdb.FinishBreakpoint):
            def __init__(self):
                super().__init__(internal=True); self.silent=True
                self.row={'event':'native-status-timer','before':val('gBattleStatus.partnerActor->debuff'),
                          'duration_before':val('gBattleStatus.partnerActor->debuffDuration')}
            def stop(self):
                self.row.update(after=val('gBattleStatus.partnerActor->debuff'),
                                duration_after=val('gBattleStatus.partnerActor->debuffDuration'),
                                blocks_turn=bool(val('ttyd64_partner_status_blocks_turn(gBattleStatus.partnerActor)')))
                team_trace.append(self.row); return False
        class StatusTimer(gdb.Breakpoint):
            def stop(self):
                StatusTimerFinish(); return False
        class PoisonFinish(gdb.FinishBreakpoint):
            def __init__(self):
                super().__init__(internal=True); self.silent=True
                self.before=hp()
            def stop(self):
                team_trace.append({'event':'native-poison-tick','before':self.before,'after':hp()})
                return False
        class PoisonTick(gdb.Breakpoint):
            def stop(self):
                PoisonFinish(); return False
        timer=StatusTimer('ttyd64_partner_status_update',internal=True); timer.silent=True
        poison=PoisonTick('ttyd64_partner_status_poison',internal=True); poison.silent=True
        # IDs are native BattleNames entries, not raw ROM offsets.
        for name,formation,actor_type,status in [('poison',0x1501,'ACTOR_TYPE_PUTRID_PIRANHA','STATUS_KEY_POISON'),
                                                   ('frozen',0x1d06,'ACTOR_TYPE_FROST_PIRANHA','STATUS_KEY_FROZEN')]:
            enter_road_battle(formation=formation)
            check(name+'-real-native-formation',sum(bool(val(f'gBattleStatus.enemyActors[{i}]')) for i in range(24)) == 2 and all(val(f'gBattleStatus.enemyActors[{i}]->actorType')==val(actor_type)
                  for i in range(24) if val(f'gBattleStatus.enemyActors[{i}]')))
            key('z')
            wait('gBattleStatus.flags1 & BS_FLAGS1_PLAYER_IN_BACK')
            start=len(team_trace)
            for _ in range(24):
                put('gPlayerData.curHP',99)
                cmd('call ttyd64_set_partner_hp($slicePartner,ttyd64_get_partner_max_hp($slicePartner))')
                spend_turn()
                rows=[r for r in team_trace[start:] if r['event']=='native-status-hit']
                if any(r['target_debuff']==val(status) and r['target_duration']>0 for r in rows): break
            rows=[r for r in team_trace[start:] if r['event']=='native-status-hit']
            print('NATIVE_STATUS_ROWS='+json.dumps(rows),flush=True)
            check(name+'-native-front-target',bool(rows) and all(r['target']==val('ACTOR_PLAYER' if baseline else 'ACTOR_PARTNER') for r in rows))
            check(name+'-native-enemy-applies-status',any(r['target_debuff']==val(status) and r['target_duration']>0 and not r['blocked'] for r in rows))
            if baseline:
                check(name+'-baseline-partner-never-receives-status',all(r['partner_debuff']==0 for r in rows))
            else:
                check(name+'-front-partner-receives-native-status',any(r['partner_debuff']==val(status) for r in rows))
                capture('native-'+name+'-enemy-status')
                # Native duration/poison/turn machinery advances; do not inject
                # status, cure, immunity, RNG, or enemy attack selection.
                for _ in range(6):
                    put('gPlayerData.curHP',99)
                    cmd('call ttyd64_set_partner_hp($slicePartner,ttyd64_get_partner_max_hp($slicePartner))')
                    spend_turn()
                check(name+'-native-rounds-continue',val('gBattleState') in (val('BATTLE_STATE_PLAYER_MENU'),val('BATTLE_STATE_PARTNER_MENU')))
                timers=[r for r in team_trace[start:] if r['event']=='native-status-timer' and r['before']==val(status)]
                check(name+'-native-duration-advances',bool(timers) and all(r['duration_after']==max(0,r['duration_before']-1) for r in timers))
                if name=='poison':
                    check('native-enemy-poison-ticks-partner-hp',any(r['event']=='native-poison-tick' and r['before']>1 and r['after']==r['before']-1 for r in team_trace[start:]))
                else:
                    check('native-enemy-freeze-blocks-turn-and-expires',any(r['blocks_turn'] for r in timers) and any(r['after']==0 and r['duration_after']==0 for r in timers))

                cmd('call ttyd64_mode_select_file(0)')
                start_vanilla=len(team_trace)
                for _ in range(4):
                    put('gPlayerData.curHP',99); spend_turn()
                vanilla=[r for r in team_trace[start_vanilla:] if r['event']=='native-status-hit']
                check(name+'-vanilla-still-targets-mario',bool(vanilla) and all(r['target']==val('ACTOR_PLAYER') for r in vanilla))
                cmd('call ttyd64_mode_select_file(1)')
                cmd('call ttyd64_set_partner_hp($slicePartner,0)')
                start_dead=len(team_trace)
                for _ in range(3):
                    put('gPlayerData.curHP',99); spend_turn()
                dead=[r for r in team_trace[start_dead:] if r['event']=='native-status-hit']
                check(name+'-dead-partner-falls-back',bool(dead) and all(r['target']==val('ACTOR_PLAYER') for r in dead))
            # Run Away belongs to Mario's menu. Let a frozen Mario recover
            # and spend intervening partner turns through native input.
            for _ in range(12):
                if val('gBattleState') == val('BATTLE_STATE_PLAYER_MENU'): break
                put('gPlayerData.curHP',99)
                cmd('call ttyd64_set_partner_hp($slicePartner,ttyd64_get_partner_max_hp($slicePartner))')
                spend_turn()
            flee_battle(retries=6)
            check(name+'-native-flee-world-cleanup',val('WorldPartnerID')==partner_id and
                  val('gGameStatusPtr->context')==val('CONTEXT_WORLD'))
        trace.delete(); timer.delete(); poison.delete()
        team_trace.append({'event':'native-status-method','baseline':baseline,
          'method':'Controlled Road map/recruitment/rank/initial stats (Mario cap99, native partner caps), real formation IDs1501/1d06 assigned to disposable world encounters and HP refills. Real keyboard contact/Z front order/Do Nothing/flee; actual native Putrid/Frost Piranha attack selection/RNG/status application/damage/turns. Same-battle mode/dead boundaries are injected. No forced attack/status/guard/RNG/damage, actor-type substitution or status cure. Common file-select return forced. This is not natural campaign acquisition or a new map-route acceptance.'})
    if 'native-guard' in phases:
        # Observe real Goomba scripts and schedule X through SDL keyboard input.
        # Never write the action-command ring, block result, damage or RNG.
        guard_mode = 'none'
        pending = None
        held = False
        last_frame = -1
        class GuardFrame(gdb.Breakpoint):
            def stop(self):
                nonlocal pending, held, last_frame
                frame = val('gGameStatusPtr->frameCounter')
                if frame == last_frame: return False
                last_frame = frame
                if pending is not None and frame >= pending:
                    focus()
                    subprocess.run(['xdotool','keydown' if not held else 'keyup','x'],check=True,env=runtime_env)
                    team_trace.append({'event':'guard-key','frame':frame,'down':not held,'mode':guard_mode})
                    if held:
                        pending = None
                    else:
                        time.sleep(0.04)
                        pending = frame + 3
                    held = not held
                return False
        class GuardTest(gdb.Breakpoint):
            def stop(self):
                nonlocal pending
                actor = val('script->owner1.actorID')
                if actor >= val('ACTOR_ENEMY0') and val(f'get_actor({actor})->actorType') == val('ACTOR_TYPE_GOOMBA'):
                    frame = val('gGameStatusPtr->frameCounter')
                    team_trace.append({'event':'guard-test','frame':frame,'mode':guard_mode})
                    pending = None if guard_mode == 'none' else frame + (16 if guard_mode == 'timed' else 7)
                return False
        class GuardFinish(gdb.FinishBreakpoint):
            def __init__(self, attacker):
                super().__init__(internal=True)
                self.silent = True
                self.row = {'event':'guard-hit','frame':val('gGameStatusPtr->frameCounter'),'mode':guard_mode,
                            'target':val(f'((Actor*){attacker})->targetActorID'),
                            'player_before':val('gPlayerData.curHP'),'partner_before':hp()}
            def stop(self):
                self.row.update(player_after=val('gPlayerData.curHP'),partner_after=hp(),
                                blocked=bool(val('gBattleStatus.flags1 & BS_FLAGS1_ATK_BLOCKED')),
                                block_result=val('gBattleStatus.blockResult'),damage=val('gBattleStatus.lastAttackDamage'))
                team_trace.append(self.row)
                return False
        class GuardHit(gdb.Breakpoint):
            def stop(self):
                GuardFinish(val('attacker'))
                return False
        enter_road_battle()
        frame_point=GuardFrame('render_game_mode_backUI',internal=True); frame_point.silent=True
        test_point=GuardTest('EnemyTestTarget',internal=True); test_point.silent=True
        hit_point=GuardHit('calc_enemy_damage_target',internal=True); hit_point.silent=True
        for guard_mode in ('none','timed','early'):
            start = len(team_trace)
            for _ in range(32):
                put('gPlayerData.curHP',20)
                cmd('call ttyd64_set_partner_hp($slicePartner,ttyd64_get_partner_max_hp($slicePartner))')
                spend_turn()
                rows=[r for r in team_trace[start:] if r['event']=='guard-hit']
                if {r['target'] for r in rows if r['blocked'] == (guard_mode=='timed')} == {val('ACTOR_PLAYER'),val('ACTOR_PARTNER')}: break
            rows=[r for r in team_trace[start:] if r['event']=='guard-hit']
            print('GUARD_ROWS='+json.dumps(rows),flush=True)
            check('native-'+guard_mode+'-both-team-targets',{r['target'] for r in rows} == {val('ACTOR_PLAYER'),val('ACTOR_PARTNER')})
            check('native-'+guard_mode+'-block-result',
                  {r['target'] for r in rows if r['blocked'] == (guard_mode=='timed')} == {val('ACTOR_PLAYER'),val('ACTOR_PARTNER')})
            if guard_mode != 'timed':
                check('native-'+guard_mode+'-action-command-result',all(r['block_result']==val('BLOCK_RESULT_EARLY' if guard_mode=='early' else 'BLOCK_RESULT_FAIL') for r in rows))
            # Goomba1; Kooper DEF1. Native guard saves one damage, floored at0.
            for target in ('ACTOR_PLAYER','ACTOR_PARTNER'):
                expected = max(0,1-int(target=='ACTOR_PARTNER' and partner_id==2)-int(guard_mode=='timed'))
                sample=[r for r in rows if r['target']==val(target) and r['blocked'] == (guard_mode=='timed')]
                check('native-'+guard_mode+'-'+target+'-damage',all(r['damage']==expected for r in sample))
        frame_point.delete(); test_point.delete(); hit_point.delete()
        if held: subprocess.run(['xdotool','keyup','x'],check=True,env=runtime_env)
        flee_battle()
        check('native-guard-flee-returns-world',val('WorldPartnerID')==partner_id)
        team_trace.append({'event':'native-guard-method','method':'Controlled shared route/recruitment/rank/HP/refills and stock; native Road contact, menu Do Nothing, ordinary AI/target/RNG/damage, timed X via xdotool and native SDL/action-command input ring. Early and no-input controls; no forced block/guard/RNG/damage/input-buffer writes. Common file-select return is forced.'})
    if 'family' in phases:
        baseline = os.environ.get('PARTNER_FAMILY_BASELINE') == '1'
        # Both are real kmr_06 encounters, approached from their nearest entry.
        # No actor-type substitution, StartBattle, forced damage/guard/RNG or AI calls.
        class FamilyFinish(gdb.FinishBreakpoint):
            def __init__(self, attacker):
                super().__init__(internal=True)
                self.silent = True
                self.actor = attacker
                self.row = {'event': 'family-hit', 'type': val(f'((Actor*){attacker})->actorType'),
                            'target': val(f'((Actor*){attacker})->targetActorID'),
                            'player_in_back': bool(val('gBattleStatus.flags1 & BS_FLAGS1_PLAYER_IN_BACK')),
                            'player_before': val('gPlayerData.curHP'), 'partner_before': hp()}
            def stop(self):
                self.row.update(player_after=val('gPlayerData.curHP'), partner_after=hp(),
                                blocked=bool(val('gBattleStatus.flags1 & BS_FLAGS1_ATK_BLOCKED')))
                team_trace.append(self.row)
                return False
        class FamilyHit(gdb.Breakpoint):
            def __init__(self):
                super().__init__('calc_enemy_damage_target', internal=True)
                self.silent = True
            def stop(self):
                FamilyFinish(val('attacker'))
                return False
        class FamilyTargetFinish(gdb.FinishBreakpoint):
            def __init__(self, actor_id):
                super().__init__(internal=True)
                self.silent = True
                self.index = actor_id & 255
            def stop(self):
                team_trace.append({'event':'family-choice',
                    'type':val(f'gBattleStatus.enemyActors[{self.index}]->actorType'),
                    'target':val(f'gBattleStatus.enemyActors[{self.index}]->targetActorID'),
                    'player_in_back':bool(val('gBattleStatus.flags1 & BS_FLAGS1_PLAYER_IN_BACK'))})
                return False
        class FamilyTarget(gdb.Breakpoint):
            def __init__(self):
                super().__init__('Ttyd64GoombaChooseTarget', internal=True)
                self.silent = True
            def stop(self):
                FamilyTargetFinish(val('script->owner1.actorID'))
                return False
        trace = FamilyHit()
        choices = FamilyTarget()
        for family, actor_type in [('spiky', 'ACTOR_TYPE_SPIKED_GOOMBA'), ('para', 'ACTOR_TYPE_PARAGOOMBA')]:
            enter_road_battle(family)
            wanted = val(actor_type)
            observed_types = [val(f'gBattleStatus.enemyActors[{i}]->actorType')
                              for i in range(24) if val(f'gBattleStatus.enemyActors[{i}]')]
            print('FAMILY_FORMATION=' + json.dumps({'family':family,'actor_types':observed_types}), flush=True)
            check('family-' + family + '-native-formation', any(
                val(f'gBattleStatus.enemyActors[{i}]') and val(f'gBattleStatus.enemyActors[{i}]->actorType') == wanted
                for i in range(24)))
            # Keep initial wounds out of this targeting observation. Controlled HP
            # refills between turns prevent defeat from ending the sample early.
            start = len(team_trace)
            for _ in range(6 if baseline else 36):
                # Exercise both native orders rather than waiting for a rare
                # back-target sample with Mario always in front. Swap only at
                # a fresh round; no forced RNG, menu state or input buffers.
                if not baseline and not val('gBattleStatus.flags2 & (BS_FLAGS2_PLAYER_TURN_USED | BS_FLAGS2_PARTNER_TURN_USED)'):
                    was_back = val('gBattleStatus.flags1 & BS_FLAGS1_PLAYER_IN_BACK')
                    key('z')
                    wait(f'(gBattleStatus.flags1 & BS_FLAGS1_PLAYER_IN_BACK) != {was_back} && gBattleSubState < 4 && BattleMenuState == BTL_MENU_STATE_CHOOSING')
                put('gPlayerData.curHP', 20)
                cmd('call ttyd64_set_partner_hp(1,10)')
                spend_turn()
                rows = [x for x in team_trace[start:] if x.get('event') == 'family-hit' and x['type'] == wanted]
                if baseline and len(rows) >= 3:
                    break
                if (not baseline and {x['target'] for x in rows} == {val('ACTOR_PLAYER'),val('ACTOR_PARTNER')}
                    and {x['player_in_back'] for x in rows} == {False,True}
                    and any(x['player_after'] < x['player_before'] for x in rows)
                    and any(x['partner_after'] < x['partner_before'] for x in rows)):
                    break
            rows = [x for x in team_trace[start:] if x.get('event') == 'family-hit' and x['type'] == wanted]
            check('family-' + family + '-native-targets', len(rows) >= (3 if baseline else 2) and
                  (all(x['target'] == val('ACTOR_PLAYER') for x in rows) if baseline else
                   {x['target'] for x in rows} == {val('ACTOR_PLAYER'), val('ACTOR_PARTNER')}))
            check('family-' + family + '-native-damage', any(x['player_after'] < x['player_before'] for x in rows) and
                  (all(x['partner_after'] == x['partner_before'] for x in rows) if baseline else
                   any(x['partner_after'] < x['partner_before'] for x in rows)))
            if not baseline:
                # Controlled same-battle mode boundary, not a user-facing toggle.
                cmd('call ttyd64_mode_select_file(0)')
                start_vanilla = len(team_trace)
                for _ in range(4):
                    put('gPlayerData.curHP',20)
                    spend_turn()
                vanilla = [x for x in team_trace[start_vanilla:] if x.get('event') == 'family-hit' and x['type'] == wanted]
                check('family-' + family + '-vanilla-ai-keeps-mario-target', bool(vanilla) and
                      all(x['target'] == val('ACTOR_PLAYER') for x in vanilla))
                cmd('call ttyd64_mode_select_file(1)')
                cmd('call ttyd64_set_partner_hp(1,0)')
                start_dead = len(team_trace)
                for _ in range(4):
                    put('gPlayerData.curHP',20)
                    spend_turn()
                dead = [x for x in team_trace[start_dead:] if x.get('event') == 'family-hit' and x['type'] == wanted]
                check('family-' + family + '-dead-partner-ai-falls-back', bool(dead) and hp() == 0 and
                      all(x['target'] == val('ACTOR_PLAYER') for x in dead))
            flee_battle()
            check('family-' + family + '-native-flee-world-return', val('WorldPartnerID') == 1 and
                  val('gCurrentEncounter.battleOutcome') == val('OUTCOME_PLAYER_FLED'))
        trace.delete()
        choices.delete()
        team_trace.append({'event': 'family-method', 'baseline_expected_mario_only': baseline,
                           'method': 'Controlled map/entry/progression, recruitment, initial stats/items; HP refills between turns. Real keyboard contact, Z swaps at fresh rounds, Do Nothing and flee; controlled same-battle Vanilla/zero HP boundaries; passive choice/hit tracing; native actual enemy AI, target selection, damage and turns. No forced AI/guard/RNG/damage or actor-type substitution. Common file-select startup return is forced.'})
    if 'dip' in phases:
        enter_road_battle()
        dd = val('ITEM_DOUBLE_DIP')
        for i in range(128): put(f'gPlayerData.badges[{i}]',dd if i < 2 else 0)
        put('gPlayerData.maxBP',6)
        put('gPlayerData.curMaxFP',12)
        put('gPlayerData.hardMaxFP',12)
        assert val(f'pause_badges_try_equip({dd})') == 3
        assert val(f'pause_badges_try_equip({dd})') == 3
        check('dip-native-equip-two-unlocks-ability-count',val('is_ability_active(ABILITY_DOUBLE_DIP)') == 2 and val('pause_get_total_equipped_bp_cost()') == 6)
        def choose_dip(move):
            wheel('BTL_MENU_TYPE_ITEMS')
            wait('gBattleSubState == 2 && MovesMenuState == BTL_SUBMENU_STATE_CHOOSING')
            moves = [val(f'gBattleStatus.submenuMoves[{i}]') for i in range(val('MovesOptionCount'))]
            check('dip-keyboard-submenu-' + move,moves == [val('MOVE_ITEMS'),val('MOVE_DOUBLE_DIP'),val('MOVE_TRIPLE_DIP')])
            index = moves.index(val(move))
            for _ in range(8):
                current = val('MovesCursorPos')
                if current == index: break
                key('w' if index < current else 's')
            assert val('MovesCursorPos') == index
            key('x')
            wait('gBattleSubState == 21 && gPopupState == POPUP_STATE_CHOOSING && PopupDelayTime == 0')
        for label, move, uses, stock, cancel in [('double','MOVE_DOUBLE_DIP',2,2,False),('triple','MOVE_TRIPLE_DIP',3,3,True),('triple-short-stock','MOVE_TRIPLE_DIP',3,1,False),('status-triple','MOVE_TRIPLE_DIP',3,3,False)]:
            status_dip = label == 'status-triple'
            if status_dip:
                for i in (2,3): put(f'gPlayerData.badges[{i}]',val('ITEM_FLOWER_SAVER_A'))
                put('gPlayerData.maxBP',14)
                assert val('pause_badges_try_equip(ITEM_FLOWER_SAVER_A)') == 3
                assert val('pause_badges_try_equip(ITEM_FLOWER_SAVER_A)') == 3
                check('dip-status-native-two-flower-saver-copies',val('is_ability_active(ABILITY_FLOWER_SAVER)') == 2 and val('pause_get_total_equipped_bp_cost()') == 14)
            put('gPlayerData.curHP',1)
            assert val('ttyd64_set_partner_hp($slicePartner,3)') == 3
            put('gPlayerData.curFP',12)
            item = 'ITEM_COURAGE_SHELL' if status_dip else 'ITEM_MUSHROOM'
            for i in range(10): put(f'gPlayerData.invItems[{i}]',val(item) if i < stock else 0)
            choose_dip(move)
            if cancel:
                key('c')
                wait('gBattleSubState == 2 && MovesMenuState == BTL_SUBMENU_STATE_CHOOSING')
                check('dip-cancel-initial-popup-preserves-fp-items',val('gPlayerData.curFP') == 12 and item_count() == stock)
                key('x')
                wait('gBattleSubState == 21 && gPopupState == POPUP_STATE_CHOOSING && PopupDelayTime == 0')
            cost = 6 if status_dip else (4 if uses == 2 else 8)
            for use in range(min(uses,stock)):
                key('x')
                wait('gBattleState == BATTLE_STATE_SELECT_TARGET && gBattleSubState == 1')
                if cancel and use == 1:
                    key('c')
                    wait('gBattleState == BATTLE_STATE_PLAYER_MENU && gBattleSubState == 71 && gPopupState == POPUP_STATE_CHOOSING && PopupDelayTime == 0')
                    check('dip-cancel-later-target-keeps-paid-fp-items',val('gPlayerData.curFP') == 12-cost and item_count() == stock-use)
                    key('x')
                    wait('gBattleState == BATTLE_STATE_SELECT_TARGET && gBattleSubState == 1')
                recipient = 'ACTOR_PARTNER' if use == 1 else 'ACTOR_PLAYER'
                player = 'gBattleStatus.playerActor'
                target = player+'->targetData['+player+'->targetIndexList['+player+'->selectedTargetIndex]].actorID'
                for _ in range(4):
                    if val(target) == val(recipient): break
                    key('d')
                assert val(target) == val(recipient)
                key('x')
                last = use+1 == min(uses,stock)
                if last:
                    wait('gBattleState == BATTLE_STATE_PARTNER_MENU && gBattleSubState < 4 && BattleMenuState == BTL_MENU_STATE_CHOOSING',1800)
                else:
                    wait('gBattleState == BATTLE_STATE_PLAYER_MENU && gBattleSubState == 71 && gPopupState == POPUP_STATE_CHOOSING && PopupDelayTime == 0',1800)
                check(f'dip-{label}-native-item-{use+1}-pays-once',item_count() == stock-use-1 and val('gPlayerData.curFP') == 12-cost)
            if status_dip:
                # Active TTYD64 Battle_NewStatuses.patch AddDefenseBoost overwrites
                # same-sign boosts: two Courage Shells on Mario still give +3.
                effects = {'mario_hp':val('gPlayerData.curHP'),'partner_hp':hp(),
                           'mario_defense':val('ttyd64_actor_defense_boost(gBattleStatus.playerActor)'),
                           'partner_defense':val('ttyd64_actor_defense_boost(gBattleStatus.partnerActor)')}
                print('DIP_STATUS_EFFECTS=' + json.dumps(effects,sort_keys=True))
                check('dip-status-triple-native-effects-on-both-recipients',effects ==
                      {'mario_hp':1,'partner_hp':3,'mario_defense':3,'partner_defense':3})
            else:
                check('dip-'+label+'-heals-native-recipients',val('gPlayerData.curHP') == (11 if uses == 3 and stock == 3 else 6) and hp() == (8 if stock >= 2 else 3))
            check('dip-'+label+'-one-mario-turn-partner-still-ready',bool(val('gBattleStatus.flags2 & BS_FLAGS2_PLAYER_TURN_USED')) and not val('gBattleStatus.flags2 & BS_FLAGS2_PARTNER_TURN_USED'))
            put('gPlayerData.curHP',20)
            assert val('ttyd64_set_partner_hp($slicePartner,10)') == 10
            # Restock before the next native turn initializes its item wheel.
            # Changing an empty inventory after that point leaves its cached
            # command disabled; this is setup, not a menu-state override.
            inventory()
            spend_turn()
            wait('gBattleState == BATTLE_STATE_PLAYER_MENU && gBattleSubState < 4 && BattleMenuState == BTL_MENU_STATE_CHOOSING',1800)
        cmd('call ttyd64_mode_select_file(0)')
    if 'bp' in phases:
        cmd('call ttyd64_mode_select_file(1)')
        for field,size in (('badges',128),('equippedBadges',64)):
            for i in range(size):
                put(f'gPlayerData.{field}[{i}]',val('ITEM_DOUBLE_DIP') if i < 2 else (val('ITEM_LAST_STAND') if field == 'badges' and i == 2 else 0))
        put('gPlayerData.maxBP',3)
        key('space')
        wait('gGameStatusPtr->context == CONTEXT_PAUSE && StepPauseDelay < -10')
        for _ in range(8):
            if val('gPauseTabsCurrentTab') == 1: break
            key('d')
        tick(50)
        key('x')
        wait('gPauseMenuCurrentTab == 2')
        tick(20)
        numbers, orbs = [], []
        budget_line = next(i for i,line in enumerate(source_path("src/pause/pause_badges.c").read_text().splitlines(),1) if "maxBP = playerData->maxBP;" in line)
        class DrawTrace(gdb.Breakpoint):
            def __init__(self, name):
                super().__init__(name,internal=True)
                self.silent = True
                self.function = name
            def stop(self):
                frame = gdb.newest_frame()
                caller = frame.older()
                if caller.name() == 'pause_badges_draw_contents':
                    if self.function == 'draw_number':
                        numbers.append(int(frame.read_var('value')))
                    elif caller.find_sal().line >= budget_line:
                        orbs.append(int(caller.read_var('orbIndex')))
                return False
        points = [DrawTrace('draw_number'),DrawTrace('pause_badges_draw_bp_orbs')]
        try: tick(6)
        finally:
            for point in points: point.delete()
        print('BP_RENDER_TRACE=' + json.dumps({'numbers':numbers,'summary_orb_indices':orbs}))
        before = os.environ.get('PARTNER_BP_BASELINE') == '1'
        check('bp-native-render-available-number',(-3 in numbers) if before else (numbers and min(numbers) >= 0 and 0 in numbers))
        check('bp-native-render-orbs-nonnegative',bool(orbs) and min(orbs) >= 0 and max(orbs) < 3)
        team_trace.append({'event':'bp-render','draw_number_values':numbers,'orb_indices':orbs,
                           'setup':'Injected two equipped Double Dips, maxBP3; real keyboard pause/badges input, native renderer observed, no forced draw returns.'})
        key('space')
        wait('gGameStatusPtr->context == CONTEXT_WORLD && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
    if playtest:
        # Seed only this newly-created isolated session, after native load.
        # A new session is allocated by the launcher; real saves are not used.
        for i in range(1,12):
            put(f'gPlayerData.partners[{i}].enabled',int(i in (1,2,3) if os.environ.get('PARTNER_SLICE_GROUND') == '1' else i == 1))
        if os.environ.get('PARTNER_SLICE_GROUND') == '1':
            for pid in (2,3):
                put(f'gPlayerData.partners[{pid}].level',0)
                cmd(f'call ttyd64_reset_partner_hp({pid})')
                assert val(f'ttyd64_set_partner_hp({pid},3)') == 3
            check('isolated-ground-playtest-recruits-and-seeds-supported-group',val('gPlayerData.partners[2].enabled') == 1 and val('gPlayerData.partners[3].enabled') == 1 and val('ttyd64_get_partner_max_hp(2)') == 10 and val('ttyd64_get_partner_max_hp(3)') == 15)
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
        cmd('call ttyd64_mode_select_file(1)')
        cmd('call ttyd64_partner_hp_world_bind(wCurrentPartnerId)')
        check('isolated-playtest-world-ready',hp() == 3 and val('ttyd64_partner_hp_display()') == 3 and val('wCurrentPartnerId') == partner_id and val('gPlayerStatus.inputDisabledCount') == 0)
        # Prove native input is live before handing control to the tester.
        open_items()
        check('isolated-playtest-keyboard-items-open',val('WorldPopupMenu.numEntries') == 6)
        key('c')
        wait('WorldMenuState == 0 && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
        cmd('call open_status_bar_quickly()')
        tick(30)
        capture('playtest-ready')
        report = {'partner_id':partner_id,'phases_run':phases,'checks_passed':len(checks),'checks':checks,
                  'native_states':states,'captures':captures,
                  'session':str(root),'pid':gdb.selected_inferior().pid,'ground_partners':os.environ.get('PARTNER_SLICE_GROUND') == '1',
                  'limits':'Linux developer launcher, generated new-game test seed and user-supplied archives required. Fresh isolated session; prototype on only in this process. Goombario-only default or explicitly requested ground HP group, shroom family and existing native maps; native moves/defense remain, incomplete TTYD64 port.'}
        Path(required_env('PARTNER_SLICE_RESULT')).write_text(json.dumps(report,indent=2)+'\n')
        assert save.read_bytes() == original
        if os.environ.get('PARTNER_SLICE_VERIFY_ONLY') == '1':
            cmd('kill')
            print('GOOMBARIO_PLAYTEST_VERIFIED=1')
        else:
            cmd('detach')
            print('GOOMBARIO_PLAYTEST_READY=' + str(report['pid']))
        return
    if 'ground-ui' in phases:
        assert partner_id == 1
        cmd('call ttyd64_mode_select_file(1)')
        for i in range(1,12):
            put(f'gPlayerData.partners[{i}].enabled',int(i in (1,2,3,4)))
        expected_hp = {1:3,2:4,3:6}
        for pid, amount in expected_hp.items():
            put(f'gPlayerData.partners[{pid}].level',0)
            assert val(f'ttyd64_set_partner_hp({pid},{amount})') == amount
        for pid in (2,3,1):
            key('Right')
            menu_ready(0)
            index = next(i for i in range(val('WorldPopupMenu.numEntries')) if val(f'WorldPopupMenu.userIndex[{i}]') == pid)
            for _ in range(8):
                current = val('PopupMenu_SelectedIndex')
                if current == index:
                    break
                key('w' if index < current else 's')
            assert val('WorldPopupMenu.userIndex[PopupMenu_SelectedIndex]') == pid
            key('x')
            wait(f'WorldMenuState == 0 && wCurrentPartnerId == {pid} && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
            tick(30)
            check(f'ground-world-keyboard-swap-owner-{pid}',val('WorldPartnerID') == pid and val('ttyd64_partner_hp_display_partner()') == pid and val('ttyd64_partner_hp_display()') == expected_hp[pid])
            capture(f'ground-world-{pid}')
        open_party()
        for pid in (1,2,3,4):
            for _ in range(8):
                if selected() == pid:
                    break
                key('d')
                tick(30)
            check(f'ground-pause-selected-identity-{pid}',selected() == pid and bool(val('pause_partners_hp_active()')) == (pid in expected_hp))
            capture(f'ground-pause-{pid}')
        close_pause()
        # Menu identities cover all supported, recruited ground partners and
        # retain Mario first. Unsupported Parakarry has no recipient HP route.
        for pid in (1,2,3):
            inventory()
            assert val(f'ttyd64_set_partner_hp({pid},0)') == 0
            open_recipient()
            ids = [val(f'WorldPopupMenu.userIndex[{i}]') for i in range(val('WorldPopupMenu.numEntries'))]
            check(f'ground-world-recipient-identities-{pid}',ids == [0,1,2,3])
            capture(f'ground-recipient-{pid}')
            consume(ids.index(pid))
            check(f'ground-world-keyboard-zero-heal-{pid}',val(f'ttyd64_get_partner_hp({pid})') == 5 and item_count() == 1 and val('wCurrentPartnerId') == 1)
        cmd('call ttyd64_mode_select_file(0)')
        inventory()
        put('gPlayerData.curHP',2)
        open_items()
        key('x')
        wait('WorldMenuState == 0 && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
        tick(30)
        check('ground-off-world-food-keeps-native-mario',val('gPlayerData.curHP') == 7 and item_count() == 1 and val('ttyd64_partner_hp_display()') == -1)
    if 'pause' in phases:
        open_party()
        check('off-keyboard-pause-party-keeps-native-no-heart',val('Ttyd64PausePartnerHeartHID') == -1 and val('pause_partners_hp_active()') == 0 and selected() == 1)
        capture('pause-party-off')
        close_pause()
        check('off-native-world-return-preserves-health',hp() == 3 and val('gPlayerData.curPartner') == 1)
        cmd('call ttyd64_mode_select_file(1)')
        # Native creation is deliberately used before opening the guarded cycle.
        cmd('call switch_to_partner(2)')
        tick(100)
        cmd('call switch_to_partner($slicePartner)')
        tick(100)
        check('guarded-world-owner-before-pause',val('WorldPartnerID') == partner_id and val('ttyd64_partner_hp_display()') == 3)
        open_party()
        check('guarded-pause-owns-manual-heart',val('Ttyd64PausePartnerHeartHID') >= 0 and val('get_hud_element(Ttyd64PausePartnerHeartHID)->flags & HUD_ELEMENT_FLAG_MANUAL_RENDER') != 0)
        check('guarded-selected-goombario-shows-wounded-health',val('pause_partners_hp_active()') != 0 and hp() == 3 and selected() == 1)
        capture('pause-party-wounded')
        key('d')
        wait('gPausePartnersCurrentPartnerIdx == 1')
        tick(30)
        check('carousel-other-ground-selection-has-own-hp',selected() == 2 and val('pause_partners_hp_active()') != 0 and val('gPlayerData.curPartner') == 1 and hp() == 3)
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
        assert val('ttyd64_set_partner_hp($slicePartner,0)') == 0
        check('pause-zero-hp-visible-without-changing-world-partner',val('pause_partners_hp_active()') != 0 and hp() == 0 and val('gPlayerData.curPartner') == 1)
        capture('pause-party-zero')
        put('gPlayerData.partners[$slicePartner].level',2)
        cmd('call ttyd64_reset_partner_hp($slicePartner)')
        assert val('ttyd64_set_partner_hp($slicePartner,27)') == 27
        check('pause-ultra-rank-has-independent-current-and-max',hp() == 27 and val('ttyd64_get_partner_max_hp($slicePartner)') == 30 and val('gPlayerData.partners[$slicePartner].level') == 2)
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
        check('guarded-unpause-restores-world-hp-owner',val('WorldPartnerID') == partner_id and val('ttyd64_partner_hp_display()') == 27 and hp() == 27)
        capture('pause-party-world-return')
        cmd('call ttyd64_mode_select_file(0)')
        open_party()
        check('off-reopen-allocates-no-experimental-heart',val('Ttyd64PausePartnerHeartHID') == -1 and val('pause_partners_hp_active()') == 0 and hp() == 27)
        capture('pause-party-final-off')
        close_pause()
        check('off-final-world-control-and-passive-hp',val('ttyd64_mode_enabled()') == 0 and hp() == 27 and val('gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED') == 0)
    if 'world-items' in phases:
        cmd('call ttyd64_mode_select_file(1)')
        put('gPlayerData.partners[$slicePartner].level',0)
        cmd('call ttyd64_reset_partner_hp($slicePartner)')
        put('gPlayerData.curHP',2)
        inventory()
        assert val('ttyd64_set_partner_hp($slicePartner,3)') == 3
        open_recipient()
        check('world-recipient-native-menu-identities',val('WorldPopupMenu.numEntries') == 3 and val('WorldPopupMenu.userIndex[0]') == 0 and val('WorldPopupMenu.userIndex[1]') == 1 and item_count() == 2)
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
            assert val(f'ttyd64_set_partner_hp($slicePartner,{initial})') == initial
            open_recipient()
            consume(1)
            check('world-' + item.lower() + '-potency-zero-or-cap',hp() == expected and val('gPlayerData.curHP') == 2 and item_count() == 1)
        inventory()
        assert val('ttyd64_set_partner_hp($slicePartner,3)') == 3
        open_recipient()
        consume(0)
        check('world-mario-recipient-retains-native-heal',hp() == 3 and val('gPlayerData.curHP') == 7 and item_count() == 1)
        cmd('call switch_to_partner(2)')
        tick(100)
        inventory()
        open_recipient()
        consume(1)
        check('world-inactive-goombario-heals-without-changing-partner',hp() == 8 and val('wCurrentPartnerId') == 2 and val('gPlayerData.curHP') == 7 and item_count() == 1)
        cmd('call ttyd64_mode_select_file(0)')
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
        # Observe the real rejection message before waiting for the list again.
        # An immediate CHOOSING check can return before the press is processed;
        # Cancel would then only dismiss the message rather than close the list.
        wait('gPopupState == POPUP_STATE_ALREADY_HAVE_PARTNER_AWAIT')
        wait('gBattleSubState == 31 && gPopupState == POPUP_STATE_CHOOSING && PopupDelayTime == 0')
        check('battle-current-row-rejection-preserves-hp-and-turns',hp() == 3 and val('gPlayerData.curPartner') == 1 and val('gBattleStatus.flags2 & BS_FLAGS2_PLAYER_TURN_USED') == 0)
        cancel_battle_partners()
        cmd('call ttyd64_mode_select_file(0)')
        battle_partners()
        check('battle-off-list-keeps-native-width',val('gWindows[WIN_POPUP_CONTENT].width') == 139 and val('popup_partner_hp_active()') == 0 and hp() == 3)
        capture('battle-swap-off')
        cancel_battle_partners()
        cmd('call ttyd64_mode_select_file(1)')
        battle_partners()
        key('s')
        assert val('gPopupMenu->userIndex[PopupMenu_SelectedIndex]') == 2
        key('x')
        wait('gBattleState == BATTLE_STATE_PARTNER_MENU && gPlayerData.curPartner == 2 && BattleMenuState == BTL_MENU_STATE_CHOOSING',900)
        check('mario-keyboard-swap-spends-mario-turn-preserves-goombario',hp() == 3 and val('gBattleStatus.flags2 & BS_FLAGS2_PLAYER_TURN_USED') != 0 and val('gBattleStatus.flags2 & BS_FLAGS2_PARTNER_TURN_USED') == 0 and val('ttyd64_partner_combat_active(gBattleStatus.partnerActor)') == 1)
        assert val('ttyd64_set_partner_hp($slicePartner,0)') == 0
        battle_partners()
        check('partner-menu-shows-selectable-zero-goombario',val('gPopupMenu->enabled[0]') != 0 and val('gPopupMenu->enabled[1]') == 0 and hp() == 0)
        capture('battle-swap-zero')
        key('w')
        assert val('gPopupMenu->userIndex[PopupMenu_SelectedIndex]') == 1
        key('x')
        wait('gBattleState == BATTLE_STATE_PLAYER_MENU && gPlayerData.curPartner == 1 && BattleMenuState == BTL_MENU_STATE_CHOOSING',1200)
        check('partner-keyboard-zero-swap-back-completes-next-turn',hp() == 0 and val('gBattleStatus.partnerActor->curHP') == 0 and val('btl_partner_can_act()') == 0)
        flee_battle()
        check('keyboard-flee-returns-world-with-zero-hp-owner',val('gCurrentEncounter.battleOutcome') == val('OUTCOME_PLAYER_FLED') and hp() == 0 and val('WorldPartnerID') == partner_id and val('ttyd64_partner_hp_display()') == 0 and val('gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED') == 0)
        # The completed flee above is unforced. Prevent a new road encounter
        # during the subsequent world/pause/save observation and free capture.
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_CANT_TOUCH'))
        inventory()
        open_recipient()
        consume(1)
        check('post-battle-keyboard-world-shroom-restores-zero-partner',hp() == 5 and item_count() == 1 and val('WorldPartnerID') == partner_id)
        open_party()
        check('post-battle-pause-shows-healed-partner',selected() == 1 and hp() == 5 and val('pause_partners_hp_active()') != 0)
        close_pause()
        try:
            cmd('call fio_save_game(3)')
            assert val('ttyd64_set_partner_hp($slicePartner,0)') == 0
            assert val('fio_load_game(3)') == 1
            check('playable-route-health-and-item-persist-native-fio',hp() == 5 and item_count() == 1)
        finally:
            save.write_bytes(original)
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_CANT_TOUCH'))
        cmd('call open_status_bar_quickly()')
        tick(30)
        capture('battle-route-world-return')
        check('route-final-capture-remains-in-world',val('gGameStatusPtr->context') == val('CONTEXT_WORLD') and val('gEncounterState') == val('ENCOUNTER_STATE_NEUTRAL'))
        cmd('call ttyd64_mode_select_file(0)')
    if 'regeneration' in phases:
        enter_road_battle()
        player, partner = 'gBattleStatus.playerActor', 'gBattleStatus.partnerActor'
        items = ['ITEM_SLOW_SHROOM','ITEM_GRADUAL_SYRUP','ITEM_COUPLES_CAKE','ITEM_METEOR_MEAL']
        cmd('call ttyd64_mode_select_file(0)')
        check('regen-default-off-rejects-effects',all(val('ttyd64_status_item_apply('+i+','+partner+',1)') == 0 for i in items) and val('ttyd64_actor_set_regeneration('+player+',0,2,10)') == 0)
        cmd('call ttyd64_mode_select_file(1)')
        assert val('ttyd64_set_partner_hp($slicePartner,0)') == 0
        check('regen-dead-recipient-cannot-revive',val('ttyd64_actor_set_regeneration('+partner+',0,2,10)') == 0 and val('ttyd64_actor_regeneration_heal('+partner+',7)') == 0 and hp() == 0)
        assert val('ttyd64_set_partner_hp($slicePartner,3)') == 3
        # Synthetic event arguments exercise ACTOR_SELF in the public adapters.
        cmd('set $regenEvt = (Evt*)heap_malloc(sizeof(Evt))')
        cmd('call (void*)memset($regenEvt,0,sizeof(Evt))')
        cmd('set $regenArgs = (Bytecode*)heap_malloc(3*sizeof(Bytecode))')
        put('$regenEvt->ptrReadPos','$regenArgs');put('$regenEvt->owner1.actorID',val('ACTOR_PARTNER'))
        for i,n in enumerate([val('ACTOR_SELF'),2,10]):put(f'$regenArgs[{i}]',n)
        assert val('Ttyd64SetHPRegeneration($regenEvt,1)') == 2  # ApiStatus_DONE2 is a macro, not a GDB symbol
        assert val('Ttyd64SetFPRegeneration($regenEvt,1)') == 2  # ApiStatus_DONE2 is a macro, not a GDB symbol
        check('regen-public-event-self-adapters-set-independent-axes',val('PartnerModifiers[$slicePartner].hpRegen.turns') == 10 and val('PartnerModifiers[$slicePartner].fpRegen.turns') == 10)
        cmd('call heap_free($regenArgs)');cmd('call heap_free($regenEvt)')
        cmd('call ttyd64_actor_modifiers_clear('+partner+')')
        # Controlled transparency excludes Goomba damage from the recovery delta;
        # native keyboard turns still drive the beginning-of-turn hook.
        val('inflict_status('+player+',STATUS_KEY_TRANSPARENT,20)')
        val('inflict_status('+partner+',STATUS_KEY_TRANSPARENT,20)')
        def select_regen(item, recipient):
            inventory(item)
            wheel('BTL_MENU_TYPE_ITEMS')
            wait('gBattleSubState == 41 && gPopupState == POPUP_STATE_CHOOSING && PopupDelayTime == 0')
            key('x')
            wait('gBattleState == BATTLE_STATE_SELECT_TARGET && gBattleSubState == 1')
            for _ in range(4):
                if val(player+'->targetData['+player+'->targetIndexList['+player+'->selectedTargetIndex]].actorID') == val(recipient): break
                key('d')
            assert val(player+'->targetData['+player+'->targetIndexList['+player+'->selectedTargetIndex]].actorID') == val(recipient)
        def use_regen():
            key('x')
            wait('gBattleState == BATTLE_STATE_PARTNER_MENU && BattleMenuState == BTL_MENU_STATE_CHOOSING && gBattleSubState < 4',1800)
            assert item_count() == 1 and val('gBattleStatus.flags2 & BS_FLAGS2_PLAYER_TURN_USED') and not val('gBattleStatus.flags2 & BS_FLAGS2_PARTNER_TURN_USED')
        select_regen('ITEM_SLOW_SHROOM','ACTOR_PARTNER')
        key('c')
        wait('gBattleState == BATTLE_STATE_PLAYER_MENU && gBattleSubState == 41 && gPopupState == POPUP_STATE_CHOOSING && PopupDelayTime == 0')
        check('regen-native-cancel-retains-inventory-and-no-effect',item_count() == 2 and val('PartnerModifiers[$slicePartner].hpRegen.turns') == 0)
        key('x');wait('gBattleState == BATTLE_STATE_SELECT_TARGET && gBattleSubState == 1')
        if val(player+'->targetData['+player+'->targetIndexList['+player+'->selectedTargetIndex]].actorID') != val('ACTOR_PARTNER'):key('d')
        use_regen()
        check('regen-slow-native-use-consumes-once-without-immediate-heal',hp() == 3 and val('PartnerModifiers[$slicePartner].hpRegen.amount') == 2 and val('PartnerModifiers[$slicePartner].hpRegen.turns') == 10)
        spend_turn()
        check('regen-native-begin-turn-heals-then-decrements',hp() == 5 and val('PartnerModifiers[$slicePartner].hpRegen.turns') == 9)
        put('gPlayerData.curFP',0)
        select_regen('ITEM_GRADUAL_SYRUP','ACTOR_PARTNER');use_regen()
        check('regen-syrup-native-partner-axis-has-no-immediate-fp',val('gPlayerData.curFP') == 0 and val('PartnerModifiers[$slicePartner].fpRegen.turns') == 10)
        # API controls Mario's concurrent axis and a one-turn enemy buff. Enemy
        # FP must not touch shared player FP; final-turn healing precedes expiry.
        val('ttyd64_actor_set_regeneration('+player+',1,1,1)')
        enemy='gBattleStatus.enemyActors[0]'
        put(enemy+'->curHP',1)
        val('ttyd64_actor_set_regeneration('+enemy+',0,1,1)')
        val('ttyd64_actor_set_regeneration('+enemy+',1,7,1)')
        check('regen-enemy-direct-axis-has-no-extra-turn',val('ModifierActors[1].state.hpRegen.turns') == 1)
        spend_turn()
        check('regen-native-team-fp-adds-and-enemy-does-not-own-fp',val('gPlayerData.curFP') == 3 and val(enemy+'->curHP') == 2 and val('ModifierActors[1].state.hpRegen.amount') == 0 and val('ModifierActors[0].state.fpRegen.turns') == 0)
        select_regen('ITEM_COUPLES_CAKE','ACTOR_PLAYER');use_regen()
        check('regen-couples-native-self-use-consumes-without-effect',val('ModifierActors[0].state.hpRegen.turns') == 0)
        spend_turn()
        select_regen('ITEM_COUPLES_CAKE','ACTOR_PARTNER');use_regen()
        check('regen-couples-native-other-recipient-replaces-hp-axis',val('PartnerModifiers[$slicePartner].hpRegen.amount') == 2 and val('PartnerModifiers[$slicePartner].hpRegen.turns') == 10)
        spend_turn()
        put('gPlayerData.curHP',3)
        put('gPlayerData.equippedBadges[0]',val('ITEM_POWER_RUSH'))
        put('gBattleStatus.rushFlags',val('RUSH_FLAG_POWER'))
        select_regen('ITEM_METEOR_MEAL','ACTOR_PLAYER');use_regen()
        check('regen-meteor-native-seven-now-two-for-three-turns',val('gPlayerData.curHP') == 10 and val('ModifierActors[0].state.hpRegen.amount') == 2 and val('ModifierActors[0].state.hpRegen.turns') == 3 and val('gBattleStatus.rushFlags') == 0)
        for remaining in (2,1,0):
            # One player + partner action per full native round.
            spend_turn()
            check('regen-meteor-native-expiry-turn-'+str(remaining),val('ModifierActors[0].state.hpRegen.turns') == remaining and val('gPlayerData.curHP') == 16-2*remaining)
            if remaining:spend_turn()
        check('regen-native-hp-fp-caps',hp() == val('ttyd64_get_partner_max_hp($slicePartner)') and val('gPlayerData.curFP') == val('gPlayerData.curMaxFP'))
        # Shared API overwrite is independent of the attack/defense sign rule.
        val('ttyd64_actor_set_regeneration('+partner+',0,-2,4)')
        val('ttyd64_actor_set_regeneration('+partner+',0,1,3)')
        check('regen-opposite-sign-direct-overwrite',val('PartnerModifiers[$slicePartner].hpRegen.amount') == 1 and val('PartnerModifiers[$slicePartner].hpRegen.turns') == 3)
        other=2 if partner_id==1 else 1
        def regen_swap(pid):
            battle_partners()
            for _ in range(12):
                if val('gPopupMenu->userIndex[PopupMenu_SelectedIndex]') == pid:break
                key('s')
            assert val('gPopupMenu->userIndex[PopupMenu_SelectedIndex]') == pid
            key('x',6)
            wait(f'gPlayerData.curPartner == {pid} && (gBattleState == BATTLE_STATE_PLAYER_MENU || gBattleState == BATTLE_STATE_PARTNER_MENU) && gBattleSubState < 4 && BattleMenuState == BTL_MENU_STATE_CHOOSING',1800)
        regen_swap(other)
        saved=val('PartnerModifiers[$slicePartner].hpRegen.turns')
        assert saved == 3
        spend_turn()
        spend_turn()
        check('regen-keyboard-inactive-partner-timer-pauses',val('PartnerModifiers[$slicePartner].hpRegen.turns') == saved)
        regen_swap(partner_id)
        check('regen-keyboard-swap-back-retains-axis',val('PartnerModifiers[$slicePartner].hpRegen.turns') in (2,3))
        val('ttyd64_actor_set_regeneration('+player+',0,2,3)');val('ttyd64_actor_set_regeneration('+player+',1,2,3)')
        cmd('call remove_player_buffs(PLAYER_BUFF_HP_REGEN)')
        check('regen-native-selective-removal-preserves-other-axis',val('ModifierActors[0].state.hpRegen.turns') == 0 and val('ModifierActors[0].state.fpRegen.turns') == 3)
        cmd('call remove_player_buffs(PLAYER_BUFF_ALL)')
        check('regen-native-full-buff-removal-clears-team-axes',val('ModifierActors[0].state.fpRegen.turns') == 0 and val('PartnerModifiers[$slicePartner].hpRegen.turns') == 0 and val('PartnerModifiers[$slicePartner].fpRegen.turns') == 0)
        val('ttyd64_actor_set_regeneration('+partner+',0,2,10)')
        flee_battle()
        check('regen-flee-clears-unsaved-axis',val('PartnerModifiers[$slicePartner].hpRegen.turns') == 0)
        for i in range(10):put(f'gPlayerData.invItems[{i}]',val(items[i]) if i<4 else 0)
        try:
            cmd('call fio_save_game(3)')
            for i in range(10):put(f'gPlayerData.invItems[{i}]',0)
            assert val('fio_load_game(3)') == 1
            check('regen-native-fio-round-trip-keeps-appended-ids',all(val(f'gPlayerData.invItems[{i}]') == val(item) for i,item in enumerate(items)))
        finally:save.write_bytes(original)
        cmd('call ttyd64_mode_select_file(0)')
    if 'status-items' in phases:
        enter_road_battle()
        player = 'gBattleStatus.playerActor'
        partner = 'gBattleStatus.partnerActor'
        assert val('ttyd64_set_partner_hp($slicePartner,10)') == 10
        items = ['ITEM_COURAGE_SHELL','ITEM_POWER_PUNCH','ITEM_MINI_MR_MINI','ITEM_MR_SOFTENER']
        check('items-native-definitions-have-consumable-battle-only-flags',all(val('gItemTable['+item+'].typeFlags & ITEM_TYPE_FLAG_CONSUMABLE') and val('gItemTable['+item+'].typeFlags & ITEM_TYPE_FLAG_BATTLE_USABLE') and not val('gItemTable['+item+'].typeFlags & ITEM_TYPE_FLAG_WORLD_USABLE') for item in items))
        cmd('call ttyd64_mode_select_file(0)')
        put('gBattleStatus.moveCategory',val('BTL_MENU_TYPE_ITEMS'))
        for item in items:
            put('gBattleStatus.moveArgument',val(item))
            put('gBattleStatus.curTargetListFlags',val('gItemTable['+item+'].targetFlags'))
            cmd(f'call create_target_list({player},0)')
            assert val(player+'->targetListLength') == 0
            assert val('ttyd64_status_item_apply('+item+','+partner+',1)') == 0
        check('items-flag-off-rejects-target-lists-and-effects',val('ttyd64_actor_attack_boost('+partner+')') == 0)
        inventory('ITEM_COURAGE_SHELL')
        wheel('BTL_MENU_TYPE_ITEMS')
        wait('gBattleSubState == 41 && gPopupState == POPUP_STATE_CHOOSING && PopupDelayTime == 0')
        check('items-flag-off-native-menu-disables-experimental-copies',val('gPopupMenu->enabled[0]') == 0 and val('gPopupMenu->enabled[1]') == 0 and item_count() == 2)
        key('c')
        wait('gBattleState == BATTLE_STATE_PLAYER_MENU && gBattleSubState < 4 && BattleMenuState == BTL_MENU_STATE_CHOOSING')
        cmd('call ttyd64_mode_select_file(1)')
        put('gBattleStatus.moveArgument',val('ITEM_COURAGE_SHELL'))
        put('gBattleStatus.curTargetListFlags',val('TARGET_FLAG_PLAYER'))
        assert val('ttyd64_set_partner_hp($slicePartner,0)') == 0
        cmd(f'call create_target_list({player},0)')
        check('items-dead-partner-not-offered-or-affected',val(player+'->targetListLength') == 1 and val('ttyd64_status_item_apply(ITEM_COURAGE_SHELL,'+partner+',1)') == 0)
        assert val('ttyd64_set_partner_hp($slicePartner,10)') == 10
        def select_item(item, recipient=None):
            # Keep this long item route out of Game Over; health/inventory are
            # controlled setup, effect expiry and input remain native.
            put('gPlayerData.curHP',20)
            assert val('ttyd64_set_partner_hp($slicePartner,10)') == 10
            inventory(item)
            wheel('BTL_MENU_TYPE_ITEMS')
            wait('gBattleSubState == 41 && gPopupState == POPUP_STATE_CHOOSING && PopupDelayTime == 0')
            tick(5)
            key('x')
            wait('gBattleState == BATTLE_STATE_SELECT_TARGET && gBattleSubState == 1')
            if recipient:
                for _ in range(4):
                    if val(player+'->targetData['+player+'->targetIndexList['+player+'->selectedTargetIndex]].actorID') == val(recipient):
                        break
                    key('d')
                assert val(player+'->targetData['+player+'->targetIndexList['+player+'->selectedTargetIndex]].actorID') == val(recipient)
        def finish_item():
            key('x')
            wait('gBattleState == BATTLE_STATE_PARTNER_MENU && BattleMenuState == BTL_MENU_STATE_CHOOSING && gBattleSubState < 4',1800)
            assert item_count() == 1
            assert val('gBattleStatus.flags2 & BS_FLAGS2_PLAYER_TURN_USED')
            assert not val('gBattleStatus.flags2 & BS_FLAGS2_PARTNER_TURN_USED')
        select_item('ITEM_COURAGE_SHELL','ACTOR_PARTNER')
        check('items-courage-native-menu-offers-living-partner',val(player+'->targetListLength') == 2)
        key('c')
        wait('gBattleState == BATTLE_STATE_PLAYER_MENU && gBattleSubState == 41 && gPopupState == POPUP_STATE_CHOOSING && PopupDelayTime == 0')
        check('items-cancel-keeps-both-copies-and-power',item_count() == 2 and val('ttyd64_actor_defense_boost('+partner+')') == 0)
        key('x')
        wait('gBattleState == BATTLE_STATE_SELECT_TARGET && gBattleSubState == 1')
        if val(player+'->targetData['+player+'->targetIndexList['+player+'->selectedTargetIndex]].actorID') != val('ACTOR_PARTNER'):
            key('d')
        finish_item()
        check('items-courage-keyboard-consumes-once-and-adds-three-defense',val('ttyd64_actor_defense_boost('+partner+')') == 3 and val('PartnerModifiers[$slicePartner].defense.turns') == 3)
        spend_turn()
        select_item('ITEM_POWER_PUNCH','ACTOR_PLAYER')
        finish_item()
        check('items-power-punch-native-mario-giant-and-turn-payment',val('ttyd64_actor_attack_boost('+player+')') == 2 and float(gdb.parse_and_eval(player+'->scalingFactor')) > 1.9)
        spend_turn()
        cmd('call ttyd64_actor_add_modifier('+partner+',0,-1,3)')
        select_item('ITEM_POWER_PUNCH','ACTOR_PARTNER')
        finish_item()
        check('items-power-punch-partner-opposite-sign-cancels-and-no-giant',val('ttyd64_actor_attack_boost('+partner+')') == 0 and float(gdb.parse_and_eval(partner+'->scalingFactor')) < 1.1)
        spend_turn()
        select_item('ITEM_POWER_PUNCH','ACTOR_PARTNER')
        finish_item()
        check('items-power-punch-native-partner-giant',val('ttyd64_actor_attack_boost('+partner+')') == 2 and float(gdb.parse_and_eval(partner+'->scalingFactor')) > 1.9)
        spend_turn()
        enemies = [i for i in range(val('sizeof(gBattleStatus.enemyActors)/sizeof(gBattleStatus.enemyActors[0])')) if val(f'gBattleStatus.enemyActors[{i}]')]
        assert len(enemies) >= 2
        before = {i:val(f'gBattleStatus.enemyActors[{i}]->curHP') for i in enemies}
        select_item('ITEM_MINI_MR_MINI')
        finish_item()
        check('items-mini-native-multiple-target-hit-route-and-tiny',all(val(f'ttyd64_actor_attack_boost(gBattleStatus.enemyActors[{i}])') == -2 and val(f'ttyd64_actor_is_tiny(gBattleStatus.enemyActors[{i}])') for i in enemies))
        check('items-mini-no-hp-damage-and-source-enemy-extra-turn',all(val(f'gBattleStatus.enemyActors[{i}]->curHP') == before[i] and val(f'ModifierActors[{i+1}].state.attack.turns') == 4 for i in enemies))
        spend_turn()
        select_item('ITEM_MR_SOFTENER')
        finish_item()
        check('items-softener-native-zero-defense-keeps-defense',all(val(f'ttyd64_actor_defense_boost(gBattleStatus.enemyActors[{i}])') == 0 for i in enemies))
        spend_turn()
        # Controlled part table isolates source min(normal table defense,3).
        # Actual item selection/iteration, hit test, consumption and turns stay native.
        cmd('set $itemDefense = (s32*)heap_malloc(3*sizeof(s32))')
        put('$itemDefense[0]',val('ELEMENT_NORMAL'))
        put('$itemDefense[1]',2)
        put('$itemDefense[2]',val('ELEMENT_END'))
        originals=[]
        for i in enemies:
            cmd(f'set $itemPart = get_actor_part(gBattleStatus.enemyActors[{i}],1)')
            originals.append((i,int(gdb.parse_and_eval('$itemPart->defenseTable'))))
            put('$itemPart->defenseTable','$itemDefense')
        try:
            select_item('ITEM_MR_SOFTENER')
            finish_item()
            check('items-softener-native-all-targets-use-part-table-defense',all(val(f'ttyd64_actor_defense_boost(gBattleStatus.enemyActors[{i}])') == -2 and val(f'ModifierActors[{i+1}].state.defense.turns') == 4 for i in enemies))
            put('$itemDefense[1]',5)
            for i in enemies:
                assert val(f'ttyd64_status_item_apply(ITEM_MR_SOFTENER,gBattleStatus.enemyActors[{i}],1)') == 1
            check('items-softener-controlled-api-caps-high-part-defense-at-three',all(val(f'ttyd64_actor_defense_boost(gBattleStatus.enemyActors[{i}])') == -3 for i in enemies))
            tick(45)
            check('items-native-downward-arrow-frames-advance',val('gGameStatusPtr->context') == val('CONTEXT_BATTLE'))
        finally:
            for i,original_defense in originals:
                cmd(f'set $itemPart = get_actor_part(gBattleStatus.enemyActors[{i}],1)')
                put('$itemPart->defenseTable',original_defense)
            cmd('call heap_free($itemDefense)')
        spend_turn()
        flee_battle()
        wait('WorldPartnerID == $slicePartner && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)',600)
        check('items-flee-clears-timed-power-and-world-owner',val('ModifierActors[0].state.attack.turns') == 0 and val('PartnerModifiers[$slicePartner].attack.turns') == 0 and val('WorldPartnerID') == partner_id)
        for i,item in enumerate(items):
            put(f'gPlayerData.invItems[{i}]',val(item))
        for i in range(4,10):
            put(f'gPlayerData.invItems[{i}]',0)
        put('gGameStatusPtr->saveSlot',3)
        try:
            cmd('call fio_save_game(3)')
            for i in range(10):put(f'gPlayerData.invItems[{i}]',0)
            assert val('fio_load_game(3)') == 1
            check('items-native-save-round-trip-keeps-four-appended-ids',all(val(f'gPlayerData.invItems[{i}]') == val(item) for i,item in enumerate(items)))
        finally:
            save.write_bytes(original)
        cmd('call ttyd64_mode_select_file(0)')
    if 'modifiers' in phases:
        enter_road_battle()
        actor = 'gBattleStatus.partnerActor'
        enemy = 'gBattleStatus.enemyActors[0]'
        other = 2 if partner_id == 1 else 1
        assert val('ttyd64_set_partner_hp($slicePartner,10)') == 10
        cmd('call ttyd64_mode_select_file(0)')
        put(f'{actor}->attackBoost',2)
        check('modifier-off-preserves-native-fields-and-rejects-api',val(f'ttyd64_actor_attack_boost({actor})') == 2 and val(f'ttyd64_actor_add_modifier({actor},0,4,3)') == 0)
        put(f'{actor}->attackBoost',0)
        cmd('call ttyd64_mode_select_file(1)')
        # Synthetic API arguments exercise the public event adapters. These
        # calls are debugger driven; round/swap controls below use keyboard UI.
        cmd('set $modifierEvt = (Evt*)heap_malloc(sizeof(Evt))')
        cmd('call (void*)memset($modifierEvt,0,sizeof(Evt))')
        cmd('set $modifierArgs = (Bytecode*)heap_malloc(3*sizeof(Bytecode))')
        put('$modifierEvt->ptrReadPos','$modifierArgs')
        put('$modifierEvt->owner1.actorID',val('ACTOR_PARTNER'))
        def api(name, values):
            for i,value in enumerate(values): put(f'$modifierArgs[{i}]',value)
            return val(f'{name}($modifierEvt,1)')
        api('Ttyd64AddAttackBoost',[val('ACTOR_SELF'),2,4])
        api('GetActorAttackBoost',[val('ACTOR_SELF'),-30000000])
        check('modifier-event-self-query-and-explicit-duration',val('$modifierEvt->varTable[0]') == 2 and val('PartnerModifiers[$slicePartner].attack.turns') == 4)
        api('Ttyd64AddAttackBoost',[val('ACTOR_SELF'),1,3])
        check('modifier-same-sign-replaces-strength-and-turns',val(f'ttyd64_actor_attack_boost({actor})') == 1 and val('PartnerModifiers[$slicePartner].attack.turns') == 3)
        api('Ttyd64MakeActorGiant',[val('ACTOR_SELF')])
        tick(30)
        check('modifier-giant-native-render-scale',float(gdb.parse_and_eval(f'{actor}->scalingFactor')) > 1.9)
        api('Ttyd64AddAttackBoost',[val('ACTOR_SELF'),-2,3])
        check('modifier-opposite-sign-cancels-and-removes-giant',val(f'ttyd64_actor_attack_boost({actor})') == 0 and val('PartnerModifiers[$slicePartner].size') == 0)
        assert val(f'inflict_status({actor},STATUS_KEY_SLEEP,3)') == 1
        assert val(f'inflict_status({actor},STATUS_KEY_SHRINK,3)') == 1
        api('GetStatusFlags',[val('ACTOR_SELF'),-30000000])
        expected_flags = val('STATUS_FLAG_SLEEP | STATUS_FLAG_SHRINK | STATUS_FLAG_ATTACK_BOOST')
        check('modifier-shrink-coexists-with-sleep-and-status-query',val(f'{actor}->debuff') == val('STATUS_KEY_SLEEP') and val(f'ttyd64_actor_attack_boost({actor})') == -1 and (val('$modifierEvt->varTable[0]') & expected_flags) == expected_flags)
        tick(30)
        check('modifier-tiny-native-render-scale',float(gdb.parse_and_eval(f'{actor}->scalingFactor')) < 0.5)
        cmd(f'call ttyd64_partner_status_cure_debuff({actor})')
        check('modifier-debuff-cure-preserves-timed-shrink',val(f'{actor}->debuff') == 0 and val(f'ttyd64_actor_is_tiny({actor})') == 1)
        put('$modifierEvt->varTable[0]',5)
        put('$modifierArgs[0]',-30000000)
        val('ApplyShrinkFromOwner($modifierEvt,1)')
        check('modifier-item-scaling-adds-signed-power-not-halving',val('$modifierEvt->varTable[0]') == 4)
        cmd(f'call ttyd64_actor_modifiers_clear({actor})')
        enemy_hp = val(f'{enemy}->curHP')
        put(f'{enemy}->curHP',0)
        check('modifier-shrink-rejects-dead-target',val(f'inflict_status({enemy},STATUS_KEY_SHRINK,3)') == 0)
        put(f'{enemy}->curHP',enemy_hp)
        # Direct native Mario damage with controlled attack inputs, then an
        # item damage call sharing the same target-defense consumer.
        put(f'{enemy}->maxHP',99)
        put(f'{enemy}->curHP',99)
        def player_hit(item=False):
            put('gBattleStatus.curTargetID',val('ACTOR_ENEMY0'))
            put('gBattleStatus.curTargetPart',1)
            put('gBattleStatus.curAttackDamage',4)
            put('gBattleStatus.curAttackElement',val('DAMAGE_TYPE_JUMP | DAMAGE_TYPE_NO_CONTACT'))
            put('gBattleStatus.curAttackStatus',0)
            put('gBattleStatus.curAttackEventSuppression',0)
            put('gBattleStatus.curDamageSource',val('DMG_SRC_DEFAULT'))
            cmd('set variable gBattleStatus.flags1 |= BS_FLAGS1_TRIGGER_EVENTS')
            val('calc_item_damage_enemy()' if item else 'calc_player_damage_enemy()')
            wait('!does_script_exist(gBattleStatus.enemyActors[0]->handleEventScriptID)',1800)
            return val('gBattleStatus.lastAttackDamage')
        base_hit = player_hit()
        api('Ttyd64AddAttackBoost',[val('ACTOR_PLAYER'),2,3])
        boosted_hit = player_hit()
        print('MODIFIER_MARIO_DAMAGE=' + json.dumps({'base':base_hit,'boosted':boosted_hit,'boost':val('ttyd64_actor_attack_boost(gBattleStatus.playerActor)'),'live_hp':val('gPlayerData.curHP')}))
        check('modifier-native-mario-attack-adds-timed-power',base_hit > 0 and boosted_hit == base_hit + 2)
        api('Ttyd64AddDefenseBoost',[val('ACTOR_ENEMY0'),1,3])
        armored_hit = player_hit()
        check('modifier-native-player-damage-reads-enemy-defense',armored_hit == boosted_hit - 1)
        item_hit = player_hit(True)
        cmd(f'call ttyd64_actor_modifiers_clear({enemy})')
        item_without_defense = player_hit(True)
        check('modifier-native-item-damage-reads-enemy-defense',item_hit == item_without_defense - 1)
        cmd('call ttyd64_actor_modifiers_clear(gBattleStatus.playerActor)')
        # Native enemy damage, with controlled power, recipient and no guard.
        val(f'ttyd64_actor_add_modifier({actor},1,2,4)')
        val(f'ttyd64_actor_add_modifier({enemy},0,1,3)')
        check('modifier-enemy-stores-extra-turn',val('ModifierActors[1].state.attack.turns') == 4)
        def damage(ignore=False):
            assert val('ttyd64_set_partner_hp($slicePartner,10)') == 10
            put('gBattleStatus.curTargetID',val('ACTOR_PARTNER'))
            put('gBattleStatus.curTargetPart',1)
            put('gBattleStatus.curAttackDamage',4)
            put('gBattleStatus.curAttackElement',val('DAMAGE_TYPE_UNBLOCKABLE | DAMAGE_TYPE_NO_CONTACT' + (' | DAMAGE_TYPE_IGNORE_DEFENSE' if ignore else '')))
            put('gBattleStatus.curAttackStatus',0)
            put('gBattleStatus.curAttackEventSuppression',0)
            cmd('set variable gBattleStatus.flags1 |= BS_FLAGS1_TRIGGER_EVENTS')
            val(f'calc_enemy_damage_target({enemy})')
            wait('!does_script_exist(gBattleStatus.partnerActor->handleEventScriptID)',1800)
        damage()
        check('modifier-native-enemy-attack-and-partner-defense',hp() == (8 if partner_id == 2 else 7))
        damage(True)
        check('modifier-ignore-defense-bypasses-timed-defense',hp() == 5)
        cmd(f'call ttyd64_actor_modifiers_clear({enemy})')
        # Reset recipient before keyboard rounds and swaps; keep the AI native.
        assert val('ttyd64_set_partner_hp($slicePartner,10)') == 10
        val(f'ttyd64_actor_add_modifier({actor},0,2,4)')
        val(f'ttyd64_actor_add_modifier({actor},1,1,3)')
        val(f'ttyd64_actor_set_size({actor},1)')
        def modifier_swap(pid):
            battle_partners()
            for _ in range(12):
                if val('gPopupMenu->userIndex[PopupMenu_SelectedIndex]') == pid: break
                key('s')
            assert val('gPopupMenu->userIndex[PopupMenu_SelectedIndex]') == pid
            key('x',6)
            wait(f'gPlayerData.curPartner == {pid} && (gBattleState == BATTLE_STATE_PLAYER_MENU || gBattleState == BATTLE_STATE_PARTNER_MENU) && gBattleSubState < 4 && BattleMenuState == BTL_MENU_STATE_CHOOSING',1800)
            if val('gBattleState') == val('BATTLE_STATE_PARTNER_MENU'):
                spend_turn()
        modifier_swap(other)
        check('modifier-keyboard-swap-away-pauses-inactive-record',val('PartnerModifiers[$slicePartner].attack.turns') == 4 and val(f'ttyd64_actor_attack_boost({actor})') == 0)
        modifier_swap(partner_id)
        tick(30)
        check('modifier-keyboard-swap-back-restores-size-and-ticks-once',val('PartnerModifiers[$slicePartner].attack.turns') == 3 and val('PartnerModifiers[$slicePartner].defense.turns') == 2 and val(f'ttyd64_actor_attack_boost({actor})') == 2 and float(gdb.parse_and_eval(f'{actor}->scalingFactor')) > 1.9)
        for _ in range(3):
            spend_turn()
            spend_turn()
        check('modifier-native-rounds-expire-independent-effects',val(f'ttyd64_actor_attack_boost({actor})') == 0 and val(f'ttyd64_actor_defense_boost({actor})') == 0 and val('PartnerModifiers[$slicePartner].size') == 0)
        val(f'ttyd64_actor_add_modifier({actor},0,-1,4)')
        val(f'ttyd64_actor_add_modifier({actor},1,-2,4)')
        cmd(f'call ttyd64_partner_status_clear({actor})')
        check('modifier-full-clear-removes-signed-effects',val(f'ttyd64_actor_attack_boost({actor})') == 0 and val(f'ttyd64_actor_defense_boost({actor})') == 0)
        val(f'ttyd64_actor_add_modifier({actor},0,2,4)')
        cmd('call heap_free($modifierArgs)')
        cmd('call heap_free($modifierEvt)')
        flee_battle()
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_CANT_TOUCH'))
        check('modifier-battle-exit-clears-owned-partner-record',val('PartnerModifiers[$slicePartner].attack.turns') == 0 and val('ModifierPartnerOwner') == 0)
    if 'recovery' in phases:
        # Recruitment, attacks, statuses and progression are controlled setup;
        # item targets/payment, rounds and Refresh run through native keyboard UI.
        put('gPlayerData.maxStarPower',1)
        put('gPlayerData.starPower',256)
        enter_road_battle()
        actor = 'gBattleStatus.partnerActor'
        def reaction_done():
            wait('!does_script_exist(gBattleStatus.partnerActor->handleEventScriptID) && !does_script_exist(gBattleStatus.enemyActors[0]->handleEventScriptID)',1800)
            tick(15)
        def attack(element='DAMAGE_TYPE_UNBLOCKABLE'):
            put('gBattleStatus.curTargetID',val('ACTOR_PARTNER'))
            put('gBattleStatus.curTargetPart',1)
            put('gBattleStatus.curAttackDamage',2)
            put('gBattleStatus.curAttackElement',val(element))
            put('gBattleStatus.curAttackStatus',0)
            put('gBattleStatus.curAttackEventSuppression',0)
            cmd('set variable gBattleStatus.flags1 |= BS_FLAGS1_TRIGGER_EVENTS')
        assert val('ttyd64_set_partner_hp($slicePartner,10)') == 10
        val(f'inflict_status({actor},STATUS_KEY_TRANSPARENT,4)')
        tick(3)
        attack()
        check('recovery-transparent-test-and-damage-miss',val('calc_enemy_test_target(gBattleStatus.enemyActors[0])') == val('HIT_RESULT_MISS') and val('calc_enemy_damage_target(gBattleStatus.enemyActors[0])') == val('HIT_RESULT_MISS') and hp() == 10)
        cmd(f'call ttyd64_partner_status_clear({actor})')
        tick(15)
        put('gBattleStatus.enemyActors[0]->curHP',10)
        val(f'inflict_status({actor},STATUS_KEY_STATIC,4)')
        tick(3)
        attack()
        check('recovery-static-enemy-test-detects-contact',val('calc_enemy_test_target(gBattleStatus.enemyActors[0])') == val('HIT_RESULT_HIT_STATIC'))
        result = val('calc_enemy_damage_target(gBattleStatus.enemyActors[0])')
        reaction_done()
        check('recovery-static-contact-retaliates-one-hp',result == val('HIT_RESULT_BACKFIRE') and val('gBattleStatus.enemyActors[0]->curHP') == 9 and hp() == (9 if partner_id == 2 else 8) and val(f'{actor}->staticDuration') == 4)
        attack('DAMAGE_TYPE_UNBLOCKABLE | DAMAGE_TYPE_NO_CONTACT')
        val('calc_enemy_damage_target(gBattleStatus.enemyActors[0])')
        reaction_done()
        check('recovery-static-no-contact-does-not-retaliate',val('gBattleStatus.enemyActors[0]->curHP') == 9 and hp() == (8 if partner_id == 2 else 6))
        cmd(f'call ttyd64_partner_status_clear({actor})')
        tick(15)
        val(f'inflict_status({actor},STATUS_KEY_FROZEN,4)')
        tick(3)
        val(f'inflict_status({actor},STATUS_KEY_POISON,4)')
        tick(15)
        check('recovery-replacing-frozen-dismisses-old-pillar',val(f'{actor}->icePillarEffect') == 0 and val(f'{actor}->debuff') == val('STATUS_KEY_POISON'))
        cmd(f'call ttyd64_partner_status_clear({actor})')
        tick(15)
        def item_target(item):
            inventory(item)
            wheel('BTL_MENU_TYPE_ITEMS')
            wait('gBattleSubState == 41 && gPopupState == POPUP_STATE_CHOOSING && PopupDelayTime == 0')
            tick(5)
            key('x')
            wait('gBattleState == BATTLE_STATE_SELECT_TARGET && gBattleSubState == 1')
            for _ in range(3):
                if val('gBattleStatus.playerActor->targetData[gBattleStatus.playerActor->targetIndexList[gBattleStatus.playerActor->selectedTargetIndex]].actorID') == val('ACTOR_PARTNER'):
                    break
                key('d')
            check('recovery-' + item.lower() + '-native-partner-target',val('gBattleStatus.playerActor->targetListLength') == 2 and val('gBattleStatus.playerActor->targetData[gBattleStatus.playerActor->targetIndexList[gBattleStatus.playerActor->selectedTargetIndex]].actorID') == val('ACTOR_PARTNER'))
        for item,status in [('ITEM_TASTY_TONIC','FROZEN'),('ITEM_SUPER_SODA','SLEEP')]:
            assert val('ttyd64_set_partner_hp($slicePartner,8)') == 8
            put('gPlayerData.curFP',2)
            put('gPlayerData.curMaxFP',10)
            for name in (status,'STATIC','TRANSPARENT'):
                val(f'inflict_status({actor},STATUS_KEY_{name},4)')
            tick(5)
            item_target(item)
            if item == 'ITEM_TASTY_TONIC':
                key('c')
                wait('gBattleState == BATTLE_STATE_PLAYER_MENU && gBattleSubState == 41 && gPopupState == POPUP_STATE_CHOOSING')
                check('recovery-cancel-preserves-item-hp-and-frozen',item_count() == 2 and hp() == 8 and val(f'{actor}->debuff') == val('STATUS_KEY_FROZEN'))
                key('x')
                wait('gBattleState == BATTLE_STATE_SELECT_TARGET && gBattleSubState == 1')
                if val('gBattleStatus.playerActor->targetData[gBattleStatus.playerActor->targetIndexList[gBattleStatus.playerActor->selectedTargetIndex]].actorID') != val('ACTOR_PARTNER'):
                    key('d')
            key('x')
            wait('gBattleState == BATTLE_STATE_PARTNER_MENU && gBattleSubState == 3 && BattleMenuState == BTL_MENU_STATE_CHOOSING',1800)
            check('recovery-' + item.lower() + '-cures-debuff-keeps-buffs',hp() == 8 and item_count() == 1 and val(f'{actor}->debuff') == 0 and val(f'{actor}->koStatus') == 0 and val(f'{actor}->icePillarEffect') == 0 and val('PartnerStatuses[$slicePartner].debuff') == 0 and val(f'{actor}->staticDuration') == 4 and val(f'{actor}->transparentDuration') == 4 and val('gPlayerData.curFP') == (7 if item == 'ITEM_SUPER_SODA' else 2))
            check('recovery-' + item.lower() + '-spends-mario-turn-only',bool(val('gBattleStatus.flags2 & BS_FLAGS2_PLAYER_TURN_USED')) and not val('gBattleStatus.flags2 & BS_FLAGS2_PARTNER_TURN_USED') and val('btl_partner_can_act()'))
            capture('recovery-' + item.lower())
            spend_turn()
        # Refresh: normal spirit menu/payment/script, living-partner cap and cure.
        assert val('ttyd64_set_partner_hp($slicePartner,8)') == 8
        put('gPlayerData.curHP',12)
        put('gPlayerData.curFP',2)
        put('gPlayerData.starPower',256)
        val(f'inflict_status({actor},STATUS_KEY_FROZEN,4)')
        tick(5)
        wheel('BTL_MENU_TYPE_STAR_POWERS')
        wait('gBattleSubState == 61')
        tick(15)
        refresh_index = next(i for i in range(val('MovesOptionCount')) if val(f'gBattleStatus.submenuMoves[MovesOptionIndices[MovesOptionIndexMap[{i}]]]') == val('MOVE_REFRESH'))
        for _ in range(12):
            current = val('MovesCursorPos')
            if current == refresh_index:
                break
            key('w' if refresh_index < current else 's')
        check('recovery-native-spirit-menu-selects-refresh',val('gBattleStatus.submenuMoves[MovesOptionIndices[MovesOptionIndexMap[MovesCursorPos]]]') == val('MOVE_REFRESH'))
        key('x')
        wait('gBattleState == BATTLE_STATE_SELECT_TARGET && gBattleSubState == 1')
        key('x')
        wait('gBattleState == BATTLE_STATE_PARTNER_MENU && gBattleSubState == 3 && BattleMenuState == BTL_MENU_STATE_CHOOSING',2400)
        check('recovery-refresh-native-team-hp-fp-cap-and-debuff',hp() == min(13,val('ttyd64_get_partner_max_hp($slicePartner)')) and val('gPlayerData.curHP') == 17 and val('gPlayerData.curFP') == 7 and val(f'{actor}->debuff') == 0 and val(f'{actor}->icePillarEffect') == 0 and val('PartnerStatuses[$slicePartner].debuff') == 0)
        check('recovery-refresh-spends-star-power-and-mario-turn',val('gPlayerData.starPower') < 256 and val('gBattleStatus.flags2 & BS_FLAGS2_PLAYER_TURN_USED') and not val('gBattleStatus.flags2 & BS_FLAGS2_PARTNER_TURN_USED'))
        capture('recovery-refresh')
        spend_turn()
        assert val('ttyd64_set_partner_hp($slicePartner,0)') == 0
        check('recovery-cure-items-reject-dead-partner',not val('ttyd64_partner_status_can_target_item(ITEM_TASTY_TONIC)') and not val('ttyd64_partner_status_can_target_item(ITEM_SUPER_SODA)'))
        assert val('ttyd64_set_partner_hp($slicePartner,8)') == 8
        cmd('call ttyd64_mode_select_file(0)')
        check('recovery-off-rejects-new-cure-targets',not val('ttyd64_partner_status_can_target_item(ITEM_TASTY_TONIC)') and not val('ttyd64_partner_status_can_target_item(ITEM_SUPER_SODA)'))
        cmd('call ttyd64_mode_select_file(1)')
        flee_battle()
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_CANT_TOUCH'))
        check('recovery-native-world-return',val('WorldPartnerID') == partner_id)
    if 'statuses' in phases:
        enter_road_battle()
        actor = 'gBattleStatus.partnerActor'
        assert val('ttyd64_set_partner_hp($slicePartner,10)') == 10
        cmd('call ttyd64_mode_select_file(0)')
        val(f'inflict_status({actor},STATUS_KEY_SLEEP,3)')
        check('status-off-keeps-native-partner-immunity',val(f'{actor}->debuff') == 0)
        cmd('call ttyd64_mode_select_file(1)')
        for status in ('UNUSED','DIZZY','PARALYZE','SLEEP','FROZEN','STOP','POISON','STONE','STATIC','TRANSPARENT'):
            keyname = 'STATUS_KEY_' + status
            assert val(f'inflict_status({actor},{keyname},3)') == 1
            tick(3)
            cmd('call btl_update_ko_status()')
            field = {'STONE':'stoneStatus','STATIC':'staticStatus','TRANSPARENT':'transparentStatus'}.get(status,'debuff')
            movable = status in ('POISON','SHRINK','STATIC','TRANSPARENT')
            check('status-native-application-and-turn-' + status.lower(),val(f'{actor}->{field}') == val(keyname) and bool(val('btl_partner_can_act()')) == movable)
            if status == 'FROZEN':
                check('status-frozen-owns-native-pillar',val(f'{actor}->icePillarEffect') != 0)
            cmd(f'call ttyd64_partner_status_clear({actor})')
            tick(15)
        check('status-clear-removes-projected-status-and-pillar',val(f'{actor}->debuff') == 0 and val(f'{actor}->koStatus') == 0 and val(f'{actor}->icePillarEffect') == 0)
        put('gBattleStatus.curTargetID',val('ACTOR_PARTNER'))
        put('gBattleStatus.curTargetPart',1)
        put('gBattleStatus.curAttackDamage',0)
        put('gBattleStatus.curAttackElement',val('DAMAGE_TYPE_UNBLOCKABLE'))
        put('gBattleStatus.curAttackStatus',val('STATUS_FLAG_SLEEP | STATUS_FLAG_USE_DURATION'))
        put('gBattleStatus.statusChance',100)
        put('gBattleStatus.statusDuration',3)
        cmd('set variable gBattleStatus.flags1 |= BS_FLAGS1_TRIGGER_EVENTS')
        val('calc_enemy_damage_target(gBattleStatus.enemyActors[0])')
        wait('!does_script_exist(gBattleStatus.partnerActor->handleEventScriptID)')
        check('status-enemy-damage-route-inflicts-sleep-without-hp-loss',val(f'{actor}->debuff') == val('STATUS_KEY_SLEEP') and val(f'{actor}->debuffDuration') == 3 and hp() == 10)
        cmd(f'call ttyd64_partner_status_clear({actor})')
        tick(15)
        put('gBattleStatus.curAttackStatus',0)
        val(f'inflict_status({actor},STATUS_KEY_FROZEN,3)')
        cmd('call btl_update_ko_status()')
        tick(5)
        capture('status-frozen')
        # Native keyboard swap while frozen: unavailable outgoing turn is
        # consumed, statuses persist privately and their inactive timer pauses.
        other = 2 if partner_id == 1 else 1
        def status_swap(pid):
            battle_partners()
            for _ in range(8):
                current = val('gPopupMenu->userIndex[PopupMenu_SelectedIndex]')
                if current == pid:
                    break
                key('w' if current > pid else 's')
            assert val('gPopupMenu->userIndex[PopupMenu_SelectedIndex]') == pid
            key('x',6)
            wait(f'gPlayerData.curPartner == {pid} && gBattleState == BATTLE_STATE_PLAYER_MENU && gBattleSubState == 1 && BattleMenuState == BTL_MENU_STATE_CHOOSING',1800)
        status_swap(other)
        check('status-frozen-keyboard-swap-away-retains-record',val('PartnerStatuses[$slicePartner].debuff') == val('STATUS_KEY_FROZEN') and val('PartnerStatuses[$slicePartner].debuffDuration') == 3 and val(f'{actor}->debuff') == 0)
        status_swap(partner_id)
        check('status-frozen-swap-back-restores-pillar-and-one-active-tick',val(f'{actor}->debuff') == val('STATUS_KEY_FROZEN') and val(f'{actor}->debuffDuration') == 2 and val(f'{actor}->icePillarEffect') != 0 and not val('btl_partner_can_act()'))
        spend_turn()
        check('status-frozen-next-round-decrements-once',val(f'{actor}->debuffDuration') == 1 and not val('btl_partner_can_act()'))
        spend_turn()
        check('status-frozen-expiry-clears-pillar-and-restores-turn',val(f'{actor}->debuff') == 0 and val(f'{actor}->icePillarEffect') == 0 and val('btl_partner_can_act()') == 1)
        capture('status-recovered')
        # Transparency isolates poison ticks from native Goomba damage. Native
        # keyboard rounds advance timers; no duration/turn/result writes.
        put('gPlayerData.curHP',20)
        assert val('ttyd64_set_partner_hp($slicePartner,10)') == 10
        for status in ('POISON','STATIC','TRANSPARENT'):
            val(f'inflict_status({actor},STATUS_KEY_{status},2)')
        capture('status-poison-static-transparent')
        spend_turn()
        check('status-poison-can-act-without-admission-tick',val('gBattleState') == val('BATTLE_STATE_PARTNER_MENU') and val(f'{actor}->debuffDuration') == 2 and hp() == 10)
        spend_turn()
        check('status-first-player-begin-poison-and-buff-tick',hp() == 9 and val(f'{actor}->debuffDuration') == 1 and val(f'{actor}->staticDuration') == 1 and val(f'{actor}->transparentDuration') == 1)
        spend_turn()
        spend_turn()
        check('status-second-poison-tick-expires-all-three',hp() == 8 and val(f'{actor}->debuff') == 0 and val(f'{actor}->staticStatus') == 0 and val(f'{actor}->transparentStatus') == 0)
        inventory('ITEM_LIFE_SHROOM')
        assert val('ttyd64_set_partner_hp($slicePartner,1)') == 1
        val(f'ttyd64_actor_set_regeneration({actor},0,2,10)')
        val(f'ttyd64_actor_set_regeneration({actor},1,2,10)')
        val(f'ttyd64_actor_add_modifier({actor},0,2,4)')
        val(f'inflict_status({actor},STATUS_KEY_POISON,2)')
        val(f'inflict_status({actor},STATUS_KEY_TRANSPARENT,2)')
        spend_turn()
        spend_turn()
        wait('ttyd64_get_partner_hp($slicePartner) == 10 && !does_script_exist(gBattleStatus.partnerActor->handleEventScriptID)',1800)
        check('status-lethal-poison-revives-once-and-clears-cache',hp() == 10 and item_count() == 1 and val(f'{actor}->debuff') == 0 and val(f'{actor}->transparentStatus') == 0 and val('PartnerStatuses[$slicePartner].debuff') == 0 and val(f'{actor}->koStatus') == 0)
        check('modifier-native-poison-death-and-revival-clear-power',val(f'ttyd64_actor_attack_boost({actor})') == 0)
        check('regen-native-poison-death-life-shroom-clears-both-axes',val('PartnerModifiers[$slicePartner].hpRegen.turns') == 0 and val('PartnerModifiers[$slicePartner].fpRegen.turns') == 0)
        capture('status-poison-revived')
        val(f'inflict_status({actor},STATUS_KEY_STATIC,3)')
        flee_battle()
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_CANT_TOUCH'))
        check('status-flee-clears-record-and-rebinds-world',val('PartnerStatuses[$slicePartner].staticDuration') == 0 and val('WorldPartnerID') == partner_id)
    if 'ground-contracts' in phases:
        assert partner_id in (2,3)
        enter_road_battle()
        actor = 'gBattleStatus.partnerActor'
        def reaction_done():
            wait('!does_script_exist(gBattleStatus.partnerActor->handleEventScriptID)',1200)
            tick(3)
        def item_hit(damage, element):
            put('gBattleStatus.curTargetID',val('ACTOR_PARTNER'))
            put('gBattleStatus.curTargetPart',1)
            put('gBattleStatus.curAttackDamage',damage)
            put('gBattleStatus.curAttackElement',val(element))
            put('gBattleStatus.curAttackStatus',0)
            cmd('set variable gBattleStatus.flags1 |= BS_FLAGS1_TRIGGER_EVENTS')
            val('calc_item_damage_enemy()')
            reaction_done()
        if partner_id == 2:
            check('kooper-normal-defense-one',val(f'get_defense({actor},(int*){actor}->partsTable->defenseTable,0)') == 1)
            cmd('call ttyd64_mode_select_file(0)')
            check('kooper-flag-off-native-defense-zero',val(f'get_defense({actor},(int*){actor}->partsTable->defenseTable,0)') == 0)
            cmd('call ttyd64_mode_select_file(1)')
            check('kooper-ignore-defense-remains-zero',val(f'get_defense({actor},(int*){actor}->partsTable->defenseTable,DAMAGE_TYPE_IGNORE_DEFENSE)') == 0)
            item_hit(1,'0')
            check('kooper-defense-prevents-one-damage-item',hp() == 3 and not val(f'ttyd64_kooper_flipped({actor})'))
            blocks = []
            class BlockTrace(gdb.Breakpoint):
                def __init__(self):
                    super().__init__('check_block_input',internal=True)
                    self.silent = True
                def stop(self):
                    blocks.append(1)
                    return False
            block_point = BlockTrace()
            def enemy_hit(damage, element):
                put('gBattleStatus.curTargetID',val('ACTOR_PARTNER'))
                put('gBattleStatus.curTargetPart',1)
                put('gBattleStatus.curAttackDamage',damage)
                put('gBattleStatus.curAttackElement',val(element))
                put('gBattleStatus.curAttackStatus',0)
                cmd('set variable gBattleStatus.flags1 |= BS_FLAGS1_TRIGGER_EVENTS')
                val('calc_enemy_damage_target(gBattleStatus.enemyActors[0])')
                reaction_done()
            enemy_hit(1,'0')
            check('kooper-enemy-route-defense-and-native-guard-window',hp() == 3 and len(blocks) == 1)
            enemy_hit(1,'DAMAGE_TYPE_JUMP | DAMAGE_TYPE_UNBLOCKABLE')
            check('kooper-zero-damage-jump-flips-for-two-rounds',hp() == 3 and val(f'ttyd64_kooper_flipped({actor})') == 1 and val('ttyd64_kooper_flip_turns()') == 2)
            check('kooper-flipped-defense-and-turn-unavailable',val(f'get_defense({actor},(int*){actor}->partsTable->defenseTable,0)') == 0 and val('btl_partner_can_act()') == 0 and val(f'{actor}->flags & ACTOR_FLAG_FLIPPED') != 0)
            check('kooper-enemy-jump-route-dispatches-flip',val(f'ttyd64_kooper_flipped({actor})'))
            blocks.clear()
            enemy_hit(1,'0')
            check('kooper-flipped-enemy-hit-cannot-guard',hp() == 2 and not blocks)
            block_point.delete()
            capture('contracts-kooper-flipped')
            # Controlled wounds avoid death while natural Goomba rounds advance
            # the phase callback and the begin-round latch; no countdown writes.
            assert val('ttyd64_set_partner_hp($slicePartner,10)') == 10
            spend_turn()
            check('kooper-first-native-enemy-end-stays-flipped',val('ttyd64_kooper_flip_turns()') == 1 and val(f'ttyd64_kooper_flipped({actor})') and not val('btl_partner_can_act()'))
            spend_turn()
            check('kooper-second-native-enemy-end-recovers-but-spends-round',val('ttyd64_kooper_flip_turns()') == 0 and not val(f'ttyd64_kooper_flipped({actor})') and not val('btl_partner_can_act()') and val('gBattleStatus.flags2 & BS_FLAGS2_PARTNER_TURN_USED') != 0)
            check('kooper-recovery-restores-defense-pose-and-offsets',val(f'get_defense({actor},(int*){actor}->partsTable->defenseTable,0)') == 1 and val(f'{actor}->flags & ACTOR_FLAG_FLIPPED') == 0 and val(f'{actor}->rot.z') == 0)
            capture('contracts-kooper-recovered')
            spend_turn()
            check('kooper-following-round-can-act-again',val('btl_partner_can_act()') == 1)
            # A POW uses the independent item route; lethal attacks must retain
            # death ownership instead of being replaced by another flip event.
            item_hit(1,'DAMAGE_TYPE_POW')
            check('kooper-pow-reflips',val('ttyd64_kooper_flip_turns()') == 2 and val(f'ttyd64_kooper_flipped({actor})'))
            inventory('ITEM_LIFE_SHROOM')
            assert val('ttyd64_set_partner_hp($slicePartner,1)') == 1
            item_hit(1,'DAMAGE_TYPE_QUAKE')
            wait('ttyd64_get_partner_hp($slicePartner) == 10',1200)
            reaction_done()
            check('kooper-lethal-flipped-hit-life-shroom-clears-flip',hp() == 10 and item_count() == 1 and not val(f'ttyd64_kooper_flipped({actor})') and val(f'{actor}->flags & ACTOR_FLAG_FLIPPED') == 0 and val(f'{actor}->koStatus') == 0)
            item_hit(1,'DAMAGE_TYPE_POW')
            battle_partners()
            for _ in range(3):
                if val('gPopupMenu->userIndex[PopupMenu_SelectedIndex]') == 1:
                    break
                key('w')
            key('x')
            wait('gPlayerData.curPartner == 1 && gBattleState == BATTLE_STATE_PARTNER_MENU && BattleMenuState == BTL_MENU_STATE_CHOOSING',1200)
            check('kooper-swap-away-keeps-private-countdown',val('ttyd64_kooper_flip_turns()') == 2 and not val(f'ttyd64_kooper_flipped({actor})'))
            spend_turn()
            check('kooper-inactive-countdown-advances-once-per-round',val('ttyd64_kooper_flip_turns()') == 1)
            battle_partners()
            for _ in range(3):
                if val('gPopupMenu->userIndex[PopupMenu_SelectedIndex]') == 2:
                    break
                key('s')
            key('x')
            wait('gPlayerData.curPartner == 2 && gBattleState == BATTLE_STATE_PLAYER_MENU && BattleMenuState == BTL_MENU_STATE_CHOOSING',1800)
            check('kooper-swap-back-recovers-preserved-flip-on-second-round',val('ttyd64_kooper_flip_turns()') == 0 and not val(f'ttyd64_kooper_flipped({actor})') and not val(f'{actor}->flags & ACTOR_FLAG_FLIPPED') and not val('btl_partner_can_act()'))
            spend_turn()
            check('kooper-swapped-recovery-can-act-following-round',val('ttyd64_kooper_flip_turns()') == 0 and val('btl_partner_can_act()'))
        else:
            explosions = []
            class ExplosionTrace(gdb.Breakpoint):
                def __init__(self):
                    super().__init__('battle_partner_bombette_PlayExplosionFX',internal=True)
                    self.silent = True
                def stop(self):
                    explosions.append(hp())
                    return False
            explosion_point = ExplosionTrace()
            for event in ('EVENT_BURN_HIT','EVENT_BURN_CONTACT','EVENT_SHOCK_HIT'):
                assert val('ttyd64_set_partner_hp($slicePartner,10)') == 10
                val(f'dispatch_damage_event_partner(1,{event},0)')
                reaction_done()
                check('bombette-' + event.lower() + '-hp-and-pose',hp() == 9 and val(f'{actor}->koStatus') == 0 and val(f'{actor}->rot.z') == 0 and val(f'{actor}->curPos.y') == val(f'{actor}->homePos.y'))
            check('bombette-three-native-explosion-effects',len(explosions) == 3)
            capture('contracts-bombette-explosion-return')
            inventory('ITEM_LIFE_SHROOM')
            assert val('ttyd64_set_partner_hp($slicePartner,1)') == 1
            val('dispatch_damage_event_partner(1,EVENT_BURN_CONTACT,0)')
            wait('ttyd64_get_partner_hp($slicePartner) == 10',1800)
            reaction_done()
            check('bombette-lethal-contact-revives-once-without-stale-rotation',hp() == 10 and item_count() == 1 and val(f'{actor}->rot.x') == 0 and val(f'{actor}->rot.z') == 0 and val(f'{actor}->koStatus') == 0)
            check('bombette-lethal-contact-dispatches-death-without-extra-explosion',len(explosions) == 3)
            explosion_point.delete()
        # Let any revived/available partner finish the round before Mario flees.
        while val('gBattleState') != val('BATTLE_STATE_PLAYER_MENU') or val('gBattleStatus.flags2 & BS_FLAGS2_PLAYER_TURN_USED'):
            spend_turn()
        flee_battle()
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_CANT_TOUCH'))
        check('contracts-native-world-return',val('WorldPartnerID') == partner_id and val('gCurrentEncounter.battleOutcome') == val('OUTCOME_PLAYER_FLED'))
    if 'ground-combat' in phases:
        enter_road_battle()
        # Controlled native API boundaries complement ordinary Goomba hits:
        # contact/backfire damage and item damage have independent entry points.
        val('dispatch_damage_event_partner(2, EVENT_HIT, 0)')
        wait('!does_script_exist(gBattleStatus.partnerActor->handleEventScriptID)')
        check('ground-contact-damage-updates-owned-hp-without-ko',hp() == 1 and val('gBattleStatus.partnerActor->curHP') == 1 and val('gBattleStatus.partnerActor->koStatus') == 0)
        wheel('BTL_MENU_TYPE_ITEMS')
        wait('gBattleSubState == 41 && gPopupState == POPUP_STATE_CHOOSING && PopupDelayTime == 0')
        tick(5)
        key('x')
        wait('gBattleState == BATTLE_STATE_SELECT_TARGET && gBattleSubState == 1')
        for _ in range(3):
            if val('gBattleStatus.playerActor->targetData[gBattleStatus.playerActor->targetIndexList[gBattleStatus.playerActor->selectedTargetIndex]].actorID') == val('ACTOR_PARTNER'):
                break
            key('d')
        check('ground-battle-keyboard-shroom-target-identity',val('gBattleStatus.playerActor->targetListLength') == 2 and val('gBattleStatus.playerActor->targetData[gBattleStatus.playerActor->targetIndexList[gBattleStatus.playerActor->selectedTargetIndex]].actorID') == val('ACTOR_PARTNER'))
        key('x')
        wait('ttyd64_get_partner_hp($slicePartner) == 6')
        check('ground-battle-native-food-heals-and-consumes-once',hp() == 6 and val('gBattleStatus.partnerActor->curHP') == 6 and item_count() == 1 and val('gPlayerData.curHP') == 20)
        wait('gBattleState == BATTLE_STATE_PARTNER_MENU && gBattleSubState == 3 && BattleMenuState == BTL_MENU_STATE_CHOOSING')
        check('ground-battle-food-spends-mario-turn-only',val('gBattleStatus.flags2 & BS_FLAGS2_PLAYER_TURN_USED') != 0 and val('gBattleStatus.flags2 & BS_FLAGS2_PARTNER_TURN_USED') == 0)
        capture('ground-battle-healed')
        put('gBattleStatus.curTargetID',val('ACTOR_PARTNER'))
        put('gBattleStatus.curTargetPart',1)
        put('gBattleStatus.curAttackDamage',2)
        put('gBattleStatus.curAttackElement',val('DAMAGE_TYPE_UNBLOCKABLE'))
        put('gBattleStatus.curAttackStatus',0)
        val('calc_item_damage_enemy()')
        wait('!does_script_exist(gBattleStatus.partnerActor->handleEventScriptID)')
        check('ground-item-damage-updates-owned-hp',hp() == (5 if partner_id == 2 else 4) and val('gBattleStatus.partnerActor->curHP') == (5 if partner_id == 2 else 4))
        assert val('ttyd64_set_partner_hp($slicePartner,0)') == 0
        check('ground-battle-food-rejects-dead-recipient',val('ttyd64_partner_combat_can_heal_with_item(ITEM_MUSHROOM)') == 0 and val('ttyd64_partner_combat_heal(gBattleStatus.partnerActor,5)') == 0)
        assert val('ttyd64_set_partner_hp($slicePartner,4)') == 4
        # Native partner Strategies has no Run Away entry. Spend its turn and
        # let the enemy round complete before Mario chooses escape.
        spend_turn()
        assert val('gBattleState') == val('BATTLE_STATE_PLAYER_MENU')
        flee_battle()
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_CANT_TOUCH'))
        check('ground-combat-native-flee-rebinds-world-owner',val('WorldPartnerID') == partner_id and val('gCurrentEncounter.battleOutcome') == val('OUTCOME_PLAYER_FLED'))
    if 'team' in phases:
        enter_road_battle()
        if partner_id == 2:
            for i in range(24):
                if val(f'gBattleStatus.enemyActors[{i}]'):
                    put(f'gBattleStatus.enemyActors[{i}]->attackBoost',1)
            team_trace.append({'event':'controlled-kooper-enemy-attack-boost','amount':1})
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
        assert val('ttyd64_set_partner_hp($slicePartner,1)') == 1
        for i in range(10):
            put(f'gPlayerData.invItems[{i}]',val('ITEM_LIFE_SHROOM') if i < 2 else 0)
        def model_hp():
            return val('gCurrentSaveFile.shipSaveData.partnerHP[$slicePartner].curHP')
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
        assert val('ttyd64_set_partner_hp($slicePartner,1)') == 1
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
        cmd('call ttyd64_mode_select_file(0)')
        check('team-off-target-and-swap-helpers-preserve-native',val('ttyd64_partner_team_active()') == 0 and val('ttyd64_partner_team_resolve_target(ACTOR_PARTNER)') == val('ACTOR_PARTNER') and val('ttyd64_partner_team_should_swap(1)') != 0 and val('ttyd64_partner_team_should_swap(0)') == 0 and hp() == 0)
        cmd('call ttyd64_mode_select_file(1)')
        flee_battle()
        check('team-natural-combat-flee-keeps-zero-health-world-owner',hp() == 0 and val('WorldPartnerID') == partner_id and val('gCurrentEncounter.battleOutcome') == val('OUTCOME_PLAYER_FLED'))
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_CANT_TOUCH'))
        for point in trace_points:
            point.delete()
    if 'recovery-hooks' in phases:
        baseline = os.environ.get('PARTNER_RECOVERY_BASELINE') == '1'
        compatible = (1,2,3,4,6,7,8,9)
        # Controlled current-partner/model and touch-state setup; execute the
        # real collectable callback, not a direct partner-heal API.
        for mode in (0,1):
            cmd(f'call ttyd64_mode_select_file({mode})')
            for pid in compatible:
                put('gPlayerData.curPartner',pid)
                put(f'gPlayerData.partners[{pid}].level',0)
                for before in (0,1,val(f'ttyd64_get_partner_max_hp({pid})')):
                    for other in compatible:
                        cmd(f'call ttyd64_set_partner_hp({other},2)')
                    cmd(f'call ttyd64_set_partner_hp({pid},{before})')
                    put('gPlayerData.curHP',val('gPlayerData.curMaxHP'))
                    item = val('make_item_entity_nodelay(ITEM_HEART, 5000.0, 15.0, 150.0, ITEM_SPAWN_MODE_FIXED_SPAWN_ALWAYS, 0)')
                    assert item >= 0
                    put(f'WorldItemEntities[{item}]->pickupDelay',0)
                    put(f'WorldItemEntities[{item}]->state',val('ITEM_PHYSICS_STATE_TOUCH'))
                    cmd(f'call update_item_entity_collectable(WorldItemEntities[{item}])')
                    expected = min(before + int(mode == 1 and not baseline),val(f'ttyd64_get_partner_max_hp({pid})'))
                    check(f'heart-mode-{mode}-partner-{pid}-from-{before}',val(f'ttyd64_get_partner_hp({pid})') == expected and all(val(f'ttyd64_get_partner_hp({other})') == 2 for other in compatible if other != pid) and val('gPlayerData.curHP') == val('gPlayerData.curMaxHP'))
        put('gPlayerData.curPartner',partner_id)
        enter_road_battle()
        # Actor creation/contact uses native keyboard route; only the reward
        # callback boundary/timer and wounds are injected. This is NOT proof of
        # earning a level-up or navigating its stat-choice UI.
        old_substate = val('gBattleSubState')
        old_timer = val('CelebrateSubstateTime')
        for mode in (0,1):
            cmd(f'call ttyd64_mode_select_file({mode})')
            for rank in (0,1,2):
                put('gPlayerData.partners[$slicePartner].level',rank)
                maximum = val('ttyd64_get_partner_max_hp($slicePartner)')
                for before in (0,1,maximum):
                    for other in compatible:
                        cmd(f'call ttyd64_set_partner_hp({other},2)')
                    cmd(f'call ttyd64_set_partner_hp($slicePartner,{before})')
                    put('gPlayerData.curHP',1)
                    put('gPlayerData.curFP',0)
                    put('gBattleSubState',val('BTL_SUBSTATE_LEVEL_UP_CREATE_HUD'))
                    put('CelebrateSubstateTime',18)
                    cmd('call btl_state_update_celebration()')
                    expected = maximum if mode == 1 and not baseline else before
                    check(f'level-up-mode-{mode}-rank-{rank}-from-{before}',hp() == expected and all(val(f'ttyd64_get_partner_hp({other})') == 2 for other in compatible if other != partner_id) and val('gPlayerData.curHP') == val('gPlayerData.curMaxHP') and val('gPlayerData.curFP') == val('gPlayerData.curMaxFP'))
                    if mode == 1:
                        check(f'level-up-bound-actor-rank-{rank}-from-{before}',val('gBattleStatus.partnerActor->curHP') == expected and val('gBattleStatus.partnerActor->maxHP') == maximum)
        put('gBattleSubState',old_substate)
        put('CelebrateSubstateTime',old_timer)
        cmd('call ttyd64_mode_select_file(1)')
        team_trace.append({'event':'recovery-hook-matrix','baseline_expected_missing_hooks':baseline,'world_heart_partners':list(compatible),'native_actor_partner':partner_id,'method':'Injected current partner/rank/wounds and item touch; native collectable callback. Real keyboard battle entry; injected reward substate/timer and native celebration callback, not a naturally earned level-up. No forced guard/RNG.'})
    for victory_phase in [phase for phase in phases if phase in ('victory', 'victory-dead', 'level-up')]:
        level_up = victory_phase == 'level-up'
        inactive = (1,2,3,4,6,7,8,9)
        if level_up:
            cmd('call ttyd64_mode_select_file(1)')
            for pid in inactive:
                cmd(f'call ttyd64_set_partner_hp({pid},2)')
            cmd('call ttyd64_set_partner_hp($slicePartner,0)')
            put('gPlayerData.curHP',val('gPlayerData.curMaxHP'))
            # Explicit disposable entity grant; native physics/contact and
            # keyboard walking, with no forced touch or direct collection call.
            item = val('make_item_entity_nodelay(ITEM_HEART, gPlayerStatus.pos.x + 45.0f, gPlayerStatus.pos.y + 15.0f, gPlayerStatus.pos.z, ITEM_SPAWN_MODE_FIXED_SPAWN_ALWAYS, 0)')
            assert item >= 0
            for _ in range(10):
                if val(f'WorldItemEntities[{item}]') == 0:
                    break
                key('d',16)
            check('keyboard-world-heart-revives-only-current-partner',hp() == 1 and val(f'WorldItemEntities[{item}]') == 0 and all(val(f'ttyd64_get_partner_hp({pid})') == 2 for pid in inactive if pid != partner_id) and val('gPlayerData.curHP') == val('gPlayerData.curMaxHP'))
        enter_road_battle()
        # Seed a non-level-up reward boundary; attack/HP/outcome/rewards are
        # observed, never forced. Basic attacks intentionally omit timed A.
        put('gPlayerData.starPoints',99 if level_up else 0)
        before_level = val('gPlayerData.level')
        inactive_hp = {pid:val(f'ttyd64_get_partner_hp({pid})') for pid in inactive if pid != partner_id}
        before_wins = val('gPlayerData.battlesWon')
        before_items = item_count()
        key('z')
        wait('gBattleState == BATTLE_STATE_PARTNER_MENU && gBattleSubState == 3 && BattleMenuState == BTL_MENU_STATE_CHOOSING')
        dead_victory = victory_phase == 'victory-dead'
        if dead_victory:
            if partner_id == 2:
                for i in range(24):
                    if val(f'gBattleStatus.enemyActors[{i}]'):
                        put(f'gBattleStatus.enemyActors[{i}]->attackBoost',1)
                team_trace.append({'event':'controlled-kooper-enemy-attack-boost','amount':1})
            assert val('ttyd64_set_partner_hp($slicePartner,1)') == 1
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
        # The capture advances native frames and can span world return. Block
        # subsequent contacts before it, so a new encounter cannot replace the
        # completed victory while observing rewards/input. The battle still ends natively.
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_CANT_TOUCH'))
        capture(victory_phase + '-celebration')
        if level_up:
            wait('gBattleState == BATTLE_STATE_CELEBRATION && gBattleSubState == BTL_SUBSTATE_LEVEL_UP_CHOOSE',2400)
            check('earned-level-up-restores-current-partner-and-bound-actor',hp() == val('ttyd64_get_partner_max_hp($slicePartner)') and val('gBattleStatus.partnerActor->curHP') == hp() and val('gPlayerData.level') == before_level + 1 and all(val(f'ttyd64_get_partner_hp({pid})') == amount for pid,amount in inactive_hp.items()))
            key('x',8)
        wait('gGameStatusPtr->context == CONTEXT_WORLD && gEncounterState == ENCOUNTER_STATE_NEUTRAL && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)',2400)
        reward = victory_trace[0]['reward']
        expected_points = reward - 1 if level_up else reward
        check('victory-native-star-points-and-win-count-awarded-once',reward > 0 and val('gPlayerData.starPoints') == expected_points and val('gPlayerData.battlesWon') == before_wins + 1 and val('gCurrentEncounter.battleOutcome') == val('OUTCOME_PLAYER_WON'))
        remaining_hp = hp()
        check('victory-world-owns-wounded-health-and-unused-items',(remaining_hp == 0 if dead_victory else remaining_hp > 0) and val('WorldPartnerID') == partner_id and val('ttyd64_partner_hp_display()') == remaining_hp and item_count() == before_items)
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
            assert val(f'ttyd64_set_partner_hp($slicePartner,{disturbed_hp})') == disturbed_hp
            put('gPlayerData.starPoints',0)
            assert val('fio_load_game(3)') == 1
            check('victory-native-save-load-preserves-reward-and-health',hp() == remaining_hp and val('gPlayerData.starPoints') == expected_points and val('gPlayerData.battlesWon') == before_wins + 1)
        finally:
            save_point.delete()
            save.write_bytes(original)
        put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_CANT_TOUCH'))
        cmd('call open_status_bar_quickly()')
        tick(30)
        capture(victory_phase + '-world-return')
        victory_point.delete()
        team_trace.extend([{'event':victory_phase,'attacks':attacks,'saves':saves,**victory_trace[0]}])
        cmd('call ttyd64_mode_select_file(0)')
    assert save.read_bytes() == original
    Path(required_env('PARTNER_SLICE_RESULT')).write_text(json.dumps({'partner_id':partner_id,'phases_run':phases,'checks_passed':len(checks),'checks':checks,'native_states':states,'captures':captures,'team_trace':team_trace,
        'limits':'Family phase uses real kmr_06 encounters and keyboard menus with controlled setup/refills; see family-method trace. Dip phase injects owned/equipped badges, budget, stock, wounds and FP; native pause-equip API followed by real keyboard battle menus, cancel, recipients, item scripts/payment and turn scheduling. No forced menu/guard/RNG returns in dip phase; common startup/file-select return is forced. BP phase injects an over-budget loadout and observes native rendering after keyboard pause input. Recovery-hook matrix injects identity/rank/wounds, item touch and reward substate/timer and calls native callbacks, not a naturally earned level-up. Level-up phase grants a disposable heart and initial99 star points; pickup, encounter, attacks, native rewards/level-up/stat-choice/world return/save use real keyboard. Kooper team/dead-victory enemies use a controlled +1 attack boost to exercise lethal hits through DEF1; their AI/menu/turn/death logic is native. Ground-contracts controls item/contact entry points and initial HP/inventory; Kooper countdown/recovery advances through native keyboard rounds. Only listed phases run. Victory phases use keyboard attacks, native enemy defeat/rewards/world return and keyboard Save Block hit/prompt; map/position, initial HP/items/progression and non-level-up boundary are controlled. Reload calls native FIO, not a title restart. Native keyboard pause and/or world item menu/script phases as listed. Recruitment, inventory, ranks and wounds are controlled; no all-partner UI, source artwork/choreography parity or campaign claim. Battle phase controls map/progression, inventory, health and action-command unlock; contact, swap menus, flee outcome, recovery menus and native lifecycle use real keyboard input.'},indent=2)+'\n')
    print('PARTNER_SLICE_PHASES_PASSED=' + ','.join(phases) + ':' + str(len(checks)))
    cmd('kill')


try:
    run()
except Exception:
    import traceback
    traceback.print_exc()
    print(cmd('bt 12'))
    cmd('quit 1')
