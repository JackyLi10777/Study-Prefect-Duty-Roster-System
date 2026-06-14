"""
roster/ui/theme.py

Centralized theme management for Light / Dark mode (Increment 2: CSS Custom Properties + expanded coverage).

CSS for base (shared verse/alert/kpi structure) and per-mode (dark/light overrides)
is now generated here for maintainability.

Key improvements:
- Increment 2: CSS Custom Properties (:root) for colors (including exact --accent-gold: #D4AF37), spacing, and key values. Expanded selectors for buttons, inputs, dataframes, tabs, expanders, etc. Further dark contrast polish. High Contrast foundation (vars + stub).
- Increment 3: High Contrast mode is now fully functional and toggleable. When enabled, get_high_contrast_css() is applied for significantly improved readability (extreme contrast on text, placeholders, labels, verse/reflection, etc.). Base enclosure + structure always preserved first.

Dark mode contrast strengthened for:
- Placeholders (search/inputs)
- Captions, labels, secondary text (#f0f0f0 or brighter)
- Verse text (#ffffff), reflection content, footers
- Sidebar and main area readability

Base verse enclosure (.verse-card > .verse-inner with padding/borders/shadows)
and gold #D4AF37 accents are preserved exactly (enforced via vars + !important). High Contrast mode uses high-visibility gold variant while maintaining enclosure structure.

Injection is delegated from components.py for clean separation (display layer only).
All changes confined to this file for theme logic.
"""

import streamlit as st

def get_current_theme() -> str:
    return st.session_state.get("theme", "light")

def is_dark() -> bool:
    return get_current_theme() == "dark"

