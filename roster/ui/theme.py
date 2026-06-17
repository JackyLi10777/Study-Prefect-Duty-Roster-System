"""
roster/ui/theme.py

Centralized theme management for Light / Dark mode.
Dark Mode has been boosted with high-contrast text and bright accents,
replacing the separate High Contrast mode for a simpler, more readable experience.

CSS for base (shared verse/alert/kpi structure) and per-mode (dark/light overrides)
is now generated here for maintainability.

Dark Mode now uses pure white (#ffffff) primary text, bright secondary text (#e5e7eb),
and stronger borders for maximum readability. High Contrast mode has been merged into
Dark Mode —— the toggle is now a single "Dark Mode" button.
"""

import streamlit as st

def get_current_theme() -> str:
    return st.session_state.get("theme", "light")

def is_dark() -> bool:
    return get_current_theme() == "dark"

def get_base_css() -> str:
    """Shared base CSS (verse structure, alerts, kpi, main titles, responsive).
    Injected always; mode-specific overrides in dark/light functions use !important for certainty.
    Verse enclosure and gold accents preserved.

    NOTE: High Contrast mode removed —— Dark Mode has been boosted to serve as the
          sole high-contrast dark experience. Any existing session_state.high_contrast
          values are silently ignored; callers that previously checked it now only check is_dark().
    """
    return """
<style>
    :root {
        --primary-blue: #0F766E;
        --verse-gold-light: #A68B3D;
        --verse-gold-dark: #B8972E;
        --verse-title-accent: #ffeb3b;

        --dark-bg: #1F2526;
        --dark-surface: #2A3033;
        --dark-surface-2: #343B3F;
        --dark-surface-3: #3D4549;

        --light-bg: #F7F6F3;
        --light-surface: #EFEEEB;
        --light-surface-2: #E6E5E1;
        --light-text: #1C1C26;
        --light-text-secondary: #4A4A5A;
        --light-text-tertiary: #6B6B7B;

        --danger-bg: #FEF2F2;
        --danger-border: #EF4444;
        --danger-text: #991B1B;
        --warning-bg: #FFFBEB;
        --warning-border: #F59E0B;
        --warning-text: #92400E;

        --verse-card-padding: 16px 14px;
        --verse-inner-padding: 4px 6px;
        --verse-reflection-padding: 8px 10px;
        --verse-reflection-bg-dark: rgba(212, 175, 55, 0.04);
        --verse-reflection-bg-light: rgba(11, 30, 61, 0.04);

        --kpi-label: #546E7A;
        --placeholder-light: #666666;
    }

    .main-title { color: var(--primary-blue); font-size: 34px; font-weight: 700; letter-spacing: 1.5px; margin-bottom: 2px; }
    .main-subtitle { color: #0F766E; font-size: 14px; font-weight: 600; margin-bottom: 18px; }
    .stDataFrame, [data-testid="stDataEditor"] { border-radius: 10px; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.05); }
    .stButton > button { height: 3.0rem; font-weight: 600; border-radius: 8px; transition: all 0.25s ease; }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .danger-alert { background-color: var(--danger-bg); border-left: 5px solid var(--danger-border); color: var(--danger-text); padding: 12px 14px; border-radius: 8px; margin: 8px 0; font-size: 14px; }
    .warning-alert { background-color: var(--warning-bg); border-left: 5px solid var(--warning-border); color: var(--warning-text); padding: 12px 14px; border-radius: 8px; margin: 8px 0; font-size: 14px; }
    .kpi-card { background: var(--light-surface); border-radius: 8px; padding: 10px 14px; margin: 4px 0; border-left: 4px solid var(--primary-blue); box-shadow: 0 2px 6px rgba(0,0,0,0.04); }
    .kpi-card .label { font-size: 12px; color: var(--kpi-label); }
    .kpi-card .value { font-size: 18px; font-weight: 700; color: var(--primary-blue); }
    .kpi-card.mentoring-pair-badge { border-left-color: #0F766E !important; }

    .verse-card {
        border: 2px solid var(--verse-gold-light);
        border-radius: 12px;
        padding: var(--verse-card-padding);
        box-sizing: border-box;
        margin-bottom: 12px;
        box-shadow:
            0 10px 25px -6px rgba(0, 0, 0, 0.15),
            0 4px 8px -2px rgba(0, 0, 0, 0.1),
            0 0 0 2px var(--verse-gold-light),
            0 0 12px rgba(212, 175, 55, 0.12),
            inset 0 2px 4px rgba(255, 255, 255, 0.5);
    }
    .verse-card .verse-inner {
        padding: var(--verse-inner-padding);
        margin: 0;
        box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    .verse-card .reflection-box {
        border-left: 4px solid var(--verse-gold-light);
        padding: var(--verse-reflection-padding);
        margin: 6px 0 2px 0;
        border-radius: 4px;
        box-sizing: border-box;
        max-width: 100%;
    }
    
    /* Workflow section labels */
    .workflow-label {
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.3px;
    }
    footer { visibility: hidden; }
    .edit-hint { font-size: 13px; color: #666; }

    .stApp, .stSidebar, .verse-card, .kpi-card, .stButton > button,
    input, textarea, .stTextInput input, .stTextArea textarea, .stSelectbox > div > div,
    .stMarkdown, .stCaption, label, small, .stExpander, .stTabs,
    .stMetric, .stDataFrame, .stAlert {
        transition: background-color 0.18s ease-out, color 0.18s ease-out, border-color 0.18s ease-out, box-shadow 0.18s ease-out;
    }

    @media (max-width: 768px) {
        .main-title { font-size: 26px; }
        .kpi-card .value { font-size: 16px; }
    }
</style>
"""

