#!/bin/sh
# Ghostty's performable Cmd+V already handled ordinary clipboard text.
# Use the context captured for this invocation, never a later focused pane.
set -eu
context=${HERDR_PLUGIN_CONTEXT_JSON:?missing plugin context}
pane=$(printf '%s' "$context" | jq -er '.focused_pane_id | select(type == "string" and length > 0)')
agent=$(printf '%s' "$context" | jq -r '.focused_pane_agent // ""')
key=super+v
if [ "$agent" = codex ]; then
    key=ctrl+alt+v
fi
exec "${HERDR_BIN_PATH:-herdr}" pane send-keys "$pane" "$key"