def get_base_css() -> str:
    """Shared base CSS (verse structure, alerts, kpi, main titles, responsive).
    Injected always; mode-specific overrides in dark/light functions use !important.
    Verse enclosure and gold accents preserved.
    """
    return """
<style>
    /* CSS Custom Properties (CSS Variables) for theme colors, spacing, and key values.
       Introduced in Increment 2 for maintainability. All values match previous hard-coded
       values exactly (zero visual change). Gold #D4AF37 and verse enclosure rules preserved
       as first-class concerns. */
    :root {
        /* Core brand / gold-blue aesthetic (must be preserved exactly) */
        --primary-blue: #0B1E3D;
        --accent-gold: #D4AF37;
        --verse-title-accent: #ffeb3b;

        /* Dark theme palette */
        --dark-bg: #0e1117;
        --dark-surface: #161b22;
        --dark-surface-2: #1f2937;
        --dark-surface-3: #262730;
        --dark-text: #fafafa;
        --dark-text-secondary: #f8fafc;
        --dark-text-tertiary: #ffeb3b;
        /* Improved dark contrast vars for verse/reflection (brighter for readability on dark bg while preserving enclosure; balanced not excessive) */
        --dark-verse-text: #fafafa;
        --dark-reflection-text: #f1f5f9;

        /* Light theme palette */
        --light-bg: #ffffff;
        --light-surface: #f8f9fa;
        --light-surface-2: #e8eef5;
        --light-text: #1a1a2e;
        --light-text-secondary: #333333;
        --light-text-tertiary: #555555;

        /* Alerts */
        --danger-bg: #FEF2F2;
        --danger-border: #EF4444;
        --danger-text: #991B1B;
        --warning-bg: #FFFBEB;
        --warning-border: #F59E0B;
        --warning-text: #92400E;

        /* Verse enclosure (exact previous values preserved via vars) */
        --verse-card-padding: 16px 14px;
        --verse-inner-padding: 4px 6px;
        --verse-reflection-padding: 8px 10px;
        --verse-reflection-bg-dark: rgba(212, 175, 55, 0.04);
        --verse-reflection-bg-light: rgba(11, 30, 61, 0.04);

        /* Supporting */
        --kpi-label: #546E7A;
        --placeholder-light: #666666;
        --placeholder-dark: #f0f0f0;

        /* High Contrast Mode foundation (stub for future increment - not activated yet) */
        --hc-text: #ffffff;
        --hc-bg: #000000;
        --hc-surface: #111111;
        --hc-border: #ffffff;
        --hc-gold: #ffcc00;
    }

    .main-title { color: var(--primary-blue); font-size: 34px; font-weight: 700; letter-spacing: 1.5px; margin-bottom: 2px; }
    .main-subtitle { color: var(--accent-gold); font-size: 14px; font-weight: 600; margin-bottom: 18px; }
    .stDataFrame, [data-testid="stDataEditor"] { border-radius: 10px; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.05); }
    .stButton > button { height: 3.0rem; font-weight: 600; border-radius: 8px; transition: all 0.25s ease; }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .danger-alert { background-color: var(--danger-bg); border-left: 5px solid var(--danger-border); color: var(--danger-text); padding: 12px 14px; border-radius: 8px; margin: 8px 0; font-size: 14px; }
    .warning-alert { background-color: var(--warning-bg); border-left: 5px solid var(--warning-border); color: var(--warning-text); padding: 12px 14px; border-radius: 8px; margin: 8px 0; font-size: 14px; }
    .kpi-card { background: var(--light-surface); border-radius: 8px; padding: 10px 14px; margin: 4px 0; border-left: 4px solid var(--primary-blue); box-shadow: 0 2px 6px rgba(0,0,0,0.04); }
    .kpi-card .label { font-size: 12px; color: var(--kpi-label); }
    .kpi-card .value { font-size: 18px; font-weight: 700; color: var(--primary-blue); }
    /* Base verse container for golden border frame (mode CSS will !important override).
       .verse-inner (nested) guarantees verse text + Spiritual Reflection strictly inside >=16px padding + gold border, no overflow, both modes.
       Enclosure values now driven by CSS vars for maintainability while preserving exact previous appearance. */
    .verse-card {
        border: 3px solid var(--accent-gold);
        border-radius: 12px;
        padding: var(--verse-card-padding);
        box-sizing: border-box;
        margin-bottom: 12px;
        /* Base multi-layer box-shadow (mode CSS will layer !important advanced version). */
        box-shadow: 
            0 10px 25px -6px rgba(0, 0, 0, 0.15),
            0 4px 8px -2px rgba(0, 0, 0, 0.1),
            0 0 0 2px var(--accent-gold),
            0 0 12px rgba(212, 175, 55, 0.12),
            inset 0 2px 4px rgba(255, 255, 255, 0.5);
    }
    .verse-card .verse-inner { 
        padding: var(--verse-inner-padding); 
        margin: 0; 
        box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    .verse-card .reflection-box {
        border-left: 4px solid var(--accent-gold);
        padding: var(--verse-reflection-padding);
        margin: 6px 0 2px 0;
        border-radius: 4px;
        box-sizing: border-box;
        max-width: 100%;
    }
    footer {visibility: hidden;}
    .edit-hint { font-size:13px; color:#666; }

    /* Smooth Dark/Light mode transitions (targeted, low-risk; makes toggle feel fluid without flicker on key surfaces like verse box, sidebar, text).
       Transitions on color/bg/border/shadow only. Does not affect layout, HC, or enclosure structure. */
    .stApp, .stSidebar, .verse-card, .kpi-card, .stButton > button,
    input, textarea, .stTextInput input, .stSelectbox > div > div,
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
    """Dark mode overrides with strengthened contrast.
    Uses CSS custom properties (introduced Increment 2) for colors and key values.
    Placeholders, captions, labels, verse/reflection use high-contrast #f0f0f0 / #ffffff.
    Verse enclosure and gold accents (#D4AF37) preserved exactly via vars + !important.
    Expanded coverage for additional Streamlit components for consistency.
    """
    return """
<style>
    /* Dark mode values now primarily driven by CSS vars (exact previous values preserved) */
    .stApp { background-color: var(--dark-bg); color: var(--dark-text); }
    .stSidebar { background-color: var(--dark-surface) !important; color: var(--dark-text-secondary) !important; }
    .stSidebar * { color: var(--dark-text-secondary) !important; }
    .stSidebar .stCaption, .stSidebar label, .stSidebar .stMarkdown { color: var(--dark-text-secondary) !important; }
    .stButton > button { background-color: var(--dark-surface-3); color: var(--dark-text); border: 1px solid #4b5563; }
    .stButton > button:hover { background-color: #374151; }
    .kpi-card { background-color: var(--dark-surface-2) !important; border-left-color: var(--accent-gold) !important; color: var(--dark-text); }
    .verse-card { 
        background: linear-gradient(180deg, #1a1f2e 0%, var(--dark-bg) 100%) !important; 
        border: 3px solid var(--accent-gold) !important; 
        padding: var(--verse-card-padding) !important; 
        border-radius: 12px !important; 
        box-shadow: 
            0 12px 35px -8px rgba(0, 0, 0, 0.45),
            0 6px 10px -4px rgba(0, 0, 0, 0.3),
            0 0 0 2px var(--accent-gold),
            0 0 18px rgba(212, 175, 55, 0.28),
            inset 0 2px 5px rgba(212, 175, 55, 0.18) !important;
        margin-bottom: 12px !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
    }
    .verse-card .verse-inner {
        padding: var(--verse-inner-padding) !important;
        margin: 0 !important;
        box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.12) !important;
    }
    .verse-card .verse-title { color: var(--verse-title-accent) !important; font-size: 17px !important; margin: 0 0 4px 0 !important; }
    .verse-card .verse-ref { color: var(--verse-title-accent) !important; font-weight: 600 !important; margin: 2px 0 !important; }
    .verse-card .verse-text { color: var(--dark-verse-text) !important; font-size: 14px !important; line-height: 1.55 !important; margin: 2px 0 8px 0 !important; }
    .verse-card .verse-footer { color: var(--dark-text-secondary) !important; font-size: 10px !important; margin-top: 6px !important; opacity: 0.9 !important; }
    .verse-card .reflection-box {
        background-color: var(--verse-reflection-bg-dark) !important;
        border-left: 4px solid var(--accent-gold) !important;
        padding: var(--verse-reflection-padding) !important;
        margin: 6px 0 2px 0 !important;
        border-radius: 4px !important;
        font-size: 12.5px !important;
        color: var(--dark-reflection-text) !important;
        box-shadow: none !important;
        box-sizing: border-box !important;
        max-width: 100% !important;
    }
    .verse-card .reflection-box,
    .verse-card .reflection-box * { color: var(--dark-reflection-text) !important; }
    .verse-card .reflection-box strong { color: var(--verse-title-accent) !important; }
    .stDataFrame, [data-testid="stDataEditor"] { background-color: var(--dark-surface-2); color: var(--dark-text); }
    .stAlert { background-color: var(--dark-surface-2); color: var(--dark-text); }
    .stTextInput > div > div > input, .stSelectbox > div > div { background-color: var(--dark-surface-3); color: var(--dark-text); }

    /* Strengthened dark contrast for placeholders, captions, labels, verse/reflection (using vars) */
    .stCaption { color: var(--dark-text-secondary) !important; }
    .stMarkdown { color: var(--dark-text) !important; }
    input::placeholder, textarea::placeholder, .stTextInput input::placeholder, .stTextArea textarea::placeholder { color: var(--dark-text-secondary) !important; opacity: 1 !important; }
    .stSelectbox label, .stTextInput label, .stMultiselect label, .stRadio label, .stCheckbox label { color: var(--dark-text-secondary) !important; }
    .stCaption, .stHelp, small, [data-testid="stCaptionContainer"], .stMultiselect [data-baseweb] + div { color: var(--dark-text-secondary) !important; }
    .stMarkdown small, .stMarkdown p[style*="color"], .stAlert small { color: var(--dark-text-secondary) !important; }
    .stMultiSelect label + div, .stMultiSelect .stHelp { color: var(--dark-text-secondary) !important; }
    /* Targeted stronger contrast for special labels/captions like "🛠️ 本週特殊不開放時段" and similar in dark (uses improved secondary) */
    .stMultiSelect label, .stMultiSelect > label, div[data-baseweb="select"] > label { color: var(--dark-text) !important; }

    /* Improve contrast for subheaders and titles (e.g. fairness "全體領袖生加權工作量天平..." and leave adjustment subheaders/captions) in Dark Mode */
    .stSubheader, h2, h3 { color: var(--dark-text) !important; }

    /* Ensure verse/reflection remain high contrast and enclosed (vars + explicit for robustness) */
    .verse-card .verse-text { color: var(--dark-verse-text) !important; }
    .verse-card .reflection-box,
    .verse-card .reflection-box * { color: var(--dark-reflection-text) !important; }

    /* Hardened dark contrast for secondary labels (metrics, kpi .label), inline hints, expanders/tabs */
    .stMetric label, .stMetric [data-testid="stMetricLabel"], .stMetric .stMarkdown { color: var(--dark-text-secondary) !important; }
    .kpi-card .label { color: var(--dark-text-secondary) !important; }
    p[style*="color:#666"], p[style*="color: #666"] { color: var(--dark-text-secondary) !important; }
    .edit-hint { color: var(--dark-text-secondary) !important; }
    .stExpander, .stTabs [data-baseweb], .stTabs button { color: var(--dark-text-secondary) !important; }

    /* Increment 2: Expanded component coverage for visual consistency in dark mode (using CSS vars) */
    .stTabs [data-baseweb="tab-list"] { background-color: var(--dark-surface); border-bottom: 1px solid var(--dark-surface-2); }
    .stTabs [data-baseweb="tab"] { color: var(--dark-text-secondary); }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: var(--dark-text); border-bottom-color: var(--accent-gold); }
    .stExpander { background-color: var(--dark-surface-2); border: 1px solid var(--dark-surface-3); border-radius: 8px; }
    .stExpander .stMarkdown { color: var(--dark-text-secondary); }
    .stCheckbox > label, .stRadio > label { color: var(--dark-text-secondary); }
    .stFileUploader { color: var(--dark-text-secondary); }
    .stSlider .stMarkdown { color: var(--dark-text-secondary); }
    /* Enhanced dataframe / editor rows and headers for better dark readability */
    .stDataFrame thead tr th { background-color: var(--dark-surface-2) !important; color: var(--dark-text) !important; }
    .stDataFrame tbody tr:hover { background-color: var(--dark-surface-3) !important; }
</style>
"""

def get_light_css() -> str:
    """Light mode overrides (verse structure with light gradient, dark text, standard grays for secondary).
    Uses CSS custom properties (Increment 2) for consistency with dark mode.
    Verse enclosure and gold accents preserved (with !important for overrides).
    """
    return """
<style>
    /* Light mode values now primarily driven by CSS vars (exact previous values preserved) */
    .stApp { background-color: var(--light-bg); color: var(--light-text); }
    .stSidebar { background-color: var(--light-surface) !important; color: var(--light-text) !important; }
    .stSidebar * { color: var(--light-text) !important; }
    .stSidebar .stCaption, .stSidebar label, .stSidebar .stMarkdown { color: var(--light-text-secondary) !important; }
    .stButton > button { background-color: #f0f0f0; color: var(--light-text); }
    .kpi-card { background-color: var(--light-surface) !important; border-left-color: var(--primary-blue) !important; }
    .verse-card { 
        background: linear-gradient(180deg, var(--light-surface) 0%, var(--light-surface-2) 100%) !important; 
        border: 3px solid var(--accent-gold) !important; 
        padding: var(--verse-card-padding) !important; 
        border-radius: 12px !important; 
        box-shadow: 
            0 10px 25px -6px rgba(0, 0, 0, 0.18),
            0 4px 8px -2px rgba(0, 0, 0, 0.12),
            0 0 0 2px var(--accent-gold),
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
        border-left: 4px solid var(--accent-gold) !important;
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

    /* Increment 2: Expanded component coverage mirrored for light mode consistency (using CSS vars) */
    .stTabs [data-baseweb="tab-list"] { background-color: var(--light-surface); border-bottom: 1px solid #e0e0e0; }
    .stTabs [data-baseweb="tab"] { color: var(--light-text-secondary); }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: var(--light-text); border-bottom-color: var(--accent-gold); }
    .stExpander { background-color: var(--light-surface); border: 1px solid #e0e0e0; border-radius: 8px; }
    .stExpander .stMarkdown { color: var(--light-text-secondary); }
    .stCheckbox > label, .stRadio > label { color: var(--light-text-secondary); }
    .stFileUploader { color: var(--light-text-secondary); }
    .stSlider .stMarkdown { color: var(--light-text-secondary); }
    .stDataFrame thead tr th { background-color: var(--light-surface) !important; color: var(--light-text) !important; }
    .stDataFrame tbody tr:hover { background-color: var(--light-surface-2) !important; }
</style>
"""

def apply_theme():
    """Centralized injection: base (shared verse/alert/kpi/main) + mode-specific (dark/light overrides with contrast fixes).
    Call once per render (e.g. early in app or in sidebar) for clean application.
    Verse enclosure and gold #D4AF37 accents preserved in both get_base and overrides.
    CSS variables (Increment 2) are used throughout for easier future maintenance.

    Increment 3: If high_contrast is enabled in session_state, the high-contrast CSS (using --hc-* vars)
    is applied instead of (or on top of) normal dark/light for significantly improved readability.
    When high_contrast is off, previous dark/light behavior is unchanged.
    Base is always injected first to guarantee verse enclosure structure.
    """
    st.markdown(get_base_css(), unsafe_allow_html=True)
    if st.session_state.get("high_contrast", False):
        st.markdown(get_high_contrast_css(), unsafe_allow_html=True)
    elif is_dark():
        st.markdown(get_dark_css(), unsafe_allow_html=True)
    else:
        st.markdown(get_light_css(), unsafe_allow_html=True)

def get_high_contrast_css() -> str:
    """High Contrast Mode (activated in Increment 3).
    Returns a high-visibility stylesheet using --hc-* variables for significantly improved readability
    (extreme contrast on text, placeholders, labels, verse/reflection content, etc.).
    Base CSS (including verse enclosure structure) is always applied first.
    Verse enclosure (padding, .verse-inner nesting, overflow handling) and gold accent structure
    are preserved; colors use high-contrast variants (--hc-gold for accents/borders).
    When high_contrast is disabled, normal dark/light modes are used with no change.
    """
    return """
<style>
    /* High Contrast Mode - extreme readability using --hc-* vars (Increment 3) */
    .stApp { background-color: var(--hc-bg) !important; color: var(--hc-text) !important; }
    .stSidebar { background-color: var(--hc-surface) !important; color: var(--hc-text) !important; }
    .stSidebar * { color: var(--hc-text) !important; }
    .stSidebar .stCaption, .stSidebar label, .stSidebar .stMarkdown { color: var(--hc-text) !important; }

    /* Strong contrast for placeholders, captions, labels, help text */
    .stCaption { color: var(--hc-text) !important; }
    .stMarkdown { color: var(--hc-text) !important; }
    input::placeholder, textarea::placeholder, .stTextInput input::placeholder, .stTextArea textarea::placeholder { color: var(--hc-text) !important; opacity: 1 !important; }
    .stSelectbox label, .stTextInput label, .stMultiselect label, .stRadio label, .stCheckbox label { color: var(--hc-text) !important; }
    .stCaption, .stHelp, small, [data-testid="stCaptionContainer"], .stMultiselect [data-baseweb] + div { color: var(--hc-text) !important; }
    .stMarkdown small, .stMarkdown p[style*="color"], .stAlert small { color: var(--hc-text) !important; }
    .stMetric label, .stMetric [data-testid="stMetricLabel"], .stMetric .stMarkdown { color: var(--hc-text) !important; }
    .kpi-card .label { color: var(--hc-text) !important; }
    p[style*="color:#666"], p[style*="color: #666"] { color: var(--hc-text) !important; }
    .edit-hint { color: var(--hc-text) !important; }

    /* Improve contrast for subheaders/titles and captions (e.g. the mentioned fairness and leave adjustment texts) in High Contrast mode */
    .stSubheader, h2, h3, .stCaption { color: var(--hc-text) !important; }

    /* Inputs, buttons, dataframes etc. with high contrast borders/states */
    .stButton > button { background-color: var(--hc-surface); color: var(--hc-text); border: 2px solid var(--hc-border); }
    .stTextInput > div > div > input, .stSelectbox > div > div { background-color: var(--hc-surface); color: var(--hc-text); border: 1px solid var(--hc-border); }
    .stDataFrame, [data-testid="stDataEditor"] { background-color: var(--hc-surface); color: var(--hc-text); border: 1px solid var(--hc-border); }
    .stAlert { background-color: var(--hc-surface); color: var(--hc-text); border: 1px solid var(--hc-border); }

    /* Tabs, expanders, etc. */
    .stTabs [data-baseweb="tab-list"] { background-color: var(--hc-surface); }
    .stTabs [data-baseweb="tab"] { color: var(--hc-text); }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: var(--hc-text); border-bottom-color: var(--hc-gold); }
    .stExpander { background-color: var(--hc-surface); border: 1px solid var(--hc-border); }
    .stExpander .stMarkdown { color: var(--hc-text); }

    /* Verse enclosure + high contrast content (structure preserved, colors extreme) */
    .verse-card {
        border: 3px solid var(--hc-gold) !important;
        padding: var(--verse-card-padding) !important;
        background: var(--hc-bg) !important;
        box-shadow: none !important;
        margin-bottom: 12px !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
    }
    .verse-card .verse-inner {
        padding: var(--verse-inner-padding) !important;
        margin: 0 !important;
        box-shadow: none !important;
    }
    .verse-card .verse-title { color: var(--hc-gold) !important; font-size: 17px !important; margin: 0 0 4px 0 !important; }
    .verse-card .verse-ref { color: var(--hc-gold) !important; font-weight: 600 !important; margin: 2px 0 !important; }
    .verse-card .verse-text { color: var(--hc-text) !important; font-size: 14px !important; line-height: 1.55 !important; margin: 2px 0 8px 0 !important; }
    .verse-card .verse-footer { color: var(--hc-text) !important; font-size: 10px !important; margin-top: 6px !important; opacity: 0.95 !important; }
    .verse-card .reflection-box {
        background-color: rgba(255, 204, 0, 0.08) !important;  /* subtle high-vis gold tint */
        border-left: 4px solid var(--hc-gold) !important;
        padding: var(--verse-reflection-padding) !important;
        margin: 6px 0 2px 0 !important;
        border-radius: 4px !important;
        font-size: 12.5px !important;
        color: var(--hc-text) !important;
        box-shadow: none !important;
        box-sizing: border-box !important;
        max-width: 100% !important;
    }
    .verse-card .reflection-box strong { color: var(--hc-gold) !important; }

    /* Ensure enclosure and high contrast for verse/reflection remain (no regression on structure) */
    .verse-card .verse-text { color: var(--hc-text) !important; }
    .verse-card .reflection-box { color: var(--hc-text) !important; }
</style>
"""
