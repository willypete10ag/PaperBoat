#!/usr/bin/env python3
"""ROM-free process/path acceptance; does not initialize graphics or load archives."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fixture-commit', help='Revision of an exported committed fixture; defaults to checkout HEAD')
    args = parser.parse_args()
    exe, package, output = args.executable.resolve(), args.package.resolve(), args.output.resolve()
    result = dict(started_utc=utc(), git_commit=subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], text=True).strip(), executable_sha256=sha(exe),
        fixture_sha256=sha(__file__), method='real native process CLI; synthetic non-ROM archive; no engine/gameplay',
        checks=[], runs=[], status='fail')
    result['fixture_commit'] = args.fixture_commit or result['git_commit']
    blob = subprocess.check_output(['git', 'show', result['fixture_commit'] + ':tools/porting/check_playtest_preflight.py'])
    actual = Path(__file__).read_bytes()
    result['fixture_git_blob_sha256'] = hashlib.sha256(blob).hexdigest()
    result['fixture_checkout_conversion'] = 'none' if actual == blob else 'git_crlf_lf'
    # Git's Windows checkout can convert LF to CRLF. Preserve the actual run
    # hash above, expose the original blob hash, and allow only that conversion.
    assert actual.replace(b'\r\n', b'\n') == blob.replace(b'\r\n', b'\n'), 'Fixture differs from its stated commit'
    try:
        with tempfile.TemporaryDirectory(prefix='PaperBoat playtest paths ') as tmp:
            root = Path(tmp)
            fake = root / 'synthetic archive.o2r'
            fake.write_text('Not a ROM archive. Preflight must never load this file.\n')
            unrelated = root / 'normal game home'
            unrelated.mkdir()
            sentinel = unrelated / 'paperboat.cfg.json'
            sentinel.write_text('normal configuration sentinel\n')
            env = dict(os.environ, SHIP_HOME=str(unrelated))

            def check(name, condition):
                assert condition, name
                result['checks'].append(name)

            def run(session, profile='healing', archive=fake, pkg=package, success=True):
                command = [str(exe), '--ttyd64-playtest-preflight', str(session), str(pkg), str(archive), profile]
                proc = subprocess.run(command, cwd=root, env=env, text=True, capture_output=True, timeout=60)
                result['runs'].append(dict(command=command, exit_code=proc.returncode,
                                           stdout=proc.stdout, stderr=proc.stderr))
                check('exit success' if success else 'exit failure', (proc.returncode == 0) == success)
                return proc

            for profile in ('healing', 'status'):
                session = root / ('new session ' + profile)
                run(session, profile)
                info = json.loads((session / 'playtest-session.json').read_text())
                check(profile + ' consumes setup arguments before engine ROM importer',
                      info['engine_argument_count'] == 1 and info['engine_argument_terminator'])
                # Windows may expand an 8.3 user directory (RUNNER~1) to its long
                # name. Prove actual identity, not equality of display strings.
                check(profile + ' isolated roots', Path(info['session']).samefile(session) and
                      Path(info['save_directory']).resolve() == (session / 'saves').resolve() and
                      Path(info['config']).samefile(session / 'paperboat.cfg.json'))
                check(profile + ' preflight does not create saves', not (session / 'saves').exists() and info['preflight_only'])
                check(profile + ' copies only supplied archive', sha(session / 'pm64.o2r') == sha(fake))
                check(profile + ' copies own archive', sha(session / 'paperboat.o2r') == sha(package / 'paperboat.o2r'))
                before = sha(session / 'paperboat.cfg.json')
                proc = run(session, profile, success=False)
                check(profile + ' refuses existing session', 'Session already exists' in proc.stderr and
                      sha(session / 'paperboat.cfg.json') == before)
            proc = run(root / 'missing archive session', archive=root / 'absent.o2r', success=False)
            check('missing archive diagnostic', 'setup failed' in proc.stderr and not (root / 'missing archive session').exists())
            run(root / 'bad profile session', profile='campaign', success=False)
            check('invalid profile creates nothing', not (root / 'bad profile session').exists())
            incomplete = root / 'incomplete package'
            incomplete.mkdir()
            run(root / 'missing package session', pkg=incomplete, success=False)
            check('missing package creates nothing', not (root / 'missing package session').exists())
            check('inherited normal home unchanged', sentinel.read_text() == 'normal configuration sentinel\n' and
                  sorted(p.name for p in unrelated.iterdir()) == ['paperboat.cfg.json'])
            if sys.platform == 'win32':
                launcher_root = root / 'Windows launcher sessions'
                command = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                           str(package / 'Play-TTYD64.ps1'), '-Archive', str(fake), '-SessionRoot',
                           str(launcher_root), '-PreflightOnly']
                proc = subprocess.run(command, cwd=root, env=env, text=True, capture_output=True, timeout=90)
                logs = {str(p.relative_to(launcher_root)): p.read_text(encoding='utf-8-sig')
                        for p in launcher_root.glob('logs-*/*') if p.is_file()}
                result['runs'].append(dict(command=command, exit_code=proc.returncode,
                                           stdout=proc.stdout, stderr=proc.stderr, launcher_logs=logs))
                check('Windows PowerShell 5.1 launcher exits successfully', proc.returncode == 0)
                manifests = list(launcher_root.glob('sessions/*/playtest-session.json'))
                check('Windows launcher defaults to one isolated status session', len(manifests) == 1 and
                      json.loads(manifests[0].read_text())['profile'] == 'status')
                info = json.loads(manifests[0].read_text())
                check('Windows launcher consumes setup arguments before engine ROM importer',
                      info['engine_argument_count'] == 1 and info['engine_argument_terminator'])
        result['status'] = 'pass'
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        result['ended_utc'] = utc()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + '\n')
        print(f"Playtest preflight: {result['status']}; {len(result['checks'])} checks; {output}")


if __name__ == '__main__':
    main()
