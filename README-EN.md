[中文]
### Module Dependency Graph

Call relationships and data flow between all 7 layers:

```mermaid
flowchart TD
    subgraph entry["Entry Layer"]
        APP["app.py Streamlit Main"]
    end

    subgraph ui_mod["UI Layer"]
        COMP["components.py Interface"]
        MSG["messages.py Bilingual Messages"]
    end

    subgraph core_mod["Core Layer"]
        ENGINE["engine.py Scheduling Engine"]
        POLICY["school_policy.py School Policy SSOT"]
    end

    subgraph data_mod["Data Layer"]
        STATE["state.py Session State"]
        DEMO["demo.py Demo Roster"]
    end

    subgraph util_mod["Utilities Layer"]
        PDF["pdf.py PDF Reports"]
        BACKUP["backup.py Backup/Restore"]
        IMP["importers.py Roster Import"]
    end

    subgraph ai_mod["AI Layer"]
        AI_P["parser.py DeepSeek Parser"]
    end

    subgraph err_mod["Exception Layer"]
        EXC["exceptions.py Custom Exceptions"]
    end

    APP -->|"render"| COMP
    APP -->|"init"| STATE
    APP -->|"i18n"| MSG
    COMP -->|"trigger"| ENGINE
    COMP -->|"backup"| BACKUP
    COMP -->|"import"| IMP
    COMP -->|"read/write"| STATE
    ENGINE -->|"references"| POLICY
    ENGINE -->|"read/write"| STATE
    IMP -->|"AI call"| AI_P
    PDF -->|"embed backup"| BACKUP
    PDF -->|"read"| ENGINE
    BACKUP -->|"throws"| EXC
    STATE -->|"validation"| EXC

    style POLICY fill:#0F766E,stroke:#0D9488,color:#fff
    style ENGINE fill:#0F766E,stroke:#0D9488,color:#fff
    style STATE fill:#2563EB,stroke:#1D4ED8,color:#fff
    style AI_P fill:#7C3AED,stroke:#6D28D9,color:#fff
```

**Key insight:** `school_policy.py` has no reverse dependencies — it is the true Single Source of Truth. The AI layer is only called by `importers.py`, fully decoupled from the scheduling engine.
(README.md) | **English**

<div align="center">

# Sing Yin Study Prefect Duty Roster System

