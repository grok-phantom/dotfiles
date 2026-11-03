#!/bin/sh
# Run explicitly on each host where Claude Code or Codex runs.
# Herdr merges its own hooks; chezmoi does not copy live agent configuration.
set -eu
command -v herdr >/dev/null 2>&1 || {
    echo 'herdr is not installed' >&2
    exit 1
}
if [ -d "${CLAUDE_CONFIG_DIR:-$HOME/.claude}" ]; then
    herdr integration install claude
fi
if [ -d "${CODEX_HOME:-$HOME/.codex}" ]; then
    herdr integration install codex
fi
herdr integration status
