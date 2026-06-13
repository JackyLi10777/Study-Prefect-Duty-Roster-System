import ast, sys
print("=== Safe verification for app.py after verse container + lang tweaks ===")
try:
    with open("app.py", "r", encoding="utf-8") as f: src = f.read()
    ast.parse(src)
    print("✅ Syntax OK via ast.parse - no SyntaxError introduced")
except SyntaxError as se:
    print("❌ Syntax at", se.lineno, ":", se.msg)
    sys.exit(1)
print("Note: runtime import uses env workaround (previous 9009); static confirms clean for this display-only change.")
print("=== Verify complete ===")
