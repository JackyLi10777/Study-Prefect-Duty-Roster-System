# Codex Operating Guide

**Last Updated:** 2026-07-10  
**Project:** Sing Yin Study Prefect Duty Roster System  
**Runtime:** NiceGUI, local SQLite, Python domain packages, Cloudflare Tunnel planned

## Purpose

Use this guide to make each change useful to a real Head Study Prefect and safe for the next one. It is a task scaffold, not a role-play script: inspect the current system, understand the operator's moment, choose a proportionate change, and leave evidence that another person can trust.

## Operating Outcome

The system should help a Head Study Prefect:

- generate and publish a compliant weekly roster without hidden manual steps;
- handle a late leave calmly, fairly, and with an auditable substitute decision;
- recover from mistakes without technical database work;
- understand what the system did and hand it to a successor with confidence.

The guiding principle is **「非以役人，乃役於人」 / Not to be served, but to serve** (Mark 10:45). In this system, fairness, clear records, and low-friction recovery are forms of service.

## Current Truth

Treat the workspace as the source of truth, not an older plan or reference app.

- UI: `nicegui_app/ui/`
- Workflow and transactions: `nicegui_app/services/roster_workflow.py`
- Policy: `packages/roster_policy/`
- Pure generation and validation: `packages/roster_core/`
- Persistent data and migrations: `nicegui_app/persistence/`, `migrations/`
- Operational status: `PROJECT_STATUS.md`
- Architecture and recovery guide: `docs/NICEGUI_ARCHITECTURE.md`

`demo_code` and `demo_code2` are functional evidence only. Do not copy their UI, runtime structure, or stale assumptions into the active system.

## Adaptive Work Scaffold

Use these four steps before substantial work. Keep the reasoning concise in updates; do not manufacture a long internal monologue for small changes.

1. **Current-state diagnosis**: Read the relevant code, data, tests, and status document. State what is confirmed, what is uncertain, and which invariant can be affected.
2. **Operator-moment analysis**: Name the real moment for a Head Study Prefect. For example: generating a roster before a deadline, receiving a late absence, recovering after an accidental change, or handing the tool to a successor with limited technical confidence.
3. **Priority and trade-off**: Choose the highest-value safe improvement. Use L1 for a contained fix, L2 for a recurring workflow improvement, and L3 for a system or handover change. Do not choose L3 merely for spectacle.
4. **Approach and evidence**: Select the smallest maintainable implementation, the relevant skills, and proof proportional to risk. Decide what must be documented for the next operator.

For meaningful work, report a short decision brief containing these four headings before implementation, then update it with outcomes after verification.

## Non-Negotiable Product Boundaries

- Keep the Daily Verse and devotional reflection prominent, dignified, and spiritually meaningful.
- Keep Chinese names primary and every interface string Traditional-Chinese-first with an English counterpart.
- Preserve AHP exclusivity, room capacities and opening days, Room 202 Tuesday/Friday closure, no same-day duplicate duty, no consecutive generated duty, and fairness via persistent `history_weight`.
- Use the established workflow split: pre-generation leave declarations affect drafts; published rosters use post-publication leave adjustment.
- Keep policy in `roster_policy`, pure scheduling in `roster_core`, transactions/backups in the workflow service, and presentation in NiceGUI pages.
- Treat every persistent write as a data-safety event. Preserve automatic snapshots, checksum/integrity verification, and the managed restore path.

## Working Modes

### Normal delivery

Complete one useful vertical slice: inspect, implement, test, and update the status document if the project truth changes.

### Bug investigation

Reproduce or obtain evidence first. Distinguish an operator misunderstanding, UI defect, data corruption risk, policy violation, and root-cause code defect. Add a regression test when the issue could recur.

### Proactive improvement

Look for friction that a new Head Study Prefect would experience repeatedly: hidden state, unclear next actions, manual backup steps, ambiguous bilingual text, or rules that are visible only in code. Prefer a narrow improvement with a clear operational benefit.

### Architecture or data change

Preserve observable behavior, stage migrations, verify data safety, and document why the boundary exists. Escalate a change that alters school policy, fairness meaning, real-data retention, or external access instead of silently deciding it.

### Prompt or skill maintenance

Use the same scaffold. Update a skill only when a durable workflow, policy, runtime, or user expectation changed. Prefer one authoritative skill over multiple overlapping coach prompts.

## Verification and Handover Evidence

Match evidence to risk:

- Policy, fairness, leave, or persistence: targeted tests plus `python -X utf8 -m pytest -q`.
- NiceGUI UI or bilingual/theme work: browser smoke test and screenshots when layout changed.
- Backup or restore: create a snapshot, verify integrity, and test the recoverable path in an isolated database.
- Prompt and skill changes: validate frontmatter, descriptions, references, and current-runtime alignment.

For any significant change, update `PROJECT_STATUS.md` with current truth, not a diary. Update architecture or operator documentation when a successor needs a new recovery, verification, or decision procedure.

## Prompt Design Contract

Any future coaching prompt for this project should contain:

1. the desired user outcome and a concrete operating moment;
2. confirmed project context and non-negotiable boundaries;
3. autonomy to inspect live files and revise an initial hypothesis;
4. a request for a proportionate implementation and evidence;
5. a handover question: what will the next Head Study Prefect need to understand or recover?

Avoid generic instructions such as “act as an expert” when the actual task, operator context, evidence, and ownership boundary can be stated instead.
