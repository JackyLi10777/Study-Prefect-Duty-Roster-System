import ast, sys
print("=== Mandatory verify after app.py migration (most neglected warning) ===")
try:
    with open("app.py", "r", encoding="utf-8") as f: src = f.read()
    ast.parse(src)
    print("✅ AST OK")
    import app
    print("✅ import app OK")
    from roster.ui.i18n import get_text
    print("get_text test:", get_text("most_neglected", names="Alice, Bob"))
except Exception as e:
    print("❌ ", type(e).__name__, str(e)[:200])
    sys.exit(1)
print("=== Verify complete ===")
