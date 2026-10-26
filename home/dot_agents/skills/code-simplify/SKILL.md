---
name: code-simplify
description: Simplify a small, explicit file scope or recent diff for readability while preserving behavior. Use when asked to simplify, remove redundancy, or reduce unnecessary abstraction; broad multi-role reviews use the existing review workflow.
license: Apache-2.0
metadata:
  version: local-adapter.1
---

# Code Simplify

Adapted from Anthropic's code-simplifier on 2026-10-21; see SOURCE.json.

Use the smallest change that makes the code easier to follow. Preserve behavior, public interfaces, error handling, concurrency semantics, and the project's conventions.

1. Establish scope from the user's files, current diff, or files changed in this chat. Read applicable AGENTS.md/CLAUDE.md and inspect the diff before editing. Do not expand to the whole repository without a reason tied to the request.
2. Remove dead or repeated work, unnecessary state and indirection, deeply nested control flow, and comments that restate code. Reuse an existing helper when it fits. Avoid a new abstraction for one speculative future use.
3. Prefer clear names and explicit control flow. Fewer lines are useful only when they reduce the reader's work. Keep abstractions that express a real boundary; do not merge unrelated responsibilities.
4. Apply changes only when simplification is requested. A review request returns findings. Choose one simplification workflow for this scope; do not automatically stack this skill with review-and-simplify-changes or launch a review team for a small edit.
5. Validate meaningful behavior with the project's smallest relevant check. Add a test only when it covers a real risk or regression, not to mirror the new implementation. Report what ran and any limits; leave clean code alone.

Return the material changes and verification briefly. Do not stage, commit, push, add dependencies, or make unrelated modernization changes as part of simplification.
