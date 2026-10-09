"""Actual runtime assertions on the disposable home built by cached integration."""
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


class Blocked(RuntimeError):
    pass


def check(home, environment):
    env = dict(environment, TERM='xterm-256color', PYTHONNOUSERSITE='1',
               POWERLEVEL9K_DISABLE_GITSTATUS='true')
    env.pop('TERM_PROGRAM', None)
    env.pop('TMUX', None)
    for name in ('zsh', 'vim', 'tmux', 'fzf', 'ctags'):
        if not shutil.which(name, path=env['PATH']):
            raise Blocked('Required runtime tool missing: '+name)

    def call(command, *, check=True):
        result = subprocess.run([str(x) for x in command], env=env, cwd=home,
                                capture_output=True, text=True, timeout=60)
        if check and result.returncode:
            raise RuntimeError(Path(str(command[0])).name+' failed:\n'+result.stdout+result.stderr)
        return result

    ctags = call(['ctags', '--version'], check=False)
    if ctags.returncode or 'Universal Ctags' not in ctags.stdout:
        raise Blocked('Universal Ctags is required (system BSD ctags is insufficient)')
    if '+python3' not in call(['vim', '--version']).stdout:
        raise Blocked('Vim requires Python 3 support')
    version = re.match(r'(\d+)\.(\d+)\.(\d+)', call(['fzf', '--version']).stdout)
    if not version or tuple(map(int, version.groups())) < (0, 54, 0):
        raise Blocked('fzf.vim requires fzf >= 0.54.0')
    shell = call(['zsh', '-i', '-c', '[[ -n "$ZSH_VERSION" && -n "$ZSH" ]] || exit 1; '
                  '(( $+functions[compdef] )) || exit 1; print runtime-shell-ok'])
    if shell.stderr.strip() or 'runtime-shell-ok' not in shell.stdout:
        raise RuntimeError('Zsh startup diagnostics:\n'+shell.stdout+shell.stderr)
    print('PASS: full Zsh startup and completion initialization')
    result_file = home/'vim-result'
    env['VIM_SMOKE_RESULT'] = str(result_file)
    try:
        # MRU menus need a GUI/menu context absent in batch Ex mode.
        call(['vim', '-i', 'NONE', '-n', '-N', '-es', '--cmd', 'let g:MRU_Add_Menu=0',
              '-V1'+str(home/'vim.log'), '-u', home/'.vimrc', '-S', ROOT/'tests/fixtures/runtime.vim'])
    except RuntimeError as error:
        details = result_file.read_text() if result_file.exists() else ''
        if (home/'vim.log').exists():
            details += (home/'vim.log').read_text()[-6000:]
        raise RuntimeError(str(error)+'\n'+details) from error
    if result_file.read_text().strip() != 'PASS':
        raise RuntimeError('Vim runtime assertions did not complete')
    print('PASS: Vim +python3, Jedi completion/signatures/goto, fzf runtime, Tagbar and ALE')
    tmux_smoke(home, env, call)


def tmux_smoke(home, env, call):
    socket_directory = tempfile.TemporaryDirectory(prefix='dotfiles-tmux-', dir='/tmp')
    socket = Path(socket_directory.name)/'socket'
    (home/'.tmux.conf.local').write_text('')
    env.update(TMUX_PROGRAM=shutil.which('tmux', path=env['PATH']), TMUX_SOCKET=str(socket),
               TMUX_CONF=str(home/'.tmux.conf'), TMUX_CONF_LOCAL=str(home/'.tmux.conf.local'))
    def terminate(signum, frame):
        raise InterruptedError('Runtime suite terminated')
    previous = signal.signal(signal.SIGTERM, terminate)
    try:
        call(['tmux', '-S', socket, '-f', home/'.tmux.conf', 'new-session', '-d', '-s', 'smoke', '/bin/cat'])
        call(['tmux', '-S', socket, 'source-file', '-n', home/'.tmux.conf'])
        call(['tmux', '-S', socket, 'has-session', '-t', 'smoke'])
        if call(['tmux', '-S', socket, 'show-options', '-gv', 'history-limit']).stdout.strip() != '5000':
            raise RuntimeError('Tmux full configuration did not set history-limit')
        print('PASS: Tmux full config, dedicated socket/session and expected option')
    finally:
        try:
            subprocess.run(['tmux', '-S', str(socket), 'kill-server'], env=env, capture_output=True, timeout=3)
        finally:
            signal.signal(signal.SIGTERM, previous)
            socket_directory.cleanup()
