# macOS VM acceptance plan — not yet executed

This plan is prepared, not an installation or acceptance result. No VM has been
created or started and no real home has been applied by preparing these materials.
Use `tests/fixtures/vm-result-template.json` for a future run; all cases begin
`not_run`. Copy it outside the source repository and fill in observed evidence.

## Preconditions and clean baseline

1. Separately authorize installation of a macOS VM tool and creation of a compatible
   Apple silicon macOS guest. A sensible starting allocation is 4 vCPU, 8 GB RAM and
   100 GB dynamic disk; use 10–12 GB / 120 GB for full software tests if needed.
2. Use a dedicated ordinary guest account. Do not mount the host home, forward its
   SSH agent, copy its Keychain or sign into production accounts. Use synthetic data.
3. Record VM tool/version, guest OS build/architecture, exact source commit, source
   bundle hash and test-tool versions. Copy a reviewed Git bundle or checkout into
   the guest. The local unpublished changes are not available by cloning remote main.
4. A truly blank guest still needs Git/command-line tools, Python 3.11+ for this test
   harness and chezmoi. Provisioning them is a separate approved step; this repository
   has no complete bootstrap installer. Homebrew is a further prerequisite for V10.
5. Keep both a clean OS baseline and a baseline with approved test tools installed.
   Use a powered-off VM copy or tool-supported snapshot and verify it can be restored.
   Do not equate a saved VM state with a validated application backup.
6. Keep source, reports, plans, target backups and chezmoi state/config/cache in
   distinct paths inside the guest. Only copy approved reports out; do not export
   guest credentials, private renders or production data.

## Matrix and pass criteria

| ID | Scenario | Required evidence / pass criterion |
| --- | --- | --- |
| V01 | Blank user and explicit prerequisites; `chezmoi init` without apply | Prompts are understandable; blank identity allowed; core default; no implicit system install. Synthetic `tests/fixtures/vm-core.toml` is reusable for subsequent noninteractive checks, but does not replace testing init prompts. |
| V02 | First core plan/apply/verify in the guest user account | Review plan before apply; expected owned files only; a new guest shell opens; Git identity/local include correct; no unwanted package or system changes. |
| V03 | Repeat with a new plan after V02 | Verify clean; second plan has no target diff; repeat apply/verify preserves content. Reusing the old plan is not required to succeed. |
| V04 | Upgrade from recorded old commit A to reviewed descendant B | Plan leaves source/target unchanged, apply fast-forwards and verifies; record A and B. A and B must be compatible with the controlled updater; do not pretend legacy pre-updater main provides it. |
| V05 | Dirty source, target edit, stale config/plan, divergent/backward ref | Each applicable operation stops; hash and manually compare the synthetic edits to confirm preservation; no forced reset/autostash. |
| V06 | Render failure and partial apply failure | Run the automated synthetic failure case, then a separately planned guest-only OS failure if desired; record failure, changed paths and recovery. Never assume rollback. Avoid destructive disk-full tests on the host. |
| V07 | Forward revert; restoration from a guest target backup | Save post-apply edits first, restore synthetic backup when appropriate, make a forward revert commit, generate a fresh plan and verify. Restore the baseline VM separately and distinguish that from updater recovery. |
| V08 | Full config + locked externals | First use the existing-cache integration command below. Then explicitly plan full externals and verify in guest home; check Zsh/Vim/Tmux/Yazi/fonts in real sessions. Review `exact` directory deletions. |
| V09 | Full → core | Core targets verify; optional old files remain. This is exclusion, not uninstall or cleanup. |
| V10 | Optional Homebrew/Miniforge install, repeat and upgrade | Separate baseline branch, approved network/package installation; capture versions and diffs. Test real failure handling and restore environment backups. Mocks do not satisfy this row; no promise of transactional package rollback. |
| V11 | Optional defaults, login, permissions and Keychain integration | Separate reviewed guest-only manual run; log out/in or reboot as needed. Basic guest Keychain behavior does not prove host production identity, enterprise policies or hardware-backed authentication. |

Each row must record status (`passed`, `failed`, `blocked`, `not_run`), exact command,
UTC time, commit/platform, output or assertion, and any cleanup/recovery performed.
Do not mark V10/V11 passed because `verify` or static checks succeeded.

## Safe reusable commands before any guest-home apply

These commands are safe to run on the development host as well: they only write
temporary synthetic targets and report directories, and do not provision tools.

```sh
./scripts/test all --report-dir /tmp/dotfiles-pre-vm-01
./scripts/test cached-externals --cache /path/to/reviewed-upstream-cache --report-dir /tmp/dotfiles-pre-vm-assets-01
```

An unavailable cache is a blocked integration test, not a reason to silently fetch.
For V02 onward use the reviewed plan/apply procedure in the repository README **inside
the dedicated guest only**, passing the guest repo/config/state/cache/target explicitly.
Generate plan files outside the source and use a new name per attempt. Keep a full
backup of the guest user's managed targets plus chezmoi config/state before applying.
The fixture disables Homebrew and sudo by default; enabling real software operations
belongs only to V10 after its separate baseline and prerequisites are ready.

## Environments this plan cannot replace

- Linux apt/systemd/Docker need a corresponding Linux guest or isolated service test.
  Different CPU binaries must be run on the corresponding architecture; template
  overrides are only rendering checks.
- TUN, routing, DNS/UDP/IPv6 and gateway behavior need a Linux kernel/network lab
  plus real client acceptance; macOS VM success proves none of these.
- Physical disk removal, Samba/Infuse playback and hardware/production identity
  integration require their corresponding devices and separately authorized access.
- A source commit or VM snapshot is not a backup/restore test for installed packages,
  Miniforge environments, secrets or runtime data.

UTM's macOS guest support and compatible image selection are documented at
<https://docs.getutm.app/guest-support/macos/>. A future tool choice must confirm
compatibility with the actual host OS and restore image before installation.
