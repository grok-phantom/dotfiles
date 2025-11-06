#!/bin/bash

set -eufo pipefail

if [ -x "$HOME/.vim_runtime/install_awesome_vimrc.sh" ]; then
  sh "$HOME/.vim_runtime/install_awesome_vimrc.sh"
fi

if [ -d "$HOME/.tmux" ] && [ -f "$HOME/.tmux/.tmux.conf" ]; then
  ln -sf "$HOME/.tmux/.tmux.conf" "$HOME/.tmux.conf"
  if [ -f "$HOME/.tmux/.tmux.conf.local" ]; then
    ln -sf "$HOME/.tmux/.tmux.conf.local" "$HOME/.tmux.conf.local"
  fi

  if command -v tmux >/dev/null 2>&1; then
    if tmux has-session 2>/dev/null; then
      tmux source-file "$HOME/.tmux.conf"
    fi
  fi
fi
