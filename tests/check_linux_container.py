"""Online acceptance in a fresh disposable Ubuntu Docker HOME, never in scripts/test all."""
import argparse
import hashlib
import io
import os
from pathlib import Path
import subprocess
import tarfile
import time
import urllib.request
import zipfile

from check_runtime import check

ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
EVIDENCE = HOME / 'evidence'


def run(*args, **kwargs):
    print('+', *map(str, args), flush=True)
    return subprocess.run(list(map(str, args)), cwd=ROOT, check=True, **kwargs)


def download(url, digest):
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != digest:
        raise RuntimeError('Checksum mismatch: ' + url)
    return data


def apply_twice(profile, component):
    for attempt in ('first', 'repeat'):
        plan = EVIDENCE / f'{profile}-{component}-{attempt}.json'
        options = ['--profile', profile, '--component', component]
        run('./scripts/dotfiles', 'plan', *options, '--plan', plan)
        run('./scripts/dotfiles', 'apply', *options, '--plan', plan, '--yes')
        run('./scripts/dotfiles', 'verify', *options)


def terminal_smoke():
    socket = EVIDENCE / 'tmux.sock'
    tmux = ['tmux', '-S', socket]
    sample = EVIDENCE / 'browse'
    (sample / 'child').mkdir(parents=True)
    cwd_file = EVIDENCE / 'yazi-cwd'
    try:
        run(*tmux, '-f', HOME / '.tmux.conf', 'new-session', '-d', '-s', 'shell',
            '-x', '120', '-y', '30', 'zsh -il')
        probe = ('(( $+functions[p10k] && $+functions[compdef] )) && '
                 '[[ $_comps[git] == _git ]] && print PTY-SHELL-OK')
        run(*tmux, 'send-keys', '-t', 'shell', probe, 'Enter')
        for _ in range(30):
            screen = run(*tmux, 'capture-pane', '-p', '-t', 'shell', capture_output=True, text=True).stdout
            if '\nPTY-SHELL-OK\n' in screen:
                break
            time.sleep(1)
        else:
            raise RuntimeError('Interactive p10k/completion probe failed:\n' + screen)
        if 'failed to initialize' in screen or '[ERROR]' in screen:
            raise RuntimeError('Interactive shell reported startup errors:\n' + screen)
        run(*tmux, 'send-keys', '-t', 'shell', 'git --vers', 'Tab', 'Enter')
        time.sleep(1)
        screen = run(*tmux, 'capture-pane', '-p', '-t', 'shell', capture_output=True, text=True).stdout
        (EVIDENCE / 'shell-screen.txt').write_text(screen)
        assert 'git version ' in screen, 'OMZ Git Tab completion did not execute git --version'
        run(*tmux, 'new-session', '-d', '-s', 'yazi', '-x', '120', '-y', '30',
            f'yazi --cwd-file={cwd_file} {sample}')
        time.sleep(2)
        with (EVIDENCE / 'yazi-screen.txt').open('w') as log:
            run(*tmux, 'capture-pane', '-p', '-t', 'yazi', stdout=log)
        run(*tmux, 'send-keys', '-t', 'yazi', 'l')
        time.sleep(1)
        run(*tmux, 'send-keys', '-t', 'yazi', 'q')
        for _ in range(10):
            if cwd_file.exists():
                break
            time.sleep(1)
        assert cwd_file.read_text().strip() == str(sample / 'child'), 'Yazi smart-enter did not navigate'
        print('PASS: PTY p10k, Git completion, Yazi smart-enter and clean quit', flush=True)
    finally:
        subprocess.run(list(map(str, [*tmux, 'kill-server'])), check=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manager', choices=('apt', 'brew'), default='apt',
                        help='brew requires Homebrew already installed in the test container')
    args = parser.parse_args()
    if not Path('/.dockerenv').is_file() or os.geteuid() == 0:
        raise SystemExit('Run as the test user inside a disposable Docker container')
    if (HOME / '.config/chezmoi/chezmoi.toml').exists():
        raise SystemExit('Use a fresh test HOME; this check initializes and applies dotfiles')
    EVIDENCE.mkdir()
    run('git', 'init', '-b', 'main')
    run('git', 'add', '.')
    run('git', '-c', 'user.name=Container', '-c', 'user.email=test@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Disposable source snapshot')
    run('./scripts/test', 'all', '--report-dir', EVIDENCE / 'offline')
    run('chezmoi', 'init', '--source', ROOT,
        '--promptBool', 'Is this a company machine?=false,Is this ephemeral?=false,Do you have sudo privileges on this machine?=true',
        '--promptString', 'Git email (blank to configure locally)=test@example.invalid,Git name (blank to configure locally)=Container',
        '--promptChoice', 'Configuration profile=core')
    config = HOME / '.config/chezmoi/chezmoi.toml'
    config.write_text(config.read_text().replace('homebrew = true', 'homebrew = false') +
                      '\n    herdr_enabled = false\n    cmux_enabled = false\n    ssh_managed = false\n')
    run('./scripts/check-linux', '--profile', 'core')
    apply_twice('core', 'config')
    run('zsh', '-lic', '[[ -z "$ZSH" ]] && print CORE-SHELL-OK')
    for name in ('.oh-my-zsh', '.vimrc', '.tmux.conf', '.config/yazi', 'Library'):
        assert not (HOME / name).exists(), name
    for action in ('plan', 'install', 'verify'):
        run('./scripts/software', 'packages', action, '--manager', 'apt', '--yes')
    with (EVIDENCE / 'packages.tsv').open('w') as log:
        run('dpkg-query', '-W', stdout=log)
    config.write_text(config.read_text().replace('profile = "core"', 'profile = "full"'))
    with (EVIDENCE / 'apt-full-preflight.log').open('w') as log:
        result = subprocess.run(['./scripts/check-linux', '--profile', 'full'], cwd=ROOT,
                                stdout=log, stderr=subprocess.STDOUT)
    old_fzf = 'fzf >= 0.54.0' in (EVIDENCE / 'apt-full-preflight.log').read_text()
    assert result.returncode == (2 if old_fzf else 0)
    apply_twice('full', 'externals')
    if args.manager == 'brew':
        config.write_text(config.read_text().replace('homebrew = false', 'homebrew = true'))
        for action in ('plan', 'install', 'verify', 'install'):
            run('./scripts/software', 'packages', action, '--manager', 'brew', '--yes')
        apply_twice('full', 'config')
    else:
        # Supplemental official assets are test dependencies, not apt manifest entries.
        tools = HOME / '.local/bin'
        tools.mkdir(parents=True, exist_ok=True)
        if old_fzf:
            fzf = download('https://github.com/junegunn/fzf/releases/download/v0.65.2/fzf-0.65.2-linux_amd64.tar.gz',
                           '5eb8efc0e94aa559f84ea83eeba99bea7dce818e63f92b4b62e60663220f1c14')
            with tarfile.open(fileobj=io.BytesIO(fzf), mode='r:gz') as archive:
                (tools / 'fzf').write_bytes(archive.extractfile('fzf').read())
            (tools / 'fzf').chmod(0o755)
        yazi = download('https://github.com/sxyazi/yazi/releases/download/v26.9.1/yazi-x86_64-unknown-linux-gnu.zip',
                        'a02fe91d3304294048c681f010f1100856872a4e98ecf6927328e888d40a6ad2')
        with zipfile.ZipFile(io.BytesIO(yazi)) as archive:
            for name in ('yazi', 'ya'):
                (tools / name).write_bytes(archive.read('yazi-x86_64-unknown-linux-gnu/' + name))
                (tools / name).chmod(0o755)
        os.environ['PATH'] = str(tools) + ':' + os.environ['PATH']
    os.environ['TERM'] = 'xterm-256color'
    run('./scripts/check-linux', '--profile', 'full')
    for name in ('fzf', 'yazi', 'ya', 'vim', 'tmux', 'zsh'):
        run(name, '--version' if name != 'tmux' else '-V')
    # The batch smoke check empties this file; the PTY must use the applied config.
    tmux_local = HOME / '.tmux.conf.local'
    original = tmux_local.read_text()
    try:
        check(HOME, dict(os.environ))
    finally:
        tmux_local.write_text(original)
    terminal_smoke()
    if args.manager == 'brew':
        with (EVIDENCE / 'brew-list.json').open('w') as log:
            run('brew', 'info', '--json=v2', '--installed', stdout=log)
        with (EVIDENCE / 'coexistence.log').open('w') as log:
            run('zsh', '-lic', 'for tool in git curl python3 vim tmux fzf zsh yazi; do '
                'print -- "$tool: $(whence -p $tool)"; '
                '[[ $(whence -p $tool) == /home/linuxbrew/.linuxbrew/bin/* ]] || exit 1; done', stdout=log)
            for name, option in (('git', '--version'), ('curl', '--version'), ('python3', '--version'),
                                 ('vim', '--version'), ('tmux', '-V'), ('fzf', '--version'), ('zsh', '--version')):
                run('/usr/bin/' + name, option, stdout=log)
            for binary in ('/usr/bin/vim', '/home/linuxbrew/.linuxbrew/bin/vim',
                           '/usr/bin/tmux', '/home/linuxbrew/.linuxbrew/bin/tmux'):
                run('ldd', binary, stdout=log)
        run('brew', 'linkage', '--test', 'vim', 'tmux', 'fzf', 'yazi')
    print('PASS: container installation and runtime; desktop, SSH and reboot acceptance remain separate')


if __name__ == '__main__':
    main()
