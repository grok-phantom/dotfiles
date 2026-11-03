#!/bin/sh
# Compatibility entry point: explicit install, never part of chezmoi apply.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
exec "$root/scripts/software" herdr-plugins install --yes "$@"
