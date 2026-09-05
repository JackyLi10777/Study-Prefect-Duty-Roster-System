# F1: required lifecycle evidence

Development preparation only; no release approval or deployment.
Initial base: protected main `0efd5ae656adea6226edd88664f2d609066d4907`.
Normally merged main `d639326dbd7e438747a78e50f4bb254eddea4a1c` after D2
PR #134; runtime contract changes remain those independently reviewed at
`c3fafbec0c5779970abfd0df97b3fd111a321cdd`. Final-source verification must be
recorded separately, not inferred from the earlier focused results.
Original dirty and frozen source worktrees remain untouched.

## Reproduced gap

The existing `complete_report()` validator fixture contains coverage, core task
windows and cold performance samples, but no lifecycle measurements. Before this
fix `validate_mobile_release_report` returned an empty error list for that report.
Twenty semantic actions do not prove bounded heap, DOM or listener growth.

## Version 2 contract

The mobile evidence schema advances from 1 to 2. The central validator now also
requires `lifecycle`; older reports cannot be relabeled as current evidence.
The contract fingerprint includes the target/mode matrix, baseline, measurement
protocol, cycle count and unchanged budgets. This is the mobile contract version,
not a change to the unrelated pre-push change-report schema.

Required targets are the existing person sheet, draft sheet, main drawer and
export workspace, each in verified Admin and isolated Guest contexts. Routes are
source-owned; dynamic roster fixtures are resolved by the producer. Local
maintenance diagnostics do not substitute for signed Admin. Each target/mode
needs its own fresh Chromium context, the fixed formal mobile profile and matching
run, fixture and source identities. Contexts must also be disjoint from cold
performance samples, whose required interactions have already exercised the page.
These targets are not the entire route,
authorization, content or recovery matrix.

The baseline is measured with the target closed **before its first opening**.
The final endpoint is closed after exactly 20 open/close cycles, with per-cycle
semantic, retained-state and restored-focus results. Both endpoints identify the
same browser context, completed-cycle count and increasing monotonic timestamp.
Missing counters, zero/unobserved counters, NaN, booleans, fractional counts,
wrong identity/profile, warm baselines, repeated contexts, missing/duplicate
targets or failed cycle results reject the report.

Measurement protocol `cdp-gc-250-100-v1` preserves the existing PNG diagnostic:
wait 250ms, perform one `HeapProfiler.collectGarbage`, wait 100ms, then read
`Runtime.getHeapUsage` and `Memory.getDOMCounters`. Apply it identically at the
two endpoints; no warm-up, extra collection, discarded sample or longer settling
delay may be added to make a result pass. Measurements during a loop are optional
diagnostics and cannot replace either endpoint.

Growth is recomputed from raw endpoints, not a producer's pass flag or delta:
heap <=10MiB, DOM <=100, listeners <=40. Equality passes; one unit over fails.
Decreasing counts are legitimate. No performance threshold changes occur.

## Integration and evidence limits

Tests use fictional records to validate acceptance logic, not fabricated browser
observations. A red regression reproduced acceptance with `lifecycle` missing.
Independent review additionally reproduced reuse of an already-exercised
performance context as a lifecycle context. A second red regression demonstrates
that gap; the consumer now rejects overlap across those evidence categories.
Focused contract/release-evidence tests pass (147 cases); exact-source full
verification and required CI remain separate gates.

F still owns actual measured producers, immutable evidence assembly and all
Windows/Worker/release-registry consumers. They must use this central validator
and emit missing evidence as not-run/failure, never synthesize measurements.
This isolated contract change does not wire the formal release gate by itself.
In particular D2's support expansion retention report is a different diagnostic:
its first materialization and subsequent retained cycles remain separate, and
neither may be promoted to this cold sheet/drawer contract.

All implementation is integrated before one test-site update. No RC, database
replacement, test-site deployment, real-device or recovery acceptance is claimed.
