# Workspace authority

The active continuation baseline is the `V17` worktree at
`D:\Tools\07_LiveScanner\.worktrees\v17`.

For current requirements and decisions, start with
`D:\Tools\07_LiveScanner\MOMENTUM_ENGINE_MASTER_BLUEPRINT.md`. This visible
root entry is a hard link to
`.worktrees\v17\docs\MOMENTUM_ENGINE_MASTER_BLUEPRINT.md`; both paths expose
the same authoritative file content. The active V17 `README.md`,
`CHANGELOG.md`, and remaining files in `docs` are supporting material.

Read the master blueprint completely before acting. Its Section 25 living
checkpoint is the exact cross-session restart authority. Do not reconstruct
current intent from conversation memory, a previous Codex session, another
branch or another worktree.

After changing the blueprint, verify that the root entry and worktree entry
still have identical SHA-256 hashes. Recreate the hard link if an editor
replaces the underlying file rather than updating it in place.

Do not read or use material under any directory named `Retired` unless the
owner explicitly asks for historical recovery or audit. Retired material is
superseded, invalid, historical or generated evidence and is not a current
work instruction.

Do not infer current V17 requirements from the other Git worktrees or the
root-level `LiveScreener` checkout. They preserve separate historical or
in-progress branch state.

When an active document, work instruction, working file or generated test
result becomes superseded or invalid:

1. move it into the appropriate `Retired` category;
2. keep it recoverable;
3. remove active references to it; and
4. record the move and reason in the active V17 `CHANGELOG.md`.

When a calculation, data contract, outcome, gate, goal or activation status
changes, update the master blueprint, every affected supporting document and
the active V17 changelog in the same commit.

Every implementation-progress commit must update together:

1. the master blueprint, including Section 25;
2. `docs/ACTION_PLAN_V17_CONTINUATION_2026-07-30.md`;
3. the active `CHANGELOG.md`; and
4. every other supporting document affected by the change.

Run the complete unit suite before committing. Its documentation-continuity
test rejects a code commit newer than the master, master/action/changelog
revisions that were not committed together, and dirty implementation progress
without the complete continuity-document set.
