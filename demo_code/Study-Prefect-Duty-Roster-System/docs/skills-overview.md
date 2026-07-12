# Sing Yin Skill Ecosystem Overview

This document is the human-readable index for the Sing Yin Study Prefect Duty Roster System skill ecosystem. Installed skill source files live under `C:\Users\lichu\.codex\skills`; project context lives in this repository.

## Organization

- **Project-specific skills** use the `sy-` prefix.
- **Router first**: start with `sy-toolchain` when a request spans several concerns.
- **Source of truth**: use `AGENTS.md`, `DESIGN.md`, and `docs/adr/` for project rules and architecture. Update skills when those documents change.
- **Status values**: `Active`, `Needs Update`, `Deprecated`.

## Project-Specific Skills

| Skill | Purpose / When to Use | Key Capabilities | Trigger Keywords | Status |
|---|---|---|---|---|
| `sy-toolchain` | Entry point for Sing Yin development workflow and skill routing. | Decision matrix, workflow sequencing, skill categories. | Sing Yin toolchain, skill library, development workflow, 導學風紀 | Active |
| `sy-duty-roster` | Business rules for roster generation and validation. | AHP gates, Room 302/303/202 rules, leave, fairness, `history_weight`, PDF/backup implications. | Sing Yin, Study Prefect, AHP, Room 302/303/202, roster validation | Active |
| `sy-thinking-partner` | Deeper strategic reasoning before major decisions. | JTBD framing, L1/L2/L3 options, technical debt detection, handover reasoning, bilingual UX tradeoffs. | thinking partner, architecture decision, technical debt, L1/L2/L3, fairness model | Active |
| `sy-skill-builder` | Maintain the living skill library. | Capture success cases, create/update skills, audit drift, maintain this overview. | success case, skill builder, skill drift, update SKILL.md, living skill library | Active |

## Architecture and Code Quality

| Skill | Purpose / When to Use | Key Capabilities | Trigger Keywords | Status |
|---|---|---|---|---|
| `project-structure-advisor` | Module organization and refactor planning. | Separation of concerns, package boundaries, migration guidance. | project structure, refactor, architecture | Active |
| `codebase-design` | Deeper domain/module design discussions. | Domain boundaries, model clarity, design tradeoffs. | domain design, module design, architecture | Active |
| `code-review` | Strict review for defects and maintainability. | Findings-first review, risks, missing tests. | code review, review this change | Active |
| `review` | Change review since a base point. | Diff review and regression detection. | review changes, PR review | Active |
| `check-work` | Pre-handoff verification. | Diff inspection, tests/builds, self-check loop. | check work, verify changes | Active |

## Testing and QA

| Skill | Purpose / When to Use | Key Capabilities | Trigger Keywords | Status |
|---|---|---|---|---|
| `python-tdd-testing` | Test-driven Python changes. | Red/green/refactor, pytest patterns. | TDD, write tests, pytest | Active |
| `python-testing` | Python test fixtures and coverage. | Parametrization, mocking, fixtures. | python tests, pytest fixtures | Active |
| `webapp-testing` | Local web application QA. | Browser workflow testing and screenshots. | test web app, local QA | Active |
| `playwright` | Browser automation. | End-to-end UI checks. | Playwright, browser test | Active |
| `playwright-interactive` | Persistent browser debugging when available. | Iterative UI inspection with persistent sessions. | interactive Playwright, UI debugging | Active |
| `screenshot` | OS-level screenshot fallback. | Desktop/window/region capture. | screenshot, capture screen | Active |

## UI, UX, and Documentation

| Skill | Purpose / When to Use | Key Capabilities | Trigger Keywords | Status |
|---|---|---|---|---|
| `streamlit` | Streamlit UI, state, and deployment work. | Layout, session state, Streamlit Cloud guidance. | Streamlit, session_state, app UI | Active |
| `frontend-design` | Polished interface decisions. | Visual hierarchy, usability, responsive checks. | frontend design, UI polish | Active |
| `ui-ux-pro-max` | Broader UX analysis. | Interaction patterns, user journeys, design quality. | UX, user experience | Active |
| `pdf` | PDF export and inspection. | Bilingual PDF, CJK fonts, export validation. | PDF export, reportlab, WeasyPrint | Active |
| `docx` / `documents:documents` | Word document work. | Create/edit professional documents. | docx, Word document | Active |
| `changelog-generator` | User-facing release notes. | Summarize commits into changelogs. | changelog, release notes | Active |

