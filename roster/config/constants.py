# roster/config/constants.py
"""
roster.config.constants - Single Source of Truth (SSOT) for all scheduling rules

聖言中學導學風紀當值排班平台 (Sing Yin Secondary School Study Prefect Duty Roster Platform)
核心配置模組

作者：首席導學風紀 26-27 LI Chuangjie Jacky
版本：v2.4 (roster/ package)

本檔案是 AGENTS.md §1 Core Project Rules 與 §3 Important Files 中「config.py」角色的實現：
- 定義所有學生規則、Room 302/303/202 限制、AHP 特權
- 提供不可 bypass 的 helper（get_weight, is_assistant_head_only_role, is_room_open_on_weekday 等）
- 任何涉及房間、權重、AHP 狀態的程式碼都必須透過這些 helpers（見 AGENTS.md §3 "Never bypass"）

ROOMS_CONFIG 是所有 Room 限制與權重的權威來源。
Slot 展開（ROWS_ROSTER）現在完全由 ROOMS_CONFIG + ROOM_ORDER 透過 get_roster_rows() 聲明式產生（解決 AGENTS.md Known Issue #3）。
"""

import datetime
import random
import pandas as pd

# ====================== 應用程式基本設定 ======================
APP_TITLE = "Sing Yin Study Prefect Duty Roster System"
PROJECT_FULL_NAME = "聖言中學導學風紀當值排班平台"
PROJECT_FULL_NAME_EN = "Sing Yin Secondary School Study Prefect Duty Roster Platform"
VERSION = "v2.3 Final"

# 統一職位名稱（UI 顯示與文件使用中文，符合「首席導學風紀 / 助理首席導學風紀 / 導學風紀」要求）
# 內部使用這些值，demo/legacy 資料可能仍為英文別名，check 會容錯
HEAD_ROLE = "首席導學風紀"
AHP_ROLE = "助理首席導學風紀"
REGULAR_ROLE = "導學風紀"

# Centralized role names for consistency across modules
HEAD_ROLE = "首席導學風紀"  # 首席導學風紀 (Head Study Prefect, Chinese form)
ASSIST_ROLE = "Assist. in charge"  # Slot name for AHP-only assignment
PAGE_ICON = "🛡️"
SCHOOL_NAME = "Sing Yin Secondary School"
SCHOOL_EMAIL = "s10777@syss.edu.hk"

# ====================== 排班核心業務規則 ======================
DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]

# --- Legacy list kept ONLY for migration safety verification (Phase 2 Step 1) ---
_LEGACY_ROWS_ROSTER = [
    "Assist. in charge",
    "Room 302 (Study Room)",
    "Room 303 (HW Completion) - 1",
    "Room 303 (HW Completion) - 2",
    "Room 202 (F1 Study Group) - 1",
    "Room 202 (F1 Study Group) - 2"
]

# Note: ROWS_ROSTER is now assigned at the bottom of this module using get_roster_rows()
# (after all function definitions). See end of file for the assignment + assertion.

ROOMS_CONFIG = {
    # 【核心學校規則 - AGENTS.md §1.2 & §1.3】
    # "Assist. in charge": AHP 專屬領導職位（allow_assistant_head_only=True），每日 1 槽，weight=1.0，全天開放。
    # Room 302 (Study Room): 普通領袖生專屬，1 slot/天，weight=1.0，全天開放，無任何額外限制或經驗門檻。
    # Room 303 (HW Completion): 普通領袖生專屬，2 slots/天（-1/-2），weight=1.5/槽，全天開放，同一日兩人不得重複（由 core 保證）。
    # Room 202 (F1 Study Group): 普通領袖生專屬，2 slots，weight=1.5，僅 Mon/Wed/Thu 開放（Tue/Fri 關閉 → ⬜）。
    # 任何程式碼都必須透過 is_assistant_head_only_role / is_room_open_on_weekday / get_weight 取得這些規則，不得 hardcode。
    "Assist. in charge": {"daily_slots": 1, "weight": 1.0, "available_weekdays": DAYS, "color": "assist", "allow_assistant_head_only": True, "display_name": "Assist. in charge"},
    "Room 302 (Study Room)": {"daily_slots": 1, "weight": 1.0, "available_weekdays": DAYS, "color": "room302", "allow_assistant_head_only": False, "display_name": "Room 302 (Study Room)"},
    "Room 303 (HW Completion)": {"daily_slots": 2, "weight": 1.5, "available_weekdays": DAYS, "color": "room303", "allow_assistant_head_only": False, "display_name": "Room 303 (HW Completion)"},
    "Room 202 (F1 Study Group)": {"daily_slots": 2, "weight": 1.5, "available_weekdays": ["MONDAY", "WEDNESDAY", "THURSDAY"], "color": "room202", "allow_assistant_head_only": False, "display_name": "Room 202 (F1 Study Group)"}
}

