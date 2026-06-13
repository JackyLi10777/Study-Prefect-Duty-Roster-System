import ast, sys
print("=== Mandatory verify after app.py migration (trend save message) ===")
try:
    with open("app.py", "r", encoding="utf-8") as f: src = f.read()
    ast.parse(src)
    print("✅ AST parse success")
    import app
    print("✅ import app success")
    from roster.ui.i18n import get_text
    print("get_text test:", get_text("saved_trend_week", week_num=5))
except Exception as e:
    print("❌ ", type(e).__name__, str(e)[:200])
    sys.exit(1)
print("=== Verify complete (display only, no backup/core impact) ===")
