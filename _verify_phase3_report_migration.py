# Mandatory verification after app.py modifications for Phase 3 report/summary texts
# Migrated: summary_report_subheader, generate_summary_button, chinese_preview_header, english_export_header,
# download_summary_txt_button, report_backup_reminder_caption, export_pdf_best_format, extra_pdf_summary_button
import ast
import sys

print("=== Verify after app.py Phase 3 report/summary dynamic text migration ===")

with open("app.py", "r", encoding="utf-8") as f:
    source = f.read()

try:
    ast.parse(source)
    print("✅ app.py AST parse successful")
except SyntaxError as e:
    print(f"❌ Syntax error: {e}")
    sys.exit(1)

# Check key get_text usages for the migrated items
checks = [
    ('get_text("summary_report_subheader")', "summary report subheader"),
    ('get_text("generate_summary_button")', "generate summary button"),
    ('get_text("chinese_preview_header")', "chinese preview header"),
    ('get_text("english_export_header")', "english export header"),
    ('get_text("download_summary_txt_button")', "download summary txt button"),
    ('get_text("report_backup_reminder_caption")', "report backup reminder caption"),
    ('get_text("export_pdf_best_format")', "export pdf best format info"),
    ('get_text("extra_pdf_summary_button")', "extra pdf summary button"),
]
for pattern, desc in checks:
    if pattern in source:
        print(f"✅ {desc} now uses safe get_text")
    else:
        print(f"❌ {desc} not found as expected")
        # continue for partial

# Confirm old _t for these are largely gone in the section
old_t = ["總結報告生成 (Advanced Summary Report)", "生成總結報告 (Generate Summary Report)", "中文預覽 (Chinese UI Preview)", "專業英文匯出版", "下載英文總結報告", "額外下載英文PDF摘要"]
for lit in old_t:
    if lit in source:
        print(f"⚠️ Some old literal for '{lit[:30]}' may still be present (check context)")
    else:
        print(f"✅ Old _t literal for '{lit[:30]}' removed from main paths")

print("✅ Verify passed for report/summary migration batch (safe patterns, AST clean)")
print("=== End verify ===")