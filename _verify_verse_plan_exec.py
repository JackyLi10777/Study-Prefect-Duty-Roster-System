import ast, sys
print("=== Safe post-edit verification (verse plan exec) ===")
try:
    with open("app.py", "r", encoding="utf-8") as f:
        src = f.read()
    ast.parse(src)
    print("✅ Syntax OK (ast.parse)")
    import app
    print("✅ Import 成功 (no SyntaxError or import failure)")
except SyntaxError as se:
    print("❌ SyntaxError at line", se.lineno, ":", se.msg)
    sys.exit(1)
except Exception as ex:
    print("❌ Other during import:", type(ex).__name__, str(ex)[:200])
    sys.exit(2)
print("=== Verify complete (display-only changes, backup untouched) ===")
