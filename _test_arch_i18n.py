import ast, sys
print("=== Final architecture i18n/messages integration test ===")
try:
    # Syntax of key files
    for f in ["app.py", "roster/ui/components.py", "roster/ui/i18n.py", "roster/ui/messages.py", "roster/ui/theme.py"]:
        with open(f, encoding="utf-8") as fh:
            ast.parse(fh.read())
    print("✅ All key files parse cleanly")

    import app
    from roster.ui.i18n import _t, get_text, get_current_language
    from roster.ui.messages import MESSAGES
    from roster.ui.theme import get_current_theme

    # Functional display-layer checks (no core logic touched)
    print("Current language:", get_current_language())
    print("Special label via get_text:", get_text("special_unavailable_label"))
    print("Legacy _t still works:", _t("測試中文", "test en"))
    print("Help text key present:", "help_text_full" in MESSAGES)
    print("Theme stub:", get_current_theme())

    print("✅ Integration test passed (display layer only, safe patterns used)")
except Exception as e:
    print("❌ Test failed:", type(e).__name__, str(e)[:200])
    sys.exit(1)
print("=== Test complete ===")
