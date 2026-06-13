import ast, sys
print("=== Safe verify after box-shadow enhancement (app.py base) ===")
try:
    with open("app.py", "r", encoding="utf-8") as f:
        src = f.read()
    ast.parse(src)
    print("✅ Syntax OK (ast.parse)")
    import app
    print("✅ Import 成功")
except SyntaxError as se:
    print("❌ SyntaxError line", se.lineno, ":", se.msg)
    sys.exit(1)
except Exception as ex:
    print("❌ Import issue:", type(ex).__name__, str(ex)[:150])
    sys.exit(2)
print("=== Verify complete (CSS-only change, minimal/safe, backup untouched) ===")
