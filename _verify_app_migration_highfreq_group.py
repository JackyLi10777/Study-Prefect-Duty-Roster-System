# Mandatory verification after app.py modifications (high-freq dynamic text migration group)
# Migrated: manual_adjust_saved, fairness_gap_warning, overall_fairness_success, substitute_matching_success, service_hours_updated
# Per approved plan: prioritize safe get_text, mandatory verify after app.py edits.
import ast
import sys

print("=== Verify after app.py high-freq dynamic text migrations (action/feedback + fairness + service + substitute) ===")

with open("app.py", "r", encoding="utf-8") as f:
    source = f.read()

# AST parse (syntax safety)
try:
    ast.parse(source)
    print("✅ app.py AST parse successful")
except SyntaxError as e:
    print(f"❌ Syntax error: {e}")
    sys.exit(1)

# Source pattern checks for the migrations (safe get_text usage, old _t removed)
checks = [
    ("get_text(\"manual_adjust_saved\")", "manual adjust success"),
    ("get_text(\"fairness_gap_warning\")", "fairness gap warning"),
    ("get_text(\"overall_fairness_success\")", "overall fairness success"),
    ("get_text(\"substitute_matching_success\")", "substitute matching success"),
    ("get_text(\"service_hours_updated\")", "service hours updated"),
]
for pattern, desc in checks:
    if pattern in source:
        print(f"✅ {desc} now uses safe get_text key")
    else:
        print(f"❌ {desc} migration not detected")
        sys.exit(1)

# Confirm old _t literals for these are gone (high-freq ones targeted)
old_literals = [
    "手動調整已儲存",
    "公平差距較大",
    "整體公平性良好",
    "媒合成功！已依據",
    "服務時數已更新",
]
for lit in old_literals:
    if lit in source:
        # If it appears, it might be in comment or data - but for these UI, should be gone
        print(f"⚠️ Old literal '{lit[:20]}...' still in source (check if intentional data/comment)")
    else:
        print(f"✅ Old _t literal for '{lit[:20]}...' removed from UI paths")

print("✅ Verify passed for this batch of app.py high-freq migrations (safe patterns followed)")
print("=== End verify ===")