"""Provision one hash-locked test binary in an ephemeral GitHub runner only."""
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import tarfile
import urllib.request

if __name__ == '__main__':
    if os.environ.get('GITHUB_ACTIONS') != 'true' or not os.environ.get('RUNNER_TEMP'):
        raise SystemExit('CI-only helper. Local tests never install dependencies.')
    lock = json.loads(Path(__file__).with_name('ci-tools.json').read_text())
    architecture = {'x86_64': 'amd64', 'aarch64': 'arm64', 'arm64': 'arm64'}[platform.machine()]
    key = platform.system().lower() + '_' + architecture
    name = f"chezmoi_{lock['chezmoi_version']}_{key}.tar.gz"
    url = f"https://github.com/twpayne/chezmoi/releases/download/v{lock['chezmoi_version']}/{name}"
    with urllib.request.urlopen(url, timeout=60) as response:
        content = response.read()
    if hashlib.sha256(content).hexdigest() != lock['assets'][key]:
        raise SystemExit('Downloaded chezmoi archive does not match the reviewed digest')
    directory = Path(os.environ['RUNNER_TEMP'])/'dotfiles-ci-bin'
    directory.mkdir(mode=0o700, exist_ok=False)
    with tarfile.open(fileobj=io.BytesIO(content), mode='r:gz') as archive:
        member = archive.getmember('chezmoi')
        if not member.isfile():
            raise SystemExit('Expected a regular chezmoi executable in the release archive')
        binary = directory/'chezmoi'
        binary.write_bytes(archive.extractfile(member).read())
        binary.chmod(0o700)
    with open(os.environ['GITHUB_PATH'], 'a') as output:
        output.write(str(directory)+'\n')
