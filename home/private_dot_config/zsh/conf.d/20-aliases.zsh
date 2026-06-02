if command -v bat >/dev/null 2>&1; then
  alias cat=bat
elif command -v batcat >/dev/null 2>&1; then
  alias cat=batcat
fi

if command -v eza >/dev/null 2>&1; then
  alias ls='eza'
  alias ll='eza -lah'
fi

if command -v fdfind >/dev/null 2>&1; then
  alias fd=fdfind
fi
