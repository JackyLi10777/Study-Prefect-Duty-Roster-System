# F2b1: generated assets in the source-owned release checklist

Base: protected main `33022c9f259a3a989571e7065cfe8110cb50b503`.
Work is isolated in `codex/release-generated-assets-20260905`; original dirty
worktrees and databases remain untouched. No deployment or release tag.

## Scope

The next bounded acceptance dependency is generated-output consistency. Add
`generated_design_tokens` and `generated_service_weave_delivery` immediately
after repository hygiene in the shared checklist and actual release runner.
Each invokes the existing generator with `--check`, never its write mode.
The checks cover NiceGUI token CSS, the Worker token contract and inline token
alignment, derived white mark, favicon module and both landing theme copies.

The manifest now has 17 checks. Its schema remains 1 and report schema remains
4 because their shapes did not change; the canonical manifest hash changes.
Python and both deployment consumers therefore reject previous 15-check reports
and reports omitting either asset check. Historical evidence is not rewritten.
Both checker scripts also join the runtime source fingerprint; their inputs and
outputs already fall within the existing release source roots.

## Verification

Three red regressions first prove absent declarations and absent runner calls.
Real generator subprocess tests copy only public source/assets into temporary
fixtures, deliberately corrupt or remove individual outputs, require nonzero failure,
and compare every fixture file hash before/after both success and failure.
A missing fixture config import was corrected before the three intended red
regressions were recorded. No generator writes to the repository during tests.
Runner tests retain the failed check and disposable evidence. Existing strict
reader/CLI/PowerShell tests additionally reject self-omitted asset checks.

Focused checks: 96 release reader/runner/CLI/PowerShell/asset cases passed,
including all missing/stale fixtures. Another 98 existing Windows/Worker
deployment and design/brand regressions passed. Both real repository `--check`
commands, governance and whitespace checks passed without changing outputs.
Full/remote CI results still need their exact clean checkpoint; none of these
focused checks is formal release or real-device acceptance.

## Still pending

Independent Chromium/WebKit/layout/performance execution, the v2 raw lifecycle
consumer and Public/Viewer producers/gates remain separate work. This patch does
not change current fail-fast orchestration, performance thresholds, Worker
runtime or generated outputs, and does not claim completion of the full plan.
