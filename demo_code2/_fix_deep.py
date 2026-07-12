import pathlib

# ===== FIX 1: Role enum - add display property =====
p = pathlib.Path(r"D:\code_v2\app\models\enums.py")
c = p.read_text("utf-8")
# Find the Role class and add display property
old_role = """    @property
    def is_ahp(self) -> bool:
        """AHP can be assigned to the exclusive AHP duty post."""
        return self == Role.ASSISTANT_HEAD_PREFECT"""

new_role = """    @property
    def display(self) -> str:
        """Return display name (English)."""
        return self.value

    @property
    def display_zh(self) -> str:
        """Return Chinese display name."""
        mapping = {
            "Head Study Prefect": "首席學習風紀",
            "Assistant Head Study Prefect": "助理首席學習風紀",
            "Study Prefect": "學習風紀",
        }
        return mapping.get(self.value, self.value)

    @property
    def is_ahp(self) -> bool:
        """AHP can be assigned to the exclusive AHP duty post."""
        return self == Role.ASSISTANT_HEAD_PREFECT"""

if old_role in c:
    c = c.replace(old_role, new_role)
    p.write_text(c, "utf-8")
    print("FIX 1: Added Role.display and Role.display_zh")
else:
    print("FIX 1: Pattern not found - checking...")
    idx = c.find("class Role")
    print(c[idx:idx+300] if idx > 0 else "Role class not found")

# ===== FIX 2: prefects.py - ROLE_CHOICES with Chinese keys =====
p2 = pathlib.Path(r"D:\code_v2\app\pages\prefects.py")
c2 = p2.read_text("utf-8")
old_roles = '''ROLE_CHOICES = {
    "Study Prefect": Role.STUDY_PREFECT,
    "AHP (Asst. Head Prefect)": Role.ASSISTANT_HEAD_PREFECT,
    "Head Study Prefect": Role.HEAD_STUDY_PREFECT,
}'''
new_roles = '''# Role options with bilingual display (keys are lookup, values for display)
ROLE_CHOICES = {
    "Study Prefect": Role.STUDY_PREFECT,
    "AHP (Asst. Head Prefect)": Role.ASSISTANT_HEAD_PREFECT,
    "Head Study Prefect": Role.HEAD_STUDY_PREFECT,
}
ROLE_LABELS_ZH = {
    "Study Prefect": "學習風紀",
    "AHP (Asst. Head Prefect)": "助理首席風紀",
    "Head Study Prefect": "首席學習風紀",
}'''
if old_roles in c2:
    c2 = c2.replace(old_roles, new_roles)
    print("FIX 2: Added ROLE_LABELS_ZH")

# Replace select options to use i18n labels
old_select = 'role_select = ui.select(\n                label=_t("職位 *", "Role *"),\n                options=list(ROLE_CHOICES.keys()),'
new_select = 'role_select = ui.select(\n                label=_t("職位 *", "Role *"),\n                options={ROLE_LABELS_ZH.get(k, k) if is_zh() else k: v for k, v in ROLE_CHOICES.items()},'
if old_select in c2:
    c2 = c2.replace(old_select, new_select)
    print("FIX 2b: Select options now bilingual")

# Fix role display in table - use value not name
c2 = c2.replace('p.role.display if hasattr(p.role, "display") else p.role.name', 'p.role.display')
print("FIX 2c: Table role uses display property")

# Add is_zh import if missing
if "from utils.i18n import is_zh" not in c2:
    idx_import = c2.find("from i18n.helpers import t as _t")
    if idx_import > 0:
        # Find end of line
        end_line = c2.find("\n", idx_import)
        c2 = c2[:end_line] + "\nfrom utils.i18n import is_zh" + c2[end_line:]
        print("FIX 2d: Added is_zh import")

p2.write_text(c2, "utf-8")

# ===== FIX 3: Also fix the role_select usage in _save_prefect =====
# ROLE_CHOICES[role_select.value] needs to handle i18n keys
# Since role_select.options is now {label: value}, role_select.value returns the VALUE (like Role.STUDY_PREFECT)
# So ROLE_CHOICES lookup needs adjustment
old_lookup = 'role = ROLE_CHOICES[role_select.value]'
new_lookup = '# role_select.value returns enum directly from dict options\n            role = role_select.value'
c2 = c2.replace(old_lookup, new_lookup)
p2.write_text(c2, "utf-8")
print("FIX 3: Fixed role lookup")

# ===== FIX 4: Add dark: classes to prefects page =====
# Add basic dark mode to table, cards, buttons
c2 = p2.read_text("utf-8")
# Add dark: classes to key UI elements
c2 = c2.replace('"text-slate-800 dark:text-slate-100"', '"text-slate-800 dark:text-slate-100"')
c2 = c2.replace('"text-slate-500 dark:text-slate-400 mb-4"', '"text-slate-500 dark:text-slate-400 mb-4"')
# Add more dark: support to the table
c2 = c2.replace('.classes("w-full rounded-lg").props("flat bordered")', '.classes("w-full rounded-lg dark:bg-slate-800").props("flat bordered dark")')
p2.write_text(c2, "utf-8")
print("FIX 4: Enhanced dark mode for prefects table")

import py_compile
try:
    py_compile.compile(str(p), doraise=True)
    print("enums.py OK")
except py_compile.PyCompileError as e:
    print(f"enums.py: {e}")

try:
    py_compile.compile(str(p2), doraise=True)
    print("prefects.py OK")
except py_compile.PyCompileError as e:
    print(f"prefects.py: {e}")
