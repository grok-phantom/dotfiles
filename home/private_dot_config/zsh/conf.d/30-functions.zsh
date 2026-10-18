if command -v yazi >/dev/null 2>&1; then
  y() {
    local tmp cwd
    tmp="$(mktemp "${TMPDIR:-/tmp}/yazi-cwd.XXXXXX")" || return
    command yazi "$@" --cwd-file="$tmp"
    if cwd="$(command cat -- "$tmp" 2>/dev/null)" && [[ -n "$cwd" && "$cwd" != "$PWD" ]]; then
      builtin cd -- "$cwd"
    fi
    command rm -f -- "$tmp"
  }
  alias yy='y'
  alias r='y'
  alias ranger='y'
fi

# cct [name] [claude args...]: start Claude Code in a throwaway project under
# ~/workspace/scratch, so ad-hoc sessions never run from $HOME. A fixed path
# per name keeps `claude --resume` working; omit the name for a timestamp.
cct() {
  local name="${1:-$(date +%Y%m%d-%H%M)}"
  (( $# )) && shift
  if [[ "$name" == */* || "$name" == .* ]]; then
    print -u2 "cct: name must be a plain directory name"
    return 1
  fi
  local dir="$HOME/workspace/scratch/$name"
  mkdir -p -- "$dir" && builtin cd -- "$dir" && command claude "$@"
}
