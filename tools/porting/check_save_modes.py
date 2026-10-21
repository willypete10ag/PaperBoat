#!/usr/bin/env python3
"""Shared save-mode acceptance. Creation/continuation use real keyboard only.
Restart/legacy then compare Heart Blocks with explicitly injected setup.

Lifecycle uses native CLI setup, explicit harmless JSON probes/native I/O APIs,
then injected route/1 HP/empty items with real encounter/Do Nothing/native death,
game-over/title/keyboard continue. No forced guard, RNG or reset/game-over API.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone


def utc():
    return datetime.now(timezone.utc).isoformat()


def observe():
    import gdb
    scenario = os.environ['SAVE_MODE_SCENARIO']
    result = dict(status='fail', checks=[], scenario=scenario, setup=__doc__)
    def cmd(s): return gdb.execute(s, to_string=True)
    def val(s): return int(gdb.parse_and_eval(s))
    def until(s):
        b = gdb.Breakpoint(s, temporary=True, internal=True)
        b.silent = True
        cmd('continue')
        stopped = [t for t in gdb.selected_inferior().threads() if t.is_stopped()]
        assert len(stopped) == 1
        stopped[0].switch()
        assert gdb.selected_frame().name() == s
    def wait(s, budget=1800):
        for _ in range(budget):
            if val(s): return
            until('step_game_mode')
        raise AssertionError('Frame budget: ' + s)
    def key(s, frames=8):
        window = subprocess.check_output(['xdotool', 'search', '--onlyvisible', '--pid',
                                         str(gdb.selected_inferior().pid)], text=True).splitlines()[0]
        subprocess.run(['xdotool', 'windowfocus', window], check=True)
        subprocess.run(['xdotool', 'keydown', s], check=True)
        try:
            for _ in range(frames): until('render_game_mode_backUI')
        finally:
            subprocess.run(['xdotool', 'keyup', s], check=True)
        for _ in range(10): until('render_game_mode_backUI')
    def check(s, test, method):
        assert test, s
        result['checks'].append(dict(check=s, method=method))
        print('SAVE_MODE_CHECK=' + s, flush=True)
    try:
        for s in ('non-stop on', 'pagination off', 'confirm off', 'print thread-events off'): cmd('set ' + s)
        b = gdb.Breakpoint('state_step_world' if scenario == 'lifecycle' else 'state_step_logos', temporary=True, internal=True)
        b.silent = True
        cmd('run')
        [t for t in gdb.selected_inferior().threads() if t.is_stopped()][0].switch()
        def tick(n=1):
            for _ in range(n): until('step_game_mode')
        def choose_slot(target):
            for _ in range(8):
                selected = val('filemenu_menus[0]->selected')
                if selected == target: return
                key(('w' if selected // 2 > target // 2 else 's') if selected // 2 != target // 2
                    else ('a' if selected % 2 > target % 2 else 'd'))
            raise AssertionError('Slot navigation')
        def enter_files():
            for _ in range(40):
                if val('CurGameModeID == GAME_MODE_TITLE_SCREEN'): break
                key('space', 20)
            wait('CurGameModeID == GAME_MODE_TITLE_SCREEN && gGameStatus.startupState == TITLE_STATE_HOLD')
            key('space')
            until('filemenu_update')
            tick(40)
        if scenario != 'lifecycle':
            enter_files()
            check('ordinary title defaults to Vanilla', val('ttyd64_mode_enabled()') == 0,
                  'real keyboard startup/title; no debugger-injected state')
            session = Path(os.environ['SAVE_MODE_SESSION'])
            if scenario == 'create':
                for slot, rules in ((0, 'vanilla'), (1, 'ttyd64')):
                    choose_slot(slot)
                    key('x')
                    wait('filemenu_currentMenu == FILE_MENU_INPUT_NAME')
                    tick(35)
                    key('x')  # first ordinary filename character
                    wait('filemenu_filename_pos > 0')
                    key('space')
                    wait('filemenu_currentMenu == FILE_MENU_CONFIRM && filemenu_menus[1]->state == FM_CHOOSE_MODE')
                    tick(35)
                    check(f'new file {slot} offers Vanilla by default', val('filemenu_menus[1]->selected') == 0,
                          'real keyboard filename/Start; no injected state')
                    if rules == 'ttyd64': key('s')
                    check(f'new file {slot} selects requested rules', val('filemenu_menus[1]->selected') == (1 if rules == 'ttyd64' else 0),
                          'real keyboard selection; native grid state observed')
                    key('x')
                    wait('filemenu_menus[1]->state == FM_CONFIRM_CREATE')
                    key('x')
                    wait('filemenu_currentMenu == FILE_MENU_MESSAGE')
                    saved = json.loads((session / f'saves/file{slot}.json').read_text())
                    check(f'new file {slot} saves {rules}', saved['ship']['ttyd64Mode'] == {'version': 1, 'rules': rules},
                          'real mode selection/create confirmation; observe native JSON')
                    tick(45)
                    key('x')
                    wait('filemenu_currentMenu == FILE_MENU_MAIN')
                    tick(30)
                choose_slot(1)
                key('space')
                wait('filemenu_currentMenu == FILE_MENU_CONFIRM')
                key('space')
                until('state_init_enter_world')
                check('selected TTYD64 file owns mode before gameplay initialization', val('ttyd64_mode_enabled()') == 1,
                      'real keyboard Start/file confirmation; no injected state')
            else:
                slot = 3 if scenario == 'restart' else 1
                choose_slot(slot)
                key('space')
                wait('filemenu_currentMenu == FILE_MENU_CONFIRM')
                key('space')
                until('state_step_world')
                wait('!(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
                tick(60)
                expected = 1 if scenario == 'restart' else 0
                check('fresh-process keyboard continue selects saved mode', val('ttyd64_mode_enabled()') == expected,
                      'real keyboard startup/title/slot/Start; no injected state')
                check('fresh-process world HP display follows mode', val('ttyd64_partner_hp_display()') == (3 if expected else -1),
                      'observe native world HUD owner after real keyboard continuation')
                check('fresh-process Dip costs follow mode', val('get_move_fp_cost(MOVE_DOUBLE_DIP)') == (4 if expected else 3)
                      and val('get_move_bp_cost(MOVE_DOUBLE_DIP)') == (3 if expected else 1),
                      'debugger read-only cost API queries after native load')
                check('normal Village has no proof pickups in this mode', all(not val(f'WorldItemEntities[{i}]') or
                      val(f'WorldItemEntities[{i}]->itemID') != val('ITEM_PITY_FLOWER') for i in range(256)),
                      'native map after real keyboard continuation, before injected healing setup')
                initial_hp = val('ttyd64_get_partner_hp(PARTNER_GOOMBARIO)')
                for field, amount in (('curHP', 3), ('curFP', 1), ('maxStarPower', 2), ('starPower', 0)):
                    cmd(f'set variable gPlayerData.{field} = {amount}')
                for axis, amount in (('x', 200), ('y', 0), ('z', 100)):
                    cmd(f'set variable gPlayerStatus.pos.{axis} = {amount}')
                block = val('create_entity(&Entity_HeartBlock, 200, 60, 100, 0, 0, (uintptr_t)0x80000000)')
                assert block >= 0
                tick(10)
                for _ in range(3):
                    key('x', 5)
                    tick(60)
                    if val('gPlayerData.curHP == gPlayerData.curMaxHP'): break
                check('keyboard Heart Block heals Mario in both modes', val('gPlayerData.curHP == gPlayerData.curMaxHP')
                      and val('gPlayerData.curFP == gPlayerData.curMaxFP'),
                      'injected wounds/SP/position/test Heart Block; real jump/native healing animation')
                check('Heart Block extra HP/SP follows saved mode', val('ttyd64_get_partner_hp(PARTNER_GOOMBARIO)') == (10 if expected else initial_hp)
                      and val('gPlayerData.starPower') == (512 if expected else 0),
                      'injected wounds/SP/position/test Heart Block; real jump/native healing animation')
            result['status'] = 'pass'
            return
        wait('!(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
        check('CLI starts enabled', val('ttyd64_mode_enabled()') == 1, 'native CLI setup, observed')
        save = Path(os.environ['SAVE_MODE_SESSION']) / 'saves/file3.json'
        saved = json.loads(save.read_text())
        check('native developer save explicitly chooses TTYD64', saved['ship']['ttyd64Mode'] == {'version': 1, 'rules': 'ttyd64'},
              'actual native save JSON, observed')
        session = save.parent.parent
        saved['ship']['unrelatedProbe'] = {'keep': 17}
        saved['unrelatedRootProbe'] = 19
        save.write_text(json.dumps(saved))
        legacy = json.loads(json.dumps(saved))
        del legacy['ship']['ttyd64Mode']
        legacy['saveSlot'] = 1
        legacy['ship']['ttyd64PartnerHP']['partners'][1]['curHP'] = 2
        (save.parent / 'file1.json').write_text(json.dumps(legacy))
        check('native preview keeps running mode and HP', val('fio_load_summary(1)') == 1
              and val('ttyd64_mode_enabled()') == 1 and val('ttyd64_get_partner_hp(1)') == 3,
              'debugger creates mode-less legacy save; calls native summary API, observes ownership')
        check('native copy succeeds', val('fio_copy_game(3, 0)') == 1, 'controlled native copy API')
        copy = json.loads((save.parent / 'file0.json').read_text())
        check('copy retains mode and unrelated source JSON', copy['ship']['ttyd64Mode'] == saved['ship']['ttyd64Mode']
              and copy['ship']['unrelatedProbe'] == {'keep': 17} and copy['unrelatedRootProbe'] == 19
              and copy['saveSlot'] == 0 and val('ttyd64_mode_enabled()') == 1,
              'native copy API result; debugger added harmless unknown JSON probes')
        cmd('call fio_erase_game(0)')
        check('erase removes mode with copied file, keeps active owner', not (save.parent / 'file0.json').exists()
              and val('ttyd64_mode_enabled()') == 1, 'controlled native erase API')
        check('mode-less legacy load uses Vanilla', val('fio_load_game(1)') == 1 and val('ttyd64_mode_enabled()') == 0,
              'controlled native load API after explicit missing-mode JSON setup')
        check('TTYD64 preview cannot activate a Vanilla runtime', val('fio_load_summary(3)') == 1
              and val('ttyd64_mode_enabled()') == 0 and val('ttyd64_get_partner_hp(1)') == 2,
              'controlled native summary API; no runtime mode/state setter')
        check('explicit file load restores TTYD64', val('fio_load_game(3)') == 1 and val('ttyd64_mode_enabled()') == 1,
              'controlled native load API')
        cmd('call fio_save_game(3)')
        updated = json.loads(save.read_text())
        check('native save preserves mode and unrelated JSON', updated['ship']['ttyd64Mode']['rules'] == 'ttyd64'
              and updated['ship']['unrelatedProbe'] == {'keep': 17} and updated['unrelatedRootProbe'] == 19,
              'controlled native save API after harmless injected JSON probes/native load')
        check('static costs remain Vanilla', val('gMoveTable[MOVE_DOUBLE_DIP].costFP') == 3
              and val('gMoveTable[MOVE_DEFEND_PLUS].costBP') == 6, 'read-only static table observation')
        check('shared runtime costs select source rules', val('get_move_fp_cost(MOVE_DOUBLE_DIP)') == 4
              and val('get_move_bp_cost(MOVE_DOUBLE_DIP)') == 3 and val('get_move_bp_cost(MOVE_DEFEND_PLUS)') == 5,
              'read-only cost API queries')
        check('normal Village has no proof pickups', all(not val(f'WorldItemEntities[{i}]') or
              val(f'WorldItemEntities[{i}]->itemID') != val('ITEM_PITY_FLOWER') for i in range(256)),
              'native map entities observed before injected battle setup')
        cmd('set variable gGameStatus.debugEnemyContact = DEBUG_CONTACT_CANT_TOUCH')
        cmd('set variable gGameStatus.areaID = 0')
        cmd('set variable gGameStatus.mapID = 7')
        cmd('set variable gGameStatus.entryID = 0')
        cmd('call set_game_mode(GAME_MODE_CHANGE_MAP)')
        until('state_step_world')
        for _ in range(100): until('step_game_mode')
        wait('!(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
        cmd('set variable gGameStatus.debugEnemyContact = DEBUG_CONTACT_NONE')
        cmd('set variable gPlayerData.curHP = 1')
        for i in range(10): cmd(f'set variable gPlayerData.invItems[{i}] = 0')
        for _ in range(40):
            if val('gEncounterState') != val('ENCOUNTER_STATE_NEUTRAL'): break
            key('d', 16)
        wait('gGameStatus.context == CONTEXT_BATTLE && gBattleState == BATTLE_STATE_PLAYER_MENU && BattleMenuState == BTL_MENU_STATE_CHOOSING')
        check('keyboard encounter', val('gPlayerData.curHP') == 1, 'real walking; injected route, HP and empty items')
        for turn in range(4):
            if val('gGameStatus.context') != val('CONTEXT_BATTLE'): break
            idx = next(i for i in range(val('WheelOptionCount')) if val(f'WheelOptionSubmenu[{i}]') == val('BTL_MENU_TYPE_STRATEGIES'))
            for _ in range(10):
                current = val('BattleMenu_CurPos + BattleMenu_HomePos')
                if current == idx: break
                key('a' if current > idx else 'd')
            key('x')
            wait('gBattleSubState == 201 && StratsMenuState == BTL_SUBMENU_STATE_CHOOSING')
            idx = next(i for i in range(val('StratsOptionCount')) if val(f'StratsOptionMenuTypes[{i}]') == val('BTL_MENU_TYPE_DO_NOTHING'))
            for _ in range(10):
                current = val('StratsCursorPos')
                if current == idx: break
                key('w' if current > idx else 's')
            state = val('gBattleState')
            key('x')
            wait(f'gBattleState != {state}')
            wait('gGameStatus.context != CONTEXT_BATTLE || ((gBattleState == BATTLE_STATE_PLAYER_MENU || gBattleState == BATTLE_STATE_PARTNER_MENU) && gBattleSubState < 4 && BattleMenuState == BTL_MENU_STATE_CHOOSING)')
        until('state_step_game_over')
        check('native fatal attack reaches game over', val('gPlayerData.curHP') == 0,
              'keyboard Do Nothing; native enemy damage/defeat, no forced guard/RNG')
        until('state_step_title_screen')
        check('title clears active ownership until a file is selected', val('ttyd64_mode_enabled()') == 0,
              'native game-over script transitions to title; observation')
        wait('gGameStatus.startupState == TITLE_STATE_HOLD')
        key('space')
        wait('filemenu_currentMenu == FILE_MENU_MAIN && filemenu_menus[0]->state == FM_MAIN_SELECT_FILE')
        # Wait for the real file menu, not preexisting zero-initialized globals.
        until('filemenu_update')
        for _ in range(35): until('step_game_mode')
        choose_slot(3)
        key('space')
        wait('filemenu_currentMenu == FILE_MENU_CONFIRM')
        key('space')
        until('state_step_world')
        wait('!(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')
        check('native game-over/title/keyboard continue restores HP and saved mode', val('ttyd64_mode_enabled()') == 1 and
              val('ttyd64_get_partner_hp(1)') == 3,
              'real title Start, slot navigation and Start confirmation; observed')
        result['status'] = 'pass'
    except Exception as e:
        result['error'] = str(e)
        result['state'] = {s: val(s) for s in ('gGameStatus.context', 'gBattleState', 'gBattleSubState', 'gGameStatus.startupState', 'filemenu_currentMenu')}
        raise
    finally:
        Path(os.environ['SAVE_MODE_PAYLOAD']).write_text(json.dumps(result, indent=2) + '\n')
        cmd('kill')


def main():
    import argparse
    import shutil
    import signal
    import re
    p = argparse.ArgumentParser(description=__doc__)
    for s in ('source', 'executable', 'package', 'archive', 'output'): p.add_argument('--' + s, type=Path, required=True)
    p.add_argument('--fixture-commit')
    p.add_argument('--only', help='Comma-separated create,lifecycle,restart,legacy; restart/legacy require lifecycle in this run')
    a = p.parse_args()
    source, exe, package, archive, out = (getattr(a, s).resolve() for s in ('source', 'executable', 'package', 'archive', 'output'))
    out.mkdir(parents=True, exist_ok=False)
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    git = lambda *args: subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()
    commit = git('rev-parse', 'HEAD')
    assert not git('status', '--porcelain')
    receipt = json.loads((exe.parent / 'porting-build.json').read_text())
    assert receipt['game_commit'] == commit and receipt['executable_sha256'] == digest(exe)
    fixture_commit = a.fixture_commit or commit
    blob = subprocess.check_output(['git', '-C', str(source), 'show', fixture_commit + ':tools/porting/check_save_modes.py'])
    assert hashlib.sha256(blob).hexdigest() == digest(Path(__file__))
    cases = a.only.split(',') if a.only else ['create', 'lifecycle', 'restart', 'legacy']
    assert cases and len(set(cases)) == len(cases) and set(cases) <= {'create', 'lifecycle', 'restart', 'legacy'}
    assert not ({'restart', 'legacy'} & set(cases)) or 'lifecycle' in cases
    read, write = os.pipe()
    with (out / 'xvfb.log').open('w') as xlog:
        xvfb = subprocess.Popen(['Xvfb', '-displayfd', str(write), '-screen', '0', '1280x800x24', '-nolisten', 'tcp'], pass_fds=(write,), stdout=xlog, stderr=xlog)
        os.close(write)
        with os.fdopen(read) as stream: display = ':' + stream.readline().strip()
        assert display != ':' and xvfb.poll() is None
        try:
            for case in cases:
                started = utc()
                session = out / ('session-create' if case == 'create' else 'session-lifecycle')
                if case == 'create':
                    session.mkdir()
                    for name in ('paperboat.o2r', 'assets', 'config.yml', 'gamecontrollerdb.txt'):
                        (session / name).symlink_to(package / name)
                    (session / 'pm64.o2r').symlink_to(archive)
                    shutil.copyfile(package / 'playtest-keyboard.json', session / 'paperboat.cfg.json')
                env = dict(os.environ, DISPLAY=display, SHIP_HOME=str(session), SDL_AUDIODRIVER='dummy', LIBGL_ALWAYS_SOFTWARE='1', DEBUGINFOD_URLS='',
                           XDG_CACHE_HOME=str(out / 'cache'), SAVE_MODE_SESSION=str(session), SAVE_MODE_PAYLOAD=str(out / (case + '-checks.json')), SAVE_MODE_SCENARIO=case)
                command = ['gdb', '-q', '-batch', '-x', str(Path(__file__).resolve()), '--args', str(exe)]
                if case == 'lifecycle': command += ['--ttyd64-playtest', str(session), str(package), str(archive), 'healing']
                with (out / (case + '.log')).open('w') as log:
                    process = subprocess.Popen(command, cwd=package if case == 'lifecycle' else session, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                    try: code = process.wait(timeout=360)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGTERM)
                        code = process.wait(timeout=20)
                payload = out / (case + '-checks.json')
                data = json.loads(payload.read_text()) if payload.exists() else dict(status='fail', error='Missing payload')
                log_text = (out / (case + '.log')).read_text()
                loaded = {Path(path.strip()).resolve() for path in re.findall(r'Reading archive: (.+)', log_text)}
                expected_archives = {(session / 'pm64.o2r').resolve(), (session / 'paperboat.o2r').resolve()}
                if loaded != expected_archives or digest(session / 'pm64.o2r') != digest(archive) or digest(session / 'paperboat.o2r') != digest(package / 'paperboat.o2r'):
                    data.update(status='fail', error='Actual engine archive provenance mismatch')
                data.update(git_commit=commit, fixture_commit=fixture_commit, executable_sha256=digest(exe), fixture_sha256=digest(Path(__file__)),
                            rom_archive_sha256=digest(archive), port_archive_sha256=digest(package / 'paperboat.o2r'), loaded_archives=sorted(str(path) for path in loaded),
                            started_utc=started, ended_utc=utc(), command=command, exit_code=code, full_log=(out / (case + '.log')).read_text(),
                            skipped=['build performed separately', 'ROM extraction; supplied verified archive reused', 'Windows/macOS gameplay', 'unselected fixtures', 'hardware graphics/audio', 'full campaign'])
                if code: data['status'] = 'fail'
                (out / (case + '-result.json')).write_text(json.dumps(data, indent=2) + '\n')
                print(case, data['status'], data.get('error', ''), flush=True)
                if data['status'] != 'pass': raise SystemExit(1)
        finally:
            xvfb.terminate()
            xvfb.wait(timeout=10)


try:
    import gdb
except ImportError:
    gdb = None
if gdb is not None: observe()
elif __name__ == '__main__': main()
