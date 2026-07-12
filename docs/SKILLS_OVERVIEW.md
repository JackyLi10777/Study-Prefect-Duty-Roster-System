# Sing Yin Prompt and Skill Overview

**Last reviewed:** 2026-07-10  
**Applies to:** active `code_v3` NiceGUI runtime

## Shared Principles

Every project prompt and skill must:

1. begin from the current codebase and a concrete Head Study Prefect operating moment;
2. protect data persistence, school policy, fairness, clarity, and recovery before adding complexity;
3. give the executor autonomy to inspect evidence and revise an initial hypothesis;
4. use a proportionate L1/L2/L3 decision, not automatic over-engineering;
5. leave verification and a handover artifact when project truth changes;
6. keep Traditional Chinese primary, with English as a consistent counterpart;
7. treat servant leadership as operational clarity, fairness, and care rather than decorative copy.

## Standard Adaptive Scaffold

For substantial work, use:

| Step | Question | Expected output |
|---|---|---|
| Current state | What do source, tests, data, and status prove? | confirmed facts and affected boundary |
| Operator moment | What could frustrate or endanger a Head Study Prefect today or successor later? | real workflow and risk |
| Priority | Which L1/L2/L3 action delivers the most safe value? | recommendation and trade-off |
| Approach | What is the owning layer, evidence, and handover note? | scoped plan and verification |

Do not require an exposed chain of thought. Use a concise decision brief only where the decision is significant.

## Active Assets

| Asset | Purpose / when to use | Key capability | Trigger | Status |
|---|---|---|---|---|
| `CODEX_PROMPTS.md` | Baseline for all substantial project work | Current architecture, user-centered scaffold, working modes, evidence standard | feature, bug, refactor, review | Active |
| `sy-toolchain` | Route multi-area work | Maps request to NiceGUI paths, policy, testing, UI review, and documentation | where to start, architecture, workflow | Active |
| `sy-duty-roster` | Protect scheduling and fairness | Room/AHP rules, leave split, history weight, snapshot contract | roster, leave, substitute, fairness | Active |
| `sy-thinking-partner` | Make durable product decisions | Operator-moment analysis, L1/L2/L3, architecture and handover trade-offs | ambiguity, technical debt, UX decision | Active |
| `sy-skill-builder` | Maintain the living skill library | drift audit, consolidation, validation, success-case capture | prompts, skills, reusable workflow | Active |

## Consolidated Coach Modes

The requested `sing-yin-coach-normal-iteration`, `sing-yin-coach-bug-fix`, `sing-yin-coach-proactive-optimization`, and `sing-yin-coach-architecture-refactor` skills are not installed in the active Codex skill library. Their intended behavior is deliberately consolidated rather than recreated as overlapping skills:

| Former coaching intent | Authoritative home |
|---|---|
| Normal iteration | `CODEX_PROMPTS.md` - Normal delivery |
| Bug fix | `CODEX_PROMPTS.md` - Bug investigation |
| Proactive optimization | `CODEX_PROMPTS.md` - Proactive improvement |
| Architecture refactor | `CODEX_PROMPTS.md` - Architecture or data change, supported by `sy-thinking-partner` |

This keeps triggers unambiguous and prevents identical policy and handover rules from diverging across five files.

## Maintenance

Run the drift audit after an active runtime, policy, persistence, UX, deployment, or prompt/skill contract changes:

```powershell
python C:\Users\lichu\.codex\skills\sy-skill-builder\scripts\audit_skill_drift.py --project D:\code_v3 --skills C:\Users\lichu\.codex\skills
```

Validate every edited skill with:

```powershell
python -X utf8 C:\Users\lichu\.codex\skills\.system\skill-creator\scripts\quick_validate.py <skill-directory>
```
