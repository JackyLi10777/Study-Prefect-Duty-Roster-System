# Sing Yin Study Prefect Duty Roster System

**聖言中學導學風紀當值排班平台 · v2.4**  
*Sing Yin Secondary School — Study Prefect Intelligent Scheduling Platform*

> 為 **30+ 人的導學風紀团隊** 打造的專業级智能公平排班管理系统。  
> 集 AI 輔助解析、公平性演算法、师徒配對、PDF 报告生成、双通道備份還原於一體。  
> 專為 **Streamlit Cloud** 無狀態環境設計，歷经 5 輪架構重構，**62 項自動化测試**全程护航。

---

## 📊 項目規模

| 指標 | 數值 |
|------|------|
| **Python 模塊** | 33 個 |
| **代码行數** | 8153+ 行 |
| **自動化测試** | 62 項（4 個测試文件，611+ 行） |
| **Mermaid 架構圖** | 4 张 |
| **模塊化包** | 1 個主包（`roster/`），含 6 個子模塊 |
| **ADRs（架構決策記录）** | 2 份 |
| **文档** | README · AGENTS.md · 使用說明書 · 階段报告 |
| **AI 后端** | DeepSeek-V4-Flash |
| **PDF 引擎** | WeasyPrint（CSS 排版，專業级） |

---

## 🚀 核心能力

### 🤖 AI 智能導入
DeepSeek-V4-Flash 驱動的智能備註解析与欄位自動映射。支持任意格式的 Excel/CSV 名冊上傳，無需手動調整欄位順序。

### ⚖️ 公平性排班引擎
基於累积負荷點數（`history_weight`）的量化公平機制。每次排班自動更新點數權重，确保「付出越多者獲更多休息」。完整實現：

- **AHP 領導职優先**：-8.0 强力加權确保「Assist. in charge」岗位始终由 AHP 担任
- **房間智能調度**：Room 202 自動識別周二/五關閉，Room 303 双岗不重復
- **F.3 师徒優先**：低年级在平局時優先，鼓勵新人参与
- **全局負荷調节**：0.8×~2.0× 動態倍率，考試周灵活調整
- **不可連续值班**：算法層面避免同一風纪連续兩天当值

### 🤝 师徒配對系统
自動識別需要指導的風纪（點數 ≤ 2.0），配對資深風纪（點數 > 5.0）至同一房間。配對岗位可視化標記 🟦，含獨立進度追踪面板与基準线快照對比。

### 📄 專業 PDF 报告
WeasyPrint 引擎生成中英文双语彩色值班报告，含校徽、工作量审計表、师徒配對摘要、AHP 規則說明。PDF 末頁自動嵌入完整備份數据，一頁實現「發送 + 備份」。

### 💾 双通道備份与還原
- **主通道**：PDF 嵌入備份 → 上傳完整 PDF 自動還原（無需拆頁）
- **備援通道**：JSON 輕量備份 → 側邊欄一键下載/上傳
- **長期存儲**：GitHub `ai` 分支托管静態學生名冊

### 🎨 專業操作體验
深色/浅色模式、中英双语即時切换、歷史負荷趋勢圖、公平性审計儀表板、批量請假/固定值班、智慧替補推荐。Streamlit 原生组件打造，響應式适配平板。

---

## ⚡ 快速開始

```bash
pip install -r requirements.txt
streamlit run app.py
```

部署至 Streamlit Cloud 時需設置 Secrets：`DEEPSEEK_API_KEY`（AI 解析）、`GEMINI_API_KEY`（已废弃，保留兼容）。

---

## 📁 項目结構

```
Study-Prefect-Duty-Roster-System/
├── app.py                  # Streamlit 入口
├── roster/                 # 核心套件
│   ├── config/             # 學校規則 SSOT（school_policy.py）
│   ├── core/               # 排班引擎（公平演算法 · 师徒配對 · 請假調整）
│   ├── data/               # 數据層（Session State · Demo · Domain Model）
│   ├── ui/                 # UI 層（组件 · 主题 · i18n · 多语言）
│   ├── utils/              # 工具層（PDF · 備份 · 名冊導入）
│   ├── ai/                 # AI 層（DeepSeek 智能解析与欄位映射）
│   └── exceptions.py       # 结構化异常層次
├── tests/                  # 62 項自動化测試
├── docs/                   # ADR · 階段报告
└── resources/              # 静態資源
```

---

## 🔧 技术栈

