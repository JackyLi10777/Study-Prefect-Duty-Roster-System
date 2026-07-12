import pathlib, re, py_compile, subprocess

def fix_line(line):
    """Fix _t().classes() on a single line"""
    # Pattern: ui.xxx(_t(...).classes(...)) -> ui.xxx(_t(...)).classes(...)
    # Strategy: find all ) .classes( that follow _t( and move the ) before .classes
    
    # Simple case: ui.xxx(_t("A","B").classes("C")) -> ui.xxx(_t("A","B")).classes("C")
    # The key signature: _t( ... ) .classes( ... ) all inside ui.xxx( ... )
    
    # Use a simple approach: find )\\.classes( after _t( and swap
    # _t("A","B").classes("C") -> _t("A","B")).classes("C"
    # This means: move ) from before .classes to after _t args
    
    fixed = re.sub(
        r'(ui\.\w+)\((_t\([^)]+)\)\.(classes|props|style|on)(\([^)]+\))\)',
        r'\1(\2).\3\4',
        line
    )
    return fixed

pages = ['app/pages/dashboard.py', 'app/pages/prefects.py', 'app/pages/roster.py',
         'app/pages/audit.py', 'app/pages/leave.py', 'app/main.py']

total_fixes = 0
for fp in pages:
    p = pathlib.Path(r'D:\code_v2') / fp
    if not p.exists():
        continue
    lines = p.read_text('utf-8').split('\n')
    fixed_lines = []
    file_changes = 0
    for i, line in enumerate(lines):
        # Check if this line has the chaining bug
        if '_t(' in line and ').' in line and 'ui.' in line:
            new_line = fix_line(line)
            if new_line != line:
                file_changes += 1
                print(f'  {fp}:{i+1} FIXED')
                print(f'    BEFORE: {line.strip()[:120]}')
                print(f'    AFTER:  {new_line.strip()[:120]}')
            fixed_lines.append(new_line)
        else:
            fixed_lines.append(line)
    
    if file_changes > 0:
        p.write_text('\n'.join(fixed_lines), 'utf-8')
        total_fixes += file_changes

print(f'\nTotal fixes: {total_fixes}')

# Syntax check
print('\nSyntax check:')
all_ok = True
for fp in pages:
    p = pathlib.Path(r'D:\code_v2') / fp
    if not p.exists():
        continue
    try:
        py_compile.compile(str(p), doraise=True)
        print(f'  OK: {fp}')
    except py_compile.PyCompileError as e:
        print(f'  FAIL: {fp} - {e}')
        all_ok = False

# Rescan
print('\nRescan for remaining bugs:')
remaining = 0
for fp in pages:
    p = pathlib.Path(r'D:\code_v2') / fp
    if not p.exists():
        continue
    c = p.read_text('utf-8')
    for i, line in enumerate(c.split('\n'), 1):
        if re.search(r'ui\.\w+\(_t\([^)]+\)\.(classes|props)\(', line):
            remaining += 1
            print(f'  REMAINING: {fp}:{i}: {line.strip()[:120]}')

if remaining == 0:
    print('  ALL CLEAN - zero chaining bugs!')

if all_ok:
    r = subprocess.run(['python','-m','pytest','tests/','-q'], capture_output=True, text=True, cwd=r'D:\code_v2')
    print(f'\nTests: {\"52/52\" if \"52 passed\" in r.stdout+r.stderr else \"FAILED\"}')
