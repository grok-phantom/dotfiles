# External provenance

Pinned on 2026-10-03. The source repository baseline was `7a618ee5c11894cb6739bb34c85d836b802cdb82`.

- Archive commits were resolved from each upstream's public Git refs, then the exact
  `https://codeload.github.com/OWNER/REPO/tar.gz/COMMIT` bytes were downloaded and SHA-256 hashed.
- Powerlevel10k retains the previous v1.18.0 selection, resolved to its commit.
- Jedi/Parso use the gitlink commits in the selected jedi-vim tree, rather than independent latest refs.
- Fonts use a fixed powerlevel10k-media commit and hashes of each raw TTF download.
- The Yazi smart-enter directory is selected from a fixed yazi-rs/plugins archive.
- Miniforge 26.1.1-3 is a versioned release with all four existing OS/architecture choices.
  Its SHA-256 values were read from the matching official `.sh.sha256` release assets.
  The production installers were not executed during this review.

To review one archive update, resolve the intended ref with `git ls-remote`, download
the commit URL to a temporary file using HTTPS, then run `shasum -a 256 FILE`.
Review the upstream diff and change the matching revision, URL, and SHA-256 together.
For Miniforge, also review the release's OS requirements and compare a downloaded
installer against the upstream checksum before changing the lock. Never accept a
hash from a moving `latest` URL as a permanent lock.

Checksums bind reviewed bytes; they do not establish that all upstream code is safe.
Homebrew/apt package names are intentionally not described as reproducible version locks.