# Declarative room order for get_roster_rows().
# Changing the order here will change the order of ROWS_ROSTER (and thus the roster table rows).
# This list must exactly match the previous hardcoded order during the migration phase.
ROOM_ORDER = [
    "Assist. in charge",
    "Room 302 (Study Room)",
    "Room 303 (HW Completion)",
    "Room 202 (F1 Study Group)",
]

GLOBAL_LOAD_RANGE = (0.8, 2.0)
DEFAULT_GLOBAL_LOAD_MULTIPLIER = 1.0

NASA_COLORS = {
    "header_bg": "#1E293B",
    "accent_gold": "#D4AF37",
    "text_dark": "#1A1A2E",
    "assist_bg": "#FFF8E1",
    "assist_border": "#D4AF37",
    "assist_text": "#4E342E",
    "room302_bg": "#E0F7FA",
    "room302_border": "#00ACC1",
    "room302_text": "#006064",
    "room303_bg": "#FFF3E0",
    "room303_border": "#FF9800",
    "room303_text": "#E65100",
    "room202_bg": "#E3F2FD",
    "room202_border": "#2196F3",
    "room202_text": "#0D47A1",
    "x_bg": "#FFEBEE",
    "x_border": "#EF5350",
    "x_text": "#C62828",
    "empty_bg": "#FAFAFA",
    "closed_bg": "#ECEFF1",
    # PDF-specific cell colors (distinct from web room colors for export clarity)
    "pdf_303_bg": "#FEF2F2",
    "pdf_303_text": "#7F1D1D",
    "pdf_303_border": "#FCA5A5",
    "pdf_202_bg": "#FFF7ED",
    "pdf_202_text": "#78350F",
    "pdf_202_border": "#FDBA74",
    "pdf_assist_bg": "#FFF8E1",
    "pdf_assist_text": "#1E293B",
    "pdf_assist_border": "#D4AF37",
    "pdf_302_bg": "#F0FDF4",
    "pdf_302_text": "#14532D",
    "pdf_302_border": "#86EFAC",
}

def get_role_style(role: str, day: str = "") -> dict:
    """返回角色對應的顏色樣式（Web + PDF 共用）"""
    for key, cfg in ROOMS_CONFIG.items():
        if key in role or cfg["display_name"] in role:
            color_key = cfg["color"]
            break
    else:
        color_key = "empty"

    style = {"bg": NASA_COLORS["empty_bg"], "text": NASA_COLORS["text_dark"], "border": "1px solid #BDC3C7"}

    if color_key == "assist":
        style.update({"bg": NASA_COLORS["assist_bg"], "border": f"3px solid {NASA_COLORS['assist_border']}", "text": NASA_COLORS["assist_text"]})
    elif color_key == "room302":
        style.update({"bg": NASA_COLORS["room302_bg"], "border": f"2px solid {NASA_COLORS['room302_border']}", "text": NASA_COLORS["room302_text"]})
    elif color_key == "room303":
        style.update({"bg": NASA_COLORS["room303_bg"], "border": f"2px solid {NASA_COLORS['room303_border']}", "text": NASA_COLORS["room303_text"]})
    elif color_key == "room202":
        style.update({"bg": NASA_COLORS["room202_bg"], "border": f"2px solid {NASA_COLORS['room202_border']}", "text": NASA_COLORS["room202_text"]})

    if "Room 202" in role and day in ["TUESDAY", "FRIDAY"]:
        style.update({"bg": NASA_COLORS["closed_bg"], "text": "#546E7A", "font_style": "italic"})
    return style