## Data and Analysis

| Skill | Purpose / When to Use | Key Capabilities | Trigger Keywords | Status |
|---|---|---|---|---|
| `pandas` | DataFrame-heavy roster work. | CSV I/O, validation, transformations. | pandas, DataFrame, CSV | Active |
| `jupyter-notebook` | Reproducible analysis or tutorial notebooks. | Scaffold clean `.ipynb` experiments/tutorials. | notebook, Jupyter, analysis | Active |
| `xlsx` / `spreadsheets:Spreadsheets` | Spreadsheet files. | Read/write/analyze spreadsheets. | xlsx, spreadsheet, Excel | Active |

## Security and Operations

| Skill | Purpose / When to Use | Key Capabilities | Trigger Keywords | Status |
|---|---|---|---|---|
| `security-best-practices` | Explicit security review or secure coding guidance. | Python/web security best practices. | security review, secure-by-default | Active |
| `security-threat-model` | Explicit AppSec threat model. | Trust boundaries, assets, abuse paths, mitigations. | threat model, abuse paths | Active |
| `security-ownership-map` | Security-oriented ownership and bus-factor analysis. | Git history topology, sensitive-code ownership. | bus factor, ownership risk | Active |
| `sentry` | Production error triage if Sentry is adopted. | Read-only issue/event querying. | Sentry, production errors | Active |
| `deploy-pipeline` | Deployment workflow coordination. | Multi-service deployment checks. | deploy pipeline, deployment | Active |

## Meta-Skills and Planning

| Skill | Purpose / When to Use | Key Capabilities | Trigger Keywords | Status |
|---|---|---|---|---|
| `skill-creator` | Create or update skills. | Scaffolding, validation, progressive disclosure. | create skill, update skill | Active |
| `skill-installer` | Install curated or GitHub skills. | List/install skill packages. | install skill, list skills | Active |
| `find-skills` | Discover external skills. | Search/recommend installable skills. | find skills, skill ecosystem | Active |
| `skill-refiner` | Read-only skill quality audits. | Diagnosis, improvement suggestions, Chinese report. | refine skill, audit skill | Active |
| `create-plan` | Concise planning. | Step planning and sequencing. | create plan, make a plan | Active |
| `to-issues` / `to-tickets` | Convert plans into work items. | Issue breakdown and implementation slices. | make issues, tickets | Active |

## Overlaps and Routing Notes

- Use `sy-duty-roster` for school-policy logic; use `pandas` only for data mechanics.
- Use `python-tdd-testing` for new behavior; use `python-testing` for broader fixture and coverage help.
- Use `review` for concrete diffs; use `code-review` for stricter maintainability/security-minded inspection.
- Use `frontend-design` for visual craft; use `streamlit` for framework-specific implementation.
- Use `sy-thinking-partner` before L2/L3 architecture or policy decisions.
- Use `sy-skill-builder` after a successful repeated workflow or when source-of-truth docs change.

## Deprecated or Needs Update

| Skill / Artifact | Status | Reason | Recommended Action |
|---|---|---|---|
| `sy-duty-roster.skill` | Needs Update | Export/package artifact in repo; not the editable installed source. | Re-export after the installed `sy-duty-roster` skill is finalized. |
| Legacy references to a "50-skill ecosystem" | Deprecated | The installed library is larger and more dynamic. | Use this overview and `sy-toolchain` instead. |
| Any skill frontmatter with mojibake Chinese triggers | Needs Update | Broken trigger text reduces bilingual discoverability. | Repair frontmatter when encountered and validate. |

## Maintenance Loop

1. When `AGENTS.md`, `DESIGN.md`, `docs/adr/`, test commands, or user expectations change, run the `sy-skill-builder` drift audit.
2. Update affected `sy-*` skills.
3. Update this overview.
4. Run `quick_validate.py` on changed skills.
5. Re-export `.skill` packages only after installed source skills are correct.
