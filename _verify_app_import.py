import sys
print("Python:", sys.version)
try:
    import app
    print("✅ Import 成功")
except SyntaxError as se:
    print("❌ SyntaxError at line", se.lineno, ":", se.msg)
    print("text:", se.text)
except Exception as e:
    print("❌ Import 失敗:", type(e).__name__, "-", str(e)[:400])
    import traceback
    traceback.print_exc()
