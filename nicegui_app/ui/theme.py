"""Calm, modern system-interface tokens for NiceGUI pages."""

from __future__ import annotations

from nicegui import app, ui


ATMOSPHERE_THEME_PAIRS = {
    "sidebar": ("sidebar-stewardship-light-v1.webp", "sidebar-stewardship-dark-v1.webp"),
    "weekly-pulse": ("weekly-pulse-light-v1.webp", "weekly-pulse-dark-v1.webp"),
    "devotional": ("devotional-sacred-light-v1.webp", "devotional-sacred-dark-v1.webp"),
    "onboarding": ("onboarding-desk-light-v1.webp", "onboarding-desk-dark-v1.webp"),
    "handover": ("handover-archive-light-v1.webp", "handover-archive-dark-v1.webp"),
    "platform": ("platform-stewardship-light-v1.webp", "platform-stewardship-dark-v1.webp"),
    "architecture": ("architecture-stewardship-light-v1.webp", "architecture-stewardship-dark-v1.webp"),
    "architecture-lifeline": ("architecture-lifeline-light-v1.webp", "architecture-lifeline-dark-v1.webp"),
    "empty-ready": ("empty-ready-light-v1.webp", "empty-ready-dark-v1.webp"),
}


def current_theme() -> str:
    return app.storage.user.get("theme", "light")


def toggle_theme() -> None:
    app.storage.user["theme"] = "dark" if current_theme() == "light" else "light"


def sound_feedback_enabled() -> bool:
    """Sound is always opt-in so shared school computers remain quiet by default."""
    return bool(app.storage.user.get("sound_feedback", False))


def toggle_sound_feedback() -> None:
    app.storage.user["sound_feedback"] = not sound_feedback_enabled()


def set_sound_feedback(enabled: bool) -> None:
    app.storage.user["sound_feedback"] = bool(enabled)


