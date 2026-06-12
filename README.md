# Sing Yin Study Prefect Duty Roster Generator

**聖言中學導學風紀當值排班平台**  
Sing Yin Secondary School Study Prefect Duty Roster System

> **v2.4 Final**（最新版本，已完整支援「值班後請假調整」公平性功能）

為聖言中學（純男校）Study Prefect Team 量身打造的專業、公平、穩定且易用的數位排班管理系統。  
專為 Streamlit Cloud 部署設計，解決休眠資料遺失問題，並提供即時公平調整機制。

---

## ✨ 核心亮點（v2.4 新增）

### ⚖️ 值班後請假調整（最重要新功能）
值班表發布後，若有人臨時請假，可直接在主畫面**撤銷**其已計算的負荷點數，並選擇替補人員（或留空）。  
系統會自動：
- 從原值班人員的累計點數中扣除該崗位權重
- 更新值班表顯示（替補姓名 或 「請假撤銷」）
- 立即刷新公平性圖表與審計表
- 確保下次匯出 PDF 時的累計點數完全公平

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
