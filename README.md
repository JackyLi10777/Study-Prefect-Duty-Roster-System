# Sing Yin Study Prefect Duty Roster System

**聖言中學導學風紀當值排班平台**  
Sing Yin Secondary School Study Prefect Duty Roster System

> **v2.4**（已完成 `roster/` 套件重構 + 完整文件完善）

為聖言中學（純男校）Study Prefect Team 量身打造的專業、公平、穩定且易用的數位排班管理系統。  
專為 Streamlit Cloud 部署設計，解決休眠資料遺失問題，並提供即時公平調整機制。

## 專案結構（重構後）

```
Study-Prefect-Duty-Roster-System/
├── app.py                  # 入口點（薄層，透過 shim 呼叫 roster/）
├── roster/                 # 主要套件（新結構）
│   ├── __init__.py         # 包級文件 + 公開 API
│   ├── config/             # SSOT（ROOMS_CONFIG、AHP 旗標、Room 302/303 規則）
│   ├── core/               # 業務邏輯核心（generate_roster 等）
│   ├── data/               # 資料層（demo、initialize_session_state、驗證）
│   ├── ui/                 # UI 元件（原 ui_components）
│   ├── utils/              # 工具（PDF、backup、importers）
│   └── ai/                 # AI 解析（Gemini）
├── resources/              # 靜態資源（logo 等）
├── tests/                  # 測試
└── （root shims: config.py、core.py 等，僅供相容）
```

**新程式碼建議 import**：
```python
from roster import generate_roster
from roster.config import ROOMS_CONFIG, is_assistant_head_only_role
from roster.data.state import initialize_session_state
from roster.utils.backup import export_system_backup
```

根目錄的 `config.py` / `core.py` 等檔案為相容性 shim，舊程式碼仍可使用 `from core import ...`。

## 快速開始

```bash
# 安裝依賴
pip install -r requirements.txt

# 啟動（開發）
streamlit run app.py

# Cloud 部署時請確保 packages.txt 已正確設定（WeasyPrint 需要系統字型與 cairo）
```

詳細規則、驗證 checklist、Room 302/303 限制、AHP 特權請務必閱讀 `AGENTS.md`。
完整使用說明見應用內「使用說明書」。

---

## ✨ 核心亮點（v2.4 新增）

### 🤝 師徒配對（自動智慧配對）
值班表生成時，系統會根據學生的累計加權點數自動識別「需要老帶新」的風紀，並在排班時優先將他們與經驗豐富的風紀安排在同一間房。
- 值班表中帶有 🟢 綠色左邊框的儲存格代表該崗位已形成師徒配對。
- 名冊管理中的「需要老帶新」欄位可手動指定或取消。
- 替補推薦時亦會顯示「配對合適度」欄位，幫助選擇最適合的替補人選。

### ⚖️ 值班後請假調整（最重要新功能）
值班表發布後，若有人臨時請假，可直接在主畫面**撤銷**其已計算的負荷點數，並選擇替補人員（或留空）。  
系統會自動：
- 從原值班人員的累計點數中扣除該崗位權重
- 更新值班表顯示（替補姓名 或 「請假撤銷」）
- 立即刷新公平性圖表與審計表
- 確保下次匯出 PDF 時的累計點數完全公平

---

##  備份與數據持久化（重要）

本系統運行在 Streamlit Cloud（無狀態環境），資料在休眠或重新部署後可能遺失。為確保數據安全，請務必做好備份。

### 資料分類說明
- **靜態資料**：姓名、年級、班別、職位、可用日子、固定值班等。  
  主要從 GitHub 倉庫中的 `data/students.csv`（或 Excel）載入，作為來源。
- **動態資料**：累計負荷點數、累計當值次數、當週排班狀態、手動調整、請假記錄、調整日誌等。  
  這些資料需要透過備份功能保存。

### 備份方式（多層保護）

| 方式           | 類型   | 說明                                                                 | 建議使用時機                     |
|----------------|--------|----------------------------------------------------------------------|----------------------------------|
| **JSON 備份**  | 主要   | 只備份動態數據，檔案輕量。側邊欄可下載與還原。                       | 每次生成排班、調整後務必下載     |
| **PDF 最後一頁** | 備援 | PDF 最後一頁會附帶動態數據（標註內部使用）。發群前請刪除此頁。       | 作為忘記下載 JSON 時的備援       |
| **GitHub 長期保存** | 推薦 | 將重要的 JSON 備份手動上傳至 `backups/` 資料夾並 commit。            | 重要版本、期中/期末前後          |

### 長期保存建議
- 請將重要的 JSON 備份檔案上傳至 GitHub 倉庫的 `backups/` 資料夾。
- 建議命名方式：`backup_年月日_說明.json`（例如 `backup_2026-06-13_週三.json`）
- 詳細使用方式請參考 [`backups/README.md`](backups/README.md)

> ⚠️ Streamlit Cloud 為無狀態環境，強烈建議養成「操作後立即備份 + 重要版本上傳 GitHub」的習慣。

---

## 👤 作者

**26-27 Head Study Prefect（領袖生會長）**  
**LI Chuangjie Jacky（李創杰）**  
Sing Yin Secondary School（聖言中學）  
F.5E

如有任何問題或需要客製化功能，歡迎 email：**s10777@syss.edu.hk**

---

（其餘內容與之前版本相同，可直接使用我上次提供的完整 README 內容，只需將作者區塊替換為以上版本即可）

2. 最新 LICENSE（已更新作者資訊）
textMIT License

Copyright (c) 2026 LI Chuangjie Jacky（李創杰）
26-27 Head Study Prefect, Sing Yin Secondary School Study Prefect Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

================================================================================

Additional Note（附加說明）:

本專案主要供聖言中學（Sing Yin Secondary School）導學風紀團隊內部使用。
若用於商業用途、轉載、或修改後公開發布，請先聯絡作者：
LI Chuangjie Jacky（李創杰） / s10777@syss.edu.hk
