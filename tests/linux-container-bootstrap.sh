#!/bin/bash
# Disposable Ubuntu container only; never a host installation entry point.
set -eufo pipefail
test -f /.dockerenv && test "$(id -u)" = 0
cd "$(dirname "$0")/.."
export DEBIAN_FRONTEND=noninteractive
# Ubuntu's minimal image otherwise drops the fzf Vim runtime as documentation.
printf 'path-include=/usr/share/doc/fzf/*\n' > /etc/dpkg/dpkg.cfg.d/zz-fzf-runtime
if [[ -n ${http_proxy:-} ]]; then
    printf 'Acquire::http::Proxy "%s";\nAcquire::https::Proxy "%s";\nAcquire::http::Pipeline-Depth "0";\n' \
        "$http_proxy" "${https_proxy:-$http_proxy}" > /etc/apt/apt.conf.d/99-validation-proxy
fi
apt-get update
# jq/rsync enable the offline suite's clipboard and sync cases.
apt-get install -y --no-install-recommends ca-certificates curl git python3 zsh openssh-client sudo jq rsync
python3 - <<'PY'
import hashlib, io, json, pathlib, tarfile, urllib.request
lock = json.loads(pathlib.Path('tests/ci-tools.json').read_text())
name = f"chezmoi_{lock['chezmoi_version']}_linux_amd64.tar.gz"
url = f"https://github.com/twpayne/chezmoi/releases/download/v{lock['chezmoi_version']}/{name}"
with urllib.request.urlopen(url, timeout=120) as response:
    data = response.read()
assert hashlib.sha256(data).hexdigest() == lock['assets']['linux_amd64']
with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
    binary = pathlib.Path('/usr/local/bin/chezmoi')
    binary.write_bytes(archive.extractfile('chezmoi').read())
    binary.chmod(0o755)
PY
useradd --create-home --shell /bin/zsh tester
printf 'tester ALL=(ALL) NOPASSWD: ALL\n' > /etc/sudoers.d/tester
cp -a . /home/tester/repo
chown -R tester:tester /home/tester/repo
