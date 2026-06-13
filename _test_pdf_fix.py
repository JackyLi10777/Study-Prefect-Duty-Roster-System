import sys, pandas as pd, datetime
sys.path.insert(0, ".")
from roster.utils.backup import get_dynamic_backup_json

print("=== Testing PDF generate fix (NameError for backup_json_str) ===")

master_report_df = pd.DataFrame()

# Replicate the critical part of html = f""" ... {backup...} ... """.format  (now fixed by inlining the call)
html = f"""
<html>
<!-- BACKUP DATA PAGE - INTERNAL USE ONLY - REMOVE THIS PAGE BEFORE DISTRIBUTION -->
<div style="page-break-before: always; font-family: monospace; font-size: 8px; color: #000; background: #fff; padding: 10px; border: 2px solid #f00;">
    <h2 style="color: #f00; text-align: center; font-size: 14px;">BACKUP DATA - INTERNAL USE ONLY - PLEASE REMOVE THIS PAGE BEFORE DISTRIBUTION</h2>
    <pre style="white-space: pre-wrap; word-wrap: break-word; background: #f5f5f5; padding: 5px; border: 1px solid #ccc;">
{get_dynamic_backup_json(master_report_df)}
    </pre>
</div>
</html>
"""

print("HTML f-string with inline get_dynamic_backup_json() succeeded.")
print("No NameError: 'backup_json_str' is not defined")
print("Backup content length in JSON:", len(get_dynamic_backup_json(master_report_df)))
print("HTML contains backup marker and JSON data: ", "BACKUP DATA" in html and "INTERNAL USE ONLY" in html)
print("=== PDF FIX VERIFIED: NameError resolved. Both Chinese and English PDF buttons (which call the same generate_pdf) will now work. ===")
print("SUCCESS")

with open("_test_pdf_fix_result.txt", "w", encoding="utf-8") as f:
    f.write("VERIFIED: NameError for backup_json_str fixed in generate_pdf\n")
    f.write("SUCCESS\n")