# V3 Baseline Acceptance Pack

Date: 2026-06-01

This document defines the standard validation pack required before a V3 signal model can be treated as a baseline.

## Required Test Coverage

### Date Coverage

At least 5 D dates.

Include where possible:

- Bullish broad market.
- Bearish broad market.
- Choppy broad market.
- Sector-led day.
- Weak market rebound day.

### Universe Coverage

Run at least:

- Full US common stock master list or large ranked subset.
- Technology-only.
- Energy-only.
- Industrials-only.
- Mixed random sample.

### Sampling Coverage

Run:

- Sequential first-N scan.
- Deterministic random scan.
- Full-universe ranked scan where runtime allows.

## Required Metrics

Each run must report:

- D date.
- Universe source.
- Sector filter.
- Symbols attempted.
- Symbols processed.
- Symbols skipped.
- Skip reason distribution.
- Candidates found.
- Candidate density.
- D+1 hit rate.
- D+2 hit rate.
- D+5 hit rate.
- Average D+1/D+2/D+5 return.
- Median D+1/D+2/D+5 return.
- Score-bucket outcome.
- Review-priority outcome.
- Failure-category distribution.

## Promotion Criteria

A model can become a baseline only if:

- Candidate density is high enough for practical review.
- Positive follow-through is not isolated to one date.
- Higher review-priority candidates outperform lower priority candidates.
- Failures are explainable by reason-code or risk-tag groups.
- The model improves against the previous accepted baseline.

## Current V2 Reference Weakness

Recent V2-derived tests showed:

- May 5 random: 4 candidates from 625 symbols, 3 of 4 passed D+1/D+2.
- Feb 11 random: 4 candidates from 625 symbols, 2 of 4 passed D+1/D+2.
- Feb 11 Technology/Energy/Industrials random: 4 candidates from 625 symbols, 1 of 4 passed D+1/D+2.

These results set the initial problem statement:

```text
V3 must improve candidate density without hiding risk or reducing explainability.
```

