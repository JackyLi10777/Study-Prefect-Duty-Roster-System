"""
Professional Teal Design System v3.0 -- Theme Module
=====================================================
Single source of truth for all design tokens, CSS, and styling helpers
for the Sing Yin Study Prefect Duty Roster System (NiceGUI).

Usage:
    from theme import TealTheme, apply_theme
    theme = TealTheme()
    apply_theme()
"""

from nicegui import ui, app

# =============================================================================
# DESIGN TOKENS -- Color System (Section 3 of Design System)
# =============================================================================

class ColorTokens:
    PRIMARY        = "#0F766E"
    PRIMARY_DARK   = "#0D5C57"
    PRIMARY_LIGHT  = "#14B8A6"
    ACCENT_GOLD    = "#D4AF37"
    BACKGROUND     = "#F8FAFC"
    SURFACE        = "#FFFFFF"
    BORDER         = "#E2E8F0"
    TEXT_PRIMARY   = "#1E293B"
    TEXT_SECONDARY = "#64748B"
    TEXT_DISABLED  = "#94A3B8"
    SUCCESS        = "#10B981"
    WARNING        = "#F59E0B"
    ERROR          = "#EF4444"
    INFO           = "#3B82F6"
    TABLE_ROW_EVEN = "#F1F5F9"
    ERROR_BG       = "#FEF2F2"
    SUCCESS_BG     = "#F0FDF4"

class DarkColorTokens:
    BACKGROUND     = "#0F172A"
    SURFACE        = "#1E293B"
    SURFACE_2      = "#334155"
    BORDER         = "#475569"
    TEXT_PRIMARY   = "#F1F5F9"
    TEXT_SECONDARY = "#CBD5E1"
    TEXT_DISABLED  = "#64748B"
    TABLE_ROW_EVEN = "#1E293B"

COLORS = {k: v for k, v in vars(ColorTokens).items() if not k.startswith("_") and isinstance(v, str)}
DARK_COLORS = {k: v for k, v in vars(DarkColorTokens).items() if not k.startswith("_") and isinstance(v, str)}

# =============================================================================
# TYPOGRAPHY (Section 4 of Design System)
# =============================================================================

class Type:
    H1      = "text-[28px] font-bold leading-tight"
    H2      = "text-[22px] font-semibold leading-tight"
    H3      = "text-[18px] font-semibold leading-snug"
    BODY    = "text-[15px] font-normal leading-relaxed"
    BODY_SM = "text-[13px] font-normal leading-snug"
    LABEL   = "text-[14px] font-medium leading-snug"
    MONO    = "font-mono text-[13px]"

TYPOGRAPHY = {"h1": Type.H1, "h2": Type.H2, "h3": Type.H3, "body": Type.BODY, "body_sm": Type.BODY_SM, "label": Type.LABEL}

# =============================================================================
# ELEVATION / SHADOW (Section 6)
# =============================================================================

class Shadow:
    NONE   = ""
    LOW    = "shadow-sm"
    MEDIUM = "shadow-md"
    HIGH   = "shadow-lg"

class Radius:
    INPUT  = "rounded-lg"
    CARD   = "rounded-xl"
    FULL   = "rounded-full"

class Gap:
    XS  = "gap-1"; SM  = "gap-2"; MD  = "gap-4"; LG  = "gap-6"; XL  = "gap-8"

SPACING = {"xs": "p-1", "sm": "p-2", "md": "p-4", "lg": "p-6", "xl": "p-8", "2xl": "p-12"}

# =============================================================================
# THEME CLASS
# =============================================================================

class TealTheme:
    def __init__(self):
        self.color = ColorTokens()
        self.dark  = DarkColorTokens()
        self.type  = Type()
        self.shadow = Shadow()
        self.radius = Radius()
        self.gap   = Gap()

    @property
    def typography(self): return self.type

    @staticmethod
    def button_primary(): return "rounded-lg font-semibold"
    @staticmethod
    def button_secondary(): return "rounded-lg font-semibold"
    @staticmethod
    def card(): return f"{Radius.CARD} {Shadow.LOW}"
    @staticmethod
    def input_width(): return "w-full max-w-md"

def button_primary_classes():   return "rounded-lg font-semibold"
def button_secondary_classes(): return "rounded-lg font-semibold"
def button_danger_classes():    return "rounded-lg font-semibold"
def card_classes():             return f"{Radius.CARD} {Shadow.LOW}"
def input_classes():            return "w-full max-w-md"

# =============================================================================
# THEME MANAGEMENT
# =============================================================================

THEME_KEY = "theme"

def get_theme() -> str:
    return app.storage.user.get(THEME_KEY, "light")

def is_dark() -> bool:
    return get_theme() == "dark"