**聖言中學導學風紀當值排班平台 · v2.4**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.38+-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Tests](https://img.shields.io/badge/tests-62%20passed-0F766E?style=flat)](https://github.com/JackyLi10777/Study-Prefect-Duty-Roster-System/actions)
[![License](https://img.shields.io/badge/license-MIT-7C3AED?style=flat)](LICENSE)
[![DeepSeek](https://img.shields.io/badge/AI-DeepSeek_V4_Flash-4F46E5?style=flat)](https://deepseek.com)
[![Platform](https://img.shields.io/badge/deploy-Streamlit_Cloud-FF4B4B?style=flat)](https://streamlit.io/cloud)

</div>

---

> A **professional-grade intelligent fair-duty scheduling platform** built from the ground up for the Study Prefect Team of Sing Yin Secondary School, Hong Kong.
> Integrates AI-assisted parsing, fairness algorithms, mentoring pair matching, PDF report generation, and dual-channel backup/restore — all running on **Streamlit Cloud**.
> Architected through 5 rounds of structural refactoring, guarded by **62 automated tests**.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Daily Workflow](#daily-workflow)
- [FAQ](#faq)
- [System Architecture & Core Logic](#system-architecture--core-logic) (Advanced)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Backup & Data Persistence](#backup--data-persistence)
- [Author & License](#author--license)

---

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

For Streamlit Cloud deployment, configure the following Secret: `DEEPSEEK_API_KEY` (AI parsing feature).

---

## Daily Workflow

### 1. Import Roster
- **Recommended: AI Smart Auto-Match** — supports arbitrary Excel/CSV formats. DeepSeek automatically identifies and maps columns.
- Manual mode also available for standard-format uploads.

### 2. Configure Parameters
- Select prefects on leave this week in the sidebar.
- Mark special closures (exam weeks, event days).
- Adjust the global load slider (0.8× – 2.0×) to tune overall scheduling intensity.

### 3. One-Click Generation
- Click the main "Generate Fair Roster" button.
- The system automatically schedules based on cumulative historical load points, respecting AHP restrictions, room availability rules, and mentoring pair logic.

### 4. Review & Adjust
- **Visual Board**: colour-coded role markers for at-a-glance clarity.
- **Manual Edit Mode**: directly edit names or lock cells in the table.
- **Smart Substitutes**: select a date and role — system recommends candidates by lowest current load.

### 5. Export & Backup
- **Export Chinese PDF**: professional colour roster with embedded backup on the final page — send + backup in one step.
- **Export English PDF**: for external or English-speaking recipients.
- **JSON Backup**: one-click download of dynamic data from the sidebar.
- **Excel / Markdown**: convenient for copying into other documents.

> 💡 **Strongly Recommended**: download PDF or JSON backup immediately after every roster generation. Use "Upload Backup Restore" to recover after Streamlit Cloud hibernation.

---

## FAQ

**Q: PDF export fails after roster generation?**
A: Usually a WeasyPrint dependency issue. `packages.txt` on Streamlit Cloud already includes required system libraries. For local development, ensure GTK dependencies are installed.

**Q: How to recover last week's roster?**
A: Upload the previously exported PDF (no need to split pages). The system auto-parses the embedded backup on the final page. JSON backup files also work.

**Q: Should I push roster updates to GitHub?**
A: Student rosters are static data hosted on the GitHub `ai` branch. Commit and push after modifications to ensure the latest roster is used on next deployment.

**Q: How to switch Dark Mode / language?**
A: Toggle switches at the top of the sidebar for dark/light mode and Chinese/English bilingual instant switching. Settings persist automatically.

**Q: How to handle exam week scheduling?**
A: Raise the global load slider (e.g., 1.5× – 2.0×) to prioritize prefects with lower cumulative load, balancing long-term fairness.

**Q: Can multiple people use the system simultaneously?**
A: Each user's Streamlit Session is independent. For collaboration, the Head Study Prefect should operate centrally and distribute the exported PDF.

**Q: How to reset all data and start fresh?**
A: Use the "Clear All Data" button at the bottom of the sidebar (double-confirmation required; irreversible). Re-import the roster afterward.

**Q: Is mentoring pairing automatic?**
A: Yes. The system automatically identifies prefects needing guidance (cumulative points ≤ 2.0) and pairs them with experienced prefects (points > 5.0) in the same room.

---

## System Architecture & Core Logic

> 🔗 This section is for those interested in the system's design philosophy. Not required for daily operations.

### Architecture Overview

The system uses a **layered modular architecture**, separating school policy, scheduling engine, data management, user interface, utilities, and AI services into independent layers for high cohesion and low coupling.

```mermaid
flowchart TD
    APP["Streamlit App<br/>app.py"]

    subgraph core["Core Layer"]
        ENGINE["Scheduling Engine<br/>engine.py"]
        POLICY["School Policy SSOT<br/>school_policy.py"]
    end

    subgraph data["Data Layer"]
        STATE["State Management<br/>state.py"]
        DEMO["Demo Roster<br/>demo.py"]
        MODELS["Domain Models<br/>models.py"]
    end

    subgraph ui["UI Layer"]
        COMPONENTS["Interface Components<br/>components.py"]
        MESSAGES["Bilingual Messages<br/>messages.py"]
    end

    subgraph utils["Utilities Layer"]
        PDF["PDF Generation<br/>pdf.py"]
        BACKUP["Backup/Restore<br/>backup.py"]
        IMPORTERS["Roster Import<br/>importers.py"]
    end

    subgraph ai["AI Layer"]
        AI_PARSER["DeepSeek Parser<br/>parser.py"]
    end

    subgraph errors["Exception Layer"]
        EXCEPTIONS["Custom Exceptions<br/>exceptions.py"]
    end

    APP --> ENGINE
    APP --> STATE
    APP --> COMPONENTS
    COMPONENTS --> ENGINE
    COMPONENTS --> BACKUP
    COMPONENTS --> IMPORTERS
    IMPORTERS --> AI_PARSER
    ENGINE --> POLICY
    ENGINE --> STATE
    PDF --> BACKUP
    PDF --> ENGINE
    BACKUP --> EXCEPTIONS
    STATE --> EXCEPTIONS

    style POLICY fill:#0F766E,stroke:#0D9488,color:#fff
    style ENGINE fill:#0F766E,stroke:#0D9488,color:#fff
    style STATE fill:#2563EB,stroke:#1D4ED8,color:#fff
    style AI_PARSER fill:#7C3AED,stroke:#6D28D9,color:#fff
```


### Role Permission Enforcement

How the system enforces role constraints during scheduling:

```mermaid
flowchart TD
    CANDIDATE["Candidate enters slot queue"] --> ROLE_CHECK{"Check role type?"}
    
    ROLE_CHECK -->|"Head Study Prefect"| ALL_SLOTS["All slots available No restrictions"]
    ROLE_CHECK -->|"AHP"| AHP_PATH["AHP-exclusive path"]
    ROLE_CHECK -->|"Study Prefect"| SP_PATH["Regular prefect path"]
    
    AHP_PATH --> AHP_SLOT_CHECK{"Is this slot Assist. in charge?"}
    AHP_SLOT_CHECK -->|"Yes"| AHP_ASSIGN["Assign weighting -8.0"]
    AHP_SLOT_CHECK -->|"No"| AHP_SKIP["Skip AHP cannot serve this slot"]
    
    SP_PATH --> SP_SLOT_CHECK{"Is this slot Assist. in charge?"}
    SP_SLOT_CHECK -->|"No"| SP_ASSIGN["Assign standard weighting"]
    SP_SLOT_CHECK -->|"Yes"| SP_SKIP["Skip SP cannot serve Assist"]
    
    ALL_SLOTS --> CONSECUTIVE{"Consecutive day check"}
    AHP_ASSIGN --> CONSECUTIVE
    SP_ASSIGN --> CONSECUTIVE
    
    CONSECUTIVE -->|"Pass"| FINAL["Final assignment confirmed"]
    CONSECUTIVE -->|"Consecutive"| SKIP_ALL["Skip candidate try next"]
    
    AHP_SKIP --> NEXT["Try next candidate"]
    SP_SKIP --> NEXT
    SKIP_ALL --> NEXT
    NEXT --> CANDIDATE

    style ALL_SLOTS fill:#0F766E,stroke:#0D9488,color:#fff
    style AHP_ASSIGN fill:#2563EB,stroke:#1D4ED8,color:#fff
    style FINAL fill:#7C3AED,stroke:#6D28D9,color:#fff
    style SKIP_ALL fill:#DC2626,stroke:#B91C1C,color:#fff
```

**Hard constraints:**
- AHP can **only** serve "Assist. in charge" — this is non-negotiable.
- Regular prefects **cannot** serve "Assist. in charge" — skipped even if no alternatives exist.
- Consecutive-day check runs after role check; both constraints stack for full compliance.

### Core Scheduling Rules

The system fully implements all duty scheduling rules for Sing Yin's Study Prefect Team, with `school_policy.py` as the **Single Source of Truth (SSOT)**.

#### AHP (Assistant Head Study Prefect) Restrictions
- The "Assist. in charge" slot is **exclusive to AHPs**.
- A -8.0 strong weighting ensures AHPs are always prioritized for this slot.
- Regular Study Prefects cannot serve as "Assist. in charge".

#### Room Availability & Capacity

| Room | Daily Capacity | Weight | Open Days | Notes |
|------|---------------|--------|-----------|-------|
| **Room 302** | 2 | 1.2× | Mon–Fri | No duplicate assignments |
| **Room 303** | 2 | 1.2× | Mon–Fri | No duplicate assignments |
| **Room 202** | 1 | 1.0× | Mon, Wed, Thu | Auto-closed Tue & Fri |
| **Assist. in charge** | 1 | 1.4× | Mon–Fri | AHP-exclusive |

#### No Consecutive Days
- Algorithm-level guarantee: the same prefect will never be scheduled on two consecutive days.
- This rule executes before fairness calculations.


### Roster Generation Flow

End-to-end flow from data loading to PDF export:

```mermaid
flowchart TD
    A["Load student roster"] --> B["AI smart parse remarks"]
    B --> C["Tag leave personnel"]
    C --> D["Read historical load points"]
    D --> E["Sort by points low to high"]
    E --> F{"Room open?"}
    F -->|"Yes"| G["Assign slot"]
    F -->|"No"| H["Skip room"]
    G --> I{"Consecutive day trigger?"}
    I -->|"Yes"| J["Skip candidate"]
    I -->|"No"| K["Confirm assignment"]
    J --> E
    K --> L["Update load points"]
    L --> M["Run mentoring pair check"]
    M --> N["Generate final roster"]
    N --> O["Export PDF + embed backup"]

    style A fill:#2563EB,stroke:#1D4ED8,color:#fff
    style N fill:#0F766E,stroke:#0D9488,color:#fff
    style O fill:#7C3AED,stroke:#6D28D9,color:#fff
```

#### Fairness Mechanism
- **Cumulative Load Points (`history_weight`)**: updated after each scheduling cycle — the more you serve, the higher your score.
- **Dynamic Weighted Sorting**: in the next cycle, those with the lowest scores get priority rest.
- **F.3 Junior Priority**: younger prefects get scheduling preference on ties, encouraging new member participation.
- **Global Load Scaling**: 0.8× – 2.0× dynamic multiplier; increase during exam weeks to balance long-term load.

### Fairness Algorithm Detail

`history_weight` is the core quantitative metric. Full calculation flow per scheduling cycle:

```mermaid
flowchart TD
    START["Each scheduling cycle"] --> LOAD["Load all prefects history_weight"]
    LOAD --> SORT["Sort ascending by weight"]
    SORT --> PICK["Start from lowest assign slots"]
    
    PICK --> CHECK1{"Is AHP?"}
    CHECK1 -->|"Yes"| AHP_SLOT["Prioritize Assist. in charge Bonus -8.0"]
    CHECK1 -->|"No"| CHECK2{"F.3 or below?"}
    
    CHECK2 -->|"Yes"| F3_BONUS["Junior priority Bonus -1.5"]
    CHECK2 -->|"No"| NORMAL["Standard weight sort"]
    
    AHP_SLOT --> ASSIGN
    F3_BONUS --> ASSIGN
    NORMAL --> ASSIGN
    
    ASSIGN["Confirm slot"] --> UPDATE["Update weight + slot_weight x global_multiplier"]
    UPDATE --> CHECK3{"More slots remaining?"}
    CHECK3 -->|"Yes"| PICK
    CHECK3 -->|"No"| MENTOR["Run mentoring check"]
    
    MENTOR --> CHECK4{"Any prefect with weight <= 2.0?"}
    CHECK4 -->|"Yes"| PAIR["Find senior prefect weight > 5.0 to pair"]
    CHECK4 -->|"No"| DONE["Scheduling complete"]
    PAIR --> DONE
    
    style START fill:#2563EB,stroke:#1D4ED8,color:#fff
    style AHP_SLOT fill:#0F766E,stroke:#0D9488,color:#fff
    style F3_BONUS fill:#7C3AED,stroke:#6D28D9,color:#fff
    style DONE fill:#DC2626,stroke:#B91C1C,color:#fff
```

**Weight formula:**

| Slot | Base Weight | Notes |
|------|------------|-------|
| Assist. in charge | 1.4x | AHP-exclusive, -8.0 priority bonus |
| Room 302 | 1.2x | Dual-occupancy, no duplicates |
| Room 303 | 1.2x | Dual-occupancy, no duplicates |
| Room 202 | 1.0x | Single-occupancy, closed Tue/Fri |
| F.3 junior priority | -1.5 | Tiebreaker for new members |
| Consecutive days | Auto-skip | Hard constraint, non-negotiable |



### AI Import Pipeline

End-to-end flow from raw Excel upload to structured DataFrame:

```mermaid
flowchart TD
    UPLOAD["User uploads Excel/CSV"] --> DETECT["Auto-detect columns and format"]
    DETECT --> CHECK{"Columns match standard?"}
    
    CHECK -->|"Yes"| MAP["Direct map to standard columns"]
    CHECK -->|"No"| AI_CALL["Call DeepSeek API smart column mapping"]
    
    AI_CALL --> PARSE["DeepSeek-V4-Flash parses column semantics"]
    PARSE --> SUGGEST["Returns suggested mapping {original: standard}"]
    SUGGEST --> CONFIRM{"User confirms mapping?"}
    CONFIRM -->|"Yes"| MAP
    CONFIRM -->|"No"| MANUAL["Manual adjustment"]
    MANUAL --> MAP
    
    MAP --> REMARKS{"Remarks column has structured data?"}
    REMARKS -->|"Yes"| AI_REMARKS["DeepSeek parses availability/fixed duties"]
    REMARKS -->|"No"| BUILD["Build students_df"]
    AI_REMARKS --> BUILD
    
    BUILD --> VALIDATE["Validate required fields"]
    VALIDATE --> STORE["Store in session_state init history_weight"]
    STORE --> READY["Roster ready for scheduling"]
    
    style UPLOAD fill:#2563EB,stroke:#1D4ED8,color:#fff
    style AI_CALL fill:#7C3AED,stroke:#6D28D9,color:#fff
    style READY fill:#0F766E,stroke:#0D9488,color:#fff
```

**Design principles:**
- **Non-intrusive**: AI only activates when columns mismatch or remarks need parsing.
- **Human-in-the-loop**: AI suggests mappings; user confirms before proceeding.
- **Decoupled**: AI layer (roster/ai/) is independent of the scheduling engine.

### Key Design Decisions

- **School Policy as SSOT**: `school_policy.py` defines all school rules. `engine.py`, `pdf.py`, and `components.py` reference the `config` module — never hardcode.
- **Centralized Session State**: `state.py` manages all Streamlit session state with defensive helpers: `get_state`, `set_state`, `validate_state_integrity`.
- **Structured Exception Handling**: `exceptions.py` provides `BackupParseError`, `StateIntegrityError`, and others for clear, traceable error paths.
- **Decoupled AI Layer**: the AI parsing layer is independent of the core scheduling engine, callable via standard interfaces, and swappable at any time.


### Error Handling & Degradation

Per-layer exception handling with graceful fallback:

```mermaid
flowchart TD
    START["Operation triggered"] --> TRY["try block executes"]

    TRY --> CHECK_TYPE{"Error type?"}
    
    CHECK_TYPE -->|"BackupParseError"| BACKUP_ERR["Backup parse failure"]
    CHECK_TYPE -->|"StateIntegrityError"| STATE_ERR["State validation failure"]
    CHECK_TYPE -->|"API Error"| AI_ERR["AI service unavailable"]
    CHECK_TYPE -->|"Other Exception"| GEN_ERR["General error"]

    BACKUP_ERR --> BACKUP_FALLBACK["Try secondary JSON backup"]
    BACKUP_FALLBACK --> BACKUP_OK{"Secondary OK?"}
    BACKUP_OK -->|"Yes"| RECOVERED["Data restored"]
    BACKUP_OK -->|"No"| BACKUP_FAIL["Prompt manual import or use GitHub backup"]

    STATE_ERR --> STATE_DETAIL["Show specific missing fields and fix suggestions"]
    STATE_DETAIL --> STATE_USER{"User action?"}
    STATE_USER -->|"Retry"| TRY
    STATE_USER -->|"Reset"| RESET["Clear all data and restart"]

    AI_ERR --> AI_FALLBACK["Degrade to manual mode prompt user to match columns"]
    AI_FALLBACK --> MANUAL_OK["Manual import flow"]

    GEN_ERR --> GEN_LOG["Log error st.error display summary"]
    GEN_LOG --> GEN_USER{"User action?"}
    GEN_USER -->|"Retry"| TRY
    GEN_USER -->|"Skip"| SKIP["Continue with limited functionality"]

    RECOVERED --> DONE["Operation complete"]
    MANUAL_OK --> DONE
    RESET --> DONE
    SKIP --> DONE
    BACKUP_FAIL --> DONE

    style START fill:#2563EB,stroke:#1D4ED8,color:#fff
    style RECOVERED fill:#0F766E,stroke:#0D9488,color:#fff
    style BACKUP_FAIL fill:#DC2626,stroke:#B91C1C,color:#fff
    style AI_FALLBACK fill:#7C3AED,stroke:#6D28D9,color:#fff
```

**Design principles:**
- **Layered capture**: each layer (backup, state, AI, general) has its own exception type and degradation strategy.
- **User-informed**: all errors displayed via st.error / st.warning with clear cause and suggested action.
- **Never give up**: backup restore auto-tries secondary paths; AI failure degrades to manual mode — core flow never blocked.

### Backup Strategy

```mermaid
flowchart LR
    subgraph static["Static Data"]
        S1["Student Roster students_df"]
        S2["GitHub ai branch"]
        S3["Streamlit session_state"]
    end

    subgraph dynamic["Dynamic Data"]
        D1["Cumulative Load Points"]
        D2["Weekly Roster roster_df"]
        D3["Leave Records leave_tracker"]
        D4["Mentoring Pair Status"]
    end

    subgraph backup["Backup Mechanisms"]
        B1["PDF-Embedded Backup (Primary)"]
        B2["JSON Download (Secondary)"]
        B3["GitHub Long-Term Storage"]
    end

    subgraph restore["Restore Mechanisms"]
        R1["Upload PDF Auto-Parse"]
        R2["Upload JSON Restore"]
        R3["validate_state_integrity Check"]
    end

    S1 --> S2
    S2 --> S3
    D1 --> B1
    D2 --> B1
    D3 --> B1
    D4 --> B1
    D1 --> B2
    D2 --> B2
    D3 --> B2
    D4 --> B2
    B2 --> B3
    B1 --> R1
    B2 --> R2
    R1 --> R3
    R2 --> R3
    R3 --> S3
    R3 --> D1

    style B1 fill:#7C3AED,stroke:#6D28D9,color:#fff
    style B2 fill:#2563EB,stroke:#1D4ED8,color:#fff
    style R3 fill:#DC2626,stroke:#B91C1C,color:#fff
```

**Strategy:**
- **Static data** (student roster) hosted on GitHub `ai` branch; auto-loaded on startup.
- **Dynamic data** (scheduling records, load points, mentoring state) protected by PDF-embedded backup (primary) + JSON download (secondary).
- Auto-executes `validate_state_integrity()` on restore for data integrity verification.

---


### Backup Restore Decision Tree

When to use which backup method:

```mermaid
flowchart TD
    SITUATION{"Backup/restore scenario?"}
    
    SITUATION -->|"Every PDF export"| PDF_BACKUP["PDF-embedded backup Auto no manual action"]
    SITUATION -->|"After each roster generation"| JSON_DL["Download JSON backup Sidebar one-click"]
    SITUATION -->|"Major version archive"| GITHUB["Upload to GitHub backups/ folder"]
    SITUATION -->|"Restore from backup"| RESTORE_Q{"Backup file type?"}
    
    RESTORE_Q -->|"Full PDF"| PDF_RESTORE["Upload PDF Auto-parse final page backup"]
    RESTORE_Q -->|"JSON file"| JSON_RESTORE["Upload JSON Direct load"]
    
    PDF_RESTORE --> VALIDATE["validate_state_integrity() data integrity check"]
    JSON_RESTORE --> VALIDATE
    
    VALIDATE --> CHECK_OK{"Validation passed?"}
    CHECK_OK -->|"Yes"| RESTORED["System state restored continue operations"]
    CHECK_OK -->|"No"| WARN["Show specific error StateIntegrityError"]
    WARN --> FALLBACK["Try alternative backup file"]
    FALLBACK --> RESTORE_Q
    
    style PDF_BACKUP fill:#7C3AED,stroke:#6D28D9,color:#fff
    style GITHUB fill:#0F766E,stroke:#0D9488,color:#fff
    style RESTORED fill:#2563EB,stroke:#1D4ED8,color:#fff
    style WARN fill:#DC2626,stroke:#B91C1C,color:#fff
```

**Core principles:**
- PDF backup is the **most convenient daily method** — happens automatically on every export.
- JSON backup serves as **lightweight secondary** — for dynamic-data-only scenarios.
- GitHub is the **long-term archival solution** — recommended at start/mid/end of term.
- On restore, the system auto-tries all available backup paths to maximize recovery success.


## Development Investment & Technical Depth

> 🔗 This section provides advanced context on the scale of AI-assisted development behind this project.

This is not a simple utility tool — its development process represents a large-scale **AI-assisted software engineering practice**.

### AI Development Investment

| Metric | Data | Notes |
|--------|------|-------|
| **AI Platforms** | Codex · Grok · Grok Build | Multi-model collaborative development |
| **Primary Model** | DeepSeek V4 Pro | Accessed via Codex API for architecture design, code generation, test authoring, and documentation |
| **Token Consumption** | Over **1.2 billion tokens** (consumed) | Codex + DeepSeek V4 Pro portion only |
| **Estimated Total** | Approximately **2 billion tokens** | Including Grok and Grok Build contributions |

### From Investment to Quality

This AI investment is directly reflected in every layer of the project:

- **5 Rounds of Architectural Refactoring**: evolved from a single-file script to a 7-layer modular architecture. School Policy SSOT, centralized Session State management, structured exception hierarchy — each refactoring round was AI-assisted in analysis and implementation.
- **62 Automated Tests**: unit tests, engine logic tests, end-to-end integration tests — AI helped generate test frameworks and edge case coverage.
- **10 Mermaid Architecture Diagrams**: system architecture, module dependencies, scheduling flow, fairness algorithm, AI import pipeline, error handling, backup decision tree, lifecycle state machine — all AI-assisted in generation and iterative refinement.
- **DeepSeek AI Smart Parsing**: the built-in AI features (column mapping, remark parsing) also benefited from deep understanding of the DeepSeek API gained through extensive development and debugging.
- **Bilingual Documentation System**: Chinese and English READMEs with full structural parity, bilingual in-app user manual — AI-assisted translation and polishing ensure professional quality.

### Engineering Philosophy

The development model embodies the **"AI as accelerator, human as decision-maker"** collaboration paradigm:

- AI handles repetitive, large-scale work (code generation, test authoring, documentation drafts).
- Humans own architecture decisions, school rule validation, and user experience design.
- Every line of code is human-reviewed to ensure it meets the real needs of Sing Yin Secondary School.

> Approximately 2 billion tokens of AI investment, ultimately condensed into a **professional-grade system deployed on Streamlit Cloud, guarded by 62 tests, detailed in 10 architecture diagrams, and documented in full bilingual manuals**.


### Leadership & Decision-Making

This system was **initiated, designed, and led throughout development** by **LI Chuangjie Jacky**, the 26-27 Head Study Prefect.

- **Architectural Direction**: from a single-file script to a 7-layer modular architecture — every refactoring decision was made by him based on real team needs.
- **Quality Standards**: 62 automated tests, 10 architecture diagrams, full bilingual documentation — these standards did not emerge from AI automation, but from his insistence on professional-grade quality.
- **Continuous Iteration**: from the initial scheduling script, to AI parsing, mentoring pairs, PDF backup, DeepSeek migration, documentation restructuring — every major upgrade originated from his ongoing reflection and drive for improvement.
- **Human-AI Collaboration Leadership**: across approximately 2 billion tokens of AI-assisted development, he remained the decision-maker — AI provided suggestions and acceleration; he made every critical trade-off.

> Without his vision, leadership, and sustained commitment, this professional-grade intelligent scheduling system would not exist.



## Project Structure

```
Study-Prefect-Duty-Roster-System/
├── app.py                  # Streamlit entry point
├── roster/                 # Core package
│   ├── config/             # School policy SSOT (school_policy.py)
│   ├── core/               # Scheduling engine (fairness, mentoring, leave)
│   ├── data/               # Data layer (Session State, Demo, Domain Model)
│   ├── ui/                 # UI layer (Components, Theme, i18n, Bilingual)
│   ├── utils/              # Utilities (PDF, Backup, Importers)
│   ├── ai/                 # AI layer (DeepSeek parsing & column mapping)
│   └── exceptions.py       # Structured exception hierarchy
├── tests/                  # 62 automated tests
├── docs/                   # ADRs, phase reports
└── resources/              # Static assets
```

---


### System Lifecycle State Machine

State transitions from startup through a complete scheduling cycle:

```mermaid
stateDiagram-v2
    [*] --> SystemStartup
    SystemStartup --> LoadStaticData
    LoadStaticData --> AwaitingUserAction
    
    AwaitingUserAction --> ImportRoster
    ImportRoster --> RosterReady
    RosterReady --> ConfigureParameters
    ConfigureParameters --> GenerateRoster
    
    GenerateRoster --> ReviewAndAdjust
    ReviewAndAdjust --> ExportPDFBackup
    ExportPDFBackup --> AwaitingUserAction
    
    AwaitingUserAction --> UploadBackupRestore
    UploadBackupRestore --> StateValidation
    StateValidation --> RosterReady
    
    AwaitingUserAction --> ClearAllData
    ClearAllData --> AwaitingUserAction
    
    AwaitingUserAction --> [*]

    note right of GenerateRoster
        Core engine executes:
        - Role permission check
        - Consecutive day check
        - Fairness sorting
        - Mentoring pairing
    end note

    note right of StateValidation
        validate_state_integrity()
        Checks required fields
        and data consistency
    end note
```

**Key states:**
- On startup, static data auto-loads from the GitHub ai branch.
- GenerateRoster is the core state — most computation and rule checking happens here.
- After PDF export, the system returns to AwaitingUserAction, ready for a new cycle or backup restore.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend Framework** | Streamlit ≥ 1.38.0 |
| **Scheduling Engine** | Python 3.12 · Pandas ≥ 2.2.0 |
| **AI Service** | DeepSeek-V4-Flash (OpenAI-compatible API) |
| **PDF Rendering** | WeasyPrint ≥ 62.3 (CSS layout engine) |
| **Data Visualization** | Plotly ≥ 5.24.0 |
| **Test Framework** | Pytest (62 tests: unit + engine + integration) |
| **Deployment** | Streamlit Cloud (stateless, auto-hibernate recovery) |
| **Version Control** | Git · GitHub (`ai` branch for active development) |
| **File Processing** | OpenPyXL · Tabulate · Pillow |

---

## Backup & Data Persistence

This system runs on Streamlit Cloud (stateless environment). Data may be lost after hibernation or redeployment. **Always back up.**

### Data Classification
- **Static Data**: names, forms, classes, roles, availability, fixed duties → hosted on GitHub
- **Dynamic Data**: cumulative load points, weekly roster, leave records, mentoring status → preserved via backup functions

### Backup Methods

| Method | Type | Description | When to Use |
|--------|------|-------------|-------------|
| **PDF Export (with backup)** | Primary | Full JSON backup auto-embedded on final page | Every PDF export |
| **JSON Download** | Secondary | Sidebar one-click download of dynamic data | After every roster generation |
| **GitHub Long-Term** | Recommended | Upload backups to `backups/` folder | Major versions, mid-term/final |

> ⚠️ **Strongly Recommended**: cultivate the habit of "backup after every operation + upload important versions to GitHub". PDF-embedded backup is the most convenient daily backup method.

---

## Project Leadership & License

### Project Initiator & Lead Developer

**LI Chuangjie Jacky（李創杰）**
26-27 Head Study Prefect, Sing Yin Secondary School
F.5E

This system was conceived, architected, AI-development-directed, and continuously refined entirely under the initiative and leadership of LI Chuangjie Jacky.


### 📜 License

MIT License

Copyright (c) 2026 LI Chuangjie Jacky (李創杰)
26-27 Head Study Prefect, Sing Yin Secondary School Study Prefect Team

---

*This project is primarily for internal use by the Sing Yin Secondary School Study Prefect Team. Please contact the author before commercial use or redistribution.*
