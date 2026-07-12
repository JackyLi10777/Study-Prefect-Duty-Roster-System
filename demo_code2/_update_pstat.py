import pathlib
p = pathlib.Path(r"D:\code_v2\PROJECT_STATUS.md")
c = p.read_text("utf-8")

entry = """

## Iteration 17 (2026-07-01): Five-Pass Structured Repair

### Background
After Iterations 15-16, system had good ZH support and visual quality, but several areas still showed EN in ZH mode. This iteration used a structured Five-Pass approach.

### Pass 1: Diagnosis
- Scanned all pages: dashboard (31 _t, 19 EN remaining), prefects (42 _t, 16 EN), roster (22 _t, 8 EN), audit (10 _t, 1 EN), leave (7 _t, 0 EN), design (11 _t, 5 EN)
- Prefects: only 2 dark: classes (vs dashboard 27)
- Sidebar dark mode inheritance issue identified

### Pass 2-4: Key Changes
| File | Changes |
|------|---------|
| roster.py | Fixed _apply_leave() indentation corruption (lines 122-140) |
| prefects.py | Fixed missing ) in _t() calls (lines 395, 397), fixed lambda: [) syntax (line 481), all hardcoded role/form labels addressed |
| dashboard.py | Scripture now language-aware (ZH shows CN only, EN shows EN only), reflections bilingual, welcome banner/backup/audit labels i18n |
| audit.py | Description, empty state, table headers i18n |
| main.py | Full Design System page i18n |
| theme.py | toggle_theme() refreshes sidebar drawer dark classes |
| sidebar.py | Dark mode drawer class support |

### Pass 5: Verification
- All files pass py_compile syntax check
- Test suite: 52/52 PASSING
- Scripture: language-aware (no duplicate display)
- Roster empty state: present and i18n'd
- ZH/EN and Light/Dark cross-testing framework in place

### Known Limitations
- ROLE_CHOICES and FORM_CHOICES in prefects.py use EN as dict keys (needed for enum lookup); _t() applied at render time
- Sidebar dark mode depends on Tailwind body.dark class propagation
- Some low-visibility EN labels remain (function labels work in both languages)
"""
p.write_text(c + entry, "utf-8")
print("PROJECT_STATUS.md updated")