def toggle_theme():
    current = get_theme()
    new = "dark" if current == "light" else "light"
    app.storage.user[THEME_KEY] = new
    ui.run_javascript(f"document.body.classList.remove('{current}');document.body.classList.add('{new}');")
    # Refresh drawers to pick up dark: Tailwind classes
    ui.run_javascript("""
        var isDark = document.body.classList.contains('dark');
        document.querySelectorAll('.q-drawer').forEach(function(d) {
            if (isDark) { d.classList.add('dark-mode-drawer'); }
            else { d.classList.remove('dark-mode-drawer'); }
        });
        // Also refresh Quasar components that might cache styles
        if (typeof window.QQuasar !== 'undefined') {
            window.QQuasar.dark.set(isDark);
        }
    """)

# =============================================================================
# GLOBAL CSS
# =============================================================================

def get_global_css() -> str:
    C = ColorTokens()
    D = DarkColorTokens()
    return f"""
    <style>
        :root {{
            --color-primary:       {C.PRIMARY};
            --color-primary-dark:  {C.PRIMARY_DARK};
            --color-primary-light: {C.PRIMARY_LIGHT};
            --color-accent-gold:   {C.ACCENT_GOLD};
            --color-background:    {C.BACKGROUND};
            --color-surface:       {C.SURFACE};
            --color-border:        {C.BORDER};
            --color-text-primary:  {C.TEXT_PRIMARY};
            --color-text-secondary:{C.TEXT_SECONDARY};
            --color-text-disabled: {C.TEXT_DISABLED};
            --color-success:       {C.SUCCESS};
            --color-warning:       {C.WARNING};
            --color-error:         {C.ERROR};
            --color-info:          {C.INFO};
        }}

        body {{
            background-color: var(--color-background);
            color: var(--color-text-primary);
            font-family: 'Inter', 'Noto Sans TC', system-ui, -apple-system, sans-serif;
            -webkit-font-smoothing: antialiased;
        }}

        body.dark {{
            --color-background:    {D.BACKGROUND};
            --color-surface:       {D.SURFACE};
            --color-border:        {D.BORDER};
            --color-text-primary:  {D.TEXT_PRIMARY};
            --color-text-secondary:{D.TEXT_SECONDARY};
            --color-text-disabled: {D.TEXT_DISABLED};
        }}

        body.dark .bg-white  {{ background-color: {D.SURFACE}; }}
        body.dark .bg-slate-50 {{ background-color: {D.SURFACE}; }}
        body.dark .bg-slate-100 {{ background-color: {D.SURFACE_2}; }}
        body.dark .border-slate-200 {{ border-color: {D.BORDER}; }}
        body.dark .text-slate-400 {{ color: {D.TEXT_SECONDARY}; }}
        body.dark .text-slate-500 {{ color: {D.TEXT_SECONDARY}; }}
        body.dark .text-slate-600 {{ color: {D.TEXT_SECONDARY}; }}
        body.dark .hover\\:bg-slate-100:hover {{ background-color: {D.SURFACE_2}; }}

        body.dark .shadow-sm {{ box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3); }}

        /* Dark mode: Chinese text legibility (WCAG AA) */
        body.dark .text-body, body.dark table, body.dark .card, body.dark .q-card {{
            font-weight: 450;
        }}

        body, body * {{
            transition: background-color 200ms ease, color 200ms ease, border-color 200ms ease;
        }}

        @media (prefers-reduced-motion: reduce) {{
            body, body * {{ transition: none !important; }}
        }}

        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: var(--color-background); }}
        ::-webkit-scrollbar-thumb {{ background: var(--color-border); border-radius: 4px; }}

        .q-table th {{ font-weight: 600; background: var(--color-background); }}
        .q-table tbody tr:nth-child(even) {{ background: {C.TABLE_ROW_EVEN}; }}
        body.dark .q-table tbody tr:nth-child(even) {{ background: {D.TABLE_ROW_EVEN}; }}


        /* HyperOS CSS: see append_hyperos_css() */
    </style>
    """

def apply_theme():
    ui.add_head_html(get_global_css())
    theme = get_theme()
    append_hyperos_css()
    ui.add_body_html(f"""<script>document.body.classList.add("{theme}");</script>""")

