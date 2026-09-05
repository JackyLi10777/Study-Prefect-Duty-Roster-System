# F2a: one source-owned release gate declaration

Base: protected main `d8adbf55de9a56c515ec666c5e5999619c74f84d`.
Normal merge adopted protected main `f7686aa273754ee7ed3b4bca2b31de488995c8c6`
before the final candidate tests; the original worktree remains untouched.
Status: implementation and focused evidence checkpoint; full evidence pending.

The report reader previously accepted a report that reduced both its declared
and executed checks to only `automated_test_suite`. A failing regression proved
the false pass. Worker similarly compared report fields with each other, while
Windows kept a separate differently ordered list.

This batch owns only the existing 15-check runner contract, report schema 4,
strict JSON, and the evidence boundaries in Python, Windows and Worker. The
versioned source manifest is included in the release fingerprint; reports bind
its canonical hash and version. Missing, reordered, duplicated, self-reduced or
malformed successful checks cannot pass. Both deployment scripts call the same
read-only Python validator before task changes or Worker upload. Their existing
tag, clean-source, source fingerprint, backup, rollback and promotion checks stay.

No deployment command is executed for testing. PowerShell tests dot-source only
the pure evidence bridge with fictional reports and an isolated checkout path.
Historical reports are not rewritten: old schema reports become unreadable and
must be regenerated for a new candidate.

This is NOT the final acceptance system. Generated assets, Public/Viewer gates,
independent Chromium/WebKit/layout/performance execution, raw mobile evidence
assembly and the v2 lifecycle consumer still need corresponding producer wiring.
No formal mobile, p75, physical phone, restore rehearsal or deployment pass is
claimed here. No frozen donor UI, transport changes or old bulk branch is adopted.

## Review and targeted verification

Independent review found that validating one read but consuming a second read
could mix reports if the runner atomically replaced the path. The bridge now
returns the exact strictly decoded report snapshot. Both deployment consumers
use that object for source/tag and all subsequent checks; neither rereads it.
A red regression preceded the fix. Tests execute the real CLI and pure Windows
PowerShell bridge with valid, reduced, reordered, duplicate, malformed and old
schema reports, including report replacement after validation. No deploy script
is invoked, and the original database and prior worktrees remain untouched.

Targeted verification: 75 Python/CLI/PowerShell contract and reader/runner tests,
plus 84 existing Windows/Worker deployment regression tests passed. These are
fictional evidence and script tests, not real deployment or formal acceptance.
Project governance and whitespace checks passed; the complete update suite
must still run on the final clean checkpoint before merging.

The first full run on clean `9a102c647d71845de1ef0ba513e67562093bb558`
passed all six update checks (suite 398704 ms), completed 2026-09-05 13:38 UTC.
Its unchanged report is retained as `logs/change-verification-9a102c6.json`,
SHA-256 `c0b5e6d811248ebc866fffd08f706f7f1ba2c275cbbe9daa66ed05e551749b76`.
This is working-tree/full update evidence, not formal release evidence.

Subsequent review corrected a test-only catch which could swallow the test's
own snapshot assertion. Assertions now sit outside the expected rejection
catch; an injected corrupt returned snapshot must fail the real PowerShell
process. The final 75 focused checks passed including this negative control.
The previous full pass is not relabeled for the new checkpoint; another full
run and required remote CI remain mandatory before merge.
