#!/usr/bin/env python3
"""Launch the guarded Goombario slice in a fresh isolated prepared-cloud session."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', help='Check native startup/input, then close instead of handing off the game')
    parser.add_argument('--ground-partners', action='store_true', help='Recruit Goombario, Kooper and Bombette in this isolated prototype session')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    setup = Path('/workspace/.paperboat-setup')
    seed = setup / 'fp-drain/runtime/saves/file3.json'
    profile = setup / 'partner-combat/runtime/paperboat.cfg.json'
    binary_dir = repo / 'build/ninja-debug'
    for path in [seed, profile, binary_dir / 'Paperboat', binary_dir / 'pm64.o2r', binary_dir / 'paperboat.o2r']:
        if not path.is_file():
            parser.error(f'Prepared environment file missing: {path}')
    if not os.environ.get('DISPLAY'):
        parser.error('DISPLAY must name the display where you will play')
    session_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S-') + uuid.uuid4().hex[:8]
    session = setup / 'goombario-playtest/sessions' / session_id
    runtime = session / 'runtime'
    (runtime / 'saves').mkdir(parents=True, exist_ok=False)
    (session / '.owned-playtest').write_text('PaperBoat Goombario isolated playtest v1\n')
    shutil.copyfile(seed, runtime / 'saves/file3.json')
    shutil.copyfile(profile, runtime / 'paperboat.cfg.json')
    env = os.environ.copy()
    env.update(PARTNER_SLICE_PARTNER='1', PARTNER_SLICE_GROUND=str(int(args.ground_partners)), SHIP_HOME=str(runtime), XDG_CACHE_HOME=str(session / 'cache'), PARTNER_SLICE_PLAYTEST='1',
               PARTNER_SLICE_VERIFY_ONLY=str(int(args.verify)),
               PARTNER_SLICE_RESULT=str(session / 'ready.json'), DEBUGINFOD_URLS='')
    print('Fresh isolated test session: ' + str(session), flush=True)
    print('Partner HP prototype enabled only in this process. Normal launches remain off.', flush=True)
    with (session / 'launch.log').open('w') as log:
        process = subprocess.Popen(['gdb','-q','-batch','-x',str(repo / 'tools/porting/partner_playable_slice_gdb.py'),'./Paperboat'],
                                   cwd=binary_dir, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            if process.wait(timeout=180):
                raise RuntimeError('Playtest startup failed; inspect ' + str(session / 'launch.log'))
        except BaseException:
            # This process group belongs only to the just-created test session.
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            raise
    result = json.loads((session / 'ready.json').read_text())
    print(('Verified and closed' if args.verify else f'Ready: game PID {result["pid"]}') + '. Report: ' + str(session / 'ready.json'))
    print('Move W/A/S/D; A=X; B=C; Start=Space; Items=Left arrow; Partners=Right arrow; battle order=Z.')
    print('Ground partner group recruited: Goombario, Kooper, Bombette.' if args.ground_partners else 'Only Goombario is recruited.')
    print('Starts in Goomba Village: try menus/healing, then take the right exit for Goomba Road. Close the game window to finish.')
    print('Saves stay in this session. Each launch starts fresh; this is an early partner HP slice, not the full mod.')


if __name__ == '__main__':
    main()