| 層级 | 技术 |
|------|------|
| **前端框架** | Streamlit ≥ 1.38.0 |
| **排班引擎** | Python 3.12 · Pandas ≥ 2.2.0 |
| **AI 服務** | DeepSeek-V4-Flash（OpenAI 兼容 API） |
| **PDF 渲染** | WeasyPrint ≥ 62.3（CSS 排版引擎） |
| **數据可視化** | Plotly ≥ 5.24.0 |
| **测試框架** | Pytest（62 項：单元 + 引擎 + 集成） |
| **部署平台** | Streamlit Cloud（無狀態 · 自動休眠恢復） |
| **版本管理** | Git · GitHub（`ai` 分支為主開發分支） |
| **文件處理** | OpenPyXL · Tabulate · Pillow |

---

## 📖 使用說明書（精简版）

### 日常工作流
1. **導入名冊** → AI 智能匹配 或 傳统格式導入
2. **設定参數** → 請假名单 · 特殊關閉 · 全局負荷倍率
3. **一键生成** → 公平排班演算法自動計算
4. **审核調整** → 手動修改 · 請假撤销 · 智慧替補推荐
5. **導出报告** → 中文/英文 PDF（含備份）· Excel · Markdown
6. **備份保存** → JSON 下載 或 PDF 內置備份 → GitHub 長期存档

> 💡 **完整的使用說明書（11 章節）請在應用內點「📖 使用說明書」展開。**

---

## 🧠 系统架構与核心邏辑

*以下為技术参考內容，面向维护者与下一任 Head Study Prefect。*

### 整體系统概述

本系统是一套為聖言中學導學風紀團隊（Study Prefect Team）設計的**智能公平排班平台**，運行於 Streamlit Cloud。核心目標是在嚴格遵循學校規則的前提下，自動產生一份盡可能公平的每週值班表。

系统設計原則：**規則即代码（不可绕过）· 公平性可量化（history_weight）· 操作體验專業流暢（生成 → 調整 → 導出一體化）**

```mermaid
graph TB
    subgraph "使用者介面 (UI Layer)"
        A["app.py | Streamlit 入口"]
        B["roster/ui/components.py | 側邊欄 / 控制按钮 / 儀表板"]
        C["roster/ui/theme.py | 深色 / 浅色模式 CSS"]
        D["roster/ui/i18n.py | 中英双语切换"]
    end

    subgraph "核心業務邏辑 (Core Logic)"
        E["roster/core/engine.py | 公平排班演算法 | generate_roster() / 师徒配對 / 請假調整"]
        F["roster/config/school_policy.py | 學校規則 SSOT | ROOMS_CONFIG / AHP 限制 / 權重"]
    end

    subgraph "數据層 (Data Layer)"
        G["roster/data/state.py | Session State 管理 | initialize / get_state / validate"]
        H["roster/data/demo.py | 示范學生名冊"]
        I["roster/data/models.py | Domain Model / 验證"]
    end

    subgraph "工具層 (Utilities)"
        J["roster/utils/pdf.py | WeasyPrint PDF 生成 | 嵌入備份數据"]
        K["roster/utils/backup.py | JSON / PDF 備份 | 汇出与還原"]
        L["roster/utils/importers.py | Excel / CSV 名冊汇入 | 傳统格式 + AI 智能"]
    end

    subgraph "AI 輔助 (AI Layer)"
        M["roster/ai/parser.py | DeepSeek-V4-Flash | 備註智能解析 + 欄位映射"]
    end

    subgraph "外部依賴 (External)"
        N[("DeepSeek API | AI 智能解析")]
        O[("WeasyPrint | PDF 渲染引擎")]
        P[("GitHub | ai 分支静態數据")]
        Q[("Streamlit Cloud | 部署平台")]
    end

    A --> B
    A --> C
    A --> D
    A --> E
    A --> G
    E --> F
    E --> G
    B --> E
    B --> J
    B --> K
    B --> L
    L --> M
    M --> N
    J --> O
    G --> P
    K --> P
    A --> Q
```

> 🔗 系统采用分層模塊化設計。`school_policy.py` 是學校規則的**唯一事實來源**，所有排班邏辑通过 `engine.py` 统一調用規則進行公平計算。

---

### 排班核心邏辑

#### 1. AHP（助理首席導學風紀）規則
- 「Assist. in charge」岗位**僅限 AHP**。普通導學風紀不可担任。
- AHP 獲 **-8.0 優先加權**（分數越低越優先），确保領導岗位永遠由 AHP 填补。
- AHP **不可**担任 Room 302/303/202 等普通岗位。

