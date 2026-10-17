"""Guarded Goombario combat acceptance; native scripts advance only by continue.

Requires a copy of the existing FP Drain fixture save in this exact runtime.
Never enables the prototype outside this disposable battle process.
"""
import json
import os
from pathlib import Path
import gdb
import subprocess
import time


def cmd(text):
    return gdb.execute(text, to_string=True)


def val(text):
    return int(gdb.parse_and_eval(text))


def put(text, value):
    cmd(f"set variable {text} = {value}")


def until(where):
    point = gdb.Breakpoint(where, temporary=True, internal=True)
    point.silent = True
    cmd("continue")
    stopped = [t for t in gdb.selected_inferior().threads() if t.is_stopped()]
    if len(stopped) == 1:
        stopped[0].switch()
    assert gdb.selected_frame().name() == where, f'Unexpected stop before {where}'


def run():
    root = Path('/workspace/.paperboat-setup/partner-combat')
    runtime = Path(os.environ['SHIP_HOME']).resolve()
    assert runtime == root / 'runtime'
    save = runtime / 'saves/file3.json'
    original = save.read_bytes()
    assert original == Path('/workspace/.paperboat-setup/fp-drain/runtime/saves/file3.json').read_bytes()
    visual = os.environ.get('GOOMBARIO_VISUAL', '0') == '1'
    lethal = os.environ.get('GOOMBARIO_LETHAL', '0') == '1'
    if visual:
        cmd('set non-stop on')
    captures = []
    def capture(name):
        if not visual:
            return
        assert len([t for t in gdb.selected_inferior().threads() if t.is_stopped()]) == 1
        window = subprocess.check_output(['xdotool', 'search', '--onlyvisible', '--pid', str(gdb.selected_inferior().pid)], text=True).splitlines()[0]
        subprocess.run(['xdotool', 'windowraise', window], check=True)
        time.sleep(1)
        subprocess.run(['import', '-window', 'root', str(root / (name + '.png'))], check=True)
        captures.append(name)
    # Provenance guard: a copy of the disposable FP Drain writer, never a user slot.
    data = json.loads(original)
    assert data['player']['badges'].count(val('ITEM_FP_DRAIN')) == 3
    checks, observations, states = [], [], []
    def check(name, condition):
        assert condition, name
        checks.append(name)
        if val('gGameStatusPtr->context') == val('CONTEXT_BATTLE') and val('gBattleStatus.partnerActor'):
            states.append({'check':name, 'partner':val('gPlayerData.curPartner'), 'model_hp':val('ttyd64_get_partner_hp(PARTNER_GOOMBARIO)'),
                           'actor_hp':val('gBattleStatus.partnerActor->curHP'), 'ko':val('gBattleStatus.partnerActor->koStatus'),
                           'rot_x':float(gdb.parse_and_eval('gBattleStatus.partnerActor->rot.x')), 'state':val('gBattleState')})
        print('GOOMBARIO_CHECK=' + name)
    actor = 'gBattleStatus.partnerActor'
    hp = lambda: val('ttyd64_get_partner_hp(PARTNER_GOOMBARIO)')
    def health(amount):
        assert val(f'ttyd64_set_partner_hp(PARTNER_GOOMBARIO, {amount})') == amount
    def tick():
        until('btl_update')
    def drain(limit=420, revival=False):
        item_frames = 0
        protection_checked = False
        for frame in range(limit):
            tick()
            if revival and not protection_checked and hp() > 0 and val('DeathScriptID') != 0 and val('does_script_exist(DeathScriptID)'):
                protected_id = val('DeathScriptID')
                cmd('call dispatch_event_partner(EVENT_HIT)')
                check('revival-positive-hp-script-protected', val(f'{actor}->handleEventScriptID') == protected_id)
                protection_checked = True
            if revival and visual:
                if val('ShroudTintAmt') >= 216 and any(val(f'BattleItemEntities[{i}]') != 0 for i in range(256)):
                    item_frames += 1
                if item_frames >= 4 and 'revival-shroud' not in captures:
                    capture('revival-shroud')
                if hp() > 0 and 'revival-recover' not in captures and any(val(f'gEffectInstances[{i}] != 0 && gEffectInstances[{i}]->effectID == 0x40 && gEffectInstances[{i}]->data.recover->lifetime >= 10') for i in range(96)):
                    capture('revival-recover')
            if val(f'{actor}->handleEventScriptID') == 0 or not val(f'does_script_exist({actor}->handleEventScriptID)'):
                if hp() > 0 or val(f'ttyd64_partner_combat_death_handled({actor})'):
                    return frame
        raise AssertionError('event/defeat did not complete within frame budget')
    for setting in ('pagination off', 'confirm off', 'print thread-events off'):
        cmd('set ' + setting)
    gdb.Breakpoint('state_step_startup', temporary=True, internal=True)
    cmd('run')
    if visual:
        [t for t in gdb.selected_inferior().threads() if t.is_stopped()][0].switch()
    put('gPortResetToTitleScreen', 1)
    until('state_step_title_screen')
    check('default-off-at-title', val('gTtyd64PartnerHPPrototypeEnabled') == 0)
    put('TitleScreenNextState', val('NEXT_STATE_FILE_SELECT'))
    put('gGameStatusPtr->startupState', val('TITLE_STATE_EXIT'))
    put('gGameStatusPtr->titleScreenTimer', 0)
    until('filemenu_update')
    assert val('fio_load_game(3)') == 1
    put('filemenu_menus[0]->state', val('FM_MAIN_SELECT_FILE'))
    put('filemenu_menus[0]->selected', 0)
    put('filemenu_currentMenu', val('FILE_MENU_MAIN'))
    cmd('call set_game_mode(GAME_MODE_END_FILE_SELECT)')
    cmd('return')
    until('state_step_world')
    cmd('call load_demo_battle(4)')
    cmd('return')
    until('load_partner_actor')
    # Load before creation, then explicitly establish the controlled context.
    assert val('fio_load_game(3)') == 1
    cmd('call evt_set_variable((Evt*)0, GF_Tutorial_SwapTurnOrder, 1)')
    put('gPlayerData.curPartner', val('PARTNER_GOOMBARIO'))
    put('gPlayerData.partners[1].enabled', 1)
    put('gPlayerData.partners[1].level', 0)
    cmd('call ttyd64_reset_partner_hp(1)')
    for i in range(64):
        put(f'gPlayerData.equippedBadges[{i}]', 0)
    for i in range(10):
        put(f'gPlayerData.invItems[{i}]', 0)
    put('gPlayerData.curHP', 30)
    put('gPlayerData.curMaxHP', 30)
    until('calc_enemy_test_target')
    cmd('set variable gGameStatusPtr->demoBattleFlags &= ~DEMO_BTL_FLAG_ENABLED')
    put('gTtyd64PartnerHPPrototypeEnabled', 1)
    cmd(f'call ttyd64_partner_hp_bind_actor({actor})')
    check('native-created-goombario-binds-in-controlled-context', val(f'ttyd64_partner_combat_active({actor})') == 1 and hp() == 10 and val(f'{actor}->curHP') == 10)
    # Redirect a real enemy script's test and damage target, preserving execution.
    put('gBattleStatus.curTargetID', val('ACTOR_PARTNER'))
    put('gBattleStatus.curTargetPart', 1)
    put('actor->targetActorID', val('ACTOR_PARTNER'))
    put('actor->targetPartID', 1)
    until('calc_enemy_damage_target')
    check('enemy-test-does-not-install-sentinel', hp() == 10 and val(f'{actor}->curHP') == 10)
    cmd('set $enemy = attacker')
    put('gBattleStatus.curTargetID', val('ACTOR_PARTNER'))
    put('gBattleStatus.curTargetPart', 1)
    put('gBattleStatus.curAttackDamage', 12 if lethal else 3)
    cmd('set variable gBattleStatus.curAttackElement = DAMAGE_TYPE_UNBLOCKABLE')
    cmd('set variable gBattleStatus.flags1 &= ~BS_FLAGS1_TUTORIAL_BATTLE')
    cmd('set variable gBattleStatus.flags1 |= BS_FLAGS1_TRIGGER_EVENTS')
    cmd('finish')
    check('real-enemy-lethal-clamps-zero' if lethal else 'real-enemy-hit-persists-10-to-7', hp() == (0 if lethal else 7) and val(f'{actor}->curHP') == hp() and val('gBattleStatus.lastAttackDamage') == (12 if lethal else 3))
    check('enemy-hit-no-ko-turns', val(f'{actor}->koStatus') == 0 and val(f'{actor}->koDuration') == 0)
    drain()
    if lethal:
        check('real-lethal-native-defeat-completes', val(f'ttyd64_partner_combat_death_handled({actor})') != 0 and float(gdb.parse_and_eval(f'{actor}->rot.x')) == 86)
        for _ in range(240):
            tick()
            if val('gBattleState') == val('BATTLE_STATE_PLAYER_MENU'):
                break
        check('native-turn-reaches-mario-menu-with-dead-partner', val('gBattleState') == val('BATTLE_STATE_PLAYER_MENU') and val('btl_partner_can_act()') == 0)
        for _ in range(3):
            tick()
        capture('enemy-lethal-death')
        # Fixture reset only; general SetEnemyHP healing presentation is unported.
        health(10)
        put(f'{actor}->rot.x', 0)
        cmd(f'set variable {actor}->flags |= ACTOR_FLAG_USING_IDLE_ANIM')
        cmd('set variable gBattleStatus.flags2 &= ~BS_FLAGS2_PARTNER_TURN_USED')

    def target():
        put('gBattleStatus.curTargetID', val('ACTOR_PARTNER'))
        put('gBattleStatus.curTargetPart', 1)
        put('gBattleStatus.curAttackStatus', 0)
        put('gBattleStatus.curAttackElement', val('DAMAGE_TYPE_UNBLOCKABLE'))
        cmd('set variable gBattleStatus.flags1 |= BS_FLAGS1_TRIGGER_EVENTS')
        cmd('set variable gBattleStatus.flags1 &= ~BS_FLAGS1_TUTORIAL_BATTLE')
    def enemy_case(name, damage, expected, flags=0, immune=False):
        health(10)
        target()
        put('gBattleStatus.curAttackDamage', damage)
        cmd(f'set variable {actor}->flags |= {flags}')
        if immune:
            cmd(f'set variable {actor}->partsTable->flags |= ACTOR_PART_FLAG_DAMAGE_IMMUNE')
        result = val('calc_enemy_damage_target($enemy)')
        check(name, hp() == expected and val(f'{actor}->curHP') == expected and val(f'{actor}->koStatus') == 0)
        observations.append({'case': name, 'before':10, 'after':hp(), 'result':result})
        cmd(f'set variable {actor}->flags &= ~{flags}')
        cmd(f'set variable {actor}->partsTable->flags &= ~ACTOR_PART_FLAG_DAMAGE_IMMUNE')
        drain()
    enemy_case('enemy-zero-damage', 0, 10)
    enemy_case('enemy-immune', 3, 10, immune=True)
    enemy_case('enemy-suppressed-application', 3, 10, val('ACTOR_FLAG_NO_DMG_APPLY'))
    # Guard branch is deterministic; input timing itself is not under test.
    health(10)
    target()
    put('gBattleStatus.curAttackElement', 0)
    put('gBattleStatus.curAttackDamage', 3)
    class ForceBlock(gdb.Breakpoint):
        def stop(self):
            cmd('return 1')
            return False
    block = ForceBlock('check_block_input', internal=True)
    val('calc_enemy_damage_target($enemy)')
    block.delete()
    check('guard-positive-damage-minus-one', hp() == 8 and val('gBattleStatus.lastAttackDamage') == 2 and val('gBattleStatus.flags1 & BS_FLAGS1_ATK_BLOCKED') != 0)
    drain()
    health(10)
    val('dispatch_damage_event_partner(3, EVENT_HIT, 0)')
    check('contact-damage-persists-no-ko', hp() == 7 and val(f'{actor}->curHP') == 7 and val(f'{actor}->koStatus') == 0)
    drain()
    health(10)
    val('dispatch_damage_event_partner(-3, EVENT_HIT, 0)')
    check('negative-contact-does-not-heal-or-carry', hp() == 10 and val(f'{actor}->hpChangeCounter') == 0)
    drain()
    # Use the compiled partner attack route's electrified contact/backfire branch.
    health(10)
    put('gBattleStatus.curTargetID', val('$enemy->actorID'))
    put('gBattleStatus.curTargetPart', 1)
    put('gBattleStatus.curAttackElement', val('DAMAGE_TYPE_NO_CONTACT'))
    put('gBattleStatus.curAttackDamage', 0)
    put('$enemy->staticStatus', val('STATUS_KEY_STATIC'))
    put('gBattleStatus.curAttackEventSuppression', 0)
    # NO_CONTACT suppresses shock contact, then ordinary contact backfires.
    check('no-contact-suppresses-backfire', val('calc_partner_damage_enemy()') != val('HIT_RESULT_BACKFIRE') and hp() == 10)
    put('gBattleStatus.curAttackElement', 0)
    check('native-shock-backfire-persists-no-ko', val('calc_partner_damage_enemy()') == val('HIT_RESULT_BACKFIRE') and hp() == 9 and val(f'{actor}->koStatus') == 0)
    put('$enemy->staticStatus', 0)
    drain()
    health(10)
    target()
    put('gBattleStatus.curAttackDamage', 3)
    val('calc_item_damage_enemy()')
    check('item-damage-persists', hp() == 7 and val(f'{actor}->curHP') == 7)
    drain()
    for name, damage, immunity, no_damage in (('zero',0,False,False), ('immune',3,True,False), ('suppressed-part',3,False,True)):
        health(10)
        target()
        put('gBattleStatus.curAttackDamage', damage)
        if immunity:
            cmd(f'set variable {actor}->partsTable->flags |= ACTOR_PART_FLAG_DAMAGE_IMMUNE')
        if no_damage:
            cmd(f'set variable {actor}->partsTable->targetFlags |= ACTOR_PART_TARGET_NO_DAMAGE')
        val('calc_item_damage_enemy()')
        check('item-' + name + '-keeps-hp', hp() == 10 and val(f'{actor}->curHP') == 10)
        cmd(f'set variable {actor}->partsTable->flags &= ~ACTOR_PART_FLAG_DAMAGE_IMMUNE')
        cmd(f'set variable {actor}->partsTable->targetFlags &= ~ACTOR_PART_TARGET_NO_DAMAGE')
        drain()
    health(7)
    # Native script-facing health getters/setters operate on a synthetic Evt only.
    cmd('set $api = (Evt*)calloc(1, sizeof(Evt))')
    cmd('set $args = (Bytecode*)calloc(2, sizeof(Bytecode))')
    assert val('$api') and val('$args')
    cmd('set $api->ptrReadPos = $args')
    put('$args[0]', val('ACTOR_PARTNER'))
    put('$args[1]', -30000000)  # LocalVar(0), script_api/macros.h
    val('GetActorHP($api, 1)')
    check('script-get-actor-hp-is-model-hp', val('$api->varTable[0]') == 7)
    put('$args[1]', -4)
    val('SetEnemyHP($api, 1)')
    check('script-set-hp-clamps-negative', hp() == 0 and val(f'{actor}->curHP') == 0)
    put('$args[1]', 99)
    val('SetEnemyHP($api, 1)')
    check('script-set-hp-caps-and-persists', hp() == 10 and val(f'{actor}->curHP') == 10)
    cmd('call (void)free($args)')
    cmd('call (void)free($api)')
    # Lethal native contact dispatch; the interpreter owns collapse and revival.
    val(f'inflict_status({actor}, STATUS_KEY_POISON, 3)')
    put(f'{actor}->attackBoost', 2)
    put(f'{actor}->defenseBoost', 3)
    put(f'{actor}->isGlowing', 4)
    cmd('set variable gBattleStatus.flags1 |= BS_FLAGS1_GOOMBARIO_CHARGED')
    health(2)
    val('dispatch_damage_event_partner(5, EVENT_HIT, 0)')
    check('lethal-clamps-zero-and-tracks-script', hp() == 0 and val(f'{actor}->curHP') == 0 and val('DeathScriptID') != 0)
    death_id = val('DeathScriptID')
    cmd('call dispatch_event_partner_continue_turn(EVENT_HIT)')
    target()
    val('calc_enemy_damage_target($enemy)')
    val('calc_item_damage_enemy()')
    val('dispatch_damage_event_partner(9, EVENT_HIT, 0)')
    check('active-death-rejects-additional-damage', hp() == 0 and val(f'{actor}->handleEventScriptID') == death_id)
    check('death-script-protected-from-hit-replacement', val(f'{actor}->handleEventScriptID') == death_id)
    frames = drain()
    capture('death-no-shroom')
    check('death-finished-flat-idle-disabled', float(gdb.parse_and_eval(f'{actor}->rot.x')) == 86 and val(f'{actor}->flags & ACTOR_FLAG_USING_IDLE_ANIM') == 0)
    check('death-clears-status-boosts-and-charge', val(f'{actor}->debuff') == 0 and val(f'{actor}->debuffDuration') == 0 and val(f'{actor}->attackBoost') == 0 and val(f'{actor}->defenseBoost') == 0 and val(f'{actor}->isGlowing') == 0 and val('gBattleStatus.flags1 & BS_FLAGS1_GOOMBARIO_CHARGED') == 0)
    check('death-no-repeat-and-mario-can-act', val('ttyd64_partner_combat_check_defeat()') == 0 and val('btl_player_can_act()') != 0)
    cmd('set variable gBattleStatus.flags2 &= ~BS_FLAGS2_PARTNER_TURN_USED')
    for status in ('STATUS_KEY_NORMAL','STATUS_KEY_POISON','STATUS_KEY_SHRINK'):
        put(f'{actor}->debuff', val(status))
        check('dead-turn-rejected-' + status, val('btl_partner_can_act()') == 0)
    put(f'{actor}->debuff', 0)
    target()
    check('dead-enemy-test-and-hit-rejected', val('calc_enemy_test_target($enemy)') == val('HIT_RESULT_MISS') and val('calc_enemy_damage_target($enemy)') == val('HIT_RESULT_MISS'))
    check('dead-item-hit-rejected', val('calc_item_damage_enemy()') == val('HIT_RESULT_MISS'))
    val('dispatch_damage_event_partner(9, EVENT_HIT, 0)')
    check('dead-contact-rejected-no-repeat', hp() == 0 and val(f'{actor}->handleEventScriptID') == death_id)
    # Execute complete native put-away/bring-out scripts, never pump evt_update.
    def swap(partner):
        put('gBattleStatus.lastSelectedPartner', partner)
        cmd('call btl_set_state(BATTLE_STATE_CHANGE_PARTNER)')
        for _ in range(240):
            tick()
            if val('gPlayerData.curPartner') == partner and val('gBattleState') != val('BATTLE_STATE_CHANGE_PARTNER'):
                return
        raise AssertionError('native swap exceeded frame budget')
    swap(2)
    check('full-swap-away-preserves-dead-model', hp() == 0 and val('gPlayerData.curPartner') == 2)
    swap(1)
    check('full-swap-back-restores-dead-pose-and-turn-gate', hp() == 0 and val(f'{actor}->curHP') == 0 and float(gdb.parse_and_eval(f'{actor}->rot.x')) == 86 and val(f'{actor}->flags & ACTOR_FLAG_USING_IDLE_ANIM') == 0 and val('btl_partner_can_act()') == 0)
    capture('dead-swap-back')
    try:
        cmd('call fio_save_game(3)')
        assert val('fio_load_game(3)') == 1
        check('dead-native-save-load', hp() == 0)
    finally:
        save.write_bytes(original)
    # A second death with two mushrooms; rank 1 also proves exact ten below max.
    put('gPlayerData.partners[1].level', 1)
    health(2)
    for i in range(10):
        put(f'gPlayerData.invItems[{i}]', 0)
    assert val('add_item(ITEM_LIFE_SHROOM)') >= 0
    assert val('add_item(ITEM_LIFE_SHROOM)') >= 0
    put(f'{actor}->rot.x', 0)
    val('dispatch_damage_event_partner(5, EVENT_HIT, 0)')
    frames_revive = drain(revival=True)
    count = sum(val(f'gPlayerData.invItems[{i}]') == val('ITEM_LIFE_SHROOM') for i in range(10))
    check('life-shroom-consumes-exactly-one-heals-ten', count == 1 and hp() == 10 and val(f'{actor}->curHP') == 10 and val(f'{actor}->maxHP') == 20)
    check('revival-restores-pose-idle-and-turn', float(gdb.parse_and_eval(f'{actor}->rot.x')) == 0 and val(f'{actor}->flags & ACTOR_FLAG_USING_IDLE_ANIM') != 0 and val('btl_partner_can_act()') != 0)
    capture('revival-complete')
    print('GOOMBARIO_CLEANUP=' + json.dumps({'shroud':val('ShroudTintAmt'), 'remaining_items':sum(val(f'BattleItemEntities[{i}]') != 0 for i in range(256))}))
    check('revival-shroud-and-item-cleaned', val('ShroudTintAmt') == 0 and all(val(f'BattleItemEntities[{i}]') == 0 for i in range(256)))
    check('revival-energy-effect-freed', not any(val(f'gEffectInstances[{i}] != 0 && gEffectInstances[{i}]->effectID == 0x6B') for i in range(96)))  # effect_defs.h
    check('revival-defeat-wait-finishes', val('ttyd64_partner_combat_check_defeat()') == 0)
    # Rank-zero repeat exercises the cap and secondary dispatcher's tracking.
    put('gPlayerData.partners[1].level', 0)
    health(1)
    health(0)
    cmd('call dispatch_event_partner_continue_turn(EVENT_DEATH)')
    check('continue-turn-death-is-tracked', val('DeathScriptID') == val(f'{actor}->handleEventScriptID') and val('DeathScriptID') != 0)
    drain()
    check('rank-zero-revival-caps-at-ten', hp() == 10 and val(f'{actor}->maxHP') == 10 and val('find_item(ITEM_LIFE_SHROOM)') == -1)
    assert val('add_item(ITEM_LIFE_SHROOM)') >= 0
    check('living-partner-cannot-consume-again', val(f'ttyd64_partner_combat_use_life_shroom({actor})') == 0 and val('find_item(ITEM_LIFE_SHROOM)') >= 0)
    health(0)
    put('gPlayerData.curHP', 0)
    check('helper-rejects-mario-dead-without-consuming', val(f'ttyd64_partner_combat_use_life_shroom({actor})') == 0 and hp() == 0 and val('find_item(ITEM_LIFE_SHROOM)') >= 0)
    put('gPlayerData.curHP', 30)
    health(10)
    val('remove_item(ITEM_LIFE_SHROOM)')
    # Return turn must reach a native partner menu, not just a boolean getter.
    cmd('set variable gBattleStatus.flags2 &= ~(BS_FLAGS2_PARTNER_TURN_USED | BS_FLAGS2_PLAYER_TURN_USED)')
    cmd('set variable gBattleStatus.flags1 |= BS_FLAGS1_PARTNER_ACTING')
    cmd('call btl_set_state(BATTLE_STATE_PREPARE_MENU)')
    for _ in range(240):
        tick()
        if val('gBattleState') == val('BATTLE_STATE_PARTNER_MENU'):
            break
    check('revived-partner-reaches-native-menu', val('gBattleState') == val('BATTLE_STATE_PARTNER_MENU') and val('btl_partner_can_act()') != 0)
    # Off retains vanilla sentinel and KO behavior without writing model health.
    health(6)
    put('gTtyd64PartnerHPPrototypeEnabled', 0)
    target()
    check('prototype-off-test-keeps-native-sentinel', val('calc_enemy_test_target($enemy)') != val('HIT_RESULT_MISS') and val(f'{actor}->curHP') == 127 and hp() == 6)
    put('gBattleStatus.curAttackDamage', 3)
    val('calc_enemy_damage_target($enemy)')
    check('prototype-off-enemy-keeps-native-ko-and-model', val(f'{actor}->curHP') == 124 and hp() == 6 and val(f'{actor}->koStatus') == val('STATUS_KEY_KO'))
    put(f'{actor}->koStatus', 0)
    put(f'{actor}->koDuration', 0)
    val('dispatch_damage_event_partner(2, EVENT_HIT, 0)')
    check('prototype-off-contact-keeps-native-ko-and-model', val(f'{actor}->curHP') == 125 and hp() == 6 and val(f'{actor}->koStatus') == val('STATUS_KEY_KO') and val(f'{actor}->koDuration') == 2)
    report = {'checks_passed':len(checks), 'checks':checks, 'damage_cases':observations, 'native_states':states, 'death_frames':frames, 'revival_frames':frames_revive, 'real_enemy_lethal':lethal, 'captures':captures,
              'limitations':'Controlled native battle/API checks; guard forces block result. Visual validation recorded separately.'}
    Path(os.environ['GOOMBARIO_RESULT']).write_text(json.dumps(report, indent=2)+'\n')
    print('GOOMBARIO_PASSED=' + str(len(checks)))
    cmd('kill')

try:
    run()
except Exception:
    import traceback
    traceback.print_exc()
    cmd('quit 1')
