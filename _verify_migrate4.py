import ast, sys
print("=== Mandatory verify after final app.py migration (search caption + messages keys) ===")
try:
    with open("app.py", "r", encoding="utf-8") as f: src = f.read()
    ast.parse(src)
    print("✅ AST OK")
    import app
    print("✅ import app OK")
    from roster.ui.i18n import get_text
    print("search caption test:", get_text("showing_prefix"), "10", get_text("rows_label"))
except Exception as e:
    print("❌ ", type(e).__name__, str(e)[:200])
    sys.exit(1)
print("=== Verify complete ===")
