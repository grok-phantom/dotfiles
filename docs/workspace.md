# Workspace layout

Every machine keeps code under `~/workspace` with the same relative paths, so
zoxide history, scripts, editor recents and Claude Code project memory carry over.
Repositories sync only through Git remotes; never through a sync drive.

```
~/workspace/
├── personal/
│   ├── projects/    own repositories, flat: one directory per repository
│   ├── oss/         other people's repositories (clones and forks)
│   ├── learning/    courses, exercises, demos (non-git folders allowed)
│   ├── archive/     kept but no longer maintained
│   └── worktrees/   manual worktrees as <repo>/<branch>
├── company/         same categories; only on machines allowed to hold company code
└── scratch/         throwaway code without a remote; safe to empty (`cct NAME` starts Claude Code here)
```

Rules:

- Classify by whose code it is, not by maturity. An experiment that becomes a
  product stays where it is.
- One level only: the directory name is the repository name. No grouping
  directories; open a parent directory or a `.code-workspace` file to work across
  several repositories.
- Documents and notes do not belong here; keep them in `~/Documents`.
- The chezmoi source stays at `~/.local/share/chezmoi`; do not keep another clone
  of this repository in the workspace.

Git uses the personal identity for everything under `~/workspace/personal/`
(see `personal_email` in the README), including through a symlinked root.

## Root on an external disk

A host whose internal disk is too small can keep the root on an APFS external
volume. Set both values in the local chezmoi config data:

```toml
[data]
    workspace_root = "/Volumes/<volume>/workspace"
    workspace_volume_uuid = "<Volume UUID from diskutil info>"
```

chezmoi then manages `~/workspace` as a symlink to that root. Without
`workspace_root`, `~/workspace` stays an ordinary directory and chezmoi ignores
it. While the volume is unplugged the symlink dangles; `workspace` refuses to run
instead of creating anything on the internal disk, and also stops when a
different volume is mounted under the same name.

## Commands

`~/bin/workspace`:

| Command | Effect |
| --- | --- |
| `workspace init` | Create the skeleton; `company/` only when chezmoi `company` is true |
| `workspace doctor` | Warn about unexpected directories, grouping directories, repositories without `origin`, and commits on no remote; note uncommitted changes. Exits non-zero on warnings |
| `workspace list` | Print `path<TAB>origin` for every repository with a remote |
| `workspace clone [file]` | Clone missing repositories from a list; existing paths are skipped, `company/` entries are skipped on non-company hosts |

The repository list is local data, not part of this public repository. Create it
on one machine and copy it to the other by a private channel:

```bash
workspace list > ~/.config/workspace/repos.tsv
```

Then, on the other machine, `workspace init && workspace clone`.