def get_dark_css() -> str:
    """Dark mode overrides with maximum contrast.
    After merging High Contrast into Dark Mode, all text uses pure white (#ffffff)
    or bright gray (#e5e7eb) for superb readability on dark backgrounds.
    Button borders, input borders, and surface edges are strengthened.
    Gold accents are kept subdued warm gold (#B8972E).
    """
    return """
<style>
    /* === DARK MODE —— BOOSTED CONTRAST ===
       High Contrast mode was merged into Dark Mode.
       All text uses pure white or bright gray for superior readability. */
    .stApp { background-color: var(--dark-bg); color: #ffffff; }
    .stSidebar { background-color: var(--dark-surface) !important; color: #ffffff !important; }
    .stSidebar * { color: #ffffff !important; }
    .stSidebar .stCaption, .stSidebar label, .stSidebar .stMarkdown { color: #ffffff !important; }

    .stButton > button { background-color: var(--dark-surface-3); color: #ffffff; border: 2px solid #6b7280; }
    .stButton > button:hover { background-color: #374151; border-color: #9ca3af; }

    .kpi-card { background-color: var(--dark-surface-2) !important; border-left-color: #0F766E !important; color: #ffffff; }
    .kpi-card .label { color: #f0f0f0 !important; }
    .kpi-card .value { color: #ffffff !important; }

    .verse-card {
        background: linear-gradient(180deg, #1a1f2e 0%, #0a0c10 100%) !important;
        border: 2px solid #B8972E !important;
        padding: var(--verse-card-padding) !important;
        border-radius: 12px !important;
        box-shadow:
            0 0 0 2px solid #B8972E,
            0 12px 35px -8px rgba(0, 0, 0, 0.45),
            0 6px 10px -4px rgba(0, 0, 0, 0.3),
            0 0 18px rgba(230, 194, 0, 0.25),
            inset 0 2px 5px rgba(230, 194, 0, 0.15) !important;
        margin-bottom: 12px !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
    }
    .verse-card .verse-inner {
        padding: var(--verse-inner-padding) !important;
        margin: 0 !important;
        box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.12) !important;
    }
    .verse-card .verse-title { color: #ffeb3b !important; font-size: 17px !important; margin: 0 0 4px 0 !important; }
    .verse-card .verse-ref { color: #ffeb3b !important; font-weight: 600 !important; margin: 2px 0 !important; }
    .verse-card .verse-text { color: #ffffff !important; font-size: 14px !important; line-height: 1.55 !important; margin: 2px 0 8px 0 !important; }
    .verse-card .verse-footer { color: #e5e7eb !important; font-size: 10px !important; margin-top: 6px !important; opacity: 1 !important; }
    .verse-card .reflection-box {
        background-color: rgba(230, 194, 0, 0.06) !important;
        border-left: 4px solid #B8972E !important;
        padding: var(--verse-reflection-padding) !important;
        margin: 6px 0 2px 0 !important;
        border-radius: 4px !important;
        font-size: 12.5px !important;
        color: #ffffff !important;
        box-shadow: none !important;
        box-sizing: border-box !important;
        max-width: 100% !important;
    }
    .verse-card .reflection-box,
    .verse-card .reflection-box * { color: #ffffff !important; }
    .verse-card .reflection-box strong { color: #ffeb3b !important; }

    .stDataFrame, [data-testid="stDataEditor"] { background-color: #12161e; color: #ffffff !important; }
    .stDataFrame thead tr th { background-color: #1a202c !important; color: #ffffff !important; border-bottom: 2px solid #B8972E !important; }
    .stDataFrame tbody tr:hover { background-color: #1f2937 !important; }

    .stAlert { background-color: #1e1e1e; color: #ffffff; border: 1px solid #444; }

    .stTextInput > div > div > input, .stSelectbox > div > div, .stTextArea textarea { background-color: #1a1a1a; color: #ffffff; border: 1px solid #555; }

    /* === HIGH-CONTRAST TEXT (merged from former High Contrast mode) === */
    .stCaption { color: #f0f0f0 !important; }
    .stMarkdown { color: #ffffff !important; }
    input::placeholder, textarea::placeholder, .stTextInput input::placeholder, .stTextArea textarea::placeholder { color: #aaaaaa !important; opacity: 1 !important; }
    .stSelectbox label, .stTextInput label, .stMultiselect label, .stRadio label, .stCheckbox label { color: #ffffff !important; }
    .stCaption, .stHelp, small, [data-testid="stCaptionContainer"], .stMultiselect [data-baseweb] + div { color: #f0f0f0 !important; }
    .stMarkdown small, .stMarkdown p[style*="color"], .stAlert small { color: #e5e7eb !important; }
    .stMultiSelect label + div, .stMultiSelect .stHelp { color: #f0f0f0 !important; }
    .stMultiSelect label, .stMultiSelect > label, div[data-baseweb="select"] > label { color: #ffffff !important; }

    .stSubheader, h2, h3 { color: #ffffff !important; }

    .stTabs [data-baseweb="tab-list"] { background-color: #161b22; border-bottom: 1px solid #333; }
    .stTabs [data-baseweb="tab"] { color: #e5e7eb; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #ffffff; border-bottom-color: #ffeb3b; }

    .stExpander { background-color: #161b22; border: 1px solid #333; border-radius: 8px; }
    .stExpander .stMarkdown { color: #f0f0f0; }

    .stMetric label, .stMetric [data-testid="stMetricLabel"], .stMetric .stMarkdown { color: #ffffff !important; }
    .stMetric [data-testid="stMetricValue"] { color: #ffffff !important; }

    p[style*="color:#666"], p[style*="color: #666"] { color: #e5e7eb !important; }
    .edit-hint { color: #e5e7eb !important; }
    .stCheckbox > label, .stRadio > label { color: #f0f0f0; }
    .stFileUploader { color: #f0f0f0; }
    .stSlider .stMarkdown { color: #f0f0f0; }
    .stSelectbox > div > div { background-color: #1a1a1a; color: #ffffff; }
    .stMultiselect > div > div { background-color: #1a1a1a; color: #ffffff; }

    .stInfo, .stWarning, .stSuccess, .stError { color: #ffffff !important; }

    .stSidebar .stSelectbox label, .stSidebar .stTextInput label { color: #ffffff !important; }
    .stSidebar .stCaption, .stSidebar .stMetric { color: #ffffff !important; }

    .stDataFrame td[style*="border-left: 4px solid #0F766E"] {
        background-color: rgba(5, 150, 105, 0.15) !important;
        box-shadow: inset 0 0 0 1px #0F766E !important;
    }

    .main-title { color: #ffffff !important; }
    .main-subtitle { color: #14B8A6 !important; }

    /* === EXTRA CONTRAST FOR FORM HELP, EXPANDERS, SECTION DESCRIPTIONS === */
    .stForm, .stForm label, .stForm .stMarkdown, .stForm .stCaption { color: #ffffff !important; }
    .st-bq, .st-bw, .st-bx { color: #ffffff !important; }
    .stAlert p { color: #ffffff !important; }
    .st-expander .stCaption { color: #f0f0f0 !important; }
    [data-testid="stForm"] label, [data-testid="stForm"] .stMarkdown { color: #ffffff !important; }
    .row-widget.stSelectbox label p { color: #ffffff !important; }
    .st-dg, .st-dh, .st-di, .st-dj { color: #ffffff !important; }
    .stTextInput label p, .stTextArea label p { color: #f0f0f0 !important; }
</style>
"""

