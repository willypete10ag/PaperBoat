#!/usr/bin/env python3
"""Linux native-launch/input acceptance with an observing GDB; no injected setup."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def utc():
    return datetime.now(timezone.utc).isoformat()


def observe():
    import gdb
    result = {'status': 'fail', 'checks': [], 'setup': 'native CLI new-game developer profile; no debugger setup'}
    profile = os.environ['NATIVE_PLAYTEST_PROFILE']
    descriptions = os.environ.get('NATIVE_PLAYTEST_DESCRIPTIONS', '0') == '1'
    baseline = os.environ.get('NATIVE_PLAYTEST_DESCRIPTION_BASELINE', '0') == '1'

    def cmd(command):
        return gdb.execute(command, to_string=True)

    def val(expression):
        return int(gdb.parse_and_eval(expression))

    def until(function):
        point = gdb.Breakpoint(function, temporary=True, internal=True)
        point.silent = True
        cmd('continue')
        stopped = [t for t in gdb.selected_inferior().threads() if t.is_stopped()]
        assert len(stopped) == 1
        stopped[0].switch()
        assert gdb.selected_frame().name() == function

    def wait(expression, budget=480):
        for _ in range(budget):
            if val(expression):
                return
            until('step_game_mode')
        result['timeout_state'] = {k: val(k) for k in ('WorldMenuState', 'WorldMenuType', 'gPopupState',
                                   'gGameStatus.context', 'gGameStatus.mapID', 'gGameStatus.startupState')}
        raise AssertionError('Native frame budget: ' + expression)

    def check(name, condition, method='predicate after native CLI setup'):
        assert condition, name
        result['checks'].append(dict(check=name, method=method))
        print('NATIVE_PLAYTEST_CHECK=' + name, flush=True)

    def key(name, frames=8):
        if val('gPopupState') == val('POPUP_STATE_CHOOSING') and val('PopupDelayTime') > 0:
            wait('gPopupState != POPUP_STATE_CHOOSING || PopupDelayTime == 0')
        window = subprocess.check_output(['xdotool', 'search', '--onlyvisible', '--pid',
                                         str(gdb.selected_inferior().pid)], text=True).splitlines()[0]
        subprocess.run(['xdotool', 'windowfocus', window], check=True)
        subprocess.run(['xdotool', 'keydown', name], check=True)
        try:
            for _ in range(frames):
                until('render_game_mode_backUI')
        finally:
            subprocess.run(['xdotool', 'keyup', name], check=True)
        for _ in range(8):
            until('render_game_mode_backUI')

    def neutral():
        wait('gGameStatus.context == CONTEXT_WORLD && WorldMenuState == 0 && !(gPlayerStatus.flags & PS_FLAG_INPUT_DISABLED)')

    def open_items():
        neutral()
        wait('gPlayerStatus.actionState == ACTION_STATE_IDLE')
        for _ in range(3):
            key('Left')
            if val('WorldMenuState') != 0:
                break
        wait('WorldMenuState == 3 && WorldMenuType == 1 && gPopupState == POPUP_STATE_CHOOSING && PopupDelayTime == 0')

    try:
        for setting in ('non-stop on', 'pagination off', 'confirm off', 'print thread-events off'):
            cmd('set ' + setting)
        point = gdb.Breakpoint('GameEngine::RunExtract', temporary=True, internal=True)
        point.silent = True
        cmd('run')
        [t for t in gdb.selected_inferior().threads() if t.is_stopped()][0].switch()
        # GCC can stop before the prologue has stored the argument variables.
        cmd('next')
        check('engine ROM importer receives no playtest setup arguments', val('argc') == 1 and
              val('argv[1] == 0') == 1, 'debugger observes actual engine entry arguments; no injected state')
        until('state_step_world')
        neutral()
        for _ in range(80):
            until('step_game_mode')
        check('native saved TTYD64 mode enabled in Village', val('ttyd64_mode_enabled()') == 1 and
              val('gGameStatus.areaID') == 0 and val('gGameStatus.mapID') == 1)
        check('native Mario stats and gear', val('gPlayerData.curHP') == 15 and val('gPlayerData.curMaxHP') == 20 and
              val('gPlayerData.curFP') == (3 if profile == 'healing' else 10) and val('gPlayerData.hammerLevel') == 0 and val('gPlayerData.hasActionCommands') == 1)
        check('native developer Refresh and Smooch grant', val('gPlayerData.maxStarPower') == 5 and
              val('gPlayerData.starPower') == 5 * 256)
        check('native developer badge budget and owned inventory', val('gPlayerData.maxBP') == 20 and
              sum(val(f'gPlayerData.badges[{i}]') != 0 for i in range(128)) == 15)
        expected = ('ITEM_DOUBLE_DIP', 'ITEM_DOUBLE_DIP', 'ITEM_FLOWER_SAVER_A',
                    'ITEM_FLOWER_SAVER_A', 'ITEM_PITY_FLOWER', 'ITEM_LAST_STAND')
        check('native equipped copy loadout', all(val(f'gPlayerData.equippedBadges[{i}]') == val(badge)
              for i, badge in enumerate(expected)) and
              all(val(f'gPlayerData.equippedBadges[{i}]') == 0 for i in range(len(expected),64)))
        check('native loadout price and abilities', val('pause_get_total_equipped_bp_cost()') == 18 and
              val('is_ability_active(ABILITY_DOUBLE_DIP)') == 2 and
              val('is_ability_active(ABILITY_FLOWER_SAVER)') == 2 and
              val('is_ability_active(ABILITY_FP_DRAIN)') == 0)
        for partner, maximum in ((1, 10), (2, 10), (3, 15)):
            check('native ground partner ' + str(partner), val(f'gPlayerData.partners[{partner}].enabled') == 1 and
                  val(f'ttyd64_get_partner_hp({partner})') == 3 and
                  val(f'ttyd64_get_partner_max_hp({partner})') == maximum)
        if profile == 'healing':
            check('native isolated Parakarry lifecycle setup',
                  val('gPlayerData.partners[4].enabled') == 1
                  and val('ttyd64_get_partner_hp(4)') == 3
                  and val('ttyd64_get_partner_max_hp(4)') == 15,
                  'observes native developer CLI initialization; no recruitment injection')
        check('native world partner bound', val('wCurrentPartnerId') == 1 and val('WorldPartnerID') == 1)
        save = Path(os.environ['NATIVE_PLAYTEST_SESSION']) / 'saves/file3.json'
        check('native save generated with TTYD64 mode, without a seed', save.is_file() and
              json.loads(save.read_text())['ship']['ttyd64Mode'] == {'version': 1, 'rules': 'ttyd64'})
        old_x = float(gdb.parse_and_eval('gPlayerStatus.pos.x'))
        key('d', 12)
        check('keyboard moves Mario', float(gdb.parse_and_eval('gPlayerStatus.pos.x')) > old_x,
              'real keyboard input after native CLI setup')
        open_items()
        check('keyboard inventory opens', val('WorldPopupMenu.numEntries') == 10, 'real keyboard input after native CLI setup')
        if profile == 'healing':
            check('native healing profile positive-food stock', all(
                sum(val(f'gPlayerData.invItems[{i}]') == val(item) for i in range(10)) == 1
                for item in ('ITEM_FRIED_SHROOM','ITEM_HONEY_SYRUP','ITEM_MAPLE_SUPER','ITEM_VOLT_SHROOM','ITEM_ELECTRO_POP')),
                'native CLI startup inventory observed, no debugger item grant')
        if descriptions:
            result['description_baseline'] = baseline
            result['description_setup'] = 'native TTYD64 developer file; Vanilla comparison edits only its disposable saved mode and uses native FIO load; stock is reused, not normal Vanilla acquisition'
            result['descriptions'] = []
            original = save.read_bytes()
            ported = {val(name) for name in ('ITEM_COURAGE_SHELL', 'ITEM_POWER_PUNCH', 'ITEM_MINI_MR_MINI',
                      'ITEM_MR_SOFTENER', 'ITEM_SLOW_SHROOM', 'ITEM_GRADUAL_SYRUP', 'ITEM_COUPLES_CAKE', 'ITEM_METEOR_MEAL')}
            try:
                for rules in ('ttyd64', 'vanilla'):
                    if rules == 'vanilla':
                        key('c')
                        neutral()
                        # Explicit saved-mode fixture, never a global prototype toggle.
                        data = json.loads(original)
                        data['ship']['ttyd64Mode']['rules'] = rules
                        save.write_text(json.dumps(data))
                        assert val('fio_load_game(3)') == 1
                        open_items()
                    check(rules + ' item menu uses loaded file mode', val('ttyd64_mode_enabled()') == (rules == 'ttyd64'),
                          'native CLI file; Vanilla comparison edits only disposable saved mode and calls native FIO load')
                    for row in range(val('WorldPopupMenu.numEntries')):
                        box_height = val('gWindows[WIN_POPUP_DESC].height')
                        box_width = val('gWindows[WIN_POPUP_DESC].width')
                        selected = val('PopupMenu_SelectedIndex')
                        item = val(f'gPlayerData.invItems[WorldPopupMenu.userIndex[{selected}]]')
                        message = val(f'WorldPopupMenu.descMsg[{selected}]')
                        native_lines = val(f'get_msg_lines({message})')
                        pointer = val(f'load_message_to_buffer({message})')
                        encoded = bytes(gdb.selected_inferior().read_memory(pointer, 512)).split(b'\xfd', 1)[0]
                        # Native get_msg_lines counts only nonempty lines. The
                        # renderer advances for every ENDL, including blank ones.
                        lines = encoded.count(b'\xf0') + 1
                        width = val(f'get_msg_width({message}, 0)')
                        height = lines * val('MsgCharsets[0]->newLineY')
                        expected = 3 if baseline and item in ported else 2
                        check(f'{rules} description {item} line count {lines}',
                              lines == expected if item in ported else 1 <= lines <= 2,
                              'real keyboard world-item navigation; native loaded message ENDL controls and font pitch; baseline expects reproduced overflow')
                        check(f'{rules} description {item} reproduces or clears vertical overflow',
                              (height > box_height) == (baseline and item in ported), 'compiled native line pitch against unchanged 32-pixel description box')
                        result['descriptions'].append(dict(rules=rules, item=item, lines=lines, native_nonempty_lines=native_lines, width=width, height=height,
                                                          box_height=box_height, box_width=box_width, expected_overflow=baseline and item in ported))
                        check(f'{rules} description {item} fits box width', width <= box_width - 16,
                              'compiled native message width; unchanged 280-pixel description box with 8-pixel side inset')
                        if item in ported or row == 0:
                            for _ in range(3):
                                until('render_game_mode_backUI')
                            capture = Path(os.environ['NATIVE_PLAYTEST_PAYLOAD']).parent / f'{profile}-{rules}-item-{item}.png'
                            subprocess.run(['import', '-window', 'root', str(capture)], check=True)
                            result.setdefault('private_captures', []).append(dict(name=capture.name, sha256=hashlib.sha256(capture.read_bytes()).hexdigest()))
                        if row + 1 < val('WorldPopupMenu.numEntries'):
                            key('s')
                    key('c')
                    neutral()
            finally:
                save.write_bytes(original)
            result['status'] = 'pass'
            return
        key('c')
        neutral()
        key('Right')
        wait('WorldMenuState == 3 && WorldMenuType == 0 && gPopupState == POPUP_STATE_CHOOSING')
        check('keyboard partner menu lists profile roster',
              val('WorldPopupMenu.numEntries') == (4 if profile == 'healing' else 3),
              'real keyboard input after native CLI setup; B01 healing profile includes Parakarry')
        wait('gPopupState == POPUP_STATE_CHOOSING && PopupDelayTime == 0')
        for _ in range(4):
            if val('WorldPopupMenu.userIndex[PopupMenu_SelectedIndex]') == val('PARTNER_KOOPER'):
                break
            key('s')
        assert val('WorldPopupMenu.userIndex[PopupMenu_SelectedIndex]') == val('PARTNER_KOOPER')
        key('x')
        neutral()
        wait('wCurrentPartnerId == PARTNER_KOOPER')
        check('keyboard swap binds wounded Kooper', val('WorldPartnerID') == 2 and
              val('ttyd64_get_partner_hp(2)') == 3, 'real keyboard input after native CLI setup')
        if profile == 'healing':
            open_items()
            # Native add_item compacts toward the end and inserts at the front;
            # choose by typed identity rather than assuming the first row is food.
            mushroom = next(i for i in range(val('WorldPopupMenu.numEntries'))
                            if val(f'gPlayerData.invItems[WorldPopupMenu.userIndex[{i}]]') == val('ITEM_MUSHROOM'))
            for _ in range(mushroom):
                key('s')
            key('x')
            wait('WorldMenuState == 3 && WorldMenuType == 3 && gPopupState == POPUP_STATE_CHOOSING && PopupDelayTime == 0')
            recipient = next(i for i in range(val('WorldPopupMenu.numEntries'))
                             if val(f'WorldPopupMenu.userIndex[{i}]') == val('PARTNER_KOOPER'))
            for _ in range(recipient):
                key('s')
            key('x')
            neutral()
            for _ in range(30):
                until('step_game_mode')
            check('keyboard Mushroom heals chosen partner', val('ttyd64_get_partner_hp(2)') == 8,
                  'real keyboard input after native CLI setup')
        key('space')
        wait('gGameStatus.context == CONTEXT_PAUSE && StepPauseDelay < -10')
        check('keyboard pause opens', val('gGameStatus.context') == val('CONTEXT_PAUSE'), 'real keyboard input after native CLI setup')
        for _ in range(8):
            if val('gPauseTabsCurrentTab') == 1:
                break
            key('d')
        assert val('gPauseTabsCurrentTab') == 1
        key('x')
        wait('gPauseMenuCurrentTab == 2')
        check('keyboard badge panel exposes native copy loadout', val('gPauseBadgesNumItems') == 15 and
              val('pause_get_total_equipped_bp_cost()') == 18, 'real keyboard input after native CLI setup')
        # Private inspection aid only; captures are excluded from publication.
        for _ in range(12):
            until('render_game_mode_backUI')
        subprocess.run(['import', '-window', 'root', str(Path(os.environ['NATIVE_PLAYTEST_PAYLOAD']).parent /
                        (profile + '-badges.png'))], check=True)
        key('space')
        neutral()
        check('keyboard unpause restores owner', val('WorldPartnerID') == 2, 'real keyboard input after native CLI setup')
        # Explicitly controlled reset boundary; no assertion that keyboard reset was tested.
        cmd('call set_game_mode(GAME_MODE_STARTUP)')
        wait('ttyd64_mode_enabled() == 0')
        for _ in range(10):
            until('step_game_mode')
        check('controlled startup clears active mode, saved file remains TTYD64', val('ttyd64_mode_enabled()') == 0 and
              val('gPlayerData.curHP') == 10 and
              json.loads(save.read_text())['ship']['ttyd64Mode']['rules'] == 'ttyd64', 'debugger API selects STARTUP; native reset runs, predicate observation')
        result['status'] = 'pass'
    except Exception as error:
        result['error'] = str(error)
        result['failure_health'] = {str(i): val(f'ttyd64_get_partner_hp({i})') for i in (1, 2, 3)}
        raise
    finally:
        Path(os.environ['NATIVE_PLAYTEST_PAYLOAD']).write_text(json.dumps(result, indent=2) + '\n')
        cmd('kill')


def main():
    import argparse
    import signal
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('executable', 'package', 'archive', 'output'):
        parser.add_argument('--' + arg, type=Path, required=True)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--fixture-commit', help='Committed exported driver revision; defaults to the game checkout HEAD')
    parser.add_argument('--descriptions', action='store_true', help='Inspect grouped world item descriptions in both saved modes')
    parser.add_argument('--description-baseline', action='store_true', help='Expect the pre-fix three-line ported descriptions')
    args = parser.parse_args()
    assert not args.description_baseline or args.descriptions
    exe, package, archive, output = (getattr(args, k).resolve() for k in ('executable', 'package', 'archive', 'output'))
    output.mkdir(parents=True, exist_ok=False)
    source = args.source.resolve()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
    assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=source), 'Commit changes before recording acceptance'
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    fixture_commit = args.fixture_commit or commit
    blob = subprocess.check_output(['git', 'show', fixture_commit + ':tools/porting/check_native_playtest.py'], cwd=source)
    assert hashlib.sha256(blob).hexdigest() == digest(Path(__file__)), 'Driver differs from stated fixture commit'
    read_fd, write_fd = os.pipe()
    xvfb = subprocess.Popen(['Xvfb', '-displayfd', str(write_fd), '-screen', '0', '1280x800x24', '-nolisten', 'tcp'],
                            pass_fds=(write_fd,), stdout=subprocess.DEVNULL, stderr=(output / 'xvfb.log').open('w'))
    os.close(write_fd)
    with os.fdopen(read_fd) as stream:
        display = ':' + stream.readline().strip()
    assert display != ':' and xvfb.poll() is None, 'Owned Xvfb failed to start'
    try:
        for profile in ('healing', 'status'):
            session = output / ('session-' + profile)
            payload = output / (profile + '-checks.json')
            started = utc()
            env = dict(os.environ, DISPLAY=display, SDL_AUDIODRIVER='dummy', LIBGL_ALWAYS_SOFTWARE='1',
                       DEBUGINFOD_URLS='', XDG_CACHE_HOME=str(output / 'cache'), NATIVE_PLAYTEST_PROFILE=profile,
                       NATIVE_PLAYTEST_SESSION=str(session), NATIVE_PLAYTEST_PAYLOAD=str(payload),
                       NATIVE_PLAYTEST_DESCRIPTIONS=str(int(args.descriptions)),
                       NATIVE_PLAYTEST_DESCRIPTION_BASELINE=str(int(args.description_baseline)))
            command = ['gdb', '-q', '-batch', '-x', str(Path(__file__).resolve()), '--args', str(exe),
                       '--ttyd64-playtest', str(session), str(package), str(archive), profile]
            log = output / (profile + '.log')
            with log.open('w') as stream:
                process = subprocess.Popen(command, cwd=package, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    code = process.wait(timeout=420 if args.descriptions else 240)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGTERM)
                    code = process.wait(timeout=20)
            data = json.loads(payload.read_text()) if payload.exists() else {'status': 'fail', 'error': 'No check payload'}
            data.update(git_commit=commit, fixture_commit=fixture_commit, executable_sha256=digest(exe), fixture_sha256=digest(Path(__file__)),
                        archive_sha256=digest(archive), started_utc=started, ended_utc=utc(), exit_code=code,
                        command=command, full_log=log.read_text(), skipped=['build performed separately', 'ROM extraction; supplied verified archive reused',
                        'Windows rendering/input', 'hardware graphics/audio', 'full registered ROM-dependent fixture suite'])
            if code:
                data['status'] = 'fail'
            (output / (profile + '-result.json')).write_text(json.dumps(data, indent=2) + '\n')
            print(profile + ': ' + data['status'], flush=True)
            if data['status'] != 'pass':
                raise RuntimeError('Native playtest failed; inspect ' + str(output))
    finally:
        xvfb.terminate()
        xvfb.wait(timeout=10)


try:
    import gdb
except ImportError:
    gdb = None
if gdb is not None:
    observe()
elif __name__ == '__main__':
    main()
