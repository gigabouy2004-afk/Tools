# V17 development authority

Before changing this repository, read
`docs/MOMENTUM_ENGINE_MASTER_BLUEPRINT.md` completely. Its Section 25 living
checkpoint is the authoritative restart point. Do not reconstruct current
intent from conversation history, another branch, another worktree or a file
under `Retired`.

The active implementation branch is `V17`. In the established Windows
workspace it is checked out at
`D:\Tools\07_LiveScanner\.worktrees\v17`, and
`D:\Tools\07_LiveScanner\MOMENTUM_ENGINE_MASTER_BLUEPRINT.md` is a visible hard
link to the authoritative document.

Every implementation-progress commit must update together:

1. `docs/MOMENTUM_ENGINE_MASTER_BLUEPRINT.md`, including Section 25;
2. `docs/ACTION_PLAN_V17_CONTINUATION_2026-07-30.md`;
3. `CHANGELOG.md`; and
4. every supporting document affected by the change.

Update `README.md` when setup, commands, user-visible behavior or release
status changes. Add a new validation record when new measured evidence changes
or closes a gate.

Run the complete unit suite before committing. The documentation-continuity
test rejects:

- master/action-plan/changelog revisions that were not committed together;
- an implementation commit newer than the master blueprint;
- dirty implementation progress without all three continuity documents; and
- a master blueprint without its authoritative restart markers.

After editing the master blueprint in the established Windows workspace,
verify that the root and worktree paths have identical SHA-256 hashes and that
the root path remains a hard link.

Do not use material under any `Retired` directory unless the owner explicitly
requests historical recovery or audit. When active material becomes
superseded, move it to the appropriate `Retired` category, remove active
references, and record the move and reason in `CHANGELOG.md`.
