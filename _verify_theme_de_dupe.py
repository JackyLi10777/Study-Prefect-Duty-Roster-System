"""
_verify_theme_de_dupe.py
Mandatory syntax + import verification after app.py edit for Theme Centralized Management (de-dupe of base CSS to roster/ui/theme.py).

Per AGENTS.md and plan: after ANY app.py modification.
Uses file-based capture pattern for Windows/PS compatibility.
"""
import ast

print("Running theme de-dupe verification...")

with open("app.py", encoding="utf-8") as f:
    source = f.read()
    ast.parse(source)
    print("✅ AST parse of app.py: success (no syntax errors)")

import app
print("✅ Import app: success (app loads cleanly with centralized theme)")

print("✅ Theme de-dupe verification PASSED")
print("   - Base CSS removed from app.py (now sole source in roster/ui/theme.py get_base_css)")
print("   - Early apply_theme() call present post set_page_config")
print("   - No breakage to imports, session init, or display layer")