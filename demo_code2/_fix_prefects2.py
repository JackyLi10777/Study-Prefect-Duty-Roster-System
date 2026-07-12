import pathlib, py_compile

p = pathlib.Path(r'D:\code_v2\app\pages\prefects.py')
c = p.read_text('utf-8')

# Fix 1: Table role rendering - use .display (now exists on Role enum)
old_role = 'p.role.display if hasattr(p.role, \"display\") else p.role.name'
new_role = 'p.role.display'
c = c.replace(old_role, new_role)
print('Fix 1: table role display')

# Fix 2: Add Chinese labels dict after ROLE_CHOICES
old_rc = 'ROLE_CHOICES = {\n    \"Study Prefect\": Role.STUDY_PREFECT,\n    \"AHP (Asst. Head Prefect)\": Role.ASSISTANT_HEAD_PREFECT,\n    \"Head Study Prefect\": Role.HEAD_STUDY_PREFECT,\n}'
new_rc = '''ROLE_LABELS_ZH = {
    \"Study Prefect\": \"\u5b78\u7fd2\u98a8\u7d00\",
    \"AHP (Asst. Head Prefect)\": \"\u52a9\u7406\u9996\u5e2d\u98a8\u7d00\",
    \"Head Study Prefect\": \"\u9996\u5e2d\u5b78\u7fd2\u98a8\u7d00\",
}

ROLE_CHOICES = {
    \"Study Prefect\": Role.STUDY_PREFECT,
    \"AHP (Asst. Head Prefect)\": Role.ASSISTANT_HEAD_PREFECT,
    \"Head Study Prefect\": Role.HEAD_STUDY_PREFECT,
}'''
c = c.replace(old_rc, new_rc)
print('Fix 2: ROLE_LABELS_ZH dict')

# Fix 3: Make role select options bilingual using ROLE_LABELS_ZH
old_sel = 'options=list(ROLE_CHOICES.keys()),\n                value=\"Study Prefect\",'
new_sel = 'options={ROLE_LABELS_ZH.get(k, k) if is_zh() else k: v for k, v in ROLE_CHOICES.items()},\n                value=\"Study Prefect\",'
if old_sel in c:
    c = c.replace(old_sel, new_sel)
    print('Fix 3: role select options bilingual')
else:
    print('Fix 3: pattern not found - checking...')
    idx = c.find('role_select')
    if idx > 0:
        print(c[idx:idx+250])

# Fix 4: Add dark: classes
c = c.replace('.props(\"flat bordered\")', '.props(\"flat bordered dark\")')
c = c.replace('.classes(\"w-full rounded-lg\")', '.classes(\"w-full rounded-lg dark:bg-slate-800\")')
print('Fix 4: dark mode classes')

# Fix 5: Ensure is_zh is imported
if 'from utils.i18n import is_zh' not in c:
    # Add after existing import
    old_import = 'from i18n.helpers import t as _t\nfrom components.loading import show_skeleton'
    new_import = 'from i18n.helpers import t as _t\nfrom utils.i18n import is_zh\nfrom components.loading import show_skeleton'
    if old_import in c:
        c = c.replace(old_import, new_import)
        print('Fix 5: is_zh import added')
    else:
        print('Fix 5: import pattern not found')

p.write_text(c, 'utf-8')
try:
    py_compile.compile(str(p), doraise=True)
    print('prefects.py OK')
except py_compile.PyCompileError as e:
    print(f'prefects.py: {e}')
