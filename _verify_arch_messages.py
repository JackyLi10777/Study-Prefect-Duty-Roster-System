import ast
import sys
print("=== Architecture messages/i18n verification ===")
try:
    with open("app.py", "r", encoding="utf-8") as f:
        src = f.read()
    ast.parse(src)
    print("✅ AST parse OK")
    import app
    print("✅ import app 成功")
    from roster.ui.i18n import _t, get_text
    print("✅ i18n import OK")
    # Quick functional check (display layer only)
    print("get_text test (special):", get_text("special_unavailable_label")[:30], "...")
    print("Legacy _t test:", _t("測試", "test"))
except Exception as e:
    print("❌ Verification failed:", type(e).__name__, str(e)[:200])
    sys.exit(1)
print("=== Verification complete (zero impact on backup/core) ===")
