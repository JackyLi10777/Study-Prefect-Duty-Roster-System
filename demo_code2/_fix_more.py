import pathlib

# Fix prefects.py: ROLE_CHOICES and FORM_CHOICES with Chinese labels
p = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c = p.read_text("utf-8")

# Current role choices are hardcoded EN like "Study Prefect", "AHP (Asst. Head Prefect)"
# They need to show Chinese labels in Chinese mode
# BUT they''re used as dict keys to look up Role enums, so we need a different approach
# Instead of changing the dict, we should use _t() in the select options
# Let me check how role_select is used...

# Actually, looking at the code, ROLE_CHOICES is a dict {label: enum_value}
# The select uses list(ROLE_CHOICES.keys()) as options
# And ROLE_CHOICES[role_select.value] to get the enum
# So we need the keys to be translatable

# Best approach: keep ROLE_CHOICES as {key: value} but also add a translated version
# For now, add translation-aware labels as comments showing the mapping
print("prefects.py ROLE_CHOICES currently:")
idx = c.find("ROLE_CHOICES")
if idx > 0:
    print(c[idx:idx+300])

# Fix leave.py hardcoded English labels
p2 = pathlib.Path(r"D:\code_v2\app\pages\leave.py")
c2 = p2.read_text("utf-8")
# Check the state of leave.py
print("\nleave.py size:", len(c2), "chars, _t() count:", c2.count("_t("))

# Count hardcoded EN labels in leave.py
import re
en_labels = re.findall(r'"([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,4})"', c2)
excluded = {"True","False","None","Prefect","Roster","Weekday","Monday","Tuesday",
            "Wednesday","Thursday","Friday","Leave Adjustment","Prefect Name",
            "Find Assignments","STUDY_PREFECT","LEAVE_MARKER","ON LEAVE",
            "Leave Revoked","ASSISTANT_HEAD_PREFECT","HEAD_STUDY_PREFECT"}
en_labels = [l for l in en_labels if l not in excluded]
print(f"Remaining EN labels in leave.py: {en_labels[:10]}")
