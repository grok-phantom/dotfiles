# cmux names the tmux sessions it creates cmux-new-<id>; rename one after the
# first directory its shell moves to, so the cmux sidebar shows the project.
if [[ -n "$TMUX" ]] && (( $+commands[tmux] )); then
  _tmux_name_cmux_session() {
    [[ "$PWD" != "$HOME" ]] || return 0
    local current name candidate n=2
    current="$(tmux display-message -t "$TMUX_PANE" -p '#{session_name}' 2>/dev/null)" || return 0
    [[ "$current" == cmux-new-* ]] || {
      add-zsh-hook -d chpwd _tmux_name_cmux_session
      return 0
    }
    # tmux rejects . and : in session names.
    name="${${PWD:t}#.}"
    name="${name//[.:]/-}"
    [[ -n "$name" ]] || return 0
    candidate="$name"
    while tmux has-session -t "=$candidate" 2>/dev/null; do
      candidate="$name-$((n++))"
    done
    tmux rename-session -t "$TMUX_PANE" -- "$candidate" 2>/dev/null
  }
  autoload -Uz add-zsh-hook
  add-zsh-hook chpwd _tmux_name_cmux_session
  _tmux_name_cmux_session
fi
