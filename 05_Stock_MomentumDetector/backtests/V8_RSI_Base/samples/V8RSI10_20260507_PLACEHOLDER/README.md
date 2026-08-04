# V8 RSI Placeholder-Cutoff Functional Sample

Evaluation date: 2026-05-07

Purpose: prove that variable-driven lower and upper RSI cutoffs execute correctly after Foundation eligibility.

```text
RSI period variable: 14
Lower-limit variable: 30
Upper-limit variable: 65
Rule type: LOWER_UPPER_RANGE
Boundary mode: INCLUSIVE
Limit status: PLACEHOLDER_FUNCTIONAL_TEST_ONLY
Operational use approved: False
```

The values 30 and 65 are not recommended trading values. They were deliberately supplied to exercise allow/stop behavior and matching messages.

All ten sample symbols passed Foundation. Two fell inside the placeholder range and eight exceeded its placeholder upper limit.
