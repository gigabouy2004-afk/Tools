# Changelog

## 2026-07-30 - No-translation-loss continuity enforcement

### Added

- Made the master blueprint a mandatory living authority that matures in the
  same commit as implementation progress.
- Added a session-start/session-end reconciliation protocol and an
  authoritative living checkpoint containing current gates, frozen decisions,
  last completed work, next exact action and explicit non-started scope.
- Required the master blueprint, active action plan and changelog to be updated
  together on every implementation-progress commit.
- Added a regression test that detects documentation revisions which are not
  committed together, implementation commits newer than the master, and dirty
  implementation handoffs without corresponding continuity-document updates.
- Added repository and workspace Codex guidance so a future session starts
  from the master checkpoint and never reconstructs current intent from chat,
  another worktree or `Retired` material.

### Why

Development continuity must survive session boundaries without relying on
conversation memory. The committed repository now carries its own complete
background, current state, evidence boundary, action plan and exact restart
instruction, with an automated check against code/documentation drift.

### Validation

- 82 unit and regression tests passed, including four continuity checks.
- Syntax compilation and diff checks passed.
- The visible root blueprint remained a hard link to the authoritative V17
  blueprint with an identical SHA-256 hash.

## 2026-07-30 - Free runtime-only execution plan

### Changed

- Approved free-access runtime acquisition as the normal product-delivery
  profile.
- Prohibited required local universe masters, historical databases,
  historical-data folders, persistent market-data caches and resume
  checkpoints from the normal runtime path.
- Required provider cookie/timezone caches to use cleaned per-run temporary
  storage rather than persistent application data.
- Defined explicit-code and planned `--universe nasdaq|nyse|all` inputs.
- Defined a small-list lane and a bulk daily-first all-market lane with
  candidate-only current-session enrichment.
- Added runtime delivery gates R1-R8, staged scale benchmarks, bounded provider
  failure behavior, memory/progress requirements and explicit partial-coverage
  output.
- Permanently separated `CURRENT_SURVIVOR_REFERENCE_ONLY` runtime backtests
  from promotion-quality evidence.
- Replaced the archive-dependent continuation plan and moved its superseded
  version to
  `Retired/Documentation/Superseded V17 Plans/ACTION_PLAN_V17_ARCHIVE_DEPENDENT_2026-07-30.md`.

### Why

The application must run without data installation or specialist tuning and
must accept anything from a few stock codes to the current Nasdaq/NYSE
listed-equity universe. Bulk daily acquisition and candidate-only enrichment
minimize application overhead, while explicit evidence labels prevent free
current-universe data from being mistaken for survivorship-free,
promotion-quality validation.

## 2026-07-30 - Active documentation synchronization

### Changed

- Updated every active V17 document to name
  `docs/MOMENTUM_ENGINE_MASTER_BLUEPRINT.md` as the primary development
  authority.
- Assigned explicit roles to the engine specification, research protocol,
  field guide, validation records, tagged handover and action plan.
- Updated the handover file map and continuation guidance for the cleaned V17
  structure.
- Removed ambiguity between current development instructions and immutable
  historical evidence.

### Maintenance rule

Future changes to calculations, data contracts, outcomes, gates, goals or
activation status must update the master blueprint, each affected supporting
document, the README when entry guidance changes, and this changelog in the
same commit.

## 2026-07-30 - Standalone Momentum Engine authority

### Added

- Created `docs/MOMENTUM_ENGINE_MASTER_BLUEPRINT.md` as the primary,
  self-contained development authority.
- Consolidated the validated V17 foundation, previous-session/current-session
  logic, inherited benchmark parameters, point-in-time research contract,
  backtesting evidence, chronological validation design, development gates,
  interim milestones, final goals, guardrails and reproduction commands.

### Why

The Momentum Engine must remain developable from one document in total
isolation. A new session should not need to reconstruct intent from multiple
handover, validation or planning files, and must never consult retired
material to fill a perceived gap.

## 2026-07-30 - Active/retired documentation boundary

### Changed

- Pre-V17 documentation was moved from `docs` to
  `Retired/Documentation/Pre-V17`.
- The prior full changelog was retained in the same archive and replaced by
  this active V17-only changelog.
- A post-signoff working appendix was separated from the authoritative V17
  handover and retained under `Retired/Documentation/Working Session Notes`.
- Generated baseline outputs and smoke-test results were moved from `output`
  to `Retired/Test Results/V17 Baseline 2026-07-29`.
- The invalid root-level local note and other superseded root documents,
  historical results, backups and temporary working files were consolidated
  under the workspace-level `Retired` directory.

### Why

Retired material is preserved for audit and recovery, but it is not a current
source of requirements, calculations, thresholds, conclusions or work
instructions. Separating it prevents superseded or invalid context from
misdirecting future application reads.

This is an ongoing documentation-lifecycle rule: when a document, work
instruction, working file or generated test result is superseded, invalidated
or no longer part of the active baseline, it must be moved to `Retired` and
the move and reason must be recorded in this changelog.

## Unreleased - V17 momentum research foundation

### Added

- U.S.-only V17 research entry point using the previous completed session as
  its immutable daily foundation.
- Completed current-session 1-hour and 4-hour diagnostics reconstructed from
  regular-session 30-minute bars.
- Point-in-time daily feature and future-outcome panel foundation for all
  supplied equity/session observations, including young listings.
- Chronological training, calibration and untouched-holdout assignment with
  outcome-boundary purging.
- Plain-language review output, research protocol, field guide, validation
  records, authoritative handover and continuation action plan.

### Validation

- 78 deterministic and regression tests passed at the baseline handover.
- The five-year inherited daily-rule replay produced a -0.0627% gross mean and
  failed the promotion gate.
- Multi-year 4-hour/1-hour efficacy remains untested pending a replayable
  several-year 30-minute archive.
- No classifier or production rule was introduced.