def get_weight(role: str) -> float:
    """
    取得指定崗位的權重（用於公平計算與請假調整）。
    Room 302 = 1.0；Room 303/202 slots = 1.5；Assist = 1.0。
    任何權重相關邏輯都必須呼叫此函數（AGENTS.md 要求）。
    """
    for key, cfg in ROOMS_CONFIG.items():
        if key in role:
            return cfg["weight"]
    return 1.5

def is_assistant_head_only_role(role: str) -> bool:
    """
    判斷該崗位是否為 AHP 專屬（Assist. in charge）。
    回傳 True 時，僅 "Assistant 首席導學風紀" 可擔任；
    其餘崗位則僅 "Study Prefect" 可擔任（硬限制）。
    """
    for key, cfg in ROOMS_CONFIG.items():
        if key in role:
            return cfg.get("allow_assistant_head_only", False)
    return False

def is_room_open_on_weekday(room: str, day: str) -> bool:
    """
    判斷該房間在指定日子是否開放。
    Room 302/303：全天開放（MON-FRI）。
    Room 202：僅 MON/WED/THU（Tue/Fri 會在 core 產生 "⬜"）。
    """
    for key, cfg in ROOMS_CONFIG.items():
        if key in room:
            return day in cfg["available_weekdays"]
    return True

def get_daily_slots(role: str) -> int:
    """
    取得該房間每日應有槽位數。
    現在由 ROOMS_CONFIG + daily_slots 驅動（已聲明式）。
    支援傳入具體 row 名稱（如 "Room 303 (HW Completion) - 1"）或 config key。
    """
    base = get_base_role(role)
    cfg = ROOMS_CONFIG.get(base, {})
    return cfg.get("daily_slots", 1)

def get_roster_rows() -> list[str]:
    """根據 ROOMS_CONFIG + daily_slots 動態展開 roster 行。

    這讓 slot 數量與多槽位命名完全由 config 驅動（解決 AGENTS.md Known Issue #3）。
    必須在遷移期間產生與舊硬編碼 ROWS_ROSTER 完全相同的列表。
    """
    rows: list[str] = []
    for key in ROOM_ORDER:
        if key not in ROOMS_CONFIG:
            continue
        cfg = ROOMS_CONFIG[key]
        slots = cfg.get("daily_slots", 1)
        display = cfg.get("display_name", key)
        if slots > 1:
            for i in range(1, slots + 1):
                rows.append(f"{display} - {i}")
        else:
            rows.append(display)
    return rows

def get_base_role(row: str) -> str:
    """將具體 roster 行名對應回 ROOMS_CONFIG 的 key。

    取代之前 engine.py 中的 `row.split(" - ")[0].strip()` hack。
    支援 key 本身或帶後綴的形式（如 "Room 303 (HW Completion) - 1"）。
    """
    # 直接 key 匹配
    if row in ROOMS_CONFIG:
        return row
    # display_name 精確匹配
    for key, cfg in ROOMS_CONFIG.items():
        if cfg.get("display_name") == row:
            return key
    # 去掉 " - N" 後綴
    if " - " in row:
        base = row.split(" - ")[0].strip()
        if base in ROOMS_CONFIG:
            return base
        for key, cfg in ROOMS_CONFIG.items():
            if cfg.get("display_name") == base:
                return key
    # 遷移期保險 fallback
    if " - " in row:
        return row.split(" - ")[0].strip()
    return row

# ====================== 角色名稱正規化（支援中英文） ======================
ROLE_MAP = {
    "Assistant 首席導學風紀": AHP_ROLE,
    "首席導學風紀": AHP_ROLE,
    "Study Prefect": REGULAR_ROLE,
    "助理首席導學風紀": AHP_ROLE,
    "首席導學風紀": AHP_ROLE,
    "導學風紀": REGULAR_ROLE,
}

