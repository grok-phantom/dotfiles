# Terminals

macOS `full` manages one iTerm2 Dynamic Profile and a minimal Ghostty config.
`core` and Linux skip both; Linux package installation is unchanged.

## iTerm2

`wizplus` has its own stable GUID. The old exported GUID could collide with a
regular profile, causing iTerm2 to ignore the dynamic profile. Existing regular
profiles and the default profile are never replaced or selected automatically.
Choose **Profiles → wizplus** to try it.

The 46-line JSON explicitly owns MesloLGS NF 11, the existing Gruvbox ANSI palette,
selection/cursor colors, Option-key behavior, terminal type, mouse reporting,
scrollback/bell preferences and application-driven resize behavior. The empty
profile keyboard map is intentional; app-level shortcuts remain local. Other
fields inherit the default profile, including login shell, working directory,
close handling and window size. No global plist, session history, SSH commands or
machine paths are tracked. Keep global preferences local until a concrete portable
setting is needed. Changing the default parent later can change inherited fields.

Dynamic Profiles require `Name` and `Guid`; a regular profile with the same GUID
wins. See [iTerm2 documentation](https://iterm2.com/documentation-dynamic-profiles.html).

## Ghostty

Start with only `font-family = MesloLGS NF`, size 11, and `Gruvbox Dark`.
The existing full-profile font provision supplies MesloLGS NF. `config` remains
supported by 1.3.1 and older releases; `config.ghostty` is also supported since
1.2.3. A macOS config under `~/Library/Application Support/com.mitchellh.ghostty/`
loads after XDG config and may override it. Avoid maintaining conflicting copies.

Ghostty 1.3.1 stable was checked with its own CLI. Run `./scripts/verify-terminals`
after upgrades; it validates both source and effective config, font/theme presence,
and native search binding, failing when a required capability disappears.
This does not establish compatibility with every older release or GUI behavior.

Default macOS shortcuts from that binary:

| Action | Shortcut |
| --- | --- |
| Tab | Cmd+T; Ctrl+Tab / Ctrl+Shift+Tab |
| Split right / down | Cmd+D / Cmd+Shift+D |
| Focus split | Cmd+[ / Cmd+] |
| Search | Cmd+F; Cmd+G / Cmd+Shift+G |
| Copy / paste | Cmd+C / Cmd+V |
| Fullscreen | Cmd+Enter or Ctrl+Cmd+F |

Automatic zsh integration is enabled; existing zsh/p10k/fzf/zoxide/Yazi/tmux
configuration stays intact. Do not source iTerm2 integration in Ghostty or set
`TERM` globally. Ghostty defaults to `xterm-ghostty`; its bundled terminfo works in
its own environment but may be missing on remote systems. SSH environment/terminfo
injection is disabled by default in this version. Do not enable remote installation
without reviewing the target. iTerm2's native tmux control-mode UI is not replicated
by Ghostty; normal tmux inside the terminal is a separate workflow.

Window state uses the macOS-dependent `window-save-state = default`; this is not a
promise to restore running shell jobs. Before making Ghostty primary, test Chinese
IME composition/candidates, mixed-width text, paste safety, Yazi previews, tmux,
search in long output, tabs/splits, and quit/relaunch with disposable sessions.
Automated text injection cannot verify IME feel. Keep iTerm2 available meanwhile.

## Apply and rollback

Preview/apply only these two targets with `chezmoi diff` / `chezmoi apply
--exclude scripts`; create `~/.config/ghostty` first if absent. Do not apply the whole
home tree just to trial a terminal. Back up the current DynamicProfiles JSON and
local iTerm2 plist privately before changing them; never commit a live plist.

Rollback the source with a forward `git revert` of the terminal change, then
restore the backed-up DynamicProfiles JSON. Remove the newly added Ghostty config
if there was no previous file (Git revert alone does not remove an unmanaged target).
Quit only disposable Ghostty sessions and move Ghostty.app to Trash if unwanted.
No default-terminal, startup or accessibility permission change is required.
Do not restore a stale whole plist over newer user preferences; it is a last-resort
backup, to restore only with iTerm2 fully quit and explicit review.

Sources: [installation](https://ghostty.org/download),
[configuration](https://ghostty.org/docs/config),
[shell integration](https://ghostty.org/docs/features/shell-integration).
