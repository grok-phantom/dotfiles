# Reproducible local tests and CI

The canonical command is `./scripts/test all` (`make test` is an alias). Test tooling
requires Python 3.11+; this does not change the update CLI's Python 3.9+ support.
The launcher uses `PYTHON` when provided, otherwise finds Python 3.13, 3.12, 3.11,
then a suitable `python3`. It never installs anything. An explicit unsupported
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
| `unit` | Original 33 tests plus 3 recovery and 10 source-snapshot cases, real chezmoi rendering and temporary target writes | Network/package managers/Miniforge installer are mocks; no host software or settings changed |
| `static` | Python/JSON/TOML parsing, shell syntax, whitespace and lock format | No template apply, download, external checksum verification or system validation |
| `cached-externals` | Verifies actual bytes of 20 supplied locked resources, temporary full apply/verify/repeat | Requires an existing cache; no downloads or installers; does not prove plugins work in a login session |
| `all` | `unit` + `static` | Does not include cache integration, VM or live software installation |

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

Actions are pinned to full SHAs verified from the official repositories: checkout
v4.2.2, setup-python v5.6.0 and upload-artifact v4.6.2. Python is pinned to 3.13.13.
`tests/ci-tools.json` pins chezmoi 2.73.0 release archive digests from
<https://github.com/twpayne/chezmoi/releases/tag/v2.73.0>. The CI-only helper downloads
and verifies those bytes, then extracts only the regular `chezmoi` executable into
runner temporary storage. It is not called by local test commands.

Hosted OS images, Git/Bash and the Ubuntu Zsh system package are not byte-for-byte
locked; the reports record the relevant actual versions. CI provisions dependencies
only on ephemeral runners. This workflow has not been run remotely merely by adding
the YAML; its first execution requires a separately authorized push.

The artifact contains only synthetic test reports/logs, is retained for seven days,
and is uploaded even on test failure. No home directory, cache, credentials or rendered
user configuration is included.
