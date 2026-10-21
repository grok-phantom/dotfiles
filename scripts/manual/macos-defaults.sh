#!/bin/bash

set -euo pipefail

if [[ $(uname -s) != Darwin || ${1:-} != --apply ]]; then
  echo "Review this script first; run on macOS with --apply to change preferences." >&2
  exit 1
fi

# Safari search provider.
safari_defaults_ok=true
defaults write com.apple.Safari SearchProviderIdentifier -string "com.google.www" || safari_defaults_ok=false
defaults write com.apple.Safari SearchProviderShortName -string "Google" || safari_defaults_ok=false
defaults write com.apple.Safari SearchProviderURL -string "https://www.google.com/search?q={searchTerms}" || safari_defaults_ok=false
if [ "$safari_defaults_ok" = false ]; then
  echo "Warning: could not update Safari search provider. Review macOS permissions manually; no additional access is required for dotfiles updates." >&2
fi

# Trackpad: tap to click.
defaults write com.apple.AppleMultitouchTrackpad Clicking -bool true
defaults write com.apple.driver.AppleBluetoothMultitouch.trackpad Clicking -bool true
defaults write NSGlobalDomain com.apple.mouse.tapBehavior -int 1
defaults write NSGlobalDomain com.apple.trackpad.enableSecondaryClick -bool true
# Trackpad: disable three-finger tap for Look Up & data detectors.
defaults write com.apple.AppleMultitouchTrackpad TrackpadThreeFingerTapGesture -int 0
defaults write com.apple.driver.AppleBluetoothMultitouch.trackpad TrackpadThreeFingerTapGesture -int 0

# Appearance: switch light/dark automatically.
defaults write NSGlobalDomain AppleInterfaceStyleSwitchesAutomatically -bool true

# Dock: make icons smaller.
defaults write com.apple.dock tilesize -int 31
# Mission Control: keep Spaces in a fixed order.
defaults write com.apple.dock mru-spaces -bool false

# Window tiling: no gaps between tiled windows.
defaults write com.apple.WindowManager EnableTiledWindowMargins -bool false

# Keyboard: fast key repeat (helps vim navigation on held keys).
defaults write NSGlobalDomain KeyRepeat -int 2
defaults write NSGlobalDomain InitialKeyRepeat -int 15
# Disable press-and-hold accent popup so held keys repeat normally.
defaults write NSGlobalDomain ApplePressAndHoldEnabled -bool false

# Finder: show path bar, status bar, and filename extensions.
defaults write com.apple.finder ShowPathbar -bool true
defaults write com.apple.finder ShowStatusBar -bool true
defaults write com.apple.finder FXPreferredViewStyle -string "Nlsv"
defaults write NSGlobalDomain AppleShowAllExtensions -bool true

# Menu bar: hide icons we don't want cluttering the bar.
# macOS 26+ stores these as "NSStatusItem VisibleCC <item>"; the older
# "NSStatusItem Visible" and Spotlight MenuItemHidden keys are ignored.
# Spotlight/Search icon.
defaults write com.apple.Spotlight "NSStatusItem VisibleCC Item-0" -bool false
# Wi-Fi (available in Control Center dropdown, no need on bar).
defaults write com.apple.controlcenter "NSStatusItem VisibleCC WiFi" -bool false
# Battery (available in Control Center).
defaults write com.apple.controlcenter "NSStatusItem VisibleCC Battery" -bool false
# Text Input / input-source switcher.
defaults write com.apple.TextInputMenu visible -bool false

# Restart only the affected services so changes are picked up.
killall Dock           >/dev/null 2>&1 || true
killall Finder         >/dev/null 2>&1 || true
killall SystemUIServer >/dev/null 2>&1 || true
killall ControlCenter  >/dev/null 2>&1 || true
killall Spotlight      >/dev/null 2>&1 || true

echo "Applied macOS defaults."