def normalize_role(role: str) -> str:
    """Map various role name formats to the canonical Chinese name."""
    return ROLE_MAP.get(role.strip(), role.strip())

def normalize_students_role_column(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize the 'role' column of a students DataFrame in place."""
    if "role" in df.columns:
        df["role"] = df["role"].apply(lambda x: normalize_role(str(x).strip()))
    return df

# ====================== 每日聖經金句（完整版 - 已替換用戶最新提供內容） ======================
DAILY_VERSES = {
    0: [  # Monday
        "「你要專心仰賴耶和華，不可倚靠自己的聰明。」——箴言 3:5",
        "「凡事都要憑著愛心行。」——哥林多前書 16:14",
        "「你們要謹慎自守，警醒禱告。」——彼得前書 4:7",
        "「我靠著那加給我力量的，凡事都能做。」——腓立比書 4:13",
        "「智慧為首，所以要得智慧。」——箴言 4:7",
        "「你們要彼此同心，互相體恤。」——羅馬書 12:16",
        "「你們各人要存心謙卑，以基督耶穌的心為心。」——腓立比書 2:5",
        "「要用智慧與人交往。」——歌羅西書 4:5",
        "「忠心僕人是有福的。」——馬太福音 24:46",
        "「你們當以基督耶穌的心為心。」——腓立比書 2:5",
        "「你們要彼此擔當重擔。」——加拉太書 6:2",
        "「謙卑自己的人，必被高舉。」——雅各書 4:10",
        "「你們作主人的，要按公平和公義待僕人。」——歌羅西書 4:1",
        "「人子來，並不是要受人的服事，乃是要服事人。」——馬可福音 10:45",
        "「你們中間誰願為大，就必作你們的用人。」——馬太福音 20:26"
    ],
    1: [  # Tuesday
        "「你們作主人的，要按公平和公義待僕人。」——歌羅西書 4:1",
        "「你們不可欺壓寡婦和孤兒。」——出埃及記 22:22",
        "「你們要為困苦和貧窮的人伸冤。」——箴言 31:9",
        "「你們中間誰願為首，就必作眾人的僕人。」——馬可福音 10:44",
        "「你們要彼此洗腳，我給你們做了榜樣。」——約翰福音 13:15",
        "「愛是恆久忍耐，又有恩慈。」——哥林多前書 13:4",
        "「要彼此擔當重擔。」——加拉太書 6:2",
        "「你們要作鹽作光。」——馬太福音 5:13-14",
        "「智慧人的心教導他的口。」——箴言 16:23",
        "「我將你的話藏在心裡，免得我得罪你。」——詩篇 119:11",
        "「凡事都要規規矩矩地按著次序行。」——哥林多前書 14:40",
        "「要追求和睦，並要彼此建立。」——羅馬書 14:19",
        "「你們要彼此同心，互相體恤。」——羅馬書 12:16",
        "「謙卑的人必得尊榮。」——箴言 29:23",
        "「你們要謹慎自守，警醒禱告。」——彼得前書 4:7"
    ],
    2: [  # Wednesday
        "「你們中間誰願為大，就必作你們的用人。」——馬太福音 20:26",
        "「人子來，並不是要受人的服事，乃是要服事人。」——馬可福音 10:45",
        "「你們作領袖的，不要轄制所託付你們的，乃要作群羊的榜樣。」——彼得前書 5:3",
        "「我為你們作了榜樣，叫你們照著我向你們所做的去做。」——約翰福音 13:15",
        "「你們各人要存心謙卑，以基督耶穌的心為心。」——腓立比書 2:5",
        "「你們要彼此擔當重擔。」——加拉太書 6:2",
        "「你們要作鹽作光。」——馬太福音 5:13-14",
        "「智慧人的心教導他的口。」——箴言 16:23",
        "「我將你的話藏在心裡，免得我得罪你。」——詩篇 119:11",
        "「凡事都要規規矩矩地按著次序行。」——哥林多前書 14:40",
        "「要追求和睦，並要彼此建立。」——羅馬書 14:19",
        "「你們要彼此同心，互相體恤。」——羅馬書 12:16",
        "「謙卑的人必得尊榮。」——箴言 29:23",
        "「你們要謹慎自守，警醒禱告。」——彼得前書 4:7",
        "「智慧為首，所以要得智慧。」——箴言 4:7",
        "「你們各人要存心謙卑，以基督耶穌的心為心。」——腓立比書 2:5"
    ],
    3: [  # Thursday
        "「你們作監督的，必須無可指責，只作一個婦人的丈夫，有節制，自守，端正，樂意接待遠人，善於教導。」——提摩太前書 3:2",
        "「忠心的人必多得福。」——箴言 28:20",
        "「你要以善勝惡。」——羅馬書 12:21",
        "「我為你們捨命。」——約翰福音 10:15",
        "「你們當以基督耶穌的心為心。」——腓立比書 2:5",
        "「作監督的，必須無可指責。」——提多書 1:7",
        "「你們要彼此相愛，像我愛你們一樣。」——約翰福音 15:12",
        "「你要專心仰賴耶和華，不可倚靠自己的聰明。」——箴言 3:5",
        "「凡事都要憑著愛心行。」——哥林多前書 16:14",
        "「你們要謹慎自守，警醒禱告。」——彼得前書 4:7",
        "「我靠著那加給我力量的，凡事都能做。」——腓立比書 4:13",
        "「智慧為首，所以要得智慧。」——箴言 4:7",
        "「你們要彼此同心，互相體恤。」——羅馬書 12:16",
        "「你們各人要存心謙卑，以基督耶穌的心為心。」——腓立比書 2:5",
        "「要用智慧與人交往。」——歌羅西書 4:5",
        "「忠心僕人是有福的。」——馬太福音 24:46"
    ],
    4: [  # Friday
        "「你要專心仰賴耶和華，不可倚靠自己的聰明。」——箴言 3:5",
        "「凡事都要憑著愛心行。」——哥林多前書 16:14",
        "「你們要謹慎自守，警醒禱告。」——彼得前書 4:7",
        "「我靠著那加給我力量的，凡事都能做。」——腓立比書 4:13",
        "「智慧為首，所以要得智慧。」——箴言 4:7",
        "「你們要彼此同心，互相體恤。」——羅馬書 12:16",
        "「你們各人要存心謙卑，以基督耶穌的心為心。」——腓立比書 2:5",
        "「要用智慧與人交往。」——歌羅西書 4:5",
        "「忠心僕人是有福的。」——馬太福音 24:46",
        "「你們當以基督耶穌的心為心。」——腓立比書 2:5",
        "「你們要彼此擔當重擔。」——加拉太書 6:2",
        "「謙卑自己的人，必被高舉。」——雅各書 4:10",
        "「你們作主人的，要按公平和公義待僕人。」——歌羅西書 4:1",
        "「你們中間誰願為大，就必作你們的用人。」——馬太福音 20:26",
        "「人子來，並不是要受人的服事，乃是要服事人。」——馬可福音 10:45",
        "「你們作領袖的，不要轄制所託付你們的，乃要作群羊的榜樣。」——彼得前書 5:3",
        "「我為你們作了榜樣，叫你們照著我向你們所做的去做。」——約翰福音 13:15"
    ]
}

GEMINI_MODEL = "gemini-3.5-flash"

# --- Declarative ROWS_ROSTER computation (Phase 2 Step 1) ---
# Must be after all function definitions so get_roster_rows and get_base_role are defined.
ROWS_ROSTER = get_roster_rows()

# Safety assertion for Phase 2 Step 1 only.
# If this fails, declarative expansion does not match the old list yet.
# Easy rollback: comment out the ROWS_ROSTER = get_roster_rows() line + this assert,
# then restore the original list assignment (e.g. assign _LEGACY_ROWS_ROSTER back to ROWS_ROSTER).
assert ROWS_ROSTER == _LEGACY_ROWS_ROSTER, (
    "get_roster_rows() must exactly reproduce the legacy ROWS_ROSTER list. "
    "Check ROOM_ORDER order and display_name values in ROOMS_CONFIG."
)