#### 2. Room 配置表

| 房間 | 每日名额 | 權重 | 開放日 | 備註 |
|------|---------|------|--------|------|
| **Room 302**（Study Room） | 1 人 | 1.0 | 周一至周五 | 無额外限制 |
| **Room 303**（HW Completion） | 2 人 | 1.5 | 周一至周五 | 同日兩人不可為同一人 |
| **Room 202**（F1 Study Group） | 2 人 | 1.5 | 周一、三、四 | **周二/五關閉**（F.1 有其他活動） |

#### 3. 公平性機制

- 每位風纪持有 `history_weight`（初始 0.0），每次值班累加岗位權重。
- **點數越低 = 后续排班優先度越高**（體現仆人領袖精神）。
- **F.3 师徒優先**：平局時低年级優先。**不可連续值班**：同日不重復，次日不連续。
- **全局負荷調节**：0.8×~2.0× 滑杆實時調节整體平衡速度。

#### 4. 师徒配對

- 系统自動識別需要指導的風纪（`history_weight` ≤ 2.0）。
- 優先將 mentor（> 5.0）与 mentee 配對至同一房間（Room 303/202）。
- 成功配對顯示 🟦 標記，提供 **-2.0 加分**（遠小於 AHP -8.0，确保領導優先）。

```mermaid
flowchart TD
    A["📋 載入學生名冊 | students_df"] --> B["🔍 AI 智能解析備註 | ai_parse_remarks()"]
    B --> C["📊 構建候選人池 | 过滤請假 / 不可用 / 角色限制"]
    C --> D["🏠 遍歷每個岗位 | Assist → Room 302 → 303 → 202"]
    D --> E["🔒 是否為 AHP 專属？ | is_assistant_head_only_role()"]
    E -->|是| F["僅選 AHP 候選人"]
    E -->|否| G["僅選普通 Study Prefect"]
    F --> H["📐 房間是否開放？ | is_room_open_on_weekday()"]
    G --> H
    H -->|否| I["標記為 ⬜ 關閉"]
    H -->|是| J["⚖️ 計算公平分數 | history_weight × multiplier | + AHP bonus (-8.0) | + 隨機打破平局"]
    J --> K["👥 是否為双人房？ | Room 303 / Room 202"]
    K -->|是| L["🤝 尝試师徒配對 | mentee + mentor bonus (-2.0)"]
    K -->|否| M["直接選擇最低分候選人"]
    L --> M
    M --> N["📅 是否還有岗位？"]
    N -->|是| D
    N -->|否| O["✅ 生成最终值班表 | roster_df"]
    O --> P["📊 計算审計报告 | validate_and_compute()"]
    P --> Q["🤝 標註师徒配對 | annotate_mentoring_pairs()"]
    Q --> R["📄 顯示值班表 + 公平性圖表"]
```

---

### 系统架構設計

```mermaid
graph LR
    subgraph "入口層"
        APP["app.py"]
    end

    subgraph "UI 層"
        UI["components.py"]
        THEME["theme.py"]
        I18N["i18n.py"]
    end

    subgraph "核心層"
        ENGINE["engine.py"]
        POLICY["school_policy.py | (SSOT)"]
    end

    subgraph "數据層"
        STATE["state.py"]
        DEMO["demo.py"]
        MODELS["models.py"]
    end

    subgraph "工具層"
        PDF["pdf.py"]
        BACKUP["backup.py"]
        IMPORTERS["importers.py"]
    end

    subgraph "AI 層"
        AI["parser.py"]
    end

    subgraph "异常層"
        EXC["exceptions.py"]
    end

    APP --> UI
    APP --> ENGINE
    APP --> STATE
    APP --> THEME
    APP --> I18N
    UI --> ENGINE
    UI --> STATE
    UI --> BACKUP
    UI --> IMPORTERS
    IMPORTERS --> AI
    ENGINE --> POLICY
    ENGINE --> STATE
    PDF --> BACKUP
    PDF --> ENGINE
    BACKUP --> EXC
    STATE --> EXC

    style POLICY fill:#0F766E,stroke:#0D9488,color:#fff
    style ENGINE fill:#0F766E,stroke:#0D9488,color:#fff
    style STATE fill:#2563EB,stroke:#1D4ED8,color:#fff
```

