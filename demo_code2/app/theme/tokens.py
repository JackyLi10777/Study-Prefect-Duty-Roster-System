"""
Design tokens — single source of truth for Professional Teal Design System v4.0.
All visual values (colors, shadows, spacing, typography, radius) are defined here.
"""

# ---- Color Tokens ----
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

# Dark mode overrides
DARK_BACKGROUND     = "#0F172A"
DARK_SURFACE        = "#1E293B"
DARK_SURFACE_2      = "#334155"
DARK_BORDER         = "#475569"
DARK_TEXT_PRIMARY   = "#F1F5F9"
DARK_TEXT_SECONDARY = "#94A3B8"
DARK_TABLE_ROW_EVEN = "#1E293B"

# ---- Shadow Tokens ----
SHADOW_NONE   = ""
SHADOW_SM     = "shadow-sm"
SHADOW_MD     = "shadow-md"
SHADOW_LG     = "shadow-lg"

# ---- Radius Tokens ----
RADIUS_INPUT = "rounded-lg"
RADIUS_CARD  = "rounded-xl"
RADIUS_FULL  = "rounded-full"

# ---- Typography Tokens ----
TEXT_H1      = "text-[28px] font-bold leading-tight"
TEXT_H2      = "text-[22px] font-semibold leading-tight"
TEXT_H3      = "text-[18px] font-semibold leading-snug"
TEXT_BODY    = "text-[15px] font-normal leading-relaxed"
TEXT_BODY_SM = "text-[13px] font-normal leading-snug"
TEXT_LABEL   = "text-[14px] font-medium leading-snug"
TEXT_MONO    = "font-mono text-[13px]"

# ---- Spacing Tokens (8px grid) ----
SPACE_XS = "gap-1"
SPACE_SM = "gap-2"
SPACE_MD = "gap-4"
SPACE_LG = "gap-6"
SPACE_XL = "gap-8"

# ---- Card Glass Tokens (HyperOS v5.0) ----
GLASS_BG       = "linear-gradient(135deg, rgba(255,255,255,0.82), rgba(255,255,255,0.55))"
GLASS_BG_DARK  = "linear-gradient(135deg, rgba(30,41,59,0.82), rgba(15,23,42,0.62))"
GLASS_BLUR     = "12px"
GLASS_BORDER   = "rgba(226,232,240,0.6)"
GLASS_BORDER_DARK = "rgba(71,85,105,0.4)"

# =============================================================================
# Design System v5.5 — HyperOS Fluid Animation & Gradient Tokens
# =============================================================================

# ---- Easing Curves (HyperOS Natural Feel) ----
EASING_DEFAULT     = "cubic-bezier(0.0, 0.0, 0.2, 1)"     # Standard out
EASING_DECELERATE  = "cubic-bezier(0.0, 0.0, 0.2, 1)"     # Enter screen
EASING_ACCELERATE  = "cubic-bezier(0.4, 0.0, 1, 1)"       # Exit screen
EASING_SPRING      = "cubic-bezier(0.175, 0.885, 0.32, 1.275)"  # Bouncy emphasis
EASING_BOUNCE      = "cubic-bezier(0.68, -0.55, 0.265, 1.55)"   # Strong bounce

# ---- Animation Duration Tiers (ms) ----
DURATION_MICRO     = "120ms"    # Button press, hover, focus glow
DURATION_COMPONENT = "220ms"    # Card hover, sidebar item, tooltip
DURATION_PAGE      = "350ms"    # Tab switch, modal enter/exit, page load
DURATION_EMPHASIS  = "500ms"    # High-attention: success animation, celebration

# ---- Soft Gradient Palette (HyperOS Multi-layer) ----
# Primary teal gradient
GRAD_TEAL          = "linear-gradient(135deg, #0F766E, #14B8A6)"
GRAD_TEAL_SOFT     = "linear-gradient(135deg, rgba(15,118,110,0.08), rgba(20,184,166,0.04))"
GRAD_TEAL_GLOW     = "radial-gradient(circle at 50% 0%, rgba(20,184,166,0.12), transparent 60%)"

# Glass highlight gradients
GRAD_GLASS_HIGHLIGHT = "linear-gradient(180deg, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.05) 100%)"
GRAD_GLASS_DARK      = "linear-gradient(180deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.01) 100%)"

# Semantic gradients
GRAD_SUCCESS       = "linear-gradient(135deg, #10B981, #34D399)"
GRAD_WARNING       = "linear-gradient(135deg, #F59E0B, #FBBF24)"
GRAD_ERROR         = "linear-gradient(135deg, #EF4444, #F87171)"
GRAD_GOLD          = "linear-gradient(135deg, #D4AF37, #F0D060)"

# Background gradients
GRAD_BG_WARM       = "linear-gradient(180deg, #FDF8F0 0%, #F9F2E3 40%, #F7F6F3 100%)"
GRAD_BG_DARK_WARM  = "linear-gradient(180deg, #1E1B15 0%, #1A1812 40%, #0F172A 100%)"

# KPI card gradients
GRAD_KPI_TEAL      = "linear-gradient(135deg, rgba(15,118,110,0.95), rgba(20,184,166,0.85))"
GRAD_KPI_AMBER     = "linear-gradient(135deg, rgba(245,158,11,0.88), rgba(251,191,36,0.78))"
GRAD_KPI_SLATE     = "linear-gradient(135deg, rgba(71,85,105,0.88), rgba(100,116,139,0.78))"



# ---- Multilingual Font Stack (v4.1) ----
# Noto Sans TC: best open-source Traditional Chinese font
# Fallback chain: Noto Sans TC > PingFang TC > MS JhengHei UI > system-ui > Segoe UI > Roboto
FONT_SANS = '"Noto Sans TC", "PingFang TC", "Microsoft JhengHei UI", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
FONT_DISPLAY = '"Noto Sans TC", "PingFang TC", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
FONT_SCRIPTURE = '"Noto Serif TC", "Georgia", "Times New Roman", "Noto Sans TC", serif'

# Line heights optimized for Chinese-English mixed content
LINE_HEIGHT_ZH = 1.65
LINE_HEIGHT_EN = 1.5
LINE_HEIGHT_SCRIPTURE = 1.85

# Font weights for dark mode (Chinese needs slightly heavier weight in dark mode)
FONT_WEIGHT_DARK_BODY = 450
