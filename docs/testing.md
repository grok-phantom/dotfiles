# Reproducible local tests and CI

The canonical command is `./scripts/test all` (`make test` is an alias). Test tooling
requires Python 3.11+; this does not change the update CLI's Python 3.9+ support.
The launcher uses `PYTHON` when provided, otherwise tries Python 3.14, 3.13,
`~/opt/miniforge3/bin/python3.13`, 3.12, 3.11, then a suitable `python3`.
It never installs anything. An explicit unsupported
interpreter is rejected, not silently replaced.

```sh
PYTHON=/path/to/existing/python3.13 ./scripts/test all --report-dir /tmp/dotfiles-test-01
./scripts/test unit --report-dir /tmp/dotfiles-unit-01
./scripts/test static --report-dir /tmp/dotfiles-static-01
./scripts/test cached-externals --cache /path/to/reviewed-upstream-cache --report-dir /tmp/dotfiles-assets-01
```

Report directories must be new. Without `--report-dir`, a unique ignored
`.test-results/` directory is used. Reports and logs stay local unless explicitly
uploaded by the CI workflow. Do not put reports into the managed `home/` tree.

| Suite | Real execution | Limit |
| --- | --- | --- |
| `unit` | Update, migration, diagnostics, recovery and source-snapshot cases, real chezmoi rendering and temporary target writes | Network/package managers/Miniforge installer are mocks; no host software or settings changed |
| `static` | Python/JSON/TOML parsing, shell syntax, whitespace and lock format | No template apply, download, external checksum verification or system validation |
| `cached-externals` | Verifies actual bytes of 24 supplied locked resources, temporary full apply/verify/repeat | Requires an existing cache; no downloads or installers; does not prove plugins work in a login session |
| `runtime` | Full Zsh load/completion init, Vim Python/Jedi/fzf/Tagbar/ALE, dedicated Tmux session/config | Requires the locked cache and existing tools; synthetic config/HOME; no installers |
| `all` | `unit` + `static` | Does not include cache integration, runtime, VM or live software installation |

The launcher isolates HOME, XDG paths, Git global/system configuration, temporary
files and proxy/agent inheritance. Tests create synthetic identities and repositories;
the caller's dotfiles are not applied or inspected. Unit tests must run as a non-root
user and require installed Git, chezmoi and Zsh. Bash is required for static checks.
Missing selected dependencies are `blocked` (exit 2), assertion failures are `failed`
(exit 1), and successful selected suites return 0. Unselected/VM suites remain
`not_run`; an overall `passed` only describes `selected_suites`.

`report.json` records the exact commit, branch, dirty flag, OS/kernel/architecture,
Python and tool versions, test count, UTC timestamps and SHA-256 of each evidence log.
Reports from dirty worktrees are development evidence; rerun from the committed clean
tree for a release record. A passing report applies only to the recorded platform.

New recovery cases prove that a forward revert can restore a synthetic target,
an injected partial write is reported without pretending to roll back, manual backup
restoration permits replanning, and switching full to core preserves optional files.
The partial failure is injected, not a real disk-full or OS permission failure.
VM recovery, backups of real software and installed package versions need separate
acceptance in [the VM plan](macos-vm-acceptance.md).

Source-snapshot regressions cover ignored files before/after planning, preservation
of unmanaged targets, intentionally committed files matching ignore rules, and
rejection/preservation of ordinary untracked, staged and unstaged source changes.
They also verify pinned candidate commits when a branch moves, refusal when HEAD
changes during validation, and that late working-tree edits cannot change the
validated apply source. Real chezmoi performs the target writes; the late-edit
injection controls timing only. Apply and its verification use the same disposable
export, which is also cleaned on failure. This does not make target writes atomic
or protect against concurrent edits to the target/config or untrusted templates.

## CI scope and dependency provenance

`.github/workflows/tests.yml` runs offline suites on Ubuntu 24.04 and macOS 15
hosted runners. It uses only `contents: read`, does not persist checkout credentials,
does not use secrets or `pull_request_target`, and has no deployment or writeback step.
Fork PR code runs with the same read-only scope, with no privileged follow-up workflow.

Actions are pinned to full SHAs in [the workflow](../.github/workflows/tests.yml):
checkout v7.0.1, setup-python v7.0.0 and upload-artifact v7.0.2. Python is pinned to 3.13.13.
`tests/ci-tools.json` pins chezmoi 2.73.0 release archive digests from
<https://github.com/twpayne/chezmoi/releases/tag/v2.73.0>. The CI-only helper downloads
and verifies those bytes, then extracts only the regular `chezmoi` executable into
runner temporary storage. It is not called by local test commands.

Hosted OS images, Git/Bash and the Ubuntu Zsh system package are not byte-for-byte
locked; the reports record the relevant actual versions. CI provisions dependencies
only on ephemeral runners. Runs are triggered by pushes and pull requests; check the
run for the exact commit before claiming CI passed. A local report is not a remote CI result.

The artifact contains only synthetic test reports/logs, is retained for seven days,
and is uploaded even on test failure. No home directory, cache, credentials or rendered
user configuration is included.

## Secret scanning and dependency updates

[Secret scan](../.github/workflows/secrets.yml) runs Gitleaks on main pushes and pull
requests, with full checkout history, read-only contents/PR permissions and the
workflow's GitHub token. It does not deploy or modify source. This is separate from
the offline test workflow and does not replace reviewing rendered private data before sharing.

[Dependabot](../.github/dependabot.yml) checks GitHub Actions monthly and groups
action updates. It does not update Homebrew/apt packages, external plugin/font locks
or the Miniforge installer lock; those have separate reviewed maintenance paths.

## Optional locked-runtime check

```sh
./scripts/test runtime --cache /path/to/upstream-cache --report-dir /tmp/dotfiles-runtime-report
```

This reuses cached integration to check hashes and construct a temporary full HOME
from the committed dependency locks and synthetic config. No installed plugin tree,
local config, SSH files, Conda or Git identity is copied. Network and installers are
not used. Zsh gitstatus background work and Vim's MRU GUI menus are disabled for
this non-TTY check. Tmux uses and cleans up a dedicated socket, including controlled
cancellation. Missing tools/unsupported dependencies are blocked, not passed.
`runtime` is separate from `all`: CI need not download plugins or install runtimes.
This is a smoke test, not GUI/IME or full startup performance acceptance. Run it
after software or external lock changes; cached asset naming is unchanged.
