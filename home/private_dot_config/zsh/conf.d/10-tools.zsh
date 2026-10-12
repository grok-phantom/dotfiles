if command -v zoxide >/dev/null 2>&1; then
  eval "$(zoxide init zsh)"
fi
if command -v atuin >/dev/null 2>&1; then
  # zsh-vi-mode rebinds keys on its lazy init; bind atuin afterwards to keep Ctrl-R/Up.
  if (( $+functions[zvm_init] )) && [[ "${ZVM_INIT_MODE:-}" != sourcing ]]; then
    zvm_after_init_commands+=('eval "$(atuin init zsh)"')
  else
    eval "$(atuin init zsh)"
  fi
fi