def append_hyperos_css():
    """Inject HyperOS v4.0 Native CSS."""
    css = """<style>
        /* === HyperOS v5.0 - Premium Liquid Glass + Layered Depth === */

        :root {
            --h-shadow-sm: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
            --h-shadow-md: 0 4px 14px rgba(0,0,0,0.07), 0 2px 6px rgba(0,0,0,0.04);
            --h-shadow-lg: 0 8px 28px rgba(0,0,0,0.10), 0 4px 10px rgba(0,0,0,0.05);
            --h-shadow-xl: 0 12px 36px rgba(0,0,0,0.12), 0 6px 14px rgba(0,0,0,0.06);
            --h-glass-bg: linear-gradient(135deg, rgba(255,255,255,0.82), rgba(255,255,255,0.55));
            --h-glass-bg-dark: linear-gradient(135deg, rgba(30,41,59,0.82), rgba(15,23,42,0.62));
            --h-easing: cubic-bezier(0.0, 0.0, 0.2, 1);
            --h-border-light: rgba(226,232,240,0.6);
            --h-border-dark: rgba(71,85,105,0.4);
        }

        /* Card - premium liquid glass + deeper shadows */
        .q-card {
            border-radius: 20px !important;
            border: 1px solid var(--h-border-light) !important;
            box-shadow: var(--h-shadow-md) !important;
            background: var(--h-glass-bg) !important;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            transition: transform 0.3s var(--h-easing), box-shadow 0.3s var(--h-easing), border-color 0.3s var(--h-easing) !important;
        }
        .q-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--h-shadow-lg) !important;
            border-color: rgba(15,118,110,0.15) !important;
        }

        /* Button hierarchy */
        .q-btn {
            border-radius: 14px !important;
            transition: all 0.22s var(--h-easing) !important;
            font-weight: 500 !important;
        }
        .q-btn:hover { filter: brightness(1.06); transform: translateY(-1px); }
        .q-btn:active { transform: scale(0.95) translateY(0) !important; filter: brightness(0.90); }

        /* Primary button (teal-7) */
        .q-btn[class*=bg-teal-7]:hover { box-shadow: 0 4px 12px rgba(15,118,110,0.25) !important; }

        /* Input fields - refined */
        .q-field__control {
            border-radius: 14px !important;
            transition: all 0.22s var(--h-easing) !important;
        }
        .q-field--focused .q-field__control {
            box-shadow: 0 0 0 3px rgba(15,118,110,0.12), 0 2px 8px rgba(15,118,110,0.06) !important;
        }

        /* Table - polished */
        .q-table { border-radius: 12px !important; overflow: hidden !important; }
        .q-tr:hover td { background: rgba(15,118,110,0.03) !important; }
        .q-table th { font-weight: 600 !important; letter-spacing: 0.01em !important; }

        /* Tab panels */
        .q-tab-panels .q-tab-panel { animation: hFadeIn 0.35s var(--h-easing); }
        .q-tab--active { font-weight: 600 !important; }
        @keyframes hFadeIn {
            0pct { opacity: 0; transform: translateY(12px); }
            100pct { opacity: 1; transform: translateY(0); }
        }

        /* Sidebar refinement */
        .q-item:hover { background: rgba(15,118,110,0.05) !important; }

        /* Scripture zone - premium gold glow */
        .scripture-zone { position: relative; overflow: hidden; }
        .scripture-zone::after {
            content: ""; position: absolute; top: -100px; right: -100px;
            width: 280px; height: 280px;
            background: radial-gradient(circle, rgba(212,175,55,0.10), transparent 65%);
            pointer-events: none;
        }

        /* Status dots - refined glow */
        .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
        .status-dot.online { background: #10B981; box-shadow: 0 0 0 4px rgba(16,185,129,0.12); }
        .status-dot.offline { background: #EF4444; box-shadow: 0 0 0 4px rgba(239,68,68,0.10); }
        .status-dot.warning { background: #F59E0B; box-shadow: 0 0 0 4px rgba(245,158,11,0.12); }

        /* Empty state icons */
        .h-empty-icon { opacity: 0.4; filter: saturate(0.5); }

        /* Progress bar - teal styling */
        .q-linear-progress__track { background: rgba(15,118,110,0.08) !important; }
        .q-linear-progress__model { background: linear-gradient(90deg, #0F766E, #14B8A6) !important; }

        /* Dark mode overrides */
        body.dark .q-card {
            background: var(--h-glass-bg-dark) !important;
            border-color: var(--h-border-dark) !important;
            box-shadow: 0 4px 14px rgba(0,0,0,0.30), 0 2px 6px rgba(0,0,0,0.15) !important;
        }
        body.dark .q-card:hover {
            box-shadow: 0 8px 28px rgba(0,0,0,0.40), 0 4px 10px rgba(0,0,0,0.20) !important;
            border-color: rgba(20,184,166,0.2) !important;
        }
        body.dark .q-field--focused .q-field__control {
            box-shadow: 0 0 0 3px rgba(20,184,166,0.18), 0 2px 8px rgba(20,184,166,0.08) !important;
        }

        @media (prefers-reduced-motion:reduce) {
            *,*::before,*::after { animation-duration:0.01ms!important; transition-duration:0.01ms!important; }
        }
    </style>""" 

    ui.add_head_html(css)
