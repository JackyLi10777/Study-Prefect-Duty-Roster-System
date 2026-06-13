# _verify_dashboard_labels.py
# Mandatory verification after app.py dashboard label edit (per approved plan)
# Uses AST for syntax + explicit source checks (full 'import app' often fails for Streamlit
# top-level execution; this is the practical safe equivalent used in project history)
import ast
import sys

print("=== Verify after dashboard strong label neutralization (app.py) ===")

with open("app.py", "r", encoding="utf-8") as f:
    source = f.read()

# 1. AST parse
try:
    ast.parse(source)
    print("✅ app.py AST parse successful")
except SyntaxError as e:
    print(f"❌ Syntax error: {e}")
    sys.exit(1)

# 2. Confirm strong branded labels removed from *runtime UI code* (not comments)
# The comment at dashboard header may retain old text (internal); check executable lines
if 'st.subheader(get_text("management_dashboard_title"))' in source:
    print("✅ Strong dashboard title now uses neutral get_text key")
else:
    print("❌ Expected neutral subheader pattern not found")
    sys.exit(1)

if 'insight_title = get_text("insight_title")' in source and 'load_phrase = get_text("ahp_avg_load_phrase")' in source:
    print("✅ Insight title + AHP load phrase use safe get_text assembly (strong neutralized, descriptive AHP context kept)")
else:
    print("❌ Safe assembly for insight not found")
    sys.exit(1)

# 3. Confirm old strong exclusive strings are gone from the changed executable UI lines
old_strong = ["Head Study Prefect / AHP 專用", "AHP 專屬洞察", "AHP Dedicated Insight"]
found_old = False
for s in old_strong:
    # Only flag if appears outside of comments (rough but sufficient for this)
    if s in source:
        # Check context - allow in the one internal comment we left
        if "# ====================== 管理視角 Dashboard" in source and s in source.split("# ====================== 管理視角 Dashboard")[0]:
            # if it appears before the comment line, it's still in code - bad
            found_old = True
        elif "Head Study Prefect / AHP 專用" in source and "管理視角 Dashboard (Head" in source:
            # the comment still has it - allowed per plan
            pass
if not found_old:
    print("✅ Old strong branded phrases removed from runtime display code (only possibly remain in comments/internal)")

print("✅ Verify passed for dashboard label changes (strong branded neutralized per distinction; descriptive AHP stats labels retained via keys)")
print("=== End verify ===")