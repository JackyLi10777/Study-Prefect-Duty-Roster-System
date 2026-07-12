""" 
HyperOS v5.5 CSS generation — Fluid Edition.
Extracted from theme.py for modularity. v5.5 adds: animation easing library,
soft gradient system, micro-interaction transitions, spring animations.
"""
from theme.tokens import (
    PRIMARY, PRIMARY_DARK, TABLE_ROW_EVEN,
    DARK_TABLE_ROW_EVEN,
    GRAD_TEAL, GRAD_TEAL_SOFT, GRAD_TEAL_GLOW,
    GRAD_GLASS_HIGHLIGHT, GRAD_GLASS_DARK,
    GRAD_SUCCESS, GRAD_WARNING, GRAD_ERROR, GRAD_GOLD,
    GRAD_BG_WARM, GRAD_BG_DARK_WARM,
    GRAD_KPI_TEAL, GRAD_KPI_AMBER, GRAD_KPI_SLATE,
    EASING_DEFAULT, EASING_SPRING, EASING_BOUNCE,
    DURATION_MICRO, DURATION_COMPONENT, DURATION_PAGE, DURATION_EMPHASIS,
)


def generate_hyperos_css() -> str:
    """Generate the complete HyperOS v5.5 Fluid CSS block for injection."""
    return f"""<style>
        /* =====================================================================
           HyperOS v5.5 — Fluid Edition
           Premium Liquid Glass + Layered Depth + Smooth Animations + Gradients
           ===================================================================== */

        /* ---- Design Tokens ---- */
        :root {{
            /* Shadows */
            --h-shadow-sm: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
            --h-shadow-md: 0 4px 14px rgba(0,0,0,0.07), 0 2px 6px rgba(0,0,0,0.04);
            --h-shadow-lg: 0 8px 28px rgba(0,0,0,0.10), 0 4px 10px rgba(0,0,0,0.05);
            --h-shadow-xl: 0 12px 36px rgba(0,0,0,0.12), 0 6px 14px rgba(0,0,0,0.06);
            /* Glass */
            --h-glass-bg: linear-gradient(135deg, rgba(255,255,255,0.82), rgba(255,255,255,0.55));
            --h-glass-bg-dark: linear-gradient(135deg, rgba(30,41,59,0.82), rgba(15,23,42,0.62));
            --h-glass-highlight: {GRAD_GLASS_HIGHLIGHT};
            --h-glass-highlight-dark: {GRAD_GLASS_DARK};
            /* Easing (HyperOS Natural) */
            --h-easing: {EASING_DEFAULT};
            --h-spring: {EASING_SPRING};
            --h-bounce: {EASING_BOUNCE};
            /* Duration */
            --h-dur-micro: {DURATION_MICRO};
            --h-dur-comp: {DURATION_COMPONENT};
            --h-dur-page: {DURATION_PAGE};
            --h-dur-emph: {DURATION_EMPHASIS};
            /* Borders */
            --h-border-light: rgba(226,232,240,0.6);
            --h-border-dark: rgba(71,85,105,0.4);
            /* Fonts */
            --font-sans: "Noto Sans TC", "PingFang TC", "Microsoft JhengHei UI", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            --font-display: "Noto Sans TC", "PingFang TC", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            --font-scripture: "Noto Serif TC", "Georgia", "Times New Roman", "Noto Sans TC", serif;
            --line-height-zh: 1.65;
            --line-height-scripture: 1.85;
            /* Gradients */
            --grad-teal: {GRAD_TEAL};
            --grad-teal-soft: {GRAD_TEAL_SOFT};
            --grad-teal-glow: {GRAD_TEAL_GLOW};
            --grad-success: {GRAD_SUCCESS};
            --grad-warning: {GRAD_WARNING};
            --grad-error: {GRAD_ERROR};
            --grad-gold: {GRAD_GOLD};
            --grad-kpi-teal: {GRAD_KPI_TEAL};
            --grad-kpi-amber: {GRAD_KPI_AMBER};
            --grad-kpi-slate: {GRAD_KPI_SLATE};
        }}

        /* ---- Global Typography ---- */
        body {{ font-family: var(--font-sans) !important; line-height: var(--line-height-zh) !important; }}
        h1, h2, h3, .q-toolbar__title {{ font-family: var(--font-display) !important; }}
        .scripture-text {{ font-family: var(--font-scripture) !important; line-height: var(--line-height-scripture) !important; }}
        .scripture-ref {{ font-family: var(--font-sans) !important; letter-spacing: 0.05em !important; }}
        .q-table, .q-card, .prose {{ font-feature-settings: "tnum"; text-rendering: optimizeLegibility; }}
        body.dark .text-body, body.dark .q-table td, body.dark .q-card {{ font-weight: 450; }}

        /* =====================================================================
           CARDS — Liquid Glass + Hover Float + Gradient Border
           ===================================================================== */
        .q-card {{
            border-radius: 20px !important;
            border: 1px solid var(--h-border-light) !important;
            box-shadow: var(--h-shadow-md) !important;
            background: var(--h-glass-bg) !important;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            transition: transform var(--h-dur-comp) var(--h-easing),
                        box-shadow var(--h-dur-comp) var(--h-easing),
                        border-color var(--h-dur-comp) var(--h-easing) !important;
            position: relative; overflow: hidden;
        }}
        .q-card::before {{
            content: "";
            position: absolute; top: 0; left: 0; right: 0; height: 2px;
            background: {GRAD_TEAL};
            opacity: 0; transition: opacity var(--h-dur-comp) var(--h-easing);
        }}
        .q-card:hover {{
            transform: translateY(-4px);
            box-shadow: var(--h-shadow-lg) !important;
            border-color: rgba({PRIMARY[1:]},0.15) !important;
        }}
        .q-card:hover::before {{ opacity: 1; }}

        /* =====================================================================
           BUTTONS — Spring Press + Gradient Hover + Sound-ready
           ===================================================================== */
        .q-btn {{
            border-radius: 14px !important;
            transition: all var(--h-dur-micro) var(--h-easing) !important;
            font-weight: 500 !important;
            position: relative; overflow: hidden;
        }}
        .q-btn::after {{
            content: "";
            position: absolute; inset: 0;
            background: {GRAD_TEAL_SOFT};
            opacity: 0; transition: opacity var(--h-dur-micro) var(--h-easing);
        }}
        .q-btn:hover {{ filter: brightness(1.06); transform: translateY(-1px); }}
        .q-btn:hover::after {{ opacity: 1; }}
        .q-btn:active {{ transform: scale(0.96) translateY(0) !important; filter: brightness(0.92); }}

        /* Primary button gradient */
        .q-btn.bg-teal-7, .q-btn[class*="bg-teal"] {{
            background: {GRAD_TEAL} !important;
            box-shadow: 0 2px 8px rgba({PRIMARY[1:]},0.25);
        }}
        .q-btn.bg-teal-7:hover, .q-btn[class*="bg-teal"]:hover {{
            box-shadow: 0 4px 14px rgba({PRIMARY[1:]},0.35);
        }}

        /* Outline button glass effect */
        .q-btn--outline {{
            backdrop-filter: blur(6px);
            -webkit-backdrop-filter: blur(6px);
        }}

        /* =====================================================================
           FORM FIELDS — Focus Glow Gradient
           ===================================================================== */
        .q-field__control {{
            border-radius: 14px !important;
            transition: all var(--h-dur-micro) var(--h-easing) !important;
        }}
        .q-field--focused .q-field__control {{
            box-shadow: 0 0 0 3px rgba({PRIMARY[1:]},0.12), 0 2px 8px rgba({PRIMARY[1:]},0.06) !important;
            border-color: rgba({PRIMARY[1:]},0.3) !important;
        }}

        /* =====================================================================
           TABLE — Row Hover Glow + Smooth
           ===================================================================== */
        .q-table {{ border-radius: 12px !important; overflow: hidden !important; }}
        .q-table th {{
            background: {GRAD_TEAL_SOFT} !important;
            font-weight: 600 !important; letter-spacing: 0.02em !important;
        }}
        .q-tr {{ transition: background var(--h-dur-micro) var(--h-easing); }}
        .q-tr:hover td {{ background: rgba({PRIMARY[1:]},0.04) !important; }}

        /* =====================================================================
           SIDEBAR — Smooth Slide + Gradient Item Hover
           ===================================================================== */
        .q-item {{
            transition: all var(--h-dur-micro) var(--h-easing) !important;
            border-radius: 12px !important; margin: 2px 6px !important;
        }}
        .q-item:hover {{
            background: {GRAD_TEAL_SOFT} !important;
            transform: translateX(4px);
        }}
        .q-item.q-router-link--active {{
            background: {GRAD_TEAL} !important;
            color: white !important;
            box-shadow: 0 2px 8px rgba({PRIMARY[1:]},0.3);
        }}

        /* =====================================================================
           TABS — Smooth Panel Fade + Gradient Active Tab
           ===================================================================== */
        .q-tab {{
            transition: all var(--h-dur-micro) var(--h-easing) !important;
            border-radius: 12px 12px 0 0 !important;
        }}
        .q-tab--active {{
            background: {GRAD_TEAL_SOFT} !important;
            color: {PRIMARY} !important;
        }}
        .q-tab-panels .q-tab-panel {{
            animation: hFadeSlideIn var(--h-dur-page) var(--h-easing);
        }}

        /* =====================================================================
           MODAL / DIALOG — Spring Entrance + Backdrop Blur
           ===================================================================== */
        .q-dialog__backdrop {{
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
        }}
        .q-dialog .q-card {{
            animation: hModalIn var(--h-dur-page) var(--h-spring);
        }}

        /* =====================================================================
           SCRIPTURE ZONE — Warm Gradient + Golden Glow
           ===================================================================== */
        .scripture-zone {{
            position: relative; overflow: hidden;
            background: {GRAD_BG_WARM};
            border: 2px solid {PRIMARY_LIGHT};
            border-left: 6px solid {ACCENT_GOLD};
            transition: border-color var(--h-dur-comp) var(--h-easing);
        }}
        .scripture-zone::after {{
            content: "";
            position: absolute; top: -100px; right: -100px;
            width: 280px; height: 280px;
            background: radial-gradient(circle, rgba(212,175,55,0.12), transparent 65%);
            pointer-events: none;
            animation: hGoldPulse 4s ease-in-out infinite;
        }}

        /* =====================================================================
           KPI CARDS — Gradient Background + Hover Glow
           ===================================================================== */
        .kpi-card {{
            border-radius: 20px !important;
            overflow: hidden;
            transition: transform var(--h-dur-comp) var(--h-easing),
                        box-shadow var(--h-dur-comp) var(--h-easing) !important;
        }}
        .kpi-card:hover {{
            transform: translateY(-6px) scale(1.02);
            box-shadow: var(--h-shadow-xl) !important;
        }}
        .kpi-card.gradient {{
            color: white !important;
            background: var(--grad-kpi-teal) !important;
        }}
        .kpi-card.gradient:hover {{
            box-shadow: 0 12px 30px rgba({PRIMARY[1:]},0.35) !important;
        }}

        /* =====================================================================
           STATUS INDICATORS — Pulse Animation
           ===================================================================== */
        .status-dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }}
        .status-dot.online {{ background: #10B981; box-shadow: 0 0 0 4px rgba(16,185,129,0.12); }}
        .status-dot.offline {{ background: #EF4444; box-shadow: 0 0 0 4px rgba(239,68,68,0.10); }}
        .status-dot.warning {{ background: #F59E0B; box-shadow: 0 0 0 4px rgba(245,158,11,0.12); animation: hPulse 2s ease-in-out infinite; }}

        /* =====================================================================
           LOADING / PROGRESS — Gradient Bar
           ===================================================================== */
        .q-linear-progress__track {{ background: rgba({PRIMARY[1:]},0.08) !important; }}
        .q-linear-progress__model {{
            background: {GRAD_TEAL} !important;
            transition: width var(--h-dur-comp) var(--h-easing);
        }}

        /* =====================================================================
           NOTIFY / TOAST — Slide-in + Gradient
           ===================================================================== */
        .q-notification {{
            border-radius: 14px !important;
            animation: hNotifyIn var(--h-dur-page) var(--h-spring);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
        }}

        /* =====================================================================
           KEYFRAMES — HyperOS Fluid Animations
           ===================================================================== */
        @keyframes hFadeSlideIn {{
            0% {{ opacity: 0; transform: translateY(16px); }}
            100% {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes hModalIn {{
            0% {{ opacity: 0; transform: scale(0.92) translateY(20px); }}
            100% {{ opacity: 1; transform: scale(1) translateY(0); }}
        }}
        @keyframes hNotifyIn {{
            0% {{ opacity: 0; transform: translateX(40px) scale(0.9); }}
            100% {{ opacity: 1; transform: translateX(0) scale(1); }}
        }}
        @keyframes hGoldPulse {{
            0%, 100% {{ opacity: 0.5; }}
            50% {{ opacity: 1; }}
        }}
        @keyframes hPulse {{
            0%, 100% {{ transform: scale(1); opacity: 1; }}
            50% {{ transform: scale(1.3); opacity: 0.7; }}
        }}
        @keyframes hShimmer {{
            0% {{ background-position: -200% 0; }}
            100% {{ background-position: 200% 0; }}
        }}

        /* =====================================================================
           DARK MODE ADAPTATIONS
           ===================================================================== */
        body.dark .q-card {{
            background: var(--h-glass-bg-dark) !important;
            border-color: var(--h-border-dark) !important;
            box-shadow: 0 4px 14px rgba(0,0,0,0.30), 0 2px 6px rgba(0,0,0,0.15) !important;
        }}
        body.dark .q-card:hover {{
            box-shadow: 0 8px 28px rgba(0,0,0,0.40), 0 4px 10px rgba(0,0,0,0.20) !important;
        }}
        body.dark .q-table th {{
            background: rgba({PRIMARY[1:]},0.08) !important;
        }}
        body.dark .q-field--focused .q-field__control {{
            box-shadow: 0 0 0 3px rgba(20,184,166,0.18), 0 2px 8px rgba(20,184,166,0.08) !important;
        }}
        body.dark .scripture-zone {{
            background: {GRAD_BG_DARK_WARM};
            border-color: rgba(139,115,50,0.4);
            border-left-color: rgba(139,115,50,0.6);
        }}

        /* =====================================================================
           ACCESSIBILITY — Reduced Motion
           ===================================================================== */
        @media (prefers-reduced-motion:reduce) {{
            *,*::before,*::after {{
                animation-duration: 0.01ms !important;
                transition-duration: 0.01ms !important;
            }}
        }}


        /* =====================================================================
           DARK MODE COLOR LEAK PREVENTION (Iteration 18.5)
           Force-override common light-mode colors in dark mode
           ===================================================================== */
        body.dark .bg-white { background-color: #1E293B !important; }
        body.dark .bg-slate-50 { background-color: #1E293B !important; }
        body.dark .bg-gray-50 { background-color: #1E293B !important; }
        body.dark .bg-slate-100 { background-color: #334155 !important; }
        body.dark .bg-teal-50 { background-color: rgba(20,184,166,0.10) !important; }
        body.dark .bg-amber-50 { background-color: rgba(245,158,11,0.10) !important; }
        body.dark .text-slate-900 { color: #F1F5F9 !important; }
        body.dark .text-black { color: #F1F5F9 !important; }
        body.dark .text-slate-800 { color: #E2E8F0 !important; }
        body.dark .text-slate-700 { color: #CBD5E1 !important; }
        body.dark .text-slate-600 { color: #E2E8F0 !important; }
        body.dark .text-slate-500 { color: #CBD5E1 !important; }
        body.dark .text-slate-400 { color: #94A3B8 !important; }
        body.dark .border-slate-200 { border-color: #475569 !important; }
        body.dark .border-gray-300 { border-color: #475569 !important; }
        body.dark .border-slate-300 { border-color: #64748B !important; }
        body.dark .shadow-sm { box-shadow: 0 1px 3px rgba(0,0,0,0.40) !important; }
        body.dark .shadow-md { box-shadow: 0 4px 14px rgba(0,0,0,0.40) !important; }
        body.dark .shadow-lg { box-shadow: 0 8px 28px rgba(0,0,0,0.45) !important; }
        /* Table dark mode */
        body.dark .q-table { background-color: #1E293B !important; }
        body.dark .q-table th { background-color: #334155 !important; color: #F1F5F9 !important; }
        body.dark .q-table td { color: #E2E8F0 !important; border-color: #475569 !important; }
        body.dark .q-table tbody tr:nth-child(even) { background-color: #1A2332 !important; }
        /* Drawer/Sidebar dark mode */
        body.dark .q-drawer { background-color: #0F172A !important; }
        body.dark .q-drawer .q-item { color: #E2E8F0 !important; }
        /* Dialog/Modal */
        body.dark .q-dialog .q-card { background-color: #1E293B !important; }
        /* Input fields */
        body.dark .q-field__control { background-color: #1E293B !important; color: #F1F5F9 !important; }
        body.dark .q-field__native { color: #F1F5F9 !important; }
        /* Outline buttons */
        body.dark .q-btn--outline { border-color: #475569 !important; color: #CBD5E1 !important; }
        /* Separator */
        body.dark .q-separator { background-color: #475569 !important; }
        /* Tabs */
        body.dark .q-tab { color: #CBD5E1 !important; }
        body.dark .q-tab--active { color: #14B8A6 !important; }
        /* Expansion items */
        body.dark .q-expansion-item .q-card { background-color: #1E293B !important; }
        /* Status dots keep their own colors */
        body.dark .status-dot.online { background: #10B981; }
        body.dark .status-dot.offline { background: #EF4444; }
        body.dark .status-dot.warning { background: #F59E0B; }

    </style>"""