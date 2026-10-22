#!/bin/bash

set -euo pipefail

if [[ $(uname -s) != Darwin ]]; then
  echo "macos-defaults: run on macOS; use --check to preview preferences." >&2
  exit 1
fi

python=${PYTHON:-python3}
if ! command -v "$python" >/dev/null 2>&1 ||
   ! "$python" -I -c 'import sys; sys.exit(sys.version_info < (3, 9))'; then
  echo "macos-defaults: requires an existing Python 3.9+; set PYTHON if needed." >&2
  exit 1
fi
exec "$python" -I -B "$(dirname -- "${BASH_SOURCE[0]}")/macos_defaults.py" "$@"
