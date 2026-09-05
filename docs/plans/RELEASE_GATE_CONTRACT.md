# F2a: one source-owned release gate declaration

Base: protected main `d8adbf55de9a56c515ec666c5e5999619c74f84d`.
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