**關键設計決策：**
- **School Policy 為 SSOT**：`school_policy.py` 定義所有學校規則。`engine.py`、`pdf.py`、`components.py` 均通过 `config` 模塊引用，永不 hardcode。
- **Session State 集中管理**：`state.py` 统一管理 Streamlit 會話狀態，提供 `get_state`/`set_state`/`validate_state_integrity` 等防御性輔助函數。
- **结構化异常處理**：`exceptions.py` 提供 `BackupParseError`、`StateIntegrityError` 等自定義异常，确保備份還原与狀態校验的错誤清晰可追踪。
- **DeepSeek AI 解耦**：AI 解析層獨立於核心排班邏辑，通过標準接口調用，可隨時替换 AI 后端。

---

### 數据流与備份策略

```mermaid
flowchart LR
    subgraph "静態數据 (Static)"
        S1["📋 students_df | 姓名 / 年级 / 班別 / 职级"]
        S2["📂 GitHub ai 分支 | students.csv / Excel"]
        S3["🔄 Streamlit session_state | 首次加載時初始化"]
    end

    subgraph "動態數据 (Dynamic)"
        D1["⚖️ history_weight | 累計負荷點數"]
        D2["📊 roster_df + report_df | 当周排班 + 审計"]
        D3["📝 leave_tracker / 調整日志 | 請假記录 / 手動調整"]
        D4["🤝 mentoring_pairs | 师徒配對狀態"]
    end

    subgraph "備份機制 (Backup)"
        B1["📄 PDF 導出 | 嵌入 JSON 備份於最后一頁"]
        B2["💾 JSON 備份 | 側邊欄一键下載"]
        B3["📤 GitHub 長期保存 | backups/ 文件夹"]
    end

    subgraph "還原機制 (Restore)"
        R1["📥 上傳 PDF | parse_backup_from_pdf()"]
        R2["📥 上傳 JSON | import_system_backup()"]
        R3["✅ validate_state_integrity() | 還原后狀態校验"]
    end

    S1 --> S2
    S2 --> S3
    D1 --> B1
    D1 --> B2
    D2 --> B1
    D2 --> B2
    D3 --> B1
    D3 --> B2
    D4 --> B1
    D4 --> B2
    B2 --> B3
    B1 --> R1
    B2 --> R2
    R1 --> R3
    R2 --> R3
    R3 --> S3
    R3 --> D1

    style S2 fill:#0F766E,stroke:#0D9488,color:#fff
    style B1 fill:#7C3AED,stroke:#6D28D9,color:#fff
    style B2 fill:#2563EB,stroke:#1D4ED8,color:#fff
    style R3 fill:#DC2626,stroke:#B91C1C,color:#fff
```

**備份策略：**
- **静態數据**（學生名冊）托管於 GitHub `ai` 分支，系统启動時自動加載。
- **動態數据**（排班記录、負荷點數、师徒狀態）通过 PDF 嵌入備份（主路径）+ JSON 下載（備援）双重保护。
- 還原時自動执行 `validate_state_integrity()` 校验數据完整性。

---

## 💾 備份与數据持久化

本系统運行在 Streamlit Cloud（無狀態環境），數据在休眠或重新部署后可能遗失。請務必做好備份。

### 數据分类
- **静態數据**：姓名、年级、班別、职级、可用日子、固定值班等 → GitHub 倉库托管
- **動態數据**：累計負荷點數、当周排班、請假記录、师徒配對狀態等 → 需通过備份功能保存

### 備份方式

| 方式 | 类型 | 說明 | 建議時機 |
|------|------|------|----------|
| **PDF 導出（含備份）** | 主通道 | PDF 末頁自動嵌入完整 JSON 備份 | 每次導出 PDF 即自動備份 |
| **JSON 下載** | 備援 | 側邊欄一键下載纯動態數据 | 每次生成排班后 |
| **GitHub 長期保存** | 推荐 | 上傳備份至 `backups/` 文件夹 | 重要版本 · 期中/期末 |

> ⚠️ **强烈建議**：養成「操作后立即備份 + 重要版本上傳 GitHub」的習惯。PDF 末頁嵌入備份是最方便的日常備份方式。

---

## 👤 作者

**26-27 Head Study Prefect（首席導學風紀）**  
**LI Chuangjie Jacky（李創杰）**  
Sing Yin Secondary School（聖言中學）  
F.5E

Email: **s10777@syss.edu.hk**

---

## 📜 License

MIT License

Copyright (c) 2026 LI Chuangjie Jacky（李創杰）  
26-27 Head Study Prefect, Sing Yin Secondary School Study Prefect Team

---

*本專案主要供聖言中學導學風紀團隊內部使用。商業用途或修改發布請先联系作者。*
