---
name: systematic-debugging
description: Diagnose a reproducible bug, failing test, or unexpected behavior by collecting evidence and testing one hypothesis at a time before changing code. Use for focused bug fixing; do not combine several debugging workflows by default.
license: MIT
metadata:
  version: local-adapter.1
---

# Systematic Debugging

Standalone adaptation of obra/superpowers, 2026-10-21; see SOURCE.json. No other Superpowers skill, startup hook, or bundled executable is required.

## Establish the failure

- Read the actual error and relevant stack trace. Record expected versus observed behavior, a minimal reproduction, and relevant tool/runtime versions.
- Inspect recent changes and compare a working case with the failing one.
- For a multi-component failure, collect evidence at the boundaries until the failing layer is located. Record secret presence or metadata rather than credentials. Keep a working session or recovery path available during incident diagnosis.
- If reproduction is intermittent, gather targeted evidence. Distinguish observations from hypotheses; do not turn an unverified guess into a conclusion.

## Test an explanation

- State one hypothesis and the observation that would confirm or disprove it.
- Change one variable or add the smallest relevant diagnostic. Prefer reversible experiments and existing tools. Do not mix a bug fix with cleanup, dependency upgrades, or architectural rewrites.
- Follow the bad value or failed assumption back to its source. Compare the result to the prediction before choosing the next experiment.
- After repeated failed fixes, stop layering changes, reconsider the hypothesis and architecture, and explain the evidence gap. Continue independent investigation within the authorized scope; ask only when a missing fact or consequential choice prevents progress.

## Fix and verify

- Fix the evidenced cause. Use the failing reproduction or a meaningful regression test when feasible; an existing test or an appropriate manual reproduction can be sufficient for a small issue.
- Run the relevant test/build or client check and confirm the original failure is resolved. State the actual evidence and remaining uncertainty.
- Remove temporary instrumentation that is no longer needed. Retain useful diagnostics only if appropriate to the project.

For a review-only request, return the diagnosis and proposed change without editing. Use the user's explicit workflow selection when another debugging skill is also installed.
