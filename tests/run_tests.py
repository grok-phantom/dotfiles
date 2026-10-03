"""Offline test entry point. Never installs tools or applies to the caller's home."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
SUITES = ('unit', 'static', 'cached-externals')


def git(*args):
    return subprocess.check_output(
        ['git', '--no-optional-locks', '-C', str(ROOT), *args], text=True).strip()


def run(command, env, log, timeout=300):
    try:
        with subprocess.Popen(command, cwd=ROOT, env=env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              start_new_session=True) as process:
            try:
                output, _ = process.communicate(timeout=timeout)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                os.killpg(process.pid, signal.SIGKILL)
                output, _ = process.communicate()
                log.write_text(output + '\nFAIL: suite interrupted or timed out.\n')
                return 1, log.read_text()
            log.write_text(output)
            return process.returncode, output
    except OSError as error:
        log.write_text(f'FAIL: {error}\n')
        return 1, log.read_text()


def static_checks(env):
    files = git('ls-files', '-z').split('\0')
    # Include new tooling while reviewing an uncommitted checkout.
    files += git('ls-files', '--others', '--exclude-standard', '-z').split('\0')
    count = 0
    for name in sorted(set(filter(None, files))):
        path = ROOT / name
        if path.suffix == '.py' or name in ('scripts/dotfiles', 'scripts/software'):
            ast.parse(path.read_text(), filename=name)
            count += 1
        elif path.suffix == '.json':
            json.loads(path.read_text())
            count += 1
        elif path.suffix == '.toml':
            tomllib.loads(path.read_text())
            count += 1
    for command in (['sh', '-n', 'scripts/test'],
                    ['bash', '-n', 'scripts/manual/macos-defaults.sh'],
                    ['git', 'diff', '--check']):
        subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True)
    lock = json.loads((ROOT/'home/.chezmoidata/external-lock.json').read_text())
    assert len(lock['external_lock']) == 20, 'Review the expected resource count when changing the lock'
    for entry in lock['external_lock']:
        assert re.fullmatch(r'[0-9a-f]{64}', entry['sha256'])
        assert entry['url'].startswith('https://')
    return f'PASS: parsed {count} Python/JSON/TOML files; shell syntax, diff whitespace and 20 lock entries checked.\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('suite', nargs='?', default='all', choices=(*SUITES, 'all'))
    parser.add_argument('--report-dir', type=Path, help='A new directory; existing directories are refused')
    parser.add_argument('--cache', type=Path, help='Previously downloaded upstream archives; never downloaded here')
    args = parser.parse_args()
    selected = ('unit', 'static') if args.suite == 'all' else (args.suite,)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    destination = args.report_dir or ROOT/'.test-results'/stamp
    destination = destination.resolve()
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    report = dict(schema_version=1, repository='dotfiles', commit=git('rev-parse', 'HEAD'),
                  branch=git('branch', '--show-current'), dirty=bool(git('status', '--porcelain')),
                  started_at=datetime.now(timezone.utc).isoformat(),
                  platform=dict(system=platform.system(), release=platform.release(), machine=platform.machine()),
                  python=dict(version=platform.python_version(), executable=sys.executable), dependencies={},
                  selected_suites=list(selected), suites=[dict(name=s, status='not_run', reason='Not selected') for s in SUITES])
    report['suites'].append(dict(name='macos-vm', status='not_run', reason='Requires a separately prepared VM and manual acceptance; see docs/macos-vm-acceptance.md'))
    with tempfile.TemporaryDirectory(prefix='dotfiles-test-run-') as directory:
        temp = Path(directory)
        env = dict(PATH=os.environ.get('PATH', os.defpath), LANG='en_US.UTF-8',
                   PYTHONNOUSERSITE='1')
        env.update(HOME=str(temp/'home'), XDG_CONFIG_HOME=str(temp/'config'),
                   XDG_CACHE_HOME=str(temp/'cache'), XDG_DATA_HOME=str(temp/'data'),
                   XDG_STATE_HOME=str(temp/'state'), TMPDIR=str(temp/'tmp'),
                   GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1',
                   GIT_TERMINAL_PROMPT='0', PYTHONDONTWRITEBYTECODE='1',
                   NO_PROXY='127.0.0.1,localhost,::1')
        for key in ('HOME', 'XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'TMPDIR'):
            Path(env[key]).mkdir(mode=0o700)
        for name, command in [('git', ['git', '--version']), ('chezmoi', ['chezmoi', '--version']), ('zsh', ['zsh', '--version'])]:
            if shutil.which(command[0]):
                result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=15)
                report['dependencies'][name] = result.stdout.strip() if result.returncode == 0 else 'unavailable'
            else:
                report['dependencies'][name] = 'missing'
        for suite in report['suites']:
            name = suite['name']
            if name not in selected:
                continue
            log = destination/(name+'.log')
            suite.update(log=log.name)
            suite.pop('reason', None)
            if name != 'static':
                missing = [name for name in ('git', 'chezmoi', 'zsh') if report['dependencies'][name] in ('missing', 'unavailable')]
                if missing or os.geteuid() == 0:
                    suite.update(status='blocked', reason='Run as an ordinary user with installed tools: '+(', '.join(missing) or 'root is unsupported'))
                    log.write_text(suite['reason']+'\n')
                    continue
            if name == 'static':
                try:
                    log.write_text(static_checks(env))
                    suite['status'] = 'passed'
                except (AssertionError, OSError, ValueError, SyntaxError, subprocess.CalledProcessError) as error:
                    log.write_text(f'FAIL: {type(error).__name__}: {error}\n')
                    suite['status'] = 'failed'
            elif name == 'unit':
                code, output = run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'], env, log)
                suite['status'] = 'passed' if code == 0 else 'failed'
                match = re.search(r'Ran (\d+) tests?', output)
                suite['tests_run'] = int(match.group(1)) if match else None
                suite['scope'] = 'Temporary targets with real chezmoi; network/package installers mocked; includes recovery scenarios'
            else:
                if not args.cache or not args.cache.is_dir():
                    suite.update(status='blocked', reason='Provide --cache with the 20 previously downloaded locked resources; no download was attempted')
                    log.write_text(suite['reason']+'\n')
                    continue
                locked = json.loads((ROOT/'home/.chezmoidata/external-lock.json').read_text())['external_lock']
                expected = [item['target'] if item['kind'] == 'font' else item['repo'].replace('/', '_')+'.tar.gz' for item in locked]
                missing = sorted(set(name for name in expected if not (args.cache/name).is_file()))
                if missing:
                    suite.update(status='blocked', reason='Cache is incomplete: '+', '.join(missing))
                    log.write_text(suite['reason']+'\n')
                    continue
                code, _ = run([sys.executable, '-B', 'tests/check_cached_externals.py', '--cache', str(args.cache.resolve())], env, log)
                suite['status'] = 'passed' if code == 0 else 'failed'
                suite['scope'] = 'Offline full-profile temporary plan/apply/verify and repeat; no installers'
        for suite in report['suites']:
            if 'log' in suite:
                path = destination/suite['log']
                path.chmod(0o600)
                suite['log_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    report['status'] = 'failed' if any(s['status'] == 'failed' for s in report['suites']) else 'blocked' if any(s['status'] == 'blocked' for s in report['suites']) else 'passed'
    result = destination/'report.json'
    result.write_text(json.dumps(report, indent=2)+'\n')
    result.chmod(0o600)
    for suite in report['suites']:
        print(f"{suite['name']}: {suite['status']}" + (f" ({suite['tests_run']} tests)" if suite.get('tests_run') is not None else ''))
    print(f'Report: {result}')
    return 0 if report['status'] == 'passed' else 1 if report['status'] == 'failed' else 2


if __name__ == '__main__':
    sys.exit(main())