def get_light_css() -> str:
    """Light mode overrides (verse structure with light gradient, dark text, standard grays for secondary).
    Verse enclosure and gold accents preserved (with !important for overrides).
    """
    return """
<style>
    .stApp { background-color: var(--light-bg); color: var(--light-text); }
    .stSidebar { background-color: var(--light-surface) !important; color: var(--light-text) !important; }
    .stSidebar * { color: var(--light-text) !important; }
    .stSidebar .stCaption, .stSidebar label, .stSidebar .stMarkdown { color: var(--light-text-secondary) !important; }
    .stButton > button { background-color: #f0f0f0; color: var(--light-text); }
    .kpi-card { background-color: var(--light-surface) !important; border-left-color: var(--primary-blue) !important; }
    .verse-card {
        background: linear-gradient(180deg, var(--light-surface) 0%, var(--light-surface-2) 100%) !important;
        border: 2px solid var(--verse-gold-light) !important;
        padding: var(--verse-card-padding) !important;
        border-radius: 12px !important;
        box-shadow:
            0 10px 25px -6px rgba(0, 0, 0, 0.18),
            0 4px 8px -2px rgba(0, 0, 0, 0.12),
            0 0 0 2px var(--verse-gold-light),
            0 0 12px rgba(212, 175, 55, 0.18),
            inset 0 2px 4px rgba(255, 255, 255, 0.75) !important;
        margin-bottom: 12px !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
    }
    .verse-card .verse-inner {
        padding: var(--verse-inner-padding) !important;
        margin: 0 !important;
        box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.12) !important;
    }
    .verse-card .verse-title { color: var(--primary-blue) !important; font-size: 17px !important; margin: 0 0 4px 0 !important; font-weight: 700 !important; }
    .verse-card .verse-ref { color: var(--light-text) !important; font-weight: 600 !important; margin: 2px 0 !important; }
    .verse-card .verse-text { color: var(--light-text) !important; font-size: 14px !important; line-height: 1.55 !important; margin: 2px 0 8px 0 !important; }
    .verse-card .verse-footer { color: var(--light-text-secondary) !important; font-size: 10px !important; margin-top: 6px !important; opacity: 0.9 !important; }
    .verse-card .reflection-box {
        background-color: var(--verse-reflection-bg-light) !important;
        border-left: 4px solid var(--verse-gold-light) !important;
        padding: var(--verse-reflection-padding) !important;
        margin: 6px 0 2px 0 !important;
        border-radius: 4px !important;
        font-size: 12.5px !important;
        color: var(--light-text) !important;
        box-shadow: none !important;
        box-sizing: border-box !important;
        max-width: 100% !important;
    }
    .verse-card .reflection-box strong { color: var(--primary-blue) !important; }
    .stTextInput > div > div > input, .stSelectbox > div > div { background-color: var(--light-bg); color: var(--light-text); }
    input::placeholder, textarea::placeholder { color: var(--placeholder-light) !important; opacity: 0.85 !important; }
    .stSelectbox label, .stTextInput label, .stMultiselect label, .stRadio label, .stCheckbox label { color: var(--light-text-secondary) !important; }
    .stCaption { color: var(--light-text-tertiary) !important; }
    .stMarkdown { color: var(--light-text) !important; }

    .stTabs [data-baseweb="tab-list"] { background-color: var(--light-surface); border-bottom: 1px solid #f0f0f0; }
    .stTabs [data-baseweb="tab"] { color: var(--light-text-secondary); }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: var(--light-text); border-bottom-color: var(--verse-gold-light); }
    .stExpander { background-color: var(--light-surface); border: 1px solid #f0f0f0; border-radius: 8px; }
    .stExpander .stMarkdown { color: var(--light-text-secondary); }
    .stCheckbox > label, .stRadio > label { color: var(--light-text-secondary); }
    .stFileUploader { color: var(--light-text-secondary); }
    .stSlider .stMarkdown { color: var(--light-text-secondary); }
    .stDataFrame thead tr th { background-color: var(--light-surface) !important; color: var(--light-text) !important; }
    .stDataFrame tbody tr:hover { background-color: var(--light-surface-2) !important; }
</style>
"""

def apply_theme():
    """Centralized injection: base (shared) + mode-specific (dark/light overrides).
    Call once per render (e.g. early in app or in sidebar) for clean application.

    High Contrast mode has been removed; Dark Mode now serves as the sole high-contrast
    dark experience. Existing session_state.high_contrast values are silently ignored.
    Verse enclosure and gold accents preserved in both modes.
    Base is always injected first to guarantee verse enclosure structure.
    """
    st.markdown(get_base_css(), unsafe_allow_html=True)
    if is_dark():
        st.markdown(get_dark_css(), unsafe_allow_html=True)
    else:
        st.markdown(get_light_css(), unsafe_allow_html=True)
