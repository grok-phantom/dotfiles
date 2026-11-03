"""Subprocess lifecycle, private diagnostics and host checks (Python 3.9+)."""
from contextlib import contextmanager
import os
from pathlib import Path
import platform
import signal
import subprocess
import time


class Stop(RuntimeError):
    pass


_diagnostics = None


@contextmanager
def diagnostic_session(directory, repo):
    """Opt-in local evidence. Rendered configuration is never logged."""
    global _diagnostics
    if directory is None:
        yield
        return
    directory = directory.resolve()
    repo = repo.resolve()
    if directory == repo or repo in directory.parents:
        raise Stop('Store diagnostics outside the source repository')
    directory.mkdir(mode=0o700, exist_ok=False)
    fd = os.open(directory/'commands.log', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    previous = _diagnostics
    try:
        with os.fdopen(fd, 'wb') as stream:
            _diagnostics = stream
            yield
    finally:
        _diagnostics = previous


def record_diagnostic(stage, code, elapsed, stdout, stderr, include_output):
    if _diagnostics is None:
        return
    _diagnostics.write(f'{stage}: exit={code}, seconds={elapsed:.3f}\n'.encode())
    if include_output:
        _diagnostics.write(b'stdout:\n' + stdout + b'\nstderr:\n' + stderr + b'\n')
    _diagnostics.flush()


def interrupt(signum, frame):
    raise KeyboardInterrupt


def run(args, *, env=None, input=None, timeout=None, stage=None, diagnostic_output=False, interactive=False):
    stage = stage or Path(args[0]).name
    started = time.monotonic()
    if interactive:
        # Attached to the terminal so tools such as sudo can prompt; output is neither captured nor logged.
        code = subprocess.run([str(a) for a in args], env=env, timeout=timeout).returncode
        record_diagnostic(stage, code, time.monotonic()-started, b'', b'', False)
        if code:
            raise Stop(f"{stage} failed (exit {code}); no later step was run")
        return b''
    with subprocess.Popen([str(a) for a in args], stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, start_new_session=True) as process:
        previous_term_handler = signal.signal(signal.SIGTERM, interrupt)
        try:
            stdout, stderr = process.communicate(input, timeout=timeout)
        except BaseException as error:
            # Detached subprocesses must not continue installing/applying after cancellation.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()
            record_diagnostic(stage, 'interrupted', time.monotonic()-started, stdout, stderr, diagnostic_output)
            if isinstance(error, subprocess.TimeoutExpired):
                raise Stop(f'{stage} timed out; no later step was run')
            raise
        finally:
            signal.signal(signal.SIGTERM, previous_term_handler)
    record_diagnostic(stage, process.returncode, time.monotonic()-started, stdout, stderr, diagnostic_output)
    if process.returncode:
        # Do not echo rendered configurations, credentials in URLs, or tool stderr.
        raise Stop(f"{stage} failed (exit {process.returncode}); no later step was run")
    return stdout


def host():
    value = (platform.system(), platform.machine())
    if value[0] not in ('Darwin', 'Linux') or value[1] not in ('arm64', 'aarch64', 'x86_64'):
        raise Stop('Unsupported OS/architecture; supported: macOS/Linux on arm64 or x86_64')
    if value == ('Darwin', 'aarch64'):
        raise Stop('Unsupported macOS architecture')
    return list(value)