def apply_theme() -> None:
    """Inject one restrained theme system for every page before content renders."""
    is_dark = current_theme() == "dark"
    ui.dark_mode(value=is_dark)
    # Quasar's semantic primary is the single source for actionable controls.
    # Named teal palette classes remain available for verified/stable badges.
    ui.colors(primary="#47758B" if is_dark else "#35647C")
    ui.add_head_html(
        """
        <style>
          @font-face { font-family: "Inter"; src: url("/assets/fonts/InterVariable.woff2") format("woff2"); font-style: normal; font-weight: 100 900; font-display: swap; }
          @font-face { font-family: "Noto Sans HK"; src: url("/assets/fonts/NotoSansHK-Regular.woff2") format("woff2"); font-style: normal; font-weight: 400; font-display: swap; }
          @font-face { font-family: "Noto Sans HK"; src: url("/assets/fonts/NotoSansHK-Medium.woff2") format("woff2"); font-style: normal; font-weight: 500; font-display: swap; }
          @font-face { font-family: "Noto Sans HK"; src: url("/assets/fonts/NotoSansHK-SemiBold.woff2") format("woff2"); font-style: normal; font-weight: 600 900; font-display: swap; }
          @font-face { font-family: "Noto Serif HK"; src: url("/assets/fonts/NotoSerifHK-Regular.woff2") format("woff2"); font-style: normal; font-weight: 400; font-display: swap; }
          @font-face { font-family: "Noto Serif HK"; src: url("/assets/fonts/NotoSerifHK-SemiBold.woff2") format("woff2"); font-style: normal; font-weight: 600 900; font-display: swap; }
          :root {
            /* Semantic roles: a colour always carries the same operator meaning. */
            --sy-role-action: #35647C;
            --sy-role-action-strong: #284C60;
            --sy-role-action-soft: #E8F0F3;
            --sy-role-stable: #0F766E;
            --sy-role-stable-soft: #E6F3EF;
            --sy-role-attention: #8A5A00;
            --sy-role-attention-soft: #FFF4D6;
            --sy-role-danger: #B42318;
            --sy-role-danger-soft: #FDECE9;
            --sy-role-neutral: #5F6368;
            --sy-role-neutral-soft: #ECEDEF;
            --sy-on-action: #FFFFFF;
            --sy-on-stable: #FFFFFF;
            --sy-button-primary-bg: #35647C;
            --sy-button-primary-bg-strong: #284C60;
            --sy-teal: var(--sy-role-stable);
            --sy-teal-deep: #0A5B55;
            --sy-accent: var(--sy-role-action);
            --sy-accent-deep: var(--sy-role-action-strong);
            --sy-action-soft: var(--sy-role-action-soft);
            --sy-focus: #147A70;
            --sy-nav-ink: #303231;
            --sy-gold: #FF9F0A;
            --sy-ink: #1C1C1E;
            --sy-muted: #6E6E73;
            --sy-surface: #FFFFFF;
            --sy-ground: #F2F2F7;
            --sy-line: rgba(60, 60, 67, .18);
            --sy-surface-subtle: #E5E5EA;
            --sy-ease: cubic-bezier(.2, .8, .2, 1);
            --sy-ease-enter: cubic-bezier(.16, 1, .3, 1);
            --sy-ease-exit: cubic-bezier(.4, 0, 1, 1);
            --sy-motion-press: 90ms;
            --sy-motion-state: 180ms;
            --sy-motion-layer: 260ms;
            --sy-hover-lift: -2px;
            --sy-hover-glow: rgba(15, 118, 110, .11);
            --sy-hover-shadow: 0 14px 30px rgba(28, 28, 30, .12);
            --sy-image-sidebar: url('/assets/atmosphere/sidebar-stewardship-light-v1.webp');
            --sy-image-weekly-pulse: url('/assets/atmosphere/weekly-pulse-light-v1.webp');
            --sy-image-devotional: url('/assets/atmosphere/devotional-sacred-light-v1.webp');
            --sy-image-onboarding: url('/assets/atmosphere/onboarding-desk-light-v1.webp');
            --sy-image-handover: url('/assets/atmosphere/handover-archive-light-v1.webp');
            --sy-image-platform: url('/assets/atmosphere/platform-stewardship-light-v1.webp');
            --sy-image-architecture: url('/assets/atmosphere/architecture-stewardship-light-v1.webp');
            --sy-image-architecture-lifeline: url('/assets/atmosphere/architecture-lifeline-light-v1.webp');
            --sy-image-empty-ready: url('/assets/atmosphere/empty-ready-light-v1.webp');
            /* Component tokens */
            --sy-status-action-fg: var(--sy-role-action);
            --sy-status-action-bg: var(--sy-role-action-soft);
            --sy-status-stable-fg: var(--sy-role-stable);
            --sy-status-stable-bg: var(--sy-role-stable-soft);
            --sy-status-attention-fg: var(--sy-role-attention);
            --sy-status-attention-bg: var(--sy-role-attention-soft);
            --sy-status-danger-fg: var(--sy-role-danger);
            --sy-status-danger-bg: var(--sy-role-danger-soft);
            --sy-status-neutral-fg: var(--sy-role-neutral);
            --sy-status-neutral-bg: var(--sy-role-neutral-soft);
            --sy-sidebar-veil: linear-gradient(180deg, rgba(255,255,255,.97), rgba(255,255,255,.91) 58%, rgba(248,246,240,.95));
            --sy-empty-ready-veil: linear-gradient(90deg, rgba(255,255,255,.97) 0%, rgba(255,255,255,.94) 58%, rgba(255,255,255,.76) 100%);
            --sy-architecture-veil: linear-gradient(90deg, rgba(251,248,239,.985) 0%, rgba(251,248,239,.94) 45%, rgba(251,248,239,.30) 78%);
            --sy-architecture-mobile-veil: linear-gradient(180deg, rgba(251,248,239,.98) 0%, rgba(251,248,239,.90) 60%, rgba(251,248,239,.42) 100%);
            --sy-platform-veil: linear-gradient(90deg, rgba(250,247,239,.99) 0%, rgba(250,247,239,.95) 46%, rgba(250,247,239,.28) 78%);
          }
          html { background: #F2F2F7; color-scheme: light; }
          html:has(body.body--dark) { background: #000000; }
          .body--dark { color-scheme: dark; }
          body { background: var(--sy-ground); color: var(--sy-ink); font-family: "Inter", "Noto Sans HK", "PingFang HK", "Microsoft JhengHei", system-ui, sans-serif; }
          button, [role="button"], a, input, textarea, select { touch-action: manipulation; }
          .sy-skip-link { position: fixed; z-index: 10000; top: 10px; left: 12px; padding: 10px 14px; border: 2px solid var(--sy-focus); border-radius: 10px; color: var(--sy-ink); background: var(--sy-surface); font-weight: 750; transform: translateY(-160%); transition: transform .16s var(--sy-ease); }
          .sy-skip-link:focus-visible { transform: translateY(0); outline: 3px solid var(--sy-focus); outline-offset: 3px; }
          #main-content:focus { outline: none; }
          .body--dark {
            --sy-role-action: #9BC2D2;
            --sy-role-action-strong: #47758B;
            --sy-role-action-soft: #1A2B34;
            --sy-button-primary-bg: #47758B;
            --sy-button-primary-bg-strong: #35647C;
            --sy-role-stable: #72D6C7;
            --sy-role-stable-soft: rgba(15,118,110,.20);
            --sy-role-attention: #F0C96A;
            --sy-role-attention-soft: rgba(168,132,73,.20);
            --sy-role-danger: #FF8A80;
            --sy-role-danger-soft: rgba(180,35,24,.20);
            --sy-role-neutral: #C5C7CA;
            --sy-role-neutral-soft: #2C2C2E;
            --sy-status-action-fg: var(--sy-role-action);
            --sy-status-action-bg: var(--sy-role-action-soft);
            --sy-status-stable-fg: var(--sy-role-stable);
            --sy-status-stable-bg: var(--sy-role-stable-soft);
            --sy-status-attention-fg: var(--sy-role-attention);
            --sy-status-attention-bg: var(--sy-role-attention-soft);
            --sy-status-danger-fg: var(--sy-role-danger);
            --sy-status-danger-bg: var(--sy-role-danger-soft);
            --sy-status-neutral-fg: var(--sy-role-neutral);
            --sy-status-neutral-bg: var(--sy-role-neutral-soft);
            --sy-ink: #F5F5F7;
            --sy-muted: #AEAEB2;
            --sy-surface: #1C1C1E;
            --sy-ground: #000000;
            --sy-line: rgba(235, 235, 245, .19);
            --sy-surface-subtle: #2C2C2E;
            --sy-accent: var(--sy-role-action);
            --sy-accent-deep: var(--sy-role-action-strong);
            --sy-action-soft: var(--sy-role-action-soft);
            --sy-focus: #72D6C7;
            --sy-nav-ink: #E8E6DF;
            --sy-hover-glow: rgba(94, 234, 212, .10);
            --sy-hover-shadow: 0 16px 34px rgba(0, 0, 0, .34);
            --sy-image-sidebar: url('/assets/atmosphere/sidebar-stewardship-dark-v1.webp');
            --sy-image-weekly-pulse: url('/assets/atmosphere/weekly-pulse-dark-v1.webp');
            --sy-image-devotional: url('/assets/atmosphere/devotional-sacred-dark-v1.webp');
            --sy-image-onboarding: url('/assets/atmosphere/onboarding-desk-dark-v1.webp');
            --sy-image-handover: url('/assets/atmosphere/handover-archive-dark-v1.webp');
            --sy-image-platform: url('/assets/atmosphere/platform-stewardship-dark-v1.webp');
            --sy-image-architecture: url('/assets/atmosphere/architecture-stewardship-dark-v1.webp');
            --sy-image-architecture-lifeline: url('/assets/atmosphere/architecture-lifeline-dark-v1.webp');
            --sy-image-empty-ready: url('/assets/atmosphere/empty-ready-dark-v1.webp');
            --sy-sidebar-veil: linear-gradient(180deg, rgba(20,20,22,.96), rgba(20,20,22,.89) 56%, rgba(12,17,23,.94));
            --sy-empty-ready-veil: linear-gradient(90deg, rgba(18,20,23,.97) 0%, rgba(18,20,23,.94) 58%, rgba(18,20,23,.72) 100%);
            --sy-architecture-veil: linear-gradient(90deg, rgba(11,16,23,.985) 0%, rgba(11,16,23,.93) 46%, rgba(11,16,23,.24) 78%);
            --sy-architecture-mobile-veil: linear-gradient(180deg, rgba(11,16,23,.98) 0%, rgba(11,16,23,.90) 60%, rgba(11,16,23,.38) 100%);
            --sy-platform-veil: linear-gradient(90deg, rgba(10,15,22,.99) 0%, rgba(10,15,22,.94) 46%, rgba(10,15,22,.24) 78%);
          }
          .sy-main { display: flex; flex-direction: column; max-width: 1440px; min-height: 100vh; margin: 0 auto; padding: 32px clamp(18px, 3vw, 48px) 56px; }
          .sy-surface { background: var(--sy-surface); border: 1px solid var(--sy-line); border-radius: 20px; box-shadow: 0 8px 24px rgba(28, 28, 30, .06); }
          .sy-chapel { position: relative; isolation: isolate; overflow: hidden; min-height: 390px; padding: clamp(32px, 5vw, 72px); color: #FFF8E8; background: linear-gradient(145deg, #101A2C 0%, #152842 54%, #293650 100%); border: 1px solid rgba(238,211,147,.36); border-radius: 28px; box-shadow: 0 24px 52px rgba(8,17,31,.30); }
          .sy-chapel:before { content: ""; position: absolute; inset: 0; z-index: 0; opacity: .82; background: radial-gradient(circle at 84% 15%, rgba(248,225,171,.17), transparent 25%), radial-gradient(circle at 7% 104%, rgba(92,111,151,.25), transparent 39%), linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px), linear-gradient(rgba(255,255,255,.018) 1px, transparent 1px); background-size: auto, auto, 30px 30px, 30px 30px; pointer-events: none; }
          .sy-chapel:after { content: ""; position: absolute; z-index: 0; top: 22px; right: 24px; bottom: 22px; width: min(32vw, 360px); border-left: 1px solid rgba(238,211,147,.30); background: linear-gradient(90deg, transparent, rgba(238,211,147,.055)); pointer-events: none; }
          .sy-chapel > * { position: relative; z-index: 1; }
          .sy-chapel-seal { position: absolute !important; top: clamp(24px, 3vw, 42px); right: clamp(24px, 3vw, 42px); width: 82px; opacity: .92; filter: drop-shadow(0 8px 16px rgba(0,0,0,.18)); }
          .sy-verse { max-width: 860px; font-family: "Noto Serif HK", "PMingLiU", serif; font-size: clamp(28px, 3.8vw, 54px); line-height: 1.52; letter-spacing: .015em; text-wrap: pretty; }
          .sy-reflection { max-width: 760px; color: rgba(255,248,232,.86); font-size: 16px; line-height: 1.9; }
          .sy-kicker { color: #F2D393; font-size: 12px; font-weight: 750; letter-spacing: .12em; text-transform: uppercase; }
          .sy-sidebar .q-btn { color: var(--sy-nav-ink) !important; min-height: 44px; }
          .sy-sidebar .q-btn .q-icon, .sy-sidebar .q-btn .q-btn__content { color: inherit !important; }
          .sy-nav-active { position: relative; background: color-mix(in srgb, var(--sy-surface) 78%, var(--sy-action-soft)); color: var(--sy-ink) !important; border: 1px solid color-mix(in srgb, var(--sy-line) 72%, var(--sy-accent)); border-radius: 13px; font-weight: 720; }
          .sy-nav-active:before { content: ""; position: absolute; top: 11px; bottom: 11px; left: 5px; width: 3px; border-radius: 999px; background: var(--sy-accent); }
          .body--dark .sy-nav-active { background: var(--sy-action-soft); color: var(--sy-ink) !important; border-color: color-mix(in srgb, var(--sy-line) 66%, var(--sy-accent)); }
          .sy-nav-section { margin: 18px 10px 5px; color: var(--sy-muted); font-size: 11px; font-weight: 750; letter-spacing: .07em; text-transform: uppercase; }
          .sy-table { border-radius: 16px; overflow: hidden; border: 1px solid var(--sy-line); background: var(--sy-surface); }
          .sy-roster-mobile { display: none; }
          .sy-prefect-mobile { display: none; }
          .sy-adjustment-form { display: grid; gap: 16px; }
          .sy-adjustment-step { display: grid; gap: 10px; padding: 14px; border: 1px solid var(--sy-line); border-radius: 16px; background: color-mix(in srgb, var(--sy-surface) 92%, var(--sy-surface-subtle)); }
          .sy-adjustment-step-title { color: var(--sy-ink); font-size: 15px; font-weight: 720; line-height: 1.4; }
          .q-table__card { box-shadow: none !important; background: transparent !important; }
          .q-table th { background: var(--sy-surface-subtle); font-weight: 700; color: var(--sy-ink); }
          .q-page-container, .q-page { background: var(--sy-ground); color: var(--sy-ink); }
          .q-drawer { background: var(--sy-surface) !important; color: var(--sy-ink); }
          .q-header { background: var(--sy-surface) !important; color: var(--sy-ink); }
          .sy-app-header { min-height: 66px; box-shadow: none !important; }
          .sy-header-bar { min-height: 65px; gap: 12px; }
          .sy-header-title { min-width: 0; max-width: min(42vw, 440px); overflow: hidden; color: var(--sy-ink); text-overflow: ellipsis; white-space: nowrap; letter-spacing: -.018em; }
          .sy-header-tools { flex: 0 0 auto; min-height: 50px; padding: 3px; border: 1px solid var(--sy-line); border-radius: 16px; background: var(--sy-surface-subtle); }
          .sy-header-tools .q-btn, .sy-icon-control, .sy-language-control { min-width: 44px !important; min-height: 44px !important; color: var(--sy-nav-ink) !important; border-radius: 12px !important; }
          .sy-header-tools .q-icon, .sy-header-tools .q-btn__content { color: inherit !important; }
          .sy-language-control { padding-inline: 12px !important; font-weight: 720; }
          .sy-main { color: var(--sy-ink); }
          .sy-page-title, .sy-main > .q-label.text-2xl.font-semibold { color: var(--sy-ink); font-size: clamp(25px, 2.3vw, 31px); font-weight: 750; letter-spacing: -.03em; line-height: 1.25; }
          .sy-sidebar { position: relative; isolation: isolate; overflow: hidden; }
          .sy-sidebar:before { content: ""; position: absolute; inset: 0; z-index: 0; pointer-events: none; background: var(--sy-sidebar-veil), var(--sy-image-sidebar) right bottom / cover no-repeat; }
          .sy-sidebar > * { position: relative; z-index: 1; }
          .sy-brand-mark { width: 60px; height: 58px; padding: 3px; object-fit: contain; image-rendering: auto; transform: translateZ(0); border: 1px solid rgba(28,28,30,.14); border-radius: 15px; background: #FFFFFF; filter: drop-shadow(0 4px 10px rgba(15,118,110,.12)); }
          .body--dark .sy-brand-mark { border-color: rgba(245,245,247,.24); background: #FFFFFF; }
          .body--dark .q-field__native, .body--dark .q-field__input, .body--dark .q-field__label,
          .body--dark .q-tab, .body--dark .q-table, .body--dark .q-td, .body--dark .q-th,
          .body--dark .q-card, .body--dark .q-dialog__inner > .q-card { color: var(--sy-ink) !important; }
          .body--dark .q-field__control:before, .body--dark .q-field__control:after { border-color: var(--sy-line) !important; }
          .body--dark .q-card, .body--dark .q-table__container { background: var(--sy-surface) !important; }
          .body--dark .q-table th { background: #2C2C2E; }
          .q-tab--active { color: var(--sy-teal-deep) !important; }
          .body--dark .q-tab--active { color: #9DDED3 !important; }
          .q-btn { letter-spacing: 0 !important; border-radius: 12px !important; }
          body .q-btn.q-btn--standard:not(.q-btn--outline):not(.q-btn--flat) { background-color: var(--sy-button-primary-bg) !important; background-image: linear-gradient(180deg, color-mix(in srgb, var(--sy-button-primary-bg) 88%, white) 0%, var(--sy-button-primary-bg) 52%, var(--sy-button-primary-bg-strong) 100%) !important; color: var(--sy-on-action) !important; }
          body .q-btn.q-btn--outline:not(.text-negative) { color: var(--sy-role-action) !important; }
          body .q-btn.text-negative { color: var(--sy-role-danger) !important; }
          body .q-btn.bg-negative { color: #FFFFFF !important; background: var(--sy-role-danger) !important; background-image: none !important; }
          .q-btn:not(.q-btn--flat) { min-height: 44px; font-weight: 680; transition: transform var(--sy-motion-press) var(--sy-ease-exit), box-shadow var(--sy-motion-state) var(--sy-ease), background-color var(--sy-motion-state) var(--sy-ease); }
          .q-btn:not(.q-btn--flat):active { transform: translateY(0) scale(.982); transition-duration: var(--sy-motion-press); }
          .q-btn.q-btn--flat { transition: background-color var(--sy-motion-state) var(--sy-ease), transform var(--sy-motion-press) var(--sy-ease-exit), color var(--sy-motion-state) var(--sy-ease); }
          .q-btn:not(.disabled), .q-tab:not(.disabled), .q-expansion-item .q-item { cursor: pointer; }
          .q-btn.disabled, .q-btn[aria-disabled="true"], .q-tab.disabled { cursor: not-allowed; }
          .q-field__control { border-radius: 12px !important; background: color-mix(in srgb, var(--sy-surface) 90%, var(--sy-surface-subtle)); }
          .q-field--outlined .q-field__control:before { border-color: var(--sy-line) !important; }
          .q-field--outlined.q-field--focused .q-field__control:after { border-color: var(--sy-accent) !important; }
          .q-tab { border-radius: 12px 12px 0 0; font-weight: 650; }
          .q-dialog__backdrop { background: rgba(17, 24, 39, .42) !important; }
          .sy-progress-dialog { border: 1px solid var(--sy-line); border-radius: 24px; background: var(--sy-surface); box-shadow: 0 24px 70px rgba(28,28,30,.22); }
          .sy-partial-success-dialog { border: 1px solid color-mix(in srgb, #A88449 48%, var(--sy-line)); border-radius: 24px; background: var(--sy-surface); color: var(--sy-ink); box-shadow: 0 24px 70px rgba(28,28,30,.22); }
          .sy-partial-success-icon { display: inline-flex; align-items: center; justify-content: center; flex: 0 0 44px; width: 44px; height: 44px; border-radius: 14px; color: #7A5416; background: #F7E8C5; font-size: 23px; }
          .body--dark .sy-partial-success-icon { color: #F2D393; background: rgba(168,132,73,.22); }
          .sy-progress-dialog-icon { display: inline-flex; align-items: center; justify-content: center; width: 42px; height: 42px; border-radius: 14px; color: var(--sy-role-action); background: var(--sy-role-action-soft); font-size: 22px; }
          .sy-progress-dialog-title { color: var(--sy-ink); font-size: 17px; font-weight: 750; letter-spacing: -.01em; }
          .sy-progress-dialog-status { color: var(--sy-muted); font-size: 13px; line-height: 1.55; }
          .sy-progress-dialog-note { color: var(--sy-muted); font-size: 12px; line-height: 1.55; }
          .sy-progress-dialog .q-linear-progress { height: 6px; border-radius: 999px; overflow: hidden; background: var(--sy-surface-subtle); }
          .sy-progress-dialog .q-linear-progress__track { opacity: 1; background: var(--sy-surface-subtle) !important; }
          .sy-progress-dialog .q-linear-progress__model { background: var(--sy-accent) !important; transition: transform .32s var(--sy-ease); }
          .body--dark .sy-progress-dialog-icon { background: var(--sy-role-action-soft); color: var(--sy-role-action); }
          .sy-music-trigger { min-width: 44px !important; min-height: 44px !important; }
          .sy-music-dialog { overflow: hidden; border: 1px solid var(--sy-line); border-radius: 24px; background: var(--sy-surface); color: var(--sy-ink); box-shadow: 0 24px 70px rgba(28,28,30,.22); }
          .q-dialog__inner, .q-drawer { overscroll-behavior: contain; }
          .sy-music-dialog-header { padding: 20px 20px 16px; border-bottom: 1px solid var(--sy-line); background: linear-gradient(135deg, color-mix(in srgb, var(--sy-surface) 88%, #E8E4D9), var(--sy-surface)); }
          .sy-music-dialog-icon { display: inline-flex; align-items: center; justify-content: center; width: 44px; height: 44px; flex: 0 0 44px; border-radius: 14px; color: var(--sy-role-action); background: var(--sy-role-action-soft); font-size: 24px; }
          .sy-music-dialog-title { color: var(--sy-ink); font-size: 18px; font-weight: 760; letter-spacing: -.015em; }
          .sy-music-dialog-context { color: var(--sy-muted); font-size: 12px; line-height: 1.45; }
          .sy-music-now-playing { min-height: 22px; color: var(--sy-role-action); font-size: 13px; font-weight: 700; line-height: 1.55; }
          audio.sy-page-music-audio { display: block; width: 100%; min-height: 44px; border: 1px solid var(--sy-line); border-radius: 14px; background: var(--sy-surface-subtle); color-scheme: light; }
          .body--dark audio.sy-page-music-audio { color-scheme: dark; }
          .sy-settings-section { border-top: 3px solid color-mix(in srgb, var(--sy-role-action) 72%, var(--sy-line)); }
          .sy-settings-section-icon { color: var(--sy-role-action); font-size: 24px; }
          .sy-online-music-status { width: fit-content; padding: 7px 11px; border: 1px solid var(--sy-line); border-radius: 999px; color: var(--sy-muted); background: var(--sy-surface-subtle); font-size: 12px; font-weight: 700; }
          .sy-online-music-status--ready { border-color: color-mix(in srgb, var(--sy-role-stable) 36%, var(--sy-line)); color: var(--sy-role-stable); background: var(--sy-role-stable-soft); }
          .sy-youtube-panel { padding-top: 2px; }
          .sy-youtube-frame-wrap { width: 100%; min-height: 200px; aspect-ratio: 16 / 9; overflow: hidden; border: 1px solid var(--sy-line); border-radius: 16px; background: #111318; box-shadow: 0 8px 22px rgba(28,28,30,.10); }
          .sy-youtube-frame-wrap .nicegui-html, .sy-youtube-frame-wrap iframe { display: block; width: 100%; height: 100%; min-height: 200px; border: 0; }
          .sy-youtube-result { min-height: 72px; padding: 9px; border: 1px solid var(--sy-line); border-radius: 14px; background: var(--sy-surface-subtle); }
          .sy-youtube-thumbnail { width: 96px; height: 54px; flex: 0 0 96px; overflow: hidden; border-radius: 9px; object-fit: cover; }
          .sy-audio-setup { border: 1px solid color-mix(in srgb, var(--sy-role-attention) 30%, var(--sy-line)); border-radius: 16px; background: color-mix(in srgb, var(--sy-surface) 78%, var(--sy-role-attention-soft)); }
          .sy-music-library-item { min-height: 54px; padding: 10px 12px; border: 1px solid var(--sy-line); border-radius: 14px; background: color-mix(in srgb, var(--sy-surface) 94%, var(--sy-surface-subtle)); }
          .sy-inline-empty { display: flex; align-items: flex-start; gap: 11px; padding: 13px 14px; border: 1px dashed var(--sy-line); border-radius: 14px; background: var(--sy-surface-subtle); }
          .sy-inline-empty-icon { flex: 0 0 auto; margin-top: 1px; color: var(--sy-role-neutral); font-size: 21px; }
          .sy-inline-empty-title { color: var(--sy-ink); font-size: 13px; font-weight: 720; line-height: 1.45; }
          .sy-inline-empty-copy { color: var(--sy-muted); font-size: 12px; line-height: 1.58; }
          body .q-btn.sy-button-attention { color: var(--sy-role-attention) !important; }
          .q-btn:focus-visible, .q-field:focus-within, .q-tab:focus-visible, .q-item:focus-visible, a:focus-visible { outline: 3px solid var(--sy-focus) !important; outline-offset: 3px; border-radius: 12px; }
          .q-drawer { border-right: 1px solid var(--sy-line) !important; }
          .sy-workbench { position: relative; isolation: isolate; overflow: hidden; padding: clamp(26px, 3vw, 40px); background: var(--sy-surface); border: 1px solid var(--sy-line); border-radius: 28px; box-shadow: 0 16px 42px rgba(28,28,30,.08); transition: box-shadow .24s var(--sy-ease), transform .24s var(--sy-ease); }
          .sy-workbench:after { content: ""; position: absolute; inset: 0; z-index: 0; pointer-events: none; background: var(--sy-image-weekly-pulse) right center / cover no-repeat; opacity: .42; mask-image: linear-gradient(90deg, transparent 31%, black 77%); }
          .body--dark .sy-workbench:after { opacity: .74; filter: brightness(1.12) contrast(.96); }
          .sy-dashboard-grid { display: grid !important; grid-template-columns: minmax(0, 1fr) minmax(320px, .52fr); align-items: start !important; gap: 20px !important; }
          .sy-dashboard-grid--single { grid-template-columns: minmax(0, 1fr) !important; }
          .sy-dashboard-grid .sy-chapel-compact { max-width: none; }
          .sy-daily-start { position: relative; isolation: isolate; overflow: hidden; padding: 20px 24px; border: 1px solid rgba(166,124,52,.34); border-radius: 22px; background: linear-gradient(132deg, #F5EEDC 0%, #EFE3C9 61%, #E7D8BA 100%); color: #213047; box-shadow: 0 12px 30px rgba(74,59,35,.12); transition: box-shadow .22s var(--sy-ease); }
          .sy-daily-start:before { content: ""; position: absolute; z-index: 0; inset: 0; pointer-events: none; background: linear-gradient(90deg, rgba(248,242,228,.98) 0%, rgba(248,242,228,.90) 55%, rgba(248,242,228,.28) 100%); }
          .sy-daily-start:after { content: ""; position: absolute; inset: 0; z-index: 0; pointer-events: none; background: var(--sy-image-devotional) right center / cover no-repeat; opacity: .24; mask-image: linear-gradient(90deg, transparent 29%, black 84%); }
          .sy-daily-start-icon { color: #8B6A30; font-size: 26px; margin-top: 2px; }
          .sy-daily-start-kicker { color: #755A2B; font-size: 12px; font-weight: 750; letter-spacing: .1em; text-transform: uppercase; }
          .sy-daily-start-verse { max-width: 1050px; font-family: "Noto Serif HK", "PMingLiU", serif; font-size: clamp(20px, 2.2vw, 27px); line-height: 1.5; letter-spacing: .012em; color: #213047; }
          .sy-daily-start-reference { color: #685735; font-size: 13px; font-weight: 650; }
          .sy-daily-start-refresh { color: #755A2B !important; }
          .sy-devotional-controls { flex: 0 0 auto; }
          .sy-devotional-tone-select { width: 174px; }
          .sy-devotional-tone-select .q-field__control { min-height: 40px !important; color: #685735; background: rgba(255,252,244,.54); }
          .sy-devotional-tone-select .q-field__native, .sy-devotional-tone-select .q-field__label, .sy-devotional-tone-select .q-field__append { color: #685735 !important; }
          .sy-daily-start-reflection { border-top: 1px solid rgba(117,90,43,.28); }
          .sy-daily-start-reflection .q-item { min-height: 36px; padding: 9px 0; color: #26364D; font-weight: 700; }
          .sy-daily-start-reflection .q-expansion-item__content { color: #39465A; }
          .body--dark .sy-daily-start { border-color: rgba(222,194,127,.44); background: linear-gradient(132deg, #0F1B2D 0%, #142840 61%, #22334A 100%); color: #FFF9EB; box-shadow: 0 12px 30px rgba(10,22,38,.24); }
          .body--dark .sy-daily-start:before { background: linear-gradient(90deg, rgba(11,24,41,.96) 0%, rgba(11,24,41,.82) 54%, rgba(11,24,41,.23) 100%); }
          .body--dark .sy-daily-start:after { opacity: .43; }
          .body--dark .sy-daily-start-icon, .body--dark .sy-daily-start-kicker, .body--dark .sy-daily-start-refresh { color: #F2D393 !important; }
          .body--dark .sy-daily-start-verse, .body--dark .sy-daily-start-reflection .q-item { color: #FFF9EB; }
          .body--dark .sy-daily-start-reference { color: rgba(255,242,207,.82); }
          .body--dark .sy-devotional-tone-select .q-field__control { background: rgba(10,22,38,.42); }
          .body--dark .sy-devotional-tone-select .q-field__native, .body--dark .sy-devotional-tone-select .q-field__label, .body--dark .sy-devotional-tone-select .q-field__append { color: #F2D393 !important; }
          .body--dark .sy-daily-start-reflection { border-top-color: rgba(242,211,147,.34); }
          .body--dark .sy-daily-start-reflection .q-expansion-item__content { color: #FFF4D7; }
          .sy-operation-hint { display: flex; gap: 12px; align-items: flex-start; margin: 14px 0; padding: 12px 14px; border: 1px solid color-mix(in srgb, var(--sy-role-action) 24%, var(--sy-line)); border-left: 3px solid var(--sy-role-action); border-radius: 14px; background: color-mix(in srgb, var(--sy-surface) 82%, var(--sy-role-action-soft)); }
          .body--dark .sy-operation-hint { background: color-mix(in srgb, var(--sy-surface) 74%, var(--sy-role-action-soft)); }
          .sy-operation-hint-icon { flex: 0 0 auto; margin-top: 1px; color: var(--sy-role-action); font-size: 21px; }
          .sy-operation-hint-title { color: var(--sy-ink); font-size: 12px; font-weight: 750; letter-spacing: .04em; }
          .sy-operation-hint-copy { color: var(--sy-muted); font-size: 13px; line-height: 1.6; }
          .sy-empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 11px; min-height: 170px; padding: 28px 24px; border: 1px dashed var(--sy-line); border-radius: 20px; background: var(--sy-surface-subtle); text-align: center; }
          .sy-empty-state--illustrated { min-height: 210px; background: var(--sy-empty-ready-veil), var(--sy-image-empty-ready) right center / cover no-repeat; }
          .sy-empty-state-icon { display: inline-flex; align-items: center; justify-content: center; width: 48px; height: 48px; border-radius: 16px; color: var(--sy-role-neutral); background: var(--sy-role-neutral-soft); font-size: 25px; }
          .sy-empty-state-title { color: var(--sy-ink); font-size: 16px; font-weight: 750; }
          .sy-empty-state-copy { color: var(--sy-muted); font-size: 13px; line-height: 1.62; }
          .body--dark .sy-empty-state { background: var(--sy-surface-subtle); }
          .body--dark .sy-empty-state--illustrated { background: var(--sy-empty-ready-veil), var(--sy-image-empty-ready) right center / cover no-repeat; }
          .body--dark .sy-empty-state-icon { color: var(--sy-role-neutral); background: var(--sy-role-neutral-soft); }
          .sy-status-badge { min-height: 24px; padding: 4px 9px; border: 1px solid currentColor; border-radius: 999px; font-size: 11px; font-weight: 760; line-height: 1.25; }
          body .q-badge.sy-status-badge.sy-tone-action { color: var(--sy-status-action-fg) !important; background-color: var(--sy-status-action-bg) !important; }
          body .q-badge.sy-status-badge.sy-tone-stable { color: var(--sy-status-stable-fg) !important; background-color: var(--sy-status-stable-bg) !important; }
          body .q-badge.sy-status-badge.sy-tone-attention { color: var(--sy-status-attention-fg) !important; background-color: var(--sy-status-attention-bg) !important; }
          body .q-badge.sy-status-badge.sy-tone-danger { color: var(--sy-status-danger-fg) !important; background-color: var(--sy-status-danger-bg) !important; }
          body .q-badge.sy-status-badge.sy-tone-neutral { color: var(--sy-status-neutral-fg) !important; background-color: var(--sy-status-neutral-bg) !important; }
          .sy-fg-action { color: var(--sy-role-action) !important; }
          .sy-fg-stable { color: var(--sy-role-stable) !important; }
          .sy-fg-attention { color: var(--sy-role-attention) !important; }
          .sy-fg-danger { color: var(--sy-role-danger) !important; }
          .sy-fg-neutral { color: var(--sy-role-neutral) !important; }
          .sy-border-attention { border-color: var(--sy-role-attention) !important; }
          .sy-backup-integrity-warning { padding: 15px 16px; border: 1px solid color-mix(in srgb, var(--sy-role-attention) 34%, var(--sy-line)); border-radius: 16px; background: color-mix(in srgb, var(--sy-surface) 78%, var(--sy-role-attention-soft)); }
          .sy-backup-integrity-warning-icon { color: var(--sy-role-attention); font-size: 24px; }
          .sy-storage-lifecycle { padding: 16px 20px; border: 1px solid var(--sy-line); border-radius: 18px; background: var(--sy-surface); box-shadow: 0 6px 18px rgba(28,28,30,.04); }
          .sy-storage-lifecycle-icon { color: var(--sy-teal); font-size: 24px; }
          .sy-storage-lifecycle-title { color: var(--sy-ink); font-size: 16px; font-weight: 750; }
          .sy-storage-lifecycle-intro { color: var(--sy-muted); font-size: 13px; line-height: 1.55; }
          .sy-storage-lifecycle-expand { border-top: 1px solid var(--sy-line); }
          .sy-storage-lifecycle-expand .q-item { min-height: 36px; padding: 10px 0; color: var(--sy-ink); font-size: 13px; font-weight: 700; }
          .sy-storage-lifecycle-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; padding: 4px 0 8px; }
          .sy-storage-lifecycle-step { padding: 14px; border-radius: 14px; background: var(--sy-surface-subtle); }
          .sy-storage-step-icon { color: var(--sy-accent); font-size: 22px; }
          .sy-storage-step-title { margin-top: 12px; color: var(--sy-ink); font-size: 14px; font-weight: 750; }
          .sy-storage-step-copy { margin-top: 5px; color: var(--sy-muted); font-size: 12px; line-height: 1.58; }
          .sy-storage-backup-note { color: var(--sy-muted); font-size: 12px; line-height: 1.6; }
          .sy-status-summary { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 2px 10px; min-width: 154px; padding: 12px 14px; border-radius: 14px; background: var(--sy-surface-subtle); }
          .sy-status-summary .q-icon { grid-column: 2; grid-row: 1 / span 2; align-self: center; font-size: 20px; }
          .sy-handover-readiness-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
          .sy-handover-readiness-card { min-width: 0; padding: 20px; }
          .sy-acceptance-panel { display: grid; gap: 18px; padding: clamp(22px, 3vw, 30px); border: 1px solid var(--sy-line); border-radius: 22px; background: var(--sy-surface); box-shadow: 0 10px 28px rgba(28,28,30,.06); }
          .sy-acceptance-panel-icon { display: inline-flex; align-items: center; justify-content: center; width: 46px; height: 46px; flex: 0 0 auto; border-radius: 14px; color: var(--sy-teal); background: rgba(15,118,110,.10); font-size: 24px; }
          .sy-acceptance-title { color: var(--sy-ink); font-size: clamp(20px, 2vw, 27px); font-weight: 760; letter-spacing: -.025em; }
          .sy-acceptance-intro { max-width: 720px; color: var(--sy-muted); font-size: 14px; line-height: 1.68; }
          .sy-acceptance-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
          .sy-acceptance-card { display: grid; align-content: start; gap: 7px; min-height: 210px; padding: 20px; border: 1px solid var(--sy-line); border-radius: 18px; background: var(--sy-surface-subtle); }
          .sy-acceptance-card--human { background: color-mix(in srgb, var(--sy-surface-subtle) 84%, #FFF4D6); }
          .body--dark .sy-acceptance-card--human { background: color-mix(in srgb, var(--sy-surface-subtle) 88%, #5A3C0B); }
          .sy-acceptance-card-icon { color: var(--sy-role-neutral); font-size: 25px; }
          .sy-acceptance-card-kicker { margin-top: 5px; color: var(--sy-muted); font-size: 11px; font-weight: 780; letter-spacing: .08em; text-transform: uppercase; }
          .sy-acceptance-card-title { color: var(--sy-ink); font-size: 17px; font-weight: 720; line-height: 1.35; }
          .sy-acceptance-card-copy { color: var(--sy-muted); font-size: 13px; line-height: 1.65; }
          .sy-acceptance-meta { margin-top: 5px; color: var(--sy-ink); font-size: 12px; font-weight: 650; line-height: 1.5; }
          .sy-acceptance-steps { border-top: 1px solid var(--sy-line); }
          .sy-acceptance-steps > .q-expansion-item__container > .q-item { min-height: 48px; color: var(--sy-ink); font-weight: 690; }
          .sy-acceptance-step-list { display: grid; gap: 9px; margin: 0; padding: 8px 4px 6px 30px; color: var(--sy-muted); font-size: 13px; line-height: 1.62; }
          .sy-acceptance-actions .q-btn { min-height: 44px; }
          .sy-workbench:before { content: ""; position: absolute; z-index: 2; top: 0; left: 0; right: 0; height: 5px; background: linear-gradient(90deg, #35647C, #0F766E 62%, #A88449); }
          .sy-workbench > *, .sy-daily-start > * { position: relative; z-index: 1; }
          .sy-workbench-title { font-size: clamp(25px, 2.4vw, 36px); font-weight: 800; letter-spacing: -.035em; color: var(--sy-ink); }
          .sy-workbench-intro { max-width: 580px; color: var(--sy-muted); font-size: 15px; line-height: 1.7; }
          .sy-flow { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 0; padding: 0; list-style: none; }
          .sy-flow-step { min-height: 206px; padding: 16px; border: 1px solid transparent; border-radius: 20px; transition: transform var(--sy-motion-state) var(--sy-ease), background-color var(--sy-motion-state) var(--sy-ease), box-shadow var(--sy-motion-layer) var(--sy-ease), border-color var(--sy-motion-state) var(--sy-ease); }
          .sy-flow-index { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; background: var(--sy-surface-subtle); color: var(--sy-muted); font-family: ui-monospace, "SFMono-Regular", "Cascadia Code", monospace; font-weight: 800; font-size: 11px; }
          .sy-flow-title { color: var(--sy-ink); font-size: 17px; font-weight: 750; line-height: 1.3; }
          .sy-flow-copy { min-height: 0; color: var(--sy-muted); font-size: 13px; line-height: 1.65; }
          .sy-flow-step--active { background: linear-gradient(145deg, color-mix(in srgb, var(--sy-surface) 76%, var(--sy-action-soft)), var(--sy-surface)); border-color: color-mix(in srgb, var(--sy-line) 58%, var(--sy-accent)); box-shadow: 0 10px 28px color-mix(in srgb, var(--sy-accent) 14%, transparent); animation: sy-current-step var(--sy-motion-layer) var(--sy-ease-enter) both; }
          .sy-flow-step--active .sy-flow-index { background: var(--sy-accent); color: white; box-shadow: 0 0 0 4px color-mix(in srgb, var(--sy-accent) 16%, transparent); }
          .sy-flow-step--active .sy-flow-title { color: var(--sy-ink); }
          .sy-flow-step--done .sy-flow-index { color: var(--sy-teal); background: rgba(15,118,110,.10); }
          .sy-flow-step--pending .sy-flow-title { color: var(--sy-ink); }
          .sy-flow-disabled { color: var(--sy-muted); font-size: 12px; }
          .sy-export-option { background: color-mix(in srgb, var(--sy-surface) 90%, #EAF3FF); border: 1px solid var(--sy-line); border-radius: 18px; box-shadow: none; }
          .sy-export-option--internal { background: color-mix(in srgb, var(--sy-surface) 92%, #FFF1D6); }
          .body--dark .sy-export-option { background: rgba(10,132,255,.13); }
          .body--dark .sy-export-option--internal { background: rgba(255,159,10,.13); }
          .sy-export-symbol { display: inline-flex; align-items: center; justify-content: center; width: 56px; height: 56px; flex: 0 0 auto; border-radius: 16px; color: var(--sy-teal); background: rgba(15,118,110,.10); font-size: 29px; }
          .sy-onboarding-intro { position: relative; isolation: isolate; overflow: hidden; display: flex; align-items: center; justify-content: space-between; gap: 24px; min-height: 128px; padding: 24px 28px; border: 1px solid var(--sy-line); border-radius: 22px; background: #FAF8F2; box-shadow: 0 8px 24px rgba(28,28,30,.06); }
          .sy-onboarding-intro:before { content: ""; position: absolute; z-index: 0; inset: 0; pointer-events: none; background: linear-gradient(90deg, rgba(255,253,248,.98) 0%, rgba(255,253,248,.92) 48%, rgba(255,253,248,.30) 100%); }
          .sy-onboarding-intro:after { content: ""; position: absolute; z-index: 0; inset: 0; pointer-events: none; background: var(--sy-image-onboarding) right center / cover no-repeat; opacity: .58; mask-image: linear-gradient(90deg, transparent 27%, black 75%); }
          .sy-onboarding-intro > * { position: relative; z-index: 1; }
          .body--dark .sy-onboarding-intro { background: #111923; }
          .body--dark .sy-onboarding-intro:before { background: linear-gradient(90deg, rgba(14,21,30,.98) 0%, rgba(14,21,30,.92) 49%, rgba(14,21,30,.27) 100%); }
          .body--dark .sy-onboarding-intro:after { opacity: .68; }
          .sy-onboarding-symbol { display: inline-flex; align-items: center; justify-content: center; width: 94px; height: 94px; flex: 0 0 auto; border-radius: 24px; color: var(--sy-teal); background: rgba(15,118,110,.10); font-size: 42px; }
          .sy-handover-hero { position: relative; isolation: isolate; overflow: hidden; min-height: 190px; padding: clamp(26px, 3.5vw, 42px); border: 1px solid var(--sy-line); border-radius: 24px; background: #F7F3EA; box-shadow: 0 12px 30px rgba(28,28,30,.07); }
          .sy-handover-hero:before { content: ""; position: absolute; z-index: 0; inset: 0; pointer-events: none; background: linear-gradient(90deg, rgba(255,252,245,.98) 0%, rgba(255,252,245,.91) 46%, rgba(255,252,245,.30) 100%); }
          .sy-handover-hero:after { content: ""; position: absolute; z-index: 0; inset: 0; pointer-events: none; background: var(--sy-image-handover) right center / cover no-repeat; opacity: .62; mask-image: linear-gradient(90deg, transparent 25%, black 74%); }
          .sy-handover-hero > * { position: relative; z-index: 1; }
          .sy-handover-hero-icon { display: inline-flex; align-items: center; justify-content: center; width: 44px; height: 44px; border-radius: 14px; color: var(--sy-teal); background: rgba(15,118,110,.10); font-size: 23px; }
          .sy-handover-hero-title { margin-top: 17px; color: var(--sy-ink); font-size: clamp(25px, 2.4vw, 34px); font-weight: 760; letter-spacing: -.03em; }
          .sy-handover-hero-copy { max-width: 620px; margin-top: 8px; color: var(--sy-muted); font-size: 14px; line-height: 1.7; }
          .body--dark .sy-handover-hero { background: #101820; border-color: rgba(234,222,193,.24); box-shadow: 0 16px 36px rgba(0,0,0,.28); }
          .body--dark .sy-handover-hero:before { background: linear-gradient(90deg, rgba(11,17,26,.98) 0%, rgba(11,17,26,.91) 49%, rgba(11,17,26,.28) 100%); }
          .body--dark .sy-handover-hero:after { opacity: .70; }
          .body--dark .sy-handover-hero-icon { color: #5EEAD4; background: rgba(15,118,110,.20); }
          .sy-architecture-hero { position: relative; isolation: isolate; overflow: hidden; min-height: 262px; padding: clamp(28px, 4vw, 52px); border: 1px solid rgba(34,57,82,.18); border-radius: 26px; background: #F7F2E7; box-shadow: 0 14px 34px rgba(28,28,30,.08); }
          .sy-architecture-hero:before { content: ""; position: absolute; z-index: 0; inset: 0; pointer-events: none; background: var(--sy-architecture-veil), var(--sy-image-architecture) right center / cover no-repeat; }
          .sy-architecture-hero > * { position: relative; z-index: 1; }
          .sy-architecture-kicker { color: var(--sy-teal); font-size: 12px; font-weight: 760; letter-spacing: .1em; }
          .sy-architecture-title { max-width: 640px; color: var(--sy-ink); font-size: clamp(28px, 3vw, 40px); font-weight: 780; letter-spacing: -.035em; line-height: 1.18; }
          .sy-architecture-copy { max-width: 640px; color: var(--sy-muted); font-size: 15px; line-height: 1.72; }
          .sy-architecture-reading-note { max-width: 560px; margin-top: 12px; padding-top: 12px; border-top: 1px solid color-mix(in srgb, var(--sy-line) 72%, transparent); color: var(--sy-muted); font-size: 12px; line-height: 1.6; }
          .body--dark .sy-architecture-hero { background: #10171F; border-color: rgba(234,222,193,.22); box-shadow: 0 18px 42px rgba(0,0,0,.30); }
          .body--dark .sy-architecture-kicker { color: #5EEAD4; }
          .sy-platform-hero { position: relative; isolation: isolate; overflow: hidden; min-height: 310px; padding: clamp(30px, 4.5vw, 58px); border: 1px solid rgba(98,77,48,.18); border-radius: 28px; background: #F7F2E7; box-shadow: 0 18px 42px rgba(28,28,30,.09); }
          .sy-platform-hero:before { content: ""; position: absolute; z-index: 0; inset: 0; pointer-events: none; background: var(--sy-platform-veil), var(--sy-image-platform) center / cover no-repeat; }
          .sy-platform-hero > * { position: relative; z-index: 1; }
          .sy-platform-hero-copy { max-width: 650px; }
          .sy-platform-principle { max-width: 610px; margin-top: 18px; padding-left: 16px; border-left: 3px solid color-mix(in srgb, var(--sy-line) 45%, var(--sy-teal)); color: var(--sy-ink); font-family: "Noto Serif HK", "PMingLiU", serif; font-size: 16px; line-height: 1.75; }
          .body--dark .sy-platform-hero { background: #0D151E; border-color: rgba(234,222,193,.22); box-shadow: 0 20px 46px rgba(0,0,0,.34); }
          .sy-platform-snapshot { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); overflow: hidden; border: 1px solid var(--sy-line); border-radius: 22px; background: var(--sy-surface); box-shadow: 0 8px 24px rgba(28,28,30,.045); }
          .sy-platform-metric { display: flex; flex-direction: column; min-height: 188px; padding: 22px; border-right: 1px solid var(--sy-line); }
          .sy-platform-metric:last-child { border-right: 0; }
          .sy-platform-metric-icon { color: var(--sy-role-neutral); font-size: 23px; }
          .sy-platform-metric-value { margin-top: 16px; color: var(--sy-ink); font-family: ui-monospace, "SFMono-Regular", "Cascadia Code", monospace; font-size: 29px; font-weight: 760; letter-spacing: -.04em; }
          .sy-platform-metric-label { margin-top: 8px; color: var(--sy-ink); font-size: 14px; font-weight: 760; }
          .sy-platform-metric-note { margin-top: auto; padding-top: 12px; color: var(--sy-muted); font-size: 11px; line-height: 1.55; }
          .body--dark .sy-platform-snapshot { box-shadow: none; }
          .sy-platform-unavailable { padding: 22px; border: 1px solid var(--sy-line); border-radius: 20px; background: var(--sy-surface); }
          .sy-platform-culture { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }
          .sy-platform-value { min-height: 190px; padding: 20px; border: 1px solid var(--sy-line); border-radius: 18px; background: var(--sy-surface); }
          .sy-platform-value-index { color: var(--sy-teal); font-family: ui-monospace, "SFMono-Regular", "Cascadia Code", monospace; font-size: 11px; font-weight: 800; }
          .sy-platform-value-title { margin-top: 28px; color: var(--sy-ink); font-size: 17px; font-weight: 760; }
          .sy-platform-value-copy { margin-top: 8px; color: var(--sy-muted); font-size: 12px; line-height: 1.65; }
          .sy-platform-resources { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
          .sy-platform-resource { min-height: 116px; padding: 18px; border: 1px solid var(--sy-line); border-radius: 18px; background: var(--sy-surface); }
          .sy-platform-resource .q-btn { width: 100%; min-height: 44px; justify-content: flex-start; color: var(--sy-accent) !important; }
          .sy-engineering-hero { position: relative; isolation: isolate; overflow: hidden; min-height: 286px; padding: clamp(30px, 4.5vw, 58px); border: 1px solid color-mix(in srgb, var(--sy-line) 72%, var(--sy-accent)); border-radius: 28px; background: linear-gradient(135deg, color-mix(in srgb, var(--sy-surface) 95%, var(--sy-action-soft)), var(--sy-surface)); box-shadow: 0 18px 42px rgba(28,28,30,.08); }
          .sy-engineering-hero:before { content: ""; position: absolute; z-index: 0; inset: 0; pointer-events: none; opacity: .48; background-image: linear-gradient(color-mix(in srgb, var(--sy-line) 45%, transparent) 1px, transparent 1px), linear-gradient(90deg, color-mix(in srgb, var(--sy-line) 45%, transparent) 1px, transparent 1px), radial-gradient(circle at 86% 18%, color-mix(in srgb, var(--sy-action-soft) 80%, transparent), transparent 31%); background-size: 32px 32px, 32px 32px, auto; mask-image: linear-gradient(90deg, transparent 20%, black 62%); }
          .sy-engineering-hero > * { position: relative; z-index: 1; }
          .sy-engineering-hero .sy-architecture-copy { max-width: 720px; }
          .body--dark .sy-engineering-hero { box-shadow: 0 20px 46px rgba(0,0,0,.34); }
          .sy-engineering-facts { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); overflow: hidden; border: 1px solid var(--sy-line); border-radius: 22px; background: var(--sy-surface); }
          .sy-engineering-fact { min-height: 202px; padding: 22px; border-right: 1px solid var(--sy-line); }
          .sy-engineering-fact:last-child { border-right: 0; }
          .sy-engineering-fact-value { color: var(--sy-ink); font-family: ui-monospace, "SFMono-Regular", "Cascadia Code", monospace; font-size: 34px; font-weight: 780; letter-spacing: -.05em; }
          .sy-engineering-fact-icon { color: var(--sy-accent); font-size: 23px; }
          .sy-engineering-fact-title { margin-top: 18px; color: var(--sy-ink); font-size: 15px; font-weight: 770; }
          .sy-engineering-fact-copy { margin-top: 8px; color: var(--sy-muted); font-size: 12px; line-height: 1.62; }
          .sy-engineering-blueprint { position: relative; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; margin: 0; padding: 0; list-style: none; }
          .sy-engineering-blueprint:before { content: ""; position: absolute; z-index: 0; top: 35px; left: 5%; right: 5%; height: 1px; background: linear-gradient(90deg, var(--sy-accent), var(--sy-teal)); opacity: .34; }
          .sy-engineering-blueprint-layer { position: relative; z-index: 1; min-height: 248px; padding: 18px; border: 1px solid var(--sy-line); border-radius: 18px; background: var(--sy-surface); }
          .sy-engineering-blueprint-index { display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px; border: 1px solid color-mix(in srgb, var(--sy-line) 58%, var(--sy-accent)); border-radius: 50%; color: var(--sy-accent); background: var(--sy-surface); font-family: ui-monospace, "SFMono-Regular", "Cascadia Code", monospace; font-size: 10px; font-weight: 800; }
          .sy-engineering-blueprint-icon { color: var(--sy-muted); font-size: 21px; }
          .sy-engineering-blueprint-title { margin-top: 24px; color: var(--sy-ink); font-size: 15px; font-weight: 760; line-height: 1.42; }
          .sy-engineering-blueprint-copy { margin-top: 9px; color: var(--sy-muted); font-size: 12px; line-height: 1.65; }
          .sy-engineering-gates { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin: 0; padding: 0; list-style: none; }
          .sy-engineering-gate { display: grid; grid-template-columns: auto auto minmax(0, 1fr); align-items: center; gap: 10px; min-height: 82px; padding: 15px; border: 1px solid var(--sy-line); border-radius: 16px; background: var(--sy-surface); }
          .sy-engineering-gate-index { color: var(--sy-muted); font-family: ui-monospace, "SFMono-Regular", "Cascadia Code", monospace; font-size: 10px; font-weight: 800; }
          .sy-engineering-gate-icon { color: var(--sy-teal); font-size: 21px; }
          .sy-engineering-gate-title { color: var(--sy-ink); font-size: 13px; font-weight: 730; line-height: 1.4; }
          .sy-engineering-pillars { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
          .sy-engineering-pillar { min-height: 224px; padding: 22px; border: 1px solid var(--sy-line); border-radius: 19px; background: linear-gradient(145deg, var(--sy-surface), color-mix(in srgb, var(--sy-surface) 95%, var(--sy-action-soft))); }
          .sy-engineering-pillar-icon { display: inline-flex; align-items: center; justify-content: center; width: 42px; height: 42px; border-radius: 13px; color: var(--sy-accent); background: var(--sy-action-soft); font-size: 22px; }
          .sy-engineering-pillar-title { margin-top: 18px; color: var(--sy-ink); font-size: 17px; font-weight: 760; }
          .sy-engineering-pillar-copy { margin-top: 9px; color: var(--sy-muted); font-size: 13px; line-height: 1.68; }
          .body--dark .sy-engineering-pillar { background: var(--sy-surface); }
          .sy-engineering-evolution { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0; margin: 0; padding: 0; overflow: hidden; border: 1px solid var(--sy-line); border-radius: 20px; background: var(--sy-surface); list-style: none; }
          .sy-engineering-evolution-item { min-height: 202px; padding: 22px; border-right: 1px solid var(--sy-line); }
          .sy-engineering-evolution-item:last-child { border-right: 0; }
          .sy-engineering-evolution-title { color: var(--sy-teal); font-size: 13px; font-weight: 780; }
          .sy-engineering-evolution-copy { margin-top: 18px; color: var(--sy-muted); font-size: 12px; line-height: 1.68; }
          .sy-engineering-resources { padding: clamp(22px, 3vw, 30px); border: 1px solid var(--sy-line); border-radius: 22px; background: var(--sy-surface); }
          .sy-engineering-resources .q-btn, .sy-engineering-resource-link { min-height: 44px; }
          .sy-engineering-resource-link { display: inline-flex; align-items: center; padding: 0 16px; border-radius: 12px; color: var(--sy-on-action) !important; background: var(--sy-button-primary-bg); font-size: 13px; font-weight: 760; text-decoration: none; }
          .sy-platform-facts { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); overflow: hidden; border: 1px solid var(--sy-line); border-radius: 22px; background: var(--sy-surface); box-shadow: 0 8px 24px rgba(28,28,30,.045); }
          .sy-platform-fact { min-height: 174px; padding: 22px; border-right: 1px solid var(--sy-line); }
          .sy-platform-fact:last-child { border-right: 0; }
          .sy-platform-fact-value { color: var(--sy-accent); font-family: ui-monospace, "SFMono-Regular", "Cascadia Code", monospace; font-size: 31px; font-weight: 760; letter-spacing: -.045em; }
          .sy-platform-fact-label { margin-top: 13px; color: var(--sy-ink); font-size: 14px; font-weight: 760; }
          .sy-platform-fact-copy { margin-top: 7px; color: var(--sy-muted); font-size: 12px; line-height: 1.58; }
          .body--dark .sy-platform-facts { box-shadow: none; }
          .sy-architecture-section { display: grid; gap: 18px; padding-top: 8px; }
          .sy-architecture-section-heading { max-width: 820px; }
          .sy-architecture-section-kicker { color: var(--sy-teal); font-size: 11px; font-weight: 800; letter-spacing: .12em; }
          .sy-architecture-section-title { color: var(--sy-ink); font-size: clamp(23px, 2.4vw, 32px); font-weight: 780; letter-spacing: -.028em; line-height: 1.22; }
          .sy-architecture-section-copy { max-width: 760px; color: var(--sy-muted); font-size: 14px; line-height: 1.7; }
          .body--dark .sy-architecture-section-kicker { color: #9DDED3; }
          .sy-team-operating-model { position: relative; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; padding: 30px; overflow: hidden; border: 1px solid var(--sy-line); border-radius: 24px; background: linear-gradient(135deg, color-mix(in srgb, var(--sy-surface) 94%, #E8EEE9), var(--sy-surface)); }
          .sy-team-operating-model:before { content: ""; position: absolute; top: 130px; left: 16%; right: 16%; height: 1px; background: linear-gradient(90deg, transparent, color-mix(in srgb, var(--sy-line) 52%, var(--sy-accent)), transparent); pointer-events: none; }
          .sy-team-role { position: relative; z-index: 1; min-height: 188px; padding: 20px; border: 1px solid var(--sy-line); border-radius: 18px; background: var(--sy-surface); box-shadow: 0 7px 20px rgba(28,28,30,.05); }
          .sy-team-role--lead { grid-column: 1 / -1; width: min(100%, 520px); min-height: 162px; justify-self: center; border-color: color-mix(in srgb, var(--sy-line) 62%, var(--sy-accent)); }
          .sy-team-role-icon { display: inline-flex; align-items: center; justify-content: center; width: 42px; height: 42px; flex: 0 0 42px; border-radius: 13px; color: var(--sy-accent); background: var(--sy-action-soft); font-size: 22px; }
          .sy-team-role-title { color: var(--sy-ink); font-size: 16px; font-weight: 770; line-height: 1.35; }
          .sy-team-role-function { margin-top: 3px; color: var(--sy-muted); font-size: 11px; font-weight: 700; line-height: 1.45; }
          .sy-team-role-copy { margin-top: 17px; color: var(--sy-muted); font-size: 12px; line-height: 1.65; }
          .sy-team-operating-model-note { max-width: 920px; padding-left: 14px; border-left: 3px solid var(--sy-line-strong); color: var(--sy-muted); font-size: 12px; line-height: 1.65; }
          .body--dark .sy-team-operating-model { background: linear-gradient(135deg, color-mix(in srgb, var(--sy-surface) 92%, #132331), var(--sy-surface)); }
          .body--dark .sy-team-role { box-shadow: none; }
          .sy-capability-map { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
          .sy-capability-card { display: flex; flex-direction: column; min-height: 268px; padding: 21px; border: 1px solid var(--sy-line); border-radius: 19px; background: var(--sy-surface); box-shadow: 0 7px 20px rgba(28,28,30,.045); }
          .sy-capability-icon { color: var(--sy-accent); font-size: 26px; }
          .sy-capability-title { margin-top: 18px; color: var(--sy-ink); font-size: 16px; font-weight: 760; line-height: 1.42; }
          .sy-capability-copy { margin-top: 9px; color: var(--sy-muted); font-size: 12px; line-height: 1.64; }
          .sy-capability-output { margin-top: auto; padding-top: 16px; border-top: 1px solid var(--sy-line); color: var(--sy-teal); font-size: 11px; font-weight: 730; line-height: 1.5; }
          .body--dark .sy-capability-card { box-shadow: none; }
          .body--dark .sy-capability-output { color: #9DDED3; }
          .sy-solutions-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
          .sy-solution-card { display: flex; flex-direction: column; min-height: 292px; padding: 24px; border: 1px solid var(--sy-line); border-radius: 20px; background: linear-gradient(145deg, var(--sy-surface), color-mix(in srgb, var(--sy-surface) 94%, #E7EDF1)); box-shadow: 0 8px 24px rgba(28,28,30,.045); }
          .sy-solution-icon { display: inline-flex; align-items: center; justify-content: center; width: 44px; height: 44px; flex: 0 0 44px; border-radius: 14px; color: var(--sy-accent); background: var(--sy-action-soft); font-size: 23px; }
          .sy-solution-title { color: var(--sy-ink); font-size: 18px; font-weight: 770; line-height: 1.38; }
          .sy-solution-copy { margin-top: 18px; color: var(--sy-muted); font-size: 13px; line-height: 1.68; }
          .sy-solution-outcome { margin-top: 17px; padding-top: 14px; border-top: 1px solid var(--sy-line); color: var(--sy-ink); font-size: 12px; font-weight: 720; line-height: 1.55; }
          .sy-solution-action { min-height: 44px; margin-top: auto; color: var(--sy-accent) !important; font-weight: 720; }
          .body--dark .sy-solution-card { background: linear-gradient(145deg, var(--sy-surface), color-mix(in srgb, var(--sy-surface) 92%, #132331)); box-shadow: none; }
          .sy-architecture-lifeline-visual { position: relative; min-height: clamp(240px, 36vw, 460px); overflow: hidden; border: 1px solid var(--sy-line); border-radius: 24px; background: var(--sy-image-architecture-lifeline) center / cover no-repeat; box-shadow: 0 14px 34px rgba(28,28,30,.09); }
          .sy-architecture-lifeline-visual:after { content: ""; position: absolute; inset: 0; pointer-events: none; background: linear-gradient(90deg, color-mix(in srgb, var(--sy-surface) 18%, transparent), transparent 34%, transparent 84%, rgba(18,29,43,.08)); }
          .body--dark .sy-architecture-lifeline-visual { box-shadow: 0 18px 42px rgba(0,0,0,.32); }
          .sy-service-lifeline { position: relative; display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px; margin: 0; padding: 0; list-style: none; }
          .sy-service-lifeline:before { content: ""; position: absolute; z-index: 0; top: 33px; left: 5%; right: 5%; height: 1px; background: linear-gradient(90deg, rgba(15,118,110,.18), rgba(15,118,110,.52), rgba(168,132,73,.34)); }
          .sy-service-stage { position: relative; z-index: 1; display: flex; flex-direction: column; min-height: 260px; padding: 15px; border: 1px solid var(--sy-line); border-radius: 18px; background: var(--sy-surface); box-shadow: 0 7px 20px rgba(28,28,30,.045); transition: transform .18s var(--sy-ease), border-color .18s var(--sy-ease), box-shadow .18s var(--sy-ease); }
          .sy-service-stage-head { min-height: 38px; }
          .sy-service-stage-index { display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px; flex: 0 0 34px; border: 1px solid rgba(15,118,110,.22); border-radius: 50%; color: var(--sy-teal); background: var(--sy-surface); font-family: ui-monospace, "SFMono-Regular", "Cascadia Code", monospace; font-size: 10px; font-weight: 800; box-shadow: 0 0 0 6px var(--sy-surface); }
          .sy-service-stage-icon { color: var(--sy-muted); font-size: 21px; }
          .sy-service-stage-title { margin-top: 19px; color: var(--sy-ink); font-size: 15px; font-weight: 760; line-height: 1.4; }
          .sy-service-stage-copy { margin-top: 8px; color: var(--sy-muted); font-size: 12px; line-height: 1.62; }
          .sy-service-stage-result { margin-top: auto; padding-top: 14px; color: var(--sy-teal); font-size: 11px; font-weight: 760; line-height: 1.4; }
          .body--dark .sy-service-stage { box-shadow: none; }
          .body--dark .sy-service-stage-index { border-color: rgba(94,234,212,.32); color: #9DDED3; }
          .body--dark .sy-service-stage-result { color: #9DDED3; }
          .sy-architecture-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; }
          .sy-architecture-layer { min-height: 196px; padding: 18px; border: 1px solid var(--sy-line); border-radius: 18px; background: var(--sy-surface); box-shadow: 0 6px 18px rgba(28,28,30,.045); transition: transform .18s var(--sy-ease), box-shadow .18s var(--sy-ease); }
          .sy-architecture-layer-icon { color: var(--sy-teal); font-size: 26px; }
          .sy-architecture-layer-title { margin-top: 18px; color: var(--sy-ink); font-size: 16px; font-weight: 740; line-height: 1.35; }
          .sy-architecture-layer-copy { margin-top: 8px; color: var(--sy-muted); font-size: 13px; line-height: 1.62; }
          .body--dark .sy-architecture-layer { background: var(--sy-surface); box-shadow: none; }
          .sy-trust-evidence-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
          .sy-trust-evidence-card { min-height: 214px; padding: 22px; border: 1px solid var(--sy-line); border-radius: 20px; background: linear-gradient(145deg, var(--sy-surface), color-mix(in srgb, var(--sy-surface) 92%, #E8EEE9)); box-shadow: 0 8px 24px rgba(28,28,30,.045); }
          .sy-trust-evidence-icon { display: inline-flex; align-items: center; justify-content: center; width: 42px; height: 42px; border-radius: 13px; color: var(--sy-teal); background: rgba(15,118,110,.09); font-size: 23px; }
          .sy-trust-evidence-title { margin-top: 18px; color: var(--sy-ink); font-size: 17px; font-weight: 760; }
          .sy-trust-evidence-copy { margin-top: 8px; color: var(--sy-muted); font-size: 13px; line-height: 1.68; }
          .sy-trust-evidence-label { margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--sy-line); color: var(--sy-teal); font-family: ui-monospace, "SFMono-Regular", "Cascadia Code", monospace; font-size: 10px; font-weight: 760; letter-spacing: .02em; }
          .body--dark .sy-trust-evidence-card { background: linear-gradient(145deg, var(--sy-surface), rgba(15,118,110,.08)); box-shadow: none; }
          .body--dark .sy-trust-evidence-icon { color: #9DDED3; background: rgba(15,118,110,.20); }
          .body--dark .sy-trust-evidence-label { color: #9DDED3; }
          .sy-architecture-faq { display: grid; gap: 18px; padding: clamp(22px, 3vw, 32px); border: 1px solid var(--sy-line); border-radius: 24px; background: color-mix(in srgb, var(--sy-surface) 94%, #EEE9DE); }
          .sy-architecture-faq-list { max-width: 920px; }
          .sy-architecture-faq-item { border-bottom: 1px solid var(--sy-line); }
          .sy-architecture-faq-item:last-child { border-bottom: 0; }
          .sy-architecture-faq-item > .q-expansion-item__container > .q-item { min-height: 56px; padding: 10px 4px; color: var(--sy-ink); font-size: 14px; font-weight: 720; }
          .sy-architecture-faq-answer { max-width: 820px; padding: 0 4px 18px 44px; color: var(--sy-muted); font-size: 13px; line-height: 1.72; }
          .body--dark .sy-architecture-faq { background: color-mix(in srgb, var(--sy-surface) 94%, #0F766E); }
          .sy-feedback-channel { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 16px; width: 100%; padding: clamp(22px, 3vw, 30px); border: 1px solid color-mix(in srgb, var(--sy-line) 68%, var(--sy-accent)); border-radius: 22px; background: linear-gradient(145deg, var(--sy-surface), color-mix(in srgb, var(--sy-surface) 94%, #E7EDF1)); }
          .sy-feedback-channel--compact { max-width: 896px; }
          .sy-feedback-channel-icon { display: inline-flex; align-items: center; justify-content: center; width: 46px; height: 46px; border-radius: 15px; color: var(--sy-accent); background: var(--sy-action-soft); font-size: 24px; }
          .sy-feedback-channel-title { color: var(--sy-ink); font-size: 18px; font-weight: 770; }
          .sy-feedback-channel-copy { max-width: 850px; color: var(--sy-muted); font-size: 13px; line-height: 1.68; }
          .sy-feedback-channel-action { display: inline-flex; width: fit-content; min-height: 44px; align-items: center; margin-top: 8px; color: var(--sy-accent) !important; font-size: 13px; font-weight: 760; text-decoration: underline; text-underline-offset: 4px; }
          .sy-feedback-channel-actions { align-items: center; }
          .sy-feedback-channel-actions .sy-feedback-channel-action { margin-top: 0; }
          .sy-feedback-channel-address { color: var(--sy-ink); font-family: ui-monospace, "SFMono-Regular", "Cascadia Code", monospace; font-size: 12px; font-weight: 700; overflow-wrap: anywhere; }
          .sy-feedback-channel-note { max-width: 850px; margin-top: 7px; padding-top: 10px; border-top: 1px solid var(--sy-line); color: var(--sy-muted); font-size: 11px; line-height: 1.58; }
          .body--dark .sy-feedback-channel { background: linear-gradient(145deg, var(--sy-surface), color-mix(in srgb, var(--sy-surface) 92%, #132331)); }
          .sy-sidebar-feedback { display: grid; gap: 8px; margin-top: 18px; padding: 14px; border: 1px solid var(--sy-line); border-radius: 15px; background: color-mix(in srgb, var(--sy-surface) 90%, var(--sy-action-soft)); }
          .sy-sidebar-feedback-icon { color: var(--sy-accent); font-size: 18px; }
          .sy-sidebar-feedback-title { color: var(--sy-nav-ink); font-size: 12px; font-weight: 780; }
          .sy-sidebar-feedback-copy { color: var(--sy-muted); font-size: 10px; line-height: 1.52; }
          .sy-sidebar-feedback-link { min-height: 28px; color: var(--sy-accent) !important; font-family: ui-monospace, "SFMono-Regular", "Cascadia Code", monospace; font-size: 10px; font-weight: 720; overflow-wrap: anywhere; text-decoration: underline; text-underline-offset: 3px; }
          .sy-co-creation { position: relative; isolation: isolate; overflow: hidden; padding: clamp(26px, 3vw, 38px); padding-right: clamp(140px, 15vw, 190px); border: 1px solid rgba(15,118,110,.22); border-radius: 22px; background: linear-gradient(135deg, color-mix(in srgb, var(--sy-surface) 88%, #E7F3EF), var(--sy-surface)); }
          .sy-co-creation-crest { position: absolute !important; z-index: 0; top: 26px; right: 28px; width: 104px; height: 100px; padding: 4px; object-fit: contain; border: 1px solid rgba(28,28,30,.14); border-radius: 18px; background: #FFFFFF; box-shadow: 0 10px 24px rgba(28,28,30,.14); }
          .sy-co-creation > *:not(.sy-co-creation-crest) { position: relative; z-index: 1; }
          .sy-co-creation-title { color: var(--sy-ink); font-size: 23px; font-weight: 760; letter-spacing: -.02em; }
          .sy-co-creation-team { margin-top: 8px; color: var(--sy-teal); font-size: 13px; font-weight: 760; letter-spacing: .04em; }
          .sy-co-creation-copy { max-width: 860px; margin-top: 22px; color: var(--sy-ink); font-size: 15px; line-height: 1.78; }
          .sy-co-creation-quote { max-width: 860px; margin-top: 18px; padding-left: 16px; border-left: 3px solid var(--sy-teal); color: var(--sy-muted); font-family: "Noto Serif HK", "PMingLiU", serif; font-size: 16px; line-height: 1.85; }
          .sy-co-creation-signature { margin-top: 18px; color: var(--sy-muted); font-size: 13px; font-weight: 650; }
          .sy-codex-closing { max-width: 920px; margin-top: 28px; padding-top: 22px; border-top: 1px solid rgba(15,118,110,.22); }
          .sy-codex-closing-title { color: var(--sy-ink); font-size: 15px; font-weight: 760; }
          .sy-codex-closing-copy { margin-top: 8px; color: var(--sy-muted); font-size: 13px; line-height: 1.78; }
          .body--dark .sy-co-creation { border-color: rgba(45,212,191,.28); background: linear-gradient(135deg, rgba(15,118,110,.16), var(--sy-surface)); }
          .body--dark .sy-co-creation-team, .body--dark .sy-co-creation-quote { color: #5EEAD4; }
          .body--dark .sy-co-creation-crest { border-color: rgba(245,245,247,.24); box-shadow: 0 12px 28px rgba(0,0,0,.34); }
          .sy-pointer-reactive { --sy-pointer-x: 50%; --sy-pointer-y: 50%; position: relative; isolation: isolate; overflow: hidden; transition: transform .18s var(--sy-ease), box-shadow .22s var(--sy-ease), border-color .18s var(--sy-ease) !important; }
          .sy-pointer-reactive > *:not(.sy-pointer-light):not(.sy-co-creation-crest) { position: relative; z-index: 1; }
          .sy-pointer-light { position: absolute; z-index: 0; inset: 0; pointer-events: none; opacity: 0; background: radial-gradient(260px circle at var(--sy-pointer-x) var(--sy-pointer-y), var(--sy-hover-glow), transparent 68%); transition: opacity .18s var(--sy-ease); }
          @media (hover: hover) and (pointer: fine) {
            .q-btn:not(.q-btn--flat):not(.disabled):hover { transform: translateY(-1px); box-shadow: 0 8px 18px color-mix(in srgb, var(--sy-accent) 22%, transparent); }
            .q-btn.q-btn--flat:not(.disabled):hover { background: color-mix(in srgb, var(--sy-surface) 70%, var(--sy-action-soft)); }
            .sy-sidebar .q-btn:not(.disabled):hover { transform: translateX(2px); }
            .q-expansion-item > .q-expansion-item__container > .q-item { border-radius: 12px; transition: transform .16s var(--sy-ease), background-color .16s var(--sy-ease), color .16s var(--sy-ease); }
            .q-expansion-item > .q-expansion-item__container > .q-item:hover { transform: translateX(3px); background: color-mix(in srgb, var(--sy-surface) 88%, #DCE9E4); }
            .body--dark .q-expansion-item > .q-expansion-item__container > .q-item:hover { background: rgba(94,234,212,.08); }
            .sy-pointer-reactive:hover { transform: translateY(var(--sy-hover-lift)); box-shadow: var(--sy-hover-shadow); border-color: color-mix(in srgb, var(--sy-line) 55%, var(--sy-teal)); }
            .sy-pointer-reactive:hover .sy-pointer-light { opacity: 1; }
            .sy-service-stage:hover { transform: translateY(-2px); border-color: color-mix(in srgb, var(--sy-line) 55%, var(--sy-teal)); box-shadow: 0 12px 28px rgba(28,28,30,.08); }
            .sy-workbench:hover { box-shadow: 0 20px 50px rgba(10,55,92,.14); }
            .sy-daily-start:hover { box-shadow: 0 16px 38px rgba(10,22,38,.24); }
            .sy-flow-step--pending:hover { transform: none; box-shadow: none; }
          }
          .sy-flow-symbol { display: inline-flex; align-items: center; justify-content: center; width: 52px; height: 52px; border-radius: 16px; color: var(--sy-accent); background: var(--sy-action-soft); font-size: 27px; }
          .body--dark .sy-flow-symbol { background: var(--sy-action-soft); }
          .sy-flow-step--active .sy-flow-symbol { color: #FFFFFF; background: var(--sy-accent); box-shadow: 0 8px 18px color-mix(in srgb, var(--sy-accent) 24%, transparent); }
          .sy-flow-step--active .q-btn { box-shadow: 0 10px 22px color-mix(in srgb, var(--sy-accent) 26%, transparent); transition: transform var(--sy-motion-state) var(--sy-ease), box-shadow var(--sy-motion-layer) var(--sy-ease); }
          .sy-flow-step--active .q-btn:hover { transform: translateY(-1px); box-shadow: 0 13px 26px color-mix(in srgb, var(--sy-accent) 30%, transparent); }
          .sy-practice-banner { position: sticky; z-index: 1900; top: 0; display: flex; align-items: center; gap: 12px; width: 100%; min-height: 58px; padding: 10px clamp(16px, 3vw, 32px); border-bottom: 1px solid #D6A447; color: #3E2D0E; background: #FFF4D6; box-shadow: 0 5px 18px rgba(83,58,12,.10); }
          .sy-practice-banner-icon { flex: 0 0 auto; color: #8A5A00; font-size: 25px; }
          .sy-practice-banner-title { color: inherit; font-size: 14px; font-weight: 800; line-height: 1.35; }
          .sy-practice-banner-copy { color: #614817; font-size: 12px; line-height: 1.5; }
          .body--dark .sy-practice-banner { border-bottom-color: #876A30; color: #FFF1C7; background: #342A18; box-shadow: 0 7px 22px rgba(0,0,0,.28); }
          .body--dark .sy-practice-banner-icon { color: #F0C96A; }
          .body--dark .sy-practice-banner-copy { color: #E4D4A8; }
          .sy-maintenance-banner { position: sticky; z-index: 1901; top: 0; display: flex; align-items: flex-start; gap: 12px; width: 100%; min-height: 58px; padding: 10px clamp(16px, 3vw, 32px); border-bottom: 1px solid var(--sy-role-attention); color: #4A3200; background: var(--sy-role-attention-soft); box-shadow: 0 5px 18px rgba(83,58,12,.10); }
          .body--dark .sy-maintenance-banner { color: #FFF1C7; background: #342A18; border-bottom-color: #876A30; box-shadow: 0 7px 22px rgba(0,0,0,.28); }
          @media (max-width: 900px) { .sy-practice-banner { position: relative; align-items: flex-start; } .sy-header-title { max-width: 27vw; font-size: 15px !important; } .sy-header-tools { border-color: transparent; background: transparent; } .sy-header-tools .q-btn, .sy-icon-control, .sy-language-control { min-width: 44px !important; } }
          @keyframes sy-current-step { from { opacity: .45; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
          @media (prefers-reduced-motion: reduce) { *, *:before, *:after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; scroll-behavior: auto !important; } .q-btn:hover, .sy-sidebar .q-btn:hover, .q-expansion-item .q-item:hover, .sy-pointer-reactive:hover { transform: none !important; } .sy-pointer-light { display: none !important; } }
          .sy-chapel-compact { min-height: 0; max-width: 420px; padding: clamp(26px, 3vw, 34px); box-shadow: 0 18px 42px rgba(10,91,85,.20); }
          .sy-chapel-compact .sy-chapel-seal { top: 26px; right: 26px; width: 54px; }
          .sy-verse-compact { max-width: 100%; font-size: clamp(22px, 2vw, 30px); line-height: 1.5; padding-right: 38px; }
          .sy-reflection-compact { max-width: 100%; font-size: 13px; line-height: 1.75; }
          .sy-dashboard-verse { align-self: start; }
          .sy-verse-reflection { border-top: 1px solid rgba(255,255,255,.32); color: #F5F5F7; }
          .sy-verse-reflection .q-item { min-height: 38px; padding: 10px 0; color: #F5F5F7; font-weight: 700; }
          .sy-verse-reflection .q-expansion-item__content { color: #F5F5F7; }
          @media (min-width: 901px) and (max-width: 1500px) { .sy-service-lifeline { grid-template-columns: repeat(3, minmax(0, 1fr)); } .sy-service-lifeline:before { display: none; } .sy-service-stage { min-height: 224px; } .sy-architecture-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } .sy-capability-map { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
          @media (max-width: 900px) { .sy-main { padding: 20px 16px 36px; } .sy-chapel { min-height: 0; } .sy-chapel-seal { width: 56px; } .sy-dashboard-grid { grid-template-columns: 1fr; } .sy-dashboard-grid > * { min-width: 100% !important; } .sy-workbench { padding: 24px 20px; } .sy-workbench:after { opacity: .16; mask-image: linear-gradient(90deg, transparent 14%, black 100%); } .sy-daily-start:after { opacity: .15; mask-image: linear-gradient(90deg, transparent 16%, black 100%); } .sy-flow { grid-template-columns: 1fr; gap: 10px; } .sy-flow-step { min-height: 0; padding: 16px; } .sy-flow-symbol { width: 48px; height: 48px; font-size: 25px; } .sy-chapel-compact { max-width: none; } .sy-onboarding-intro { padding: 22px; align-items: flex-start; } .sy-onboarding-symbol { width: 70px; height: 70px; border-radius: 18px; font-size: 33px; } .sy-storage-lifecycle-grid, .sy-architecture-grid, .sy-trust-evidence-grid, .sy-handover-readiness-grid, .sy-acceptance-grid { grid-template-columns: 1fr; } .sy-service-lifeline { grid-template-columns: 1fr; gap: 10px; } .sy-service-lifeline:before { top: 20px; bottom: 20px; left: 31px; right: auto; width: 1px; height: auto; background: linear-gradient(180deg, rgba(15,118,110,.18), rgba(15,118,110,.52), rgba(168,132,73,.34)); } .sy-service-stage { min-height: 0; padding: 16px 16px 16px 58px; } .sy-service-stage-head { position: absolute; top: 14px; left: 14px; } .sy-service-stage-icon { display: none; } .sy-service-stage-title { margin-top: 0; } .sy-service-stage-result { margin-top: 12px; } .sy-architecture-hero { min-height: 0; padding: 26px 22px; } .sy-architecture-hero:before { background: var(--sy-architecture-mobile-veil), var(--sy-image-architecture) right bottom / auto 100% no-repeat; } .sy-architecture-lifeline-visual { min-height: 230px; background-position: 58% center; } .sy-architecture-layer { min-height: 0; } .sy-architecture-faq { padding: 20px 16px; } .sy-architecture-faq-answer { padding-left: 4px; } .sy-co-creation { padding: 24px 20px; padding-top: 112px; } .sy-co-creation-crest { top: 20px; left: 20px; right: auto; width: 76px; height: 73px; border-radius: 14px; } .sy-roster-desktop, .sy-prefect-directory-desktop { display: none; } .sy-roster-mobile, .sy-prefect-mobile { display: grid; gap: 18px; margin-top: 18px; } .sy-roster-mobile-notice, .sy-prefect-mobile-notice { color: var(--sy-muted); font-size: 14px; line-height: 1.55; } .sy-roster-mobile-day { display: grid; gap: 9px; } .sy-roster-mobile-day-title { color: var(--sy-ink); font-size: 18px; font-weight: 720; letter-spacing: -.01em; } .sy-roster-mobile-card, .sy-prefect-mobile-card { display: grid; gap: 12px; padding: 16px; border: 1px solid var(--sy-line); border-radius: 16px; background: var(--sy-surface); box-shadow: 0 4px 14px rgba(28,28,30,.045); } .sy-roster-mobile-post, .sy-prefect-mobile-name { color: var(--sy-ink); font-size: 16px; font-weight: 680; line-height: 1.35; } .sy-roster-mobile-time, .sy-roster-mobile-meta-label, .sy-roster-mobile-meta, .sy-prefect-mobile-class, .sy-prefect-mobile-availability, .sy-prefect-mobile-metric { color: var(--sy-muted); font-size: 14px; line-height: 1.45; } .sy-roster-mobile-prefect { color: var(--sy-ink); font-size: 20px; font-weight: 720; line-height: 1.35; overflow-wrap: anywhere; } .sy-prefect-mobile-name { font-size: 19px; font-weight: 720; overflow-wrap: anywhere; } .sy-roster-mobile-status, .sy-prefect-mobile-role { flex: 0 0 auto; padding: 4px 8px; border: 1px solid var(--sy-line); border-radius: 999px; color: var(--sy-teal); font-size: 12px; font-weight: 700; line-height: 1.2; text-align: right; } .sy-directory-selector { width: 100%; min-width: 0 !important; } .sy-directory-actions .q-btn, .sy-adjustment-actions .q-btn, .sy-acceptance-actions .q-btn { flex: 1 1 100%; min-height: 44px; } .sy-adjustment-form { gap: 12px; } .sy-adjustment-step { padding: 14px; } .sy-adjustment-form .q-field { width: 100%; } .body--dark .sy-roster-mobile-card, .body--dark .sy-prefect-mobile-card { box-shadow: none; } .body--dark .sy-roster-mobile-status, .body--dark .sy-prefect-mobile-role { color: #5EEAD4; } }
          @media (max-width: 900px) {
            .sy-platform-facts, .sy-platform-snapshot, .sy-platform-culture, .sy-platform-resources, .sy-engineering-facts, .sy-engineering-blueprint, .sy-engineering-gates, .sy-engineering-pillars, .sy-engineering-evolution, .sy-team-operating-model, .sy-capability-map, .sy-solutions-grid { grid-template-columns: 1fr; }
            .sy-platform-fact { min-height: 0; border-right: 0; border-bottom: 1px solid var(--sy-line); }
            .sy-platform-fact:last-child { border-bottom: 0; }
            .sy-platform-hero { min-height: 0; padding: 26px 22px; }
            .sy-platform-hero:before { background: var(--sy-architecture-mobile-veil), var(--sy-image-platform) 63% bottom / auto 100% no-repeat; }
            .sy-platform-metric { min-height: 0; border-right: 0; border-bottom: 1px solid var(--sy-line); }
            .sy-platform-metric:last-child { border-bottom: 0; }
            .sy-platform-value, .sy-platform-resource { min-height: 0; }
            .sy-engineering-hero { min-height: 0; padding: 26px 22px; }
            .sy-engineering-fact, .sy-engineering-evolution-item { min-height: 0; border-right: 0; border-bottom: 1px solid var(--sy-line); }
            .sy-engineering-fact:last-child, .sy-engineering-evolution-item:last-child { border-bottom: 0; }
            .sy-engineering-blueprint:before { top: 22px; bottom: 22px; left: 34px; right: auto; width: 1px; height: auto; }
            .sy-engineering-blueprint-layer { min-height: 0; padding-left: 58px; }
            .sy-engineering-blueprint-layer .sy-engineering-blueprint-index { position: absolute; top: 16px; left: 16px; }
            .sy-engineering-blueprint-layer .sy-engineering-blueprint-icon { display: none; }
            .sy-engineering-blueprint-title { margin-top: 0; }
            .sy-engineering-pillar { min-height: 0; }
            .sy-team-operating-model { padding: 18px; }
            .sy-team-operating-model:before { display: none; }
            .sy-team-role--lead { grid-column: auto; width: 100%; }
            .sy-team-role, .sy-capability-card, .sy-solution-card { min-height: 0; }
            .sy-capability-output, .sy-solution-action { margin-top: 18px; }
            .sy-feedback-channel { grid-template-columns: 1fr; }
          }
        </style>
        <script>
          // Pointer-local light is progressively attached to non-sensitive
          // contextual surfaces. Primary action colour is owned entirely by
          // semantic CSS tokens so hydration cannot flash a different colour.
          (() => {
            const pointerSurfaceSelector = [
              '.sy-flow-step:not(.sy-flow-step--pending)',
              '.sy-architecture-layer',
              '.sy-export-option',
              '.sy-onboarding-intro',
              '.sy-handover-hero',
              '.sy-co-creation',
              '.sy-trust-evidence-card',
              '.sy-platform-value',
              '.sy-platform-resource',
              '.sy-engineering-fact',
              '.sy-engineering-blueprint-layer',
              '.sy-engineering-pillar',
              '.sy-team-role',
              '.sy-capability-card',
              '.sy-solution-card',
              '.sy-storage-lifecycle'
            ].join(',');
            const enhancePointerSurface = (surface) => {
              if (surface.dataset.syPointerReady === 'true') return;
              surface.dataset.syPointerReady = 'true';
              surface.classList.add('sy-pointer-reactive');
              const light = document.createElement('span');
              light.className = 'sy-pointer-light';
              light.setAttribute('aria-hidden', 'true');
              surface.appendChild(light);
              surface.addEventListener('pointermove', (event) => {
                const bounds = surface.getBoundingClientRect();
                surface.style.setProperty('--sy-pointer-x', `${event.clientX - bounds.left}px`);
                surface.style.setProperty('--sy-pointer-y', `${event.clientY - bounds.top}px`);
              }, {passive: true});
              surface.addEventListener('pointerleave', () => {
                surface.style.setProperty('--sy-pointer-x', '50%');
                surface.style.setProperty('--sy-pointer-y', '50%');
              }, {passive: true});
            };
            const hydratePointerSurfaces = () => document.querySelectorAll(pointerSurfaceSelector).forEach(enhancePointerSurface);
            document.addEventListener('DOMContentLoaded', () => {
              hydratePointerSurfaces();
              new MutationObserver(() => {
                hydratePointerSurfaces();
              }).observe(document.body, {childList: true, subtree: true});
            });
          })();
        </script>
        """
    )
