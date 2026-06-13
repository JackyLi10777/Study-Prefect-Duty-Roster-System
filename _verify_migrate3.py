import ast, sys
print("=== Mandatory verify after app.py batch migration (version, adjustment, footer, search) ===")
try:
    with open("app.py", "r", encoding="utf-8") as f: src = f.read()
    ast.parse(src)
    print("✅ AST OK")
    import app
    print("✅ import app OK")
    from roster.ui.i18n import get_text
    print("Tests:")
    print("  version:", get_text("version_loaded_success", version=3))
    print("  adjustment (sim):", get_text("adjustment_complete", action_msg="test"))
    print("  footer:", get_text("footer_caption", version="v2.3"))
except Exception as e:
    print("❌ ", type(e).__name__, str(e)[:200])
    sys.exit(1)
print("=== Verify complete (safe patterns, display-only) ===")
