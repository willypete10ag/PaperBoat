"""Guarded partner HP across regular native battle cleanup/world restoration.

Uses a strict disposable save and existing world enemy/AI owner. Encounter entry
and exit outcome are controlled APIs; normal lifecycle runs, not demo loading.
BATTLE_RETURN_BASELINE=1 expects the preceding world-HUD restoration gap.
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
    root = Path('/workspace/.paperboat-setup/partner-battle-return')
    runtime = Path(os.environ['SHIP_HOME']).resolve()
    assert runtime == root / 'runtime'
    save = runtime / 'saves/file3.json'
    original = save.read_bytes()
    assert original == Path('/workspace/.paperboat-setup/fp-drain/runtime/saves/file3.json').read_bytes()
    baseline = os.environ.get('BATTLE_RETURN_BASELINE','0') == '1'
    checks, states, captures, capture_states = [], [], [], []
    def hp():
        return val('ttyd64_get_partner_hp(1)')
    def display():
        return val('ttyd64_partner_hp_display()')
    def check(name, condition):
        state = {'check':name,'context':val('gGameStatusPtr->context'),'hp':hp(),
                 'display_hp':display(),'world_owner':val('WorldPartnerID'),
                 'selected_partner':val('gPlayerData.curPartner'),'world_partner':val('wCurrentPartnerId'),
                 'encounter_state':val('gEncounterState'),'battle_state':val('gBattleState')}
        states.append(state)
        assert condition, name + ': ' + json.dumps(state)
        checks.append(name)
        print('BATTLE_RETURN_CHECK=' + name)
    def tick(n=1):
        for _ in range(n):
            until('step_game_mode')
    def wait(expression, budget=600):
        for _ in range(budget):
            if val(expression):
                return
            tick()
        raise AssertionError('Native frame budget: ' + expression)
    def capture(name):
        for _ in range(15):
            until('state_drawUI_world')
        cmd('call open_status_bar_quickly()')
        # World setup retracts the bar to -100; the default target is +18.
        # Ten +10 updates only reach zero. Wait for full extension, then let
        # the completed UI frame be submitted before taking a screenshot.
        for _ in range(120):
            until('state_drawUI_world')
            cmd('finish')
            if val('gStatusBar.drawPosY') >= val('port_status_bar_y()'):
                break
        else:
            raise AssertionError('Native world HUD did not fully extend')
        for _ in range(2):
            until('state_drawUI_world')
            cmd('finish')
        window = subprocess.check_output(['xdotool','search','--onlyvisible','--pid',str(gdb.selected_inferior().pid)],text=True).splitlines()[0]
        subprocess.run(['xdotool','windowraise',window],check=True)
        subprocess.run(['xdotool','windowfocus',window],check=True)
        time.sleep(0.5)
        assert int(subprocess.check_output(['xdotool','getwindowfocus'],text=True)) == int(window), 'Capture window lost focus'
        capture_state = {'capture':name,'hp':hp(),'display_hp':display(),
                         'world_owner':val('WorldPartnerID'),
                         'selected':val('gPlayerData.curPartner'),
                         'enabled':val('gPlayerData.partners[1].enabled'),
                         'hidden':val('gStatusBar.hidden'),'disabled':val('gStatusBar.disabled'),
                         'draw_y':val('gStatusBar.drawPosY'),'extended_y':val('port_status_bar_y()'),
                         'intro_part':val('gGameStatusPtr->introPart'),'demo_state':val('gGameStatusPtr->demoState')}
        capture_states.append(capture_state)
        print('BATTLE_RETURN_CAPTURE=' + json.dumps(capture_state))
        subprocess.run(['import','-window','root',str(root/(name+'.png'))],check=True)
        captures.append(name)
    def enter(expected):
        # Use an existing native enemy's event owner, not a demo/world reset.
        encounter = 'gCurrentEncounter.encounterList[0]'
        assert val(encounter) and val(encounter+'->enemy[0]')
        owner = encounter+'->enemy[0]'
        assert val(owner+'->aiScript')
        cmd(f'call start_battle({owner}->aiScript, -1)')
        wait('gGameStatusPtr->context == CONTEXT_BATTLE && gBattleStatus.partnerActor != 0 && gBattleState == BATTLE_STATE_PLAYER_MENU')
        check('native-entry-hp-' + str(expected),hp() == expected and val('gBattleStatus.partnerActor->curHP') == expected and val('ttyd64_partner_combat_active(gBattleStatus.partnerActor)') == 1)
        check('battle-entry-clears-world-ownership-' + str(expected),val('WorldPartnerID') == 0)
    def leave(expected):
        # Controlled outcome enters the actual end-battle fade/stage/cleanup
        # state, restores world heaps/NPCs/scripts and resumes encounter control.
        put('gCurrentEncounter.battleOutcome',val('OUTCOME_PLAYER_FLED'))
        cmd('call btl_set_state(BATTLE_STATE_END_BATTLE)')
        wait('gGameStatusPtr->context == CONTEXT_WORLD && gEncounterState == ENCOUNTER_STATE_NEUTRAL')
        check('native-return-keeps-hp-' + str(expected),hp() == expected and val('gPlayerData.curPartner') == 1 and val('wCurrentPartnerId') == 1)
        check('native-return-unlocks-input-' + str(expected),val('gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED') == 0)
        check('native-return-clears-combat-binding-' + str(expected),val('ttyd64_partner_combat_active(gBattleStatus.partnerActor)') == 0)
    def round_trip(expected):
        try:
            cmd('call fio_save_game(3)')
            changed = 1 if expected == 0 else 0
            assert val(f'ttyd64_set_partner_hp(1,{changed})') == changed
            assert val('fio_load_game(3)') == 1
            cmd('call sync_status_bar()')
            check('returned-hp-persists-native-fio-' + str(expected),hp() == expected and display() == expected)
        finally:
            save.write_bytes(original)
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
    for name, amount in (('areaID',0),('mapID',4),('entryID',1)):
        put('gCurrentSaveFile.'+name,amount)
    put('gCurrentSaveFile.globalBytes[0]',val('STORY_CH1_DEFEATED_KOOPA_BROS'))
    put('filemenu_menus[0]->state',val('FM_MAIN_SELECT_FILE'))
    put('filemenu_menus[0]->selected',0)
    put('filemenu_currentMenu',val('FILE_MENU_MAIN'))
    cmd('call set_game_mode(GAME_MODE_END_FILE_SELECT)')
    cmd('return')
    until('state_step_world')
    put('gGameStatusPtr->debugEnemyContact',val('DEBUG_CONTACT_CANT_TOUCH'))
    tick(100)
    for name, amount in (('curHP',30),('curMaxHP',30)):
        put('gPlayerData.'+name,amount)
    put('gPlayerData.partners[1].enabled',1)
    put('gPlayerData.partners[1].level',0)
    for i in range(64):
        put(f'gPlayerData.equippedBadges[{i}]',0)
    for i in range(10):
        put(f'gPlayerData.invItems[{i}]',0)
    cmd('call evt_set_variable((Evt*)0, GF_Tutorial_SwapTurnOrder, 1)')
    assert val('ttyd64_set_partner_hp(1,6)') == 6
    put('gTtyd64PartnerHPPrototypeEnabled',1)
    cmd('call switch_to_partner(1)')
    tick(100)
    check('native-world-goombario-ready',val('wCurrentPartnerId') == 1 and display() == 6)
    capture('battle-return-world-before')
    enter(6)
    assert val('ttyd64_set_partner_hp(1,3)') == 3
    leave(3)
    if baseline:
        check('baseline-reused-world-npc-loses-row',display() == -1 and val('WorldPartnerID') == 0)
        capture('battle-return-baseline-missing')
    else:
        check('wounded-world-row-restored',display() == 3 and val('WorldPartnerID') == 1)
        capture('battle-return-wounded')
        round_trip(3)
        enter(3)
        assert val('ttyd64_set_partner_hp(1,0)') == 0
        cmd('call btl_partner_can_act()')
        check('zero-battle-hp-rejects-turn',val('btl_partner_can_act()') == 0 and val('gBattleStatus.partnerActor->curHP') == 0)
        leave(0)
        check('zero-world-row-restored',hp() == 0 and display() == 0)
        capture('battle-return-zero')
        round_trip(0)
        enter(0)
        check('zero-reentry-rejects-turn-and-sentinel',val('btl_partner_can_act()') == 0 and val('gBattleStatus.partnerActor->curHP') == 0)
        leave(0)
        check('repeated-zero-return-keeps-world-row',display() == 0)
        put('gTtyd64PartnerHPPrototypeEnabled',0)
        check('prototype-off-hides-returned-row',display() == -1 and hp() == 0)
        capture('battle-return-prototype-off')
        owner = 'gCurrentEncounter.encounterList[0]->enemy[0]'
        cmd(f'call start_battle({owner}->aiScript, -1)')
        wait('gGameStatusPtr->context == CONTEXT_BATTLE && gBattleStatus.partnerActor != 0 && gBattleState == BATTLE_STATE_PLAYER_MENU')
        check('prototype-off-native-entry-keeps-blueprint-hp',val('gBattleStatus.partnerActor->curHP') == 99 and hp() == 0)
        check('prototype-off-native-entry-has-no-hp-binding',val('ttyd64_partner_combat_active(gBattleStatus.partnerActor)') == 0 and display() == -1)
        check('prototype-off-native-partner-can-act',val('btl_partner_can_act()') != 0)
        leave(0)
        check('prototype-off-full-return-preserves-model-and-hides-row',hp() == 0 and display() == -1)
    Path(os.environ['BATTLE_RETURN_RESULT']).write_text(json.dumps({
        'baseline':baseline,'checks_passed':len(checks),'checks':checks,'native_states':states,'captures':captures,'capture_states':capture_states,
        'limits':'Regular native encounter and world backup/restore. Existing enemy AI owner supplies StartBattle; HP wounds and OUTCOME_PLAYER_FLED/end-battle state are controlled. Does not play victory/run-away input or prove escape timing/choreography.'},indent=2)+'\n')
    print('BATTLE_RETURN_PASSED=' + str(len(checks)))
    cmd('kill')

try:
    run()
except Exception:
    import traceback
    traceback.print_exc()
    cmd('quit 1')
