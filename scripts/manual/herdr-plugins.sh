#!/bin/sh
# Explicit install on each host; never part of chezmoi apply.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
command -v herdr >/dev/null
command -v jq >/dev/null
while IFS="$(printf '\t')" read -r source revision version; do
    case "$source" in ''|'#'*) continue ;; esac
    installed=$(herdr plugin list --json)
    if printf '%s' "$installed" | jq -e --arg source "$source" --arg revision "$revision" '
        any(.result.plugins[]?; .enabled == true and
            ((.source.owner + "/" + .source.repo) == $source) and
            .source.resolved_commit == $revision and .source.requested_ref == $revision)
    ' >/dev/null; then
        printf 'Already installed: %s @ %s\n' "$source" "$revision"
        continue
    fi
    tool=
    case "$source" in
        kryptamine/herdr-auto-title) tool=go ;;
        thanhdat77/herdr-navigator) tool=cargo ;;
    esac
    if [ -n "$tool" ] && ! command -v "$tool" >/dev/null 2>&1; then
        printf 'Missing build tool for %s: %s\n' "$source" "$tool" >&2
        exit 1
    fi
    # herdr-plus otherwise downloads latest when Go is absent.
    VERSION="$version" herdr plugin install "$source" --ref "$revision" --yes
done < "$root/locks/herdr-plugins.tsv"
python3 "$root/scripts/manual/herdr-quicklook-fix.py"
# Local pane entrypoints let Plus close its popup after launching an agent tab.
herdr plugin link "$HOME/.config/herdr/plugins/local/dotfiles-quick-actions" --enabled
herdr plugin list
